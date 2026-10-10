import base64
import html
import io
import json
import logging
import os
import re
import uuid
import zipfile
import time
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
from supabase import create_client
import streamlit.components.v1 as components

st.set_page_config(page_title='AInoteManagement',page_icon='📚',layout='wide',initial_sidebar_state='expanded')
KINDS=['GROUP','SUBFILE','MARKDOWN','GRAPH','TABLE']
CONTAINERS=['GROUP','SUBFILE']
MAX_IMAGE=10*1024*1024
local_component=components.declare_component('ainote_local_save',path=str(Path(__file__).parent/'components'/'local_save'))

def config(key):
    try:return st.secrets.get(key) or os.getenv(key)
    except Exception:return os.getenv(key)

def client(url,key):return create_client(url,key)

url,key=config('SUPABASE_URL'),config('SUPABASE_ANON_KEY')
if not url or not key:
    st.title('📚 AInoteManagement v1.0')
    st.error('尚未設定 Supabase。請先完成 README.md 中的部署設定。')
    st.code('SUPABASE_URL = "https://...supabase.co"\nSUPABASE_ANON_KEY = "..."',language='toml')
    st.stop()
sb=client(url,key)
# Optional remembered login, scoped to this browser profile and website origin.
remember_component=components.declare_component('ainote_remember_device',path=str(Path(__file__).parent/'components'/'remember_device'))
remember_command=st.session_state.get('remember_command','read')
remember_request_id=st.session_state.get('remember_request_id','')
remember_result=remember_component(command=remember_command,request_id=remember_request_id,
    refresh_token=st.session_state.get('remember_value',''),key='remember_device_v1',default=None)
if remember_command in ('store','clear') and isinstance(remember_result,dict) and remember_result.get('request_id')==remember_request_id:
    st.session_state.remember_command='read'
    st.session_state.remember_value=''

def remember_action(command,refresh_token=''):
    st.session_state.remember_command=command
    st.session_state.remember_value=refresh_token
    st.session_state.remember_request_id=str(uuid.uuid4())

if not st.session_state.get('user_id') and not st.session_state.get('skip_auto_login'):
    stored=remember_result.get('refresh_token') if isinstance(remember_result,dict) else None
    if stored:
        try:
            session=client(url,key).auth.refresh_session(stored)
            st.session_state.update(access_token=session.session.access_token,
                refresh_token=session.session.refresh_token,user_id=session.user.id,remember_enabled=True)
            remember_action('store',session.session.refresh_token)
            st.rerun()
        except Exception:
            remember_action('clear')
            st.session_state.skip_auto_login=True
            st.rerun()

# Every database and storage call uses the logged-in user's JWT, not a service-role key.
def api():
    c=create_client(url,key)
    # Establish an authenticated session for both PostgREST and Storage.
    # Editing storage._client.headers alone does not reliably authenticate uploads.
    c.auth.set_session(st.session_state['access_token'], st.session_state['refresh_token'])
    return c

def current_user():return st.session_state.get('user_id')

def login_screen():
    st.title('📚 AInoteManagement')
    st.caption('個人 Markdown 筆記、樹狀文件與圖片管理')
    tab1,tab2=st.tabs(['登入','註冊'])
    with tab1:
        with st.form('login'):
            email=st.text_input('電子信箱',key='login_email')
            password=st.text_input('密碼',type='password',key='login_password')
            remember=st.checkbox('記住此裝置（自動登入）',value=False,key='login_remember')
            submit=st.form_submit_button('登入',width='stretch')
        if submit:
            try:
                result=sb.auth.sign_in_with_password({'email':email,'password':password})
                st.session_state.update(access_token=result.session.access_token,refresh_token=result.session.refresh_token,user_id=result.user.id,remember_enabled=remember,skip_auto_login=False)
                if remember:remember_action('store',result.session.refresh_token)
                else:remember_action('clear')
                st.rerun()
            except Exception as e:st.error('登入失敗，請確認帳號、密碼及信箱驗證狀態。')
    with tab2:
        with st.form('register'):
            email2=st.text_input('電子信箱',key='reg_email')
            password2=st.text_input('密碼（至少 8 碼）',type='password',key='reg_password')
            submit2=st.form_submit_button('建立帳號',width='stretch')
        if submit2:
            if len(password2)<8:st.error('密碼至少需要 8 碼。')
            else:
                try:sb.auth.sign_up({'email':email2,'password':password2});st.success('註冊已送出。若啟用信箱驗證，請先確認信箱。')
                except Exception:st.error('註冊失敗，請檢查資料或稍後再試。')

if not current_user():login_screen();st.stop()

# Refresh credentials before accessing data; expired tokens force re-login.
try:
    fresh=client(url,key).auth.refresh_session(st.session_state['refresh_token'])
    st.session_state.update(access_token=fresh.session.access_token,refresh_token=fresh.session.refresh_token,user_id=fresh.user.id)
    if st.session_state.get('remember_enabled') and remember_command!='store':
        remember_action('store',fresh.session.refresh_token)
except Exception:
    for k in ['access_token','refresh_token','user_id']:st.session_state.pop(k,None)
    remember_action('clear')
    st.warning('登入已逾時，請重新登入。');st.stop()

c=api()
uid=current_user()

def fetch_notes():
    return c.table('notes').select('*').eq('owner_id',uid).order('position').execute().data

def insert_note(kind,title,parent=None,content='',has_page=False,position=0):
    payload={'owner_id':uid,'parent_id':parent,'kind':kind,'title':title[:200], 'content':content,'has_page':has_page,'position':position}
    return c.table('notes').insert(payload).execute().data[0]

def update_note(nid,**values):
    values['updated_at']=datetime.now(timezone.utc).isoformat()
    result=c.table('notes').update(values).eq('id',nid).eq('owner_id',uid).select('id').execute()
    if not result.data:raise RuntimeError('資料庫未確認更新（0 筆）；請檢查 RLS 與資料是否存在')
    # A successful HTTP response is not enough: verify persisted content by reading it back.
    if 'content' in values:
        checked=c.table('notes').select('id,content').eq('id',nid).eq('owner_id',uid).limit(1).execute().data
        if not checked or checked[0].get('content')!=values['content']:
            raise RuntimeError('寫入後驗證失敗：資料庫內容與編輯器不同，請勿關閉此頁面')
    return result.data[0]

def set_deleted(nid, deleted):
    # Gracefully support databases not yet migrated to deleted_at.
    ids=list(subtree(nid,notes))
    now=datetime.now(timezone.utc).isoformat()
    for note_id in ids:
        payload={'is_deleted':deleted,'deleted_at':now if deleted else None}
        try:
            result=c.table('notes').update(payload).eq('id',note_id).eq('owner_id',uid).select('id').execute()
        except Exception as exc:
            # PGRST204 means the deployed schema lacks deleted_at; fall back to is_deleted.
            if 'PGRST204' not in str(exc) or 'deleted_at' not in str(exc):
                raise
            result=c.table('notes').update({'is_deleted':deleted}).eq('id',note_id).eq('owner_id',uid).select('id').execute()
        if not result.data:
            raise RuntimeError('更新失敗：請確認 notes UPDATE/SELECT RLS 與 GRANT 權限')

def delete_note(nid):
    set_deleted(nid,True)

def restore_note(nid):
    set_deleted(nid,False)

def clone_note(nid,dest):
    original=subtree(nid,notes)
    if len(original)>200:raise ValueError('一次最多複製 200 個節點')
    pending={n['id']:n for n in notes if n['id'] in original}
    mapping={}
    while pending:
        progressed=False
        for old,n in list(pending.items()):
            if old!=nid and n['parent_id'] not in mapping:continue
            parent=dest if old==nid else mapping[n['parent_id']]
            copied=insert_note(n['kind'],n['title']+' - Copy' if old==nid else n['title'],parent,n['content'],n['has_page'],n['position'])
            mapping[old]=copied['id'];del pending[old];progressed=True
        if not progressed:raise ValueError('文件結構錯誤')
    return mapping[nid]


def get_ancestors(nid,byid):
    seen=set();result=[]
    while nid and nid in byid and nid not in seen:
        seen.add(nid);result.append(nid);nid=byid[nid]['parent_id']
    return result

def subtree(nid,allnotes):
    ids={nid};changed=True
    while changed:
        before=len(ids)
        ids.update(n['id'] for n in allnotes if n['parent_id'] in ids)
        changed=len(ids)>before
    return ids

def image_bytes(raw):
    if len(raw)>MAX_IMAGE:raise ValueError('圖片不得超過 10MB')
    im=Image.open(io.BytesIO(raw));im.verify()
    im=Image.open(io.BytesIO(raw))
    if im.width*im.height>25_000_000:raise ValueError('圖片像素過大')
    im=ImageOps.exif_transpose(im)
    if getattr(im,'is_animated',False):
        if im.format!='GIF':raise ValueError('不支援此動畫格式')
        return raw,'image/gif','gif'
    im.thumbnail((2400,2400))
    if im.mode not in ('RGB','RGBA'):im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
    buf=io.BytesIO();im.save(buf,format='WEBP',quality=85,method=5)
    return buf.getvalue(),'image/webp','webp'

def upload_image(raw,note_id):
    data,mime,ext=image_bytes(raw)
    path=f'{uid}/{uuid.uuid4().hex}.{ext}'
    try:
        c.storage.from_('note-images').upload(path,data,{'content-type':mime,'upsert':'false'})
    except Exception:
        logging.getLogger(__name__).exception('Storage upload failed (bucket=note-images, uid_prefix=%s)', str(uid)[:8])
        raise
    try:
        asset=c.table('assets').insert({'owner_id':uid,'note_id':note_id,'storage_path':path,'mime_type':mime}).execute().data[0]
    except Exception:
        c.storage.from_('note-images').remove([path]);raise
    return asset['id']

def asset_url(asset_id,assets):
    # Kept for export and compatibility. Supabase signedURL may be relative.
    a=assets.get(asset_id)
    if not a:return None
    try:
        signed=c.storage.from_('note-images').create_signed_url(a['storage_path'],3600)
        path=signed.get('signedURL') or signed.get('signedUrl') or signed.get('signed_url')
        if not path:return None
        if path.startswith('http://') or path.startswith('https://'):return path
        from urllib.parse import urljoin
        return urljoin(url.rstrip('/')+'/',path.lstrip('/'))
    except Exception:
        logging.getLogger(__name__).exception('Failed to sign image URL')
        return None

def asset_image(asset_id,assets):
    # Download with authenticated Supabase client; st.image(bytes) avoids
    # relative signed URLs, expiring links, and browser-side Storage requests.
    a=assets.get(asset_id)
    if not a:return None
    path=a.get('storage_path')
    if not path:return None
    cache=st.session_state.setdefault('_asset_image_cache',{})
    cache_key=str(uid)+':'+str(path)
    hit=cache.get(cache_key)
    if hit and time.monotonic()-hit[0]<300:return hit[1]
    try:
        raw=c.storage.from_('note-images').download(path)
        if not isinstance(raw,bytes):raw=bytes(raw)
        # Limit memory consumption for long browsing sessions.
        if len(cache)>24:cache.clear()
        cache[cache_key]=(time.monotonic(),raw)
        return raw
    except Exception:
        logging.getLogger(__name__).exception('Image download failed: %s',path)
        return None

def signed_markdown(content,assets):
    # Signed URLs are generated only for assets owned by the logged-in user.
    def replace(match):
        alt,asset_id=match.group(1),match.group(2)
        url=asset_url(asset_id,assets)
        return f'![{alt}]({url})' if url else f'**[圖片無法讀取：{alt}]**'
    return re.sub(r'!\[([^\]]*)\]\(asset://([0-9a-fA-F-]{36})\)',replace,content or '')

# Table metadata is stored in the Markdown itself, so no database migration is needed.
TABLE_DEFAULT_WIDTH=120
TABLE_DEFAULT_HEIGHT=40
TABLE_WIDTH_RANGE=(60,600)
TABLE_HEIGHT_RANGE=(28,240)
def table_dimensions(content):
    match=re.search(r'<!--\s*ainote-cell:(\d+)x(\d+)\s*-->',content or '')
    if match:
        w,h=map(int,match.groups())
        return (max(TABLE_WIDTH_RANGE[0],min(w,TABLE_WIDTH_RANGE[1])),
                max(TABLE_HEIGHT_RANGE[0],min(h,TABLE_HEIGHT_RANGE[1])))
    # Compatibility with tables created before v1.9.
    old=re.search(r'<!--\s*ainote-table-size:(small|medium|large)\s*-->',content or '')
    widths={'small':70,'medium':105,'large':145}
    return (widths.get(old.group(1),TABLE_DEFAULT_WIDTH) if old else TABLE_DEFAULT_WIDTH,TABLE_DEFAULT_HEIGHT)
def keep_table_dimensions(content,width,height):
    width,height=int(width),int(height)
    if not (TABLE_WIDTH_RANGE[0]<=width<=TABLE_WIDTH_RANGE[1] and TABLE_HEIGHT_RANGE[0]<=height<=TABLE_HEIGHT_RANGE[1]):
        raise ValueError('格子寬高超出允許範圍')
    body=re.sub(r'<!--\s*ainote-(?:cell:\d+x\d+|table-size:(?:small|medium|large))\s*-->\s*','',content or '')
    return f'<!-- ainote-cell:{width}x{height} -->\n'+body

def table_with_dimensions(rows,cols,width,height):
    return keep_table_dimensions(table_markdown(rows,cols),width,height)

def render_table(content):
    frame=markdown_dataframe(content)
    if not len(frame.columns):return
    width,height=table_dimensions(content)
    table_id='ainote-table-'+uuid.uuid4().hex
    head=''.join('<th>'+html.escape(str(c))+'</th>' for c in frame.columns)
    body=''.join('<tr>'+''.join('<td>'+html.escape(str(v) if pd.notna(v) else '')+'</td>' for v in row)+'</tr>' for row in frame.itertuples(index=False,name=None))
    # Fixed pixel widths for all columns, including headers; scrolling on phones.
    cols=len(frame.columns)
    css=f"""<style>
    #{table_id}{{max-width:100%;width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}}
    #{table_id} table{{table-layout:fixed;border-collapse:collapse;width:{cols*width}px;min-width:{cols*width}px;max-width:none}}
    #{table_id} th,#{table_id} td{{box-sizing:border-box;width:{width}px;min-width:{width}px;max-width:{width}px;height:{height}px;min-height:{height}px;padding:4px 7px;border:1px solid #687080;vertical-align:middle;overflow-wrap:anywhere;white-space:normal;text-align:left;font-size:13px}}
    </style>"""
    st.markdown(css+f'<div id="{table_id}"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',unsafe_allow_html=True)

def table_markdown(rows,cols):
    if not (1<=rows<=50 and 1<=cols<=30):raise ValueError('表格尺寸必須為 1–50 列、1–30 欄')
    return dataframe_markdown(pd.DataFrame('',index=range(rows),columns=[f'欄位 {i+1}' for i in range(cols)]))

def dataframe_markdown(frame):
    def esc(v):
        return str(v if pd.notna(v) else '').replace('|', r'\|').replace('\n','<br>').strip()
    cols=[esc(v) for v in frame.columns]
    header='| '+' | '.join(cols)+' |'
    separator='| '+' | '.join('---' for _ in cols)+' |'
    lines=['| '+' | '.join(esc(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)]
    return '\n'.join([header,separator,*lines])

def markdown_dataframe(markdown):
    lines=[line.strip() for line in (markdown or '').splitlines() if line.strip().startswith('|')]
    if len(lines)<2:return pd.DataFrame([['']*3 for _ in range(3)],columns=['欄位 1','欄位 2','欄位 3'])
    def parse(line):
        return [cell.strip().replace(r'\|','|').replace('<br>','\n') for cell in re.split(r'(?<!\\)\|',line.strip().strip('|'))]
    cols=parse(lines[0])
    if not cols:return pd.DataFrame()
    data=[]
    for line in lines[2:]:
        row=parse(line)
        data.append((row+['']*len(cols))[:len(cols)])
    return pd.DataFrame(data,columns=cols,dtype=str)

def image_editor(note,assets,uid_key):
    if st.session_state.pop('image_saved_'+uid_key,False):st.success('圖片已成功儲存至 Supabase。')
    matches=list(re.finditer(r'!\[([^\]]*)\]\(asset://([0-9a-fA-F-]{36})\)',note.get('content') or ''))
    if matches:
        visible=st.toggle('顯示圖片 · '+note['title'],value=True,key='show_graph_'+uid_key)
        if visible:
            for match in matches:
                raw=asset_image(match.group(2),assets)
                if raw:st.image(raw,caption=match.group(1),width='stretch')
                else:st.warning('圖片無法載入：請檢查 Storage 與 assets 權限')
    upload=st.file_uploader('選擇或拖曳圖片',type=['png','jpg','jpeg','webp','gif'],key='upload_'+uid_key)
    paste=components.declare_component('paste_image',path=str(Path(__file__).parent/'components'/'paste_widget'))
    pasted=paste(key='paste_'+uid_key,default=None)
    if isinstance(pasted,dict) and pasted.get('data'):
        st.session_state['_paste_buffer_'+uid_key]=pasted
    incoming=upload.getvalue() if upload else None
    name=upload.name if upload else '貼上的圖片'
    pasted=st.session_state.get('_paste_buffer_'+uid_key)
    if incoming is None and isinstance(pasted,dict) and pasted.get('data'):
        try:
            incoming=base64.b64decode(pasted['data'].split(',',1)[1],validate=True)
            name=pasted.get('name') or name
        except Exception:st.warning('剪貼簿圖片格式無效')
    if st.button('儲存圖片',key='save_image_'+uid_key,disabled=not bool(incoming)):
        try:
            asset_id=upload_image(incoming,note['id'])
            clean=name.replace(']','').replace('\n',' ')
            old=note.get('content') or ''
            update_note(note['id'],content=(old+'\n' if old.strip() else '')+f'![{clean}](asset://{asset_id})')
            st.session_state['image_saved_'+uid_key]=True
            st.session_state.pop('_paste_buffer_'+uid_key,None)
            st.rerun()
        except Exception as exc:
            logging.getLogger(__name__).exception('Image save failed')
            st.error('圖片儲存失敗：'+type(exc).__name__)

def table_editor(note,uid_key):
    original=markdown_dataframe(note.get('content') or '')
    if original.empty and not len(original.columns):original=pd.DataFrame([['']*3 for _ in range(3)],columns=['欄位 1','欄位 2','欄位 3'])
    edited=st.data_editor(original,hide_index=True,width='stretch',num_rows='dynamic',key='sheet_'+uid_key)
    if st.button('儲存表格',key='save_table_'+uid_key):
        try:
            update_note(note['id'],content=keep_table_dimensions(dataframe_markdown(edited),*table_dimensions(note.get('content'))))
            st.success('表格已儲存')
            st.rerun()
        except Exception as exc:
            logging.getLogger(__name__).exception('Table save failed')
            st.error('表格儲存失敗：'+type(exc).__name__)

def show_markdown(content,assets):
    # Resolve private asset identifiers without embedding unsafe HTML.
    parts=re.split(r'(!\[[^\]]*\]\(asset://[0-9a-fA-F-]{36}\))',content)
    for part in parts:
        match=re.fullmatch(r'!\[([^\]]*)\]\(asset://([0-9a-fA-F-]{36})\)',part)
        if match:
            raw=asset_image(match.group(2),assets)
            if raw:st.image(raw,caption=match.group(1) or None,width='content')
            else:st.warning('圖片不存在或無法存取')
        elif part:st.markdown(part)

def export_group(root,notes,overrides=None):
    overrides=overrides or {}
    ids=subtree(root['id'],notes)
    selected=[n for n in notes if n['id'] in ids]
    assets=c.table('assets').select('*').eq('owner_id',uid).execute().data
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps({'format':'ainote','version':1,'root_id':root['id'],'name':root['title']},ensure_ascii=False,indent=2))
        z.writestr('structure.json',json.dumps([{**n,'content':overrides.get(n['id'],n.get('content') or '')} for n in selected],ensure_ascii=False,indent=2))
        for n in selected:z.writestr('documents/'+n['id']+'.md',overrides.get(n['id'],n.get('content') or ''))
        for a in assets:
            if a.get('note_id') in ids:
                try:z.writestr('assets/'+a['id']+Path(a['storage_path']).suffix,c.storage.from_('note-images').download(a['storage_path']))
                except Exception:pass
    return mem.getvalue()

def import_group(raw):
    if len(raw)>50*1024*1024:raise ValueError('封裝檔案太大')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist()
        if len(infos)>2000 or sum(i.file_size for i in infos)>150*1024*1024:raise ValueError('解壓內容超過限制')
        names={i.filename for i in infos}
        if 'manifest.json' not in names or 'structure.json' not in names:raise ValueError('不是有效的 ainote 封裝')
        manifest=json.loads(z.read('manifest.json'))
        source=json.loads(z.read('structure.json'))
        if manifest.get('format')!='ainote' or manifest.get('version')!=1 or not isinstance(source,list):raise ValueError('封裝格式不相容')
        if len(source)>1000:raise ValueError('文件數量超過限制')
        rootid=manifest['root_id'];old={n['id']:n for n in source}
        if rootid not in old or old[rootid]['kind']!='GROUP':raise ValueError('根節點無效')
        # Parent-before-child traversal; malformed cycles and disconnected nodes are rejected.
        mapping={};remaining=dict(old)
        while remaining:
            progress=False
            for oid,n in list(remaining.items()):
                p=n.get('parent_id')
                if oid!=rootid and p not in mapping:continue
                if n.get('kind') not in KINDS:raise ValueError('文件類型無效')
                if oid==rootid and p is not None:raise ValueError('根節點錯誤')
                created=insert_note(n['kind'],str(n.get('title','未命名'))[:200],mapping.get(p),str(n.get('content',''))[:500000],bool(n.get('has_page')),int(n.get('position',0)))
                mapping[oid]=created['id'];del remaining[oid];progress=True
            if not progress:raise ValueError('樹狀結構存在循環或遺失父節點')
        # Rehydrate referenced images and remap asset IDs.
        remap={}
        for filename in names:
            if not filename.startswith('assets/') or filename.endswith('/') or '..' in Path(filename).parts:continue
            oldasset=Path(filename).stem
            if not re.fullmatch(r'[0-9a-fA-F-]{36}',oldasset):continue
            image=z.read(filename)
            try:remap[oldasset]=upload_image(image,mapping[rootid])
            except Exception:continue
        for oid,n in old.items():
            content=str(n.get('content',''))
            for oldasset,newasset in remap.items():content=content.replace('asset://'+oldasset,'asset://'+newasset)
            if content!=n.get('content',''):update_note(mapping[oid],content=content)
        return mapping[rootid]

st.markdown('''<style>
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"]{max-width:100%;overflow-x:hidden!important}
[data-testid="stMain"], [data-testid="stMainBlockContainer"], .block-container{min-width:0!important;max-width:100%!important;box-sizing:border-box!important}
.block-container{padding:1.25rem clamp(.75rem,3vw,2rem) 3rem!important}
[data-testid="stHorizontalBlock"]{min-width:0!important;max-width:100%!important;flex-wrap:wrap!important}
[data-testid="column"]{min-width:0!important;max-width:100%!important}
[data-testid="stSidebar"]{width:min(310px,85vw)!important;min-width:0!important}
[data-testid="stSidebar"] iframe{width:100%!important;max-width:100%!important}
[data-testid="stSidebarContent"]{overflow-x:hidden!important}
[data-testid="stTextArea"] textarea{width:100%!important;max-width:100%!important;box-sizing:border-box!important}
.stButton button{border-radius:8px}
</style>''',unsafe_allow_html=True)

try:
    notes=fetch_notes()
except Exception as exc:
    logging.getLogger(__name__).exception('Database read failed')
    st.error('無法讀取資料庫。請開啟 Streamlit Cloud → Manage app → Logs 檢查詳細原因。')
    st.code(f'Error type: {type(exc).__name__}')
    st.stop()
byid={n['id']:n for n in notes}
active_notes=[n for n in notes if not n.get('is_deleted')]
roots=[n for n in active_notes if n['kind']=='GROUP' and not n['parent_id']]
if st.session_state.get('selected') not in {n['id'] for n in active_notes}:st.session_state['selected']=roots[0]['id'] if roots else None
selected=byid.get(st.session_state['selected'])

with st.sidebar:
    st.title('📚 AI Note')
    with st.popover('☰ 功能選單',width='stretch'):
        st.caption('建立組別')
        newgroup=st.text_input('組別名稱',key='newgroup')
        if st.button('＋ 創建新組別',width='stretch'):
            if newgroup.strip():
                try:r=insert_note('GROUP',newgroup.strip(),has_page=False);st.session_state.selected=r['id'];st.rerun()
                except Exception:st.error('建立失敗')
        uploaded=st.file_uploader('開啟本地組別 (.ainote / .zip)',type=['ainote','zip'],key='import')
        if uploaded and st.button('匯入組別'):
            try:st.session_state.selected=import_group(uploaded.getvalue());st.rerun()
            except Exception as e:st.error(f'匯入失敗：{e}')
        if selected:
            rootid=get_ancestors(selected['id'],byid)[-1]
            root=byid[rootid]
            if root['kind']=='GROUP':
                try:st.download_button('↓ 下載當前組別',data=export_group(root,notes),file_name='AInote_'+root['id']+'.ainote',mime='application/zip',width='stretch')
                except Exception:st.warning('暫時無法匯出')
        st.caption('本地儲存路徑由瀏覽器下載設定決定；雲端網頁不能直接設定任意本地磁碟路徑。')
    st.divider()
    st.subheader('EXPLORER')
    st.caption('右鍵操作 · 拖曳移動 · F2 · Delete')
    explorer=components.declare_component('ainote_explorer',path=str(Path(__file__).parent/'components'/'explorer'))
    payload=[{'id':n['id'],'parent_id':n['parent_id'],'kind':n['kind'],'title':n['title'],'position':n['position']} for n in active_notes]
    event=explorer(nodes=payload,selected=st.session_state.get('selected'),key='explorer_v11',default=None,height=385)
    if event and event.get('event_id')!=st.session_state.get('last_explorer_event'):
        st.session_state.last_explorer_event=event.get('event_id')
        action=event.get('action');nid=event.get('id');target=event.get('target')
        try:
            if action=='select' and nid in byid:
                st.session_state.selected=nid
                tabs=st.session_state.setdefault('open_tabs',[])
                if nid not in tabs:tabs.append(nid)
            elif action=='quick_nav' and nid in byid:
                st.session_state.quick_nav_root=nid
                st.session_state.selected=nid
            elif action=='rename' and nid in byid:
                title=str(event.get('title','')).strip()
                if title:update_note(nid,title=title[:200])
            elif action=='create':
                kind=event.get('kind');title=str(event.get('title','')).strip()
                parent=target if target in byid and byid[target]['kind'] in CONTAINERS else None
                if kind=='GROUP':parent=None
                if kind=='TABLE' and parent and title:
                    st.session_state.pending_table={'title':title,'parent':parent}
                    st.session_state.selected=parent
                    st.rerun()
                if kind in KINDS and title and (kind=='GROUP' or parent):
                    new=insert_note(kind,title,parent,has_page=kind=='SUBFILE',position=len([x for x in active_notes if x['parent_id']==parent]))
                    st.session_state.selected=new['id']
            elif action in ('move','paste') and nid in byid:
                source=byid[nid];dest=target if target in byid and byid[target]['kind'] in CONTAINERS else None
                if dest and source['kind']!='GROUP' and dest not in subtree(nid,notes) and get_ancestors(dest,byid)[-1]==get_ancestors(nid,byid)[-1]:
                    if action=='move' or event.get('cut'):
                        update_note(nid,parent_id=dest,position=len([x for x in active_notes if x['parent_id']==dest]))
                    else:clone_note(nid,dest)
            elif action=='delete' and nid in byid:delete_note(nid)
            elif action=='restore' and nid in byid:restore_note(nid)
            elif action=='reorder' and nid in byid and target in byid:
                a,b=byid[nid],byid[target]
                if a['parent_id']==b['parent_id']:
                    siblings=sorted([n for n in active_notes if n['parent_id']==a['parent_id']],key=lambda n:(n['position'],n['created_at']))
                    ids=[n['id'] for n in siblings if n['id']!=nid];ids.insert(ids.index(target),nid)
                    for i,ident in enumerate(ids):update_note(ident,position=i)
            st.rerun()
        except Exception as exc:
            logging.getLogger(__name__).exception('Explorer action failed')
            st.error(f'檔案操作失敗：{type(exc).__name__}。請至 Manage app → Logs 查看詳情。')
    pending=st.session_state.get('pending_table')
    if pending:
        st.markdown('**建立表格：'+pending['title']+'**')
        with st.form('sidebar_table_setup',clear_on_submit=False):
            m=st.number_input('M：資料列數',min_value=1,max_value=50,value=3,key='sidebar_rows')
            n=st.number_input('N：欄數',min_value=1,max_value=30,value=3,key='sidebar_cols')
            w=st.number_input('X：格子寬度（px）',min_value=60,max_value=600,value=TABLE_DEFAULT_WIDTH,key='sidebar_cell_w')
            h=st.number_input('Y：格子高度（px）',min_value=28,max_value=240,value=TABLE_DEFAULT_HEIGHT,key='sidebar_cell_h')
            ok=st.form_submit_button('確認建立表格',type='primary')
        if ok:
            try:
                created=insert_note('TABLE',pending['title'],pending['parent'],content=table_with_dimensions(m,n,w,h))
                st.session_state.selected=created['id']
                st.session_state.pop('pending_table',None)
                st.session_state['creation_notice']='已建立表格：'+created['title']
                st.rerun()
            except Exception as exc:
                logging.getLogger(__name__).exception('Create table failed')
                st.error('建立表格失敗：'+type(exc).__name__+'：'+str(exc))
        if st.button('取消建立',key='cancel_sidebar_table'):
            st.session_state.pop('pending_table',None)
            st.rerun()
    if st.session_state.get('creation_notice'):
        st.success(st.session_state.pop('creation_notice'))
    nav_root=st.session_state.get('quick_nav_root')
    if nav_root in byid:
        with st.expander('☰ 快速定位',expanded=True):
            root=byid[nav_root]
            if root['kind'] not in CONTAINERS:root=byid.get(root.get('parent_id'),root)
            def nav_children(node,depth=0,visited=None):
                visited=set() if visited is None else visited
                if node['id'] in visited:return []
                visited.add(node['id'])
                result=[(node,depth)]
                for child in sorted([n for n in active_notes if n.get('parent_id')==node['id']],key=lambda n:(n.get('position',0),n.get('title',''))):
                    if child['kind'] in CONTAINERS:result+=nav_children(child,depth+1,visited)
                    else:result.append((child,depth+1))
                return result
            targets=nav_children(root)
            for node,depth in targets:
                label=('　'*min(depth,7))+node['title']
                if st.session_state.get('workspace_mode')=='瀏覽模式':
                    anchor='ainote-'+re.sub(r'[^a-zA-Z0-9-]','',str(node['id']))
                    st.markdown(f'<a href="#{anchor}">{html.escape(label)}</a>',unsafe_allow_html=True)
                    continue
                if st.button(label,key='nav_'+root['id']+'_'+node['id'],width='stretch'):
                    st.session_state.selected=node['id']
                    st.session_state['nav_target']=node['id']
                    st.rerun()
            if st.button('關閉快速定位',key='close_quick_nav'):
                st.session_state.pop('quick_nav_root',None);st.rerun()
    with st.expander('資源回收區'):
        deleted_roots=[n for n in notes if n.get('is_deleted') and (not n['parent_id'] or not byid.get(n['parent_id'],{}).get('is_deleted'))]
        for n in deleted_roots:
            cc=st.columns([3,1]);cc[0].caption(n['title'])
            if cc[1].button('還原',key='restore_'+n['id']):
                try:restore_note(n['id']);st.rerun()
                except Exception as exc:
                    logging.getLogger(__name__).exception('Restore failed')
                    st.error('還原失敗：'+type(exc).__name__)
    with st.expander('帳號設定 · 預設儲存路徑'):
        st.caption('在支援的瀏覽器選擇本機資料夾，之後優先寫入該資料夾。瀏覽器可能要求重新授權；手機或不支援的瀏覽器改用下載。')
        local_component(mode='settings',key='local_save_settings_v1',default=None)
    with st.expander('帳號設定 · 永久註銷'):
        st.warning('此操作不可復原：永久刪除帳號、筆記、資料夾、圖片與附件。請先下載 .ainote 備份。')
        st.caption('為安全起見，需要再次輸入密碼並透過已部署的 Supabase Edge Function 執行。')
        with st.form('delete_account_form'):
            confirm_text=st.text_input('輸入「永久刪除帳號」',key='delete_account_confirm')
            confirm_password=st.text_input('再次輸入登入密碼',type='password',key='delete_account_password')
            confirm_check=st.checkbox('我了解此操作不可復原',key='delete_account_ack')
            delete_submit=st.form_submit_button('永久註銷帳號',type='primary')
        if delete_submit:
            if confirm_text!='永久刪除帳號' or not confirm_password or not confirm_check:
                st.error('請完成所有確認欄位。')
            else:
                import requests
                try:
                    response=requests.post(
                        url.rstrip('/')+'/functions/v1/delete-account',
                        headers={'Authorization':'Bearer '+st.session_state['access_token'],
                                 'apikey':key,'Content-Type':'application/json'},
                        json={'password':confirm_password},timeout=45)
                    if response.ok:
                        for session_key in ['user_id','access_token','refresh_token','selected','open_tabs']:
                            st.session_state.pop(session_key,None)
                        remember_action('clear')
                        st.session_state.skip_auto_login=True
                        st.success('帳號已永久註銷，請重新整理頁面。')
                        st.stop()
                    else:
                        logging.getLogger(__name__).warning('Account deletion failed: HTTP %s',response.status_code)
                        try:
                            error_code=response.json().get('error','delete_failed')
                        except Exception:
                            error_code='delete_failed'
                        st.error('註銷未完成：'+str(error_code)+'。請檢查 Edge Function Logs。')
                except requests.RequestException:
                    logging.getLogger(__name__).exception('Account deletion request failed')
                    st.error('註銷請求失敗，請檢查網路及 Edge Function 部署狀態。')
    st.divider()
    if st.button('登出',width='stretch'):
        for k in ['user_id','access_token','refresh_token','selected','remember_enabled']:st.session_state.pop(k,None)
        st.session_state.skip_auto_login=True
        remember_action('clear')
        st.rerun()

if not selected:
    st.title('歡迎使用 AInoteManagement')
    st.info('請在左側「功能選單」建立第一個組別，或匯入 .ainote 檔案。')
    st.stop()

# The GROUP is the browsing unit. Editing remains at the selected workspace level.
group=selected
while group.get('parent_id') and group['kind']!='GROUP':
    group=byid.get(group['parent_id'],group)
    if group['kind']=='GROUP':break
workspace=selected if selected['kind'] in CONTAINERS else byid.get(selected.get('parent_id'),selected)
workspace_id=workspace['id']
workspace_blocks=sorted(
    [n for n in active_notes if n.get('parent_id')==workspace_id and n['kind'] not in CONTAINERS],
    key=lambda n:(n.get('position',0),n.get('created_at',''))
)
assets={}
# Load asset metadata only if the group/workspace contains image references.
needs_assets=any('asset://' in (n.get('content') or '') for n in active_notes if n['kind']=='GRAPH')
if needs_assets:
    try:
        assets={a['id']:a for a in c.table('assets').select('id,storage_path,mime_type,note_id').eq('owner_id',uid).execute().data}
    except Exception:
        logging.getLogger(__name__).exception('Asset list failed')

mode=st.radio('工作模式',['瀏覽模式','編輯模式'],horizontal=True,key='workspace_mode')
report_key='save_report_'+workspace_id
report=st.session_state.get(report_key)
if report:
    if report.get('local_status'):
        st.info('本地備份優先：'+('已寫入選定資料夾' if report['local_status']=='folder' else '已觸發瀏覽器下載（請確認下載完成）'))
    if not report['failures']:
        st.success(f"已儲存並驗證：{report['successes']}/{report['total']} 個區塊。{report['saved_at']}")
        if report.get('names'):st.caption('已儲存：'+'、'.join(report['names']))
    else:
        st.error(f"儲存失敗：成功 {report['successes']}/{report['total']}，失敗 {len(report['failures'])}。")
        for note_id,code,detail in report['failures']:
            st.warning(f"區塊 {note_id}：{code}：{detail[:400]}")
    if st.button('關閉存檔報告',key='dismiss_report_'+workspace_id):
        st.session_state.pop(report_key,None)
        st.rerun()
if mode=='瀏覽模式':
    st.title(group['title'])
    nav_target=st.session_state.get('nav_target')
    if nav_target in byid and nav_target!=group['id']:
        st.info('定位：'+byid[nav_target]['title'])
    # Build one stable table of contents for the whole group, preserving Explorer order.
    def ordered_children(parent_id):
        return sorted([n for n in active_notes if n.get('parent_id')==parent_id],
            key=lambda n:(n.get('position',0),n.get('created_at') or ''))
    sections=[]
    def collect_sections(node,depth=0,seen=None):
        seen=set() if seen is None else seen
        if node['id'] in seen:return
        seen.add(node['id'])
        sections.append((node,depth))
        if node['kind'] in CONTAINERS:
            for child in ordered_children(node['id']):collect_sections(child,depth+1,seen)
    collect_sections(group)
    # Anchor IDs are derived only from UUIDs, never from untrusted titles.
    def section_anchor(note):return 'ainote-'+re.sub(r'[^a-zA-Z0-9-]','',str(note['id']))
    toc=[(node,depth) for node,depth in sections if node['kind'] in CONTAINERS]
    st.markdown('<a id="'+section_anchor(group)+'"></a>',unsafe_allow_html=True)
    for node,depth in sections:
        if node['kind'] in CONTAINERS:
            if node['id']!=group['id']:
                st.markdown('<a id="'+section_anchor(node)+'"></a>',unsafe_allow_html=True)
                st.markdown('#'*min(depth+1,6)+' '+node['title'])
            if (node.get('content') or '').strip():show_markdown(node['content'],assets)
        else:
            st.markdown('<a id="'+section_anchor(node)+'"></a>',unsafe_allow_html=True)
            if node['kind'] in ('GRAPH','TABLE') and node.get('title'):
                st.caption(('🖼️ ' if node['kind']=='GRAPH' else '▦ ')+node['title'])
            if node['kind']=='TABLE':render_table(node.get('content') or '')
            elif (node.get('content') or '').strip():show_markdown(node['content'],assets)
else:
    st.title(workspace['title'])
    # GROUP/SUBFILE are structural folders; content lives in child documents only.
    draft_keys=[]
    for block in workspace_blocks:
        st.markdown('#### '+('🖼️ ' if block['kind']=='GRAPH' else '▦ ' if block['kind']=='TABLE' else '📄 ')+block['title'])
        if block['kind']=='GRAPH':
            image_editor(block,assets,block['id'])
        elif block['kind']=='TABLE':
            # Render the grid without a separate save button; global save collects all grids.
            original=markdown_dataframe(block.get('content') or '')
            if original.empty and not len(original.columns):
                original=pd.DataFrame([['']*3 for _ in range(3)],columns=['欄位 1','欄位 2','欄位 3'])
            sheet_key='sheet_'+block['id']
            edited_frame=st.data_editor(original,hide_index=True,width='stretch',num_rows='fixed',key=sheet_key)
            st.session_state['_editor_result_'+sheet_key]=edited_frame.copy(deep=True)
            cell_w,cell_h=table_dimensions(block.get('content') or '')
            if st.button('💾 儲存表格：'+block['title'],key='save_table_inline_'+block['id']):
                try:
                    new_content=keep_table_dimensions(dataframe_markdown(edited_frame),cell_w,cell_h)
                    update_note(block['id'],content=new_content)
                    st.session_state[report_key]={'successes':1,'total':1,'failures':[],
                        'names':[block['title']],'saved_at':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                    st.rerun()
                except Exception as exc:
                    logging.getLogger(__name__).exception('Table save failed')
                    st.error('表格儲存失敗：'+type(exc).__name__+'：'+str(exc))
            draft_keys.append((block['id'],sheet_key,'table'))
        else:
            text_key='block_content_'+block['id']
            st.text_area('Markdown：'+block['title'],value=block.get('content') or '',
                height=190,key=text_key,label_visibility='collapsed')
            if st.button('💾 儲存文件：'+block['title'],key='save_text_inline_'+block['id']):
                try:
                    update_note(block['id'],content=st.session_state[text_key])
                    st.session_state[report_key]={'successes':1,'total':1,'failures':[],
                        'names':[block['title']],'saved_at':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                    st.rerun()
                except Exception as exc:
                    logging.getLogger(__name__).exception('Text save failed')
                    st.error('文件儲存失敗：'+type(exc).__name__+'：'+str(exc))
            draft_keys.append((block['id'],text_key,'text'))
    # Local-first save: browser writes the .ainote file before the server updates Supabase.
    draft_values={}
    for note_id,field_key,field_type in draft_keys:
        if field_type=='table':
            frame=st.session_state.get('_editor_result_'+field_key)
            if frame is not None:
                draft_values[note_id]=keep_table_dimensions(dataframe_markdown(frame),*table_dimensions(byid[note_id].get('content') or ''))
        else:
            draft_values[note_id]=st.session_state.get(field_key,byid[note_id].get('content') or '')
    # The backup includes the current unsaved editor drafts and all assets in the group.
    try:
        local_zip=export_group(group,active_notes,draft_values)
        local_b64=base64.b64encode(local_zip).decode('ascii')
        backup_error=None
    except Exception as exc:
        local_b64=''
        backup_error=str(exc)
    if backup_error:st.error('無法準備本地備份，已停止雲端儲存：'+backup_error)
    local_event=local_component(mode='save',data=local_b64,
        filename='AInote_'+re.sub(r'[^\w\-]+','_',group['title'])+'_'+datetime.now().strftime('%Y%m%d')+'.ainote',
        disabled=bool(backup_error) or not bool(draft_keys),key='local_save_action_'+workspace_id,default=None)
    if isinstance(local_event,dict) and local_event.get('action')=='saved':
        token=local_event.get('token')
        if token and token!=st.session_state.get('last_local_save_'+workspace_id):
            st.session_state['last_local_save_'+workspace_id]=token
            successes=[];failures=[]
            for note_id,field_key,field_type in draft_keys:
                note_name=byid.get(note_id,{}).get('title',note_id)
                try:
                    if note_id not in draft_values:raise ValueError('無法取得編輯器資料')
                    update_note(note_id,content=draft_values[note_id])
                    successes.append(note_name)
                except Exception as exc:
                    logging.getLogger(__name__).exception('Save failed: %s (%s)',note_name,note_id)
                    failures.append((note_name,type(exc).__name__,str(exc)))
            st.session_state[report_key]={
                'successes':len(successes),'total':len(draft_keys),'failures':failures,
                'names':successes,'saved_at':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'local_status':local_event.get('method','download')}
            st.rerun()
    elif isinstance(local_event,dict) and local_event.get('action')=='error':
        st.error('本地儲存失敗，未執行雲端儲存：'+str(local_event.get('message','')))
    t1,t2,t3=st.tabs(['🖼️ 圖片','▦ 表格','📄 Markdown'])
    with t1:
        if st.button('新增圖片區塊',key='new_graph_'+workspace_id):
            try:
                created=insert_note('GRAPH','新圖片',workspace_id,position=len(workspace_blocks))
                st.session_state.selected=created['id']
                st.rerun()
            except Exception as exc:
                logging.getLogger(__name__).exception('Create image block failed')
                st.error('新增失敗：'+type(exc).__name__)
    with t2:
        with st.form('new_table_'+workspace_id):
            table_name=st.text_input('表格名稱',value='新表格')
            col_m,col_n=st.columns(2)
            m=col_m.number_input('M：資料列數',min_value=1,max_value=50,value=3,step=1)
            n=col_n.number_input('N：欄數',min_value=1,max_value=30,value=3,step=1)
            col_w,col_h=st.columns(2)
            w=col_w.number_input('X：格子寬度（px）',min_value=60,max_value=600,value=TABLE_DEFAULT_WIDTH,step=5)
            h=col_h.number_input('Y：格子高度（px）',min_value=28,max_value=240,value=TABLE_DEFAULT_HEIGHT,step=5)
            create_table=st.form_submit_button('確認建立表格',type='primary')
        if create_table:
            try:
                created=insert_note('TABLE',table_name.strip() or '新表格',workspace_id,
                    content=table_with_dimensions(m,n,w,h),position=len(workspace_blocks))
                st.session_state.selected=created['id']
                st.session_state['creation_notice']='已建立表格：'+created['title']
                st.rerun()
            except Exception as exc:
                logging.getLogger(__name__).exception('Create table failed')
                st.error('新增表格失敗：'+type(exc).__name__+'：'+str(exc))
    with t3:
        text_name=st.text_input('區塊名稱',value='新段落',key='text_name_'+workspace_id)
        if st.button('新增 Markdown 區塊',key='insert_text_'+workspace_id):
            try:
                created=insert_note('MARKDOWN',text_name.strip() or '新段落',workspace_id,
                    position=len(workspace_blocks))
                st.session_state.selected=created['id']
                st.rerun()
            except Exception as exc:
                logging.getLogger(__name__).exception('Create Markdown block failed')
                st.error('新增失敗：'+type(exc).__name__)
st.divider()
st.caption('AInoteManagement v2.1 · 組別瀏覽 · 工作區儲存 · 圖片貼上 · Excel 式表格')
