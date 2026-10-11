import ast
import calendar
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
from collections import defaultdict
from datetime import datetime, timezone, date, time as dt_time, timedelta
from pathlib import Path
import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
from supabase import create_client
from matrix_engine import calculate
import streamlit.components.v1 as components

st.set_page_config(page_title='BV-Text',page_icon='📚',layout='wide',initial_sidebar_state='expanded')
KINDS=['GROUP','SUBFILE','MARKDOWN','GRAPH','TABLE','HANDWRITE']
CONTAINERS=['GROUP','SUBFILE']
MAX_IMAGE=10*1024*1024
local_component=components.declare_component('ainote_local_save',path=str(Path(__file__).parent/'components'/'local_save'))
matrix_component=components.declare_component('ainote_matrix_table',path=str(Path(__file__).parent/'components'/'matrix_table'))
paste_component=components.declare_component('paste_image',path=str(Path(__file__).parent/'components'/'paste_widget'))

def config(key):
    try:return st.secrets.get(key) or os.getenv(key)
    except Exception:return os.getenv(key)

def client(url,key):return create_client(url,key)

url,key=config('SUPABASE_URL'),config('SUPABASE_ANON_KEY')
if not url or not key:
    st.title('📚 BV-Text')
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
                refresh_token=session.session.refresh_token,user_id=session.user.id,remember_enabled=True,auth_refresh_after=time.time()+2400)
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
    st.title('📚 BV-Text')
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
                st.session_state.update(access_token=result.session.access_token,refresh_token=result.session.refresh_token,user_id=result.user.id,remember_enabled=remember,skip_auto_login=False,auth_refresh_after=time.time()+2400)
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

# Avoid rotating refresh tokens on every Streamlit rerun. A short-lived network
# error must not delete the browser's remembered login.
try:
    if time.time() >= st.session_state.get('auth_refresh_after',0):
        fresh=client(url,key).auth.refresh_session(st.session_state['refresh_token'])
        st.session_state.update(access_token=fresh.session.access_token,refresh_token=fresh.session.refresh_token,user_id=fresh.user.id,
            auth_refresh_after=time.time()+2400)
        if st.session_state.get('remember_enabled'):
            remember_action('store',fresh.session.refresh_token)
except Exception as exc:
    logging.getLogger(__name__).warning('Token refresh failed: %s',exc)
    # Keep the token and allow normal requests to determine whether login expired.
    st.session_state.auth_refresh_after=time.time()+60

c=api()
uid=current_user()

def fetch_notes():
    return c.table('notes').select('*').eq('owner_id',uid).order('position').execute().data

def insert_note(kind,title,parent=None,content='',has_page=False,position=0):
    payload={'owner_id':uid,'parent_id':parent,'kind':kind,'title':title[:200], 'content':content,'has_page':has_page,'position':position}
    result=c.table('notes').insert(payload).execute().data
    if not result:raise RuntimeError('建立失敗：資料庫未回傳新文件')
    return result[0]

def create_blocks_batch(kind, title, parent, count, content=''):
    """Create 1–20 independent blocks; roll back created rows if any insert fails."""
    count=int(count)
    if kind not in ('GRAPH','HANDWRITE') or not 1 <= count <= 20:
        raise ValueError('僅支援一次建立 1–20 份圖片或手寫稿')
    existing=c.table('notes').select('position').eq('owner_id',uid).eq('parent_id',parent).eq('is_deleted',False).execute().data or []
    next_position=max((int(x.get('position') or 0) for x in existing),default=-1)+1
    progress=operation_progress('批次建立'+('手寫稿' if kind=='HANDWRITE' else '圖片'))
    created=[]
    try:
        for i in range(count):
            name=title if count==1 else f'{title} {i+1:02d}'
            created.append(insert_note(kind,name,parent,content=content,position=next_position+i))
            progress(int((i+1)*95/count),f'已建立 {i+1}/{count}')
        progress(100,'全部建立完成')
        return created
    except Exception as exc:
        if created:
            ids=[x['id'] for x in created]
            try:
                c.table('notes').delete().eq('owner_id',uid).in_('id',ids).execute()
            except Exception as rollback_exc:
                raise RuntimeError(f'批次建立失敗，且清理部分資料失敗（{len(ids)} 份）；請檢查 Explorer：{rollback_exc}') from exc
        raise

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

def operation_progress(label):
    bar=st.progress(0,text=label+'：準備中')
    def update(pct,step):bar.progress(min(100,max(0,int(pct))),text=label+'：'+step)
    return update

def set_deleted(nid, deleted):
    # Gracefully support databases not yet migrated to deleted_at.
    ids=list(subtree(nid,notes))
    now=datetime.now(timezone.utc).isoformat()
    update_progress=operation_progress('批次'+('刪除' if deleted else '還原'))
    for i,note_id in enumerate(ids):
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
        update_progress((i+1)*100/max(len(ids),1),f'已處理 {i+1}/{len(ids)}')

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
            copied=insert_note('SUBFILE' if old==nid and n['kind']=='GROUP' else n['kind'],n['title']+' - Copy' if old==nid else n['title'],parent,n['content'],bool(n['has_page']) or bool(old==nid and n['kind']=='GROUP'),n['position'])
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
    im=Image.open(io.BytesIO(raw))
    if im.width*im.height>25_000_000:raise ValueError('圖片像素過大')
    im=ImageOps.exif_transpose(im)
    if getattr(im,'is_animated',False):
        if im.format!='GIF':raise ValueError('不支援此動畫格式')
        return raw,'image/gif','gif'
    im.load()
    im.thumbnail((2400,2400))
    if im.mode not in ('RGB','RGBA'):im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
    buf=io.BytesIO();im.save(buf,format='WEBP',quality=82,method=3)
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

def table_alignment(content):
    match=re.search(r'<!--\s*ainote-align:(left|center|right)\s*-->',content or '')
    return match.group(1) if match else 'left'
def with_table_alignment(content,alignment):
    if alignment not in ('left','center','right'):raise ValueError('對齊方式無效')
    return re.sub(r'<!--\s*ainote-align:(?:left|center|right)\s*-->\s*','',content or '').rstrip()+f'\n<!-- ainote-align:{alignment} -->'

def table_with_dimensions(rows,cols,width,height):
    return keep_table_dimensions(table_markdown(rows,cols),width,height)

def render_table(content):
    frame=markdown_dataframe(content)
    if not len(frame.columns):return
    width,height=table_dimensions(content)
    table_id='ainote-table-'+uuid.uuid4().hex
    alignment=table_alignment(content)
    body=''.join('<tr>'+''.join('<td title="('+str(r)+'*'+str(c)+')">'+html.escape(str(v) if pd.notna(v) else '')+'</td>' for c,v in enumerate(row))+'</tr>' for r,row in enumerate(frame.itertuples(index=False,name=None)))
    # Fixed pixel widths for all columns, including headers; scrolling on phones.
    cols=len(frame.columns)
    css=f"""<style>
    #{table_id}{{max-width:100%;width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}}
    #{table_id} table{{table-layout:fixed;border-collapse:collapse;width:{cols*width}px;min-width:{cols*width}px;max-width:none}}
    #{table_id} td{{box-sizing:border-box;width:{width}px;min-width:{width}px;max-width:{width}px;height:{height}px;min-height:{height}px;padding:4px 7px;border:1px solid #687080;vertical-align:middle;overflow-wrap:anywhere;white-space:normal;text-align:{alignment};font-size:13px}}
    </style>"""
    st.markdown(css+f'<div id="{table_id}"><table><tbody>{body}</tbody></table></div>',unsafe_allow_html=True)

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
    if st.session_state.pop('image_saved_'+uid_key,False):
        st.success('圖片已寫入 Storage，並已驗證資料庫引用。')
    matches=list(re.finditer(r'!\[([^\]]*)\]\(asset://([0-9a-fA-F-]{36})\)',note.get('content') or ''))
    if matches:
        visible=st.toggle('顯示圖片 · '+note['title'],value=True,key='show_graph_'+uid_key)
        if visible:
            for match in matches:
                raw=asset_url(match.group(2),assets)
                if raw:st.image(raw,caption=match.group(1),width='stretch')
                else:st.warning('圖片無法載入：請檢查 Storage 與 assets 權限')
    upload=st.file_uploader('一次選擇多張照片（最多 20 張）',type=['png','jpg','jpeg','webp','gif'],accept_multiple_files=True,key='upload_'+uid_key)
    pasted=paste_component(key='paste_'+uid_key,default=None)
    buffer_key='_paste_buffer_'+uid_key
    if isinstance(pasted,dict) and pasted.get('data'):
        nonce=str(pasted.get('nonce',''))
        if nonce!=st.session_state.get('_paste_seen_'+uid_key):
            try:
                raw=base64.b64decode(pasted['data'].split(',',1)[-1],validate=True)
                if not raw or len(raw)>MAX_IMAGE:raise ValueError('圖片為空或超過 10 MB')
                st.session_state[buffer_key]={'raw':raw,'name':pasted.get('name') or '貼上的圖片','nonce':nonce}
                st.session_state['_paste_seen_'+uid_key]=nonce
            except Exception as exc:
                st.error('貼上圖片無法解析：'+str(exc))
    saved_buffer=st.session_state.get(buffer_key)
    incoming=[(x.name,x.getvalue()) for x in upload] if upload else ([(saved_buffer.get('name','貼上的圖片'),saved_buffer['raw'])] if saved_buffer else [])
    if incoming:st.caption(f'待儲存：{len(incoming)} 張照片（同一圖片組件）')
    if st.button('儲存全部圖片',key='save_image_'+uid_key,disabled=not bool(incoming)):
        progress=st.progress(0,text='準備圖片資料…')
        try:
            if len(incoming)>20:raise ValueError('一次最多 20 張照片')
            # All uploaded photos are appended to this single GRAPH note.
            old=note.get('content') or ''
            refs=[]
            for idx,(name,raw) in enumerate(incoming):
                if not raw:raise ValueError(f'第 {idx+1} 張圖片是空的')
                aid=upload_image(raw,note['id'])
                refs.append(f'![{str(name).replace(chr(93),"").replace(chr(10)," ")}](asset://{aid})')
                progress.progress(int((idx+1)*85/len(incoming)),text=f'已上傳 {idx+1}/{len(incoming)}')
            new=(old+'\n' if old.strip() else '')+'\n'.join(refs)
            update_note(note['id'],content=new)
            progress.progress(100,text='全部圖片已上傳並驗證引用')
            st.session_state['image_saved_'+uid_key]=True
            st.session_state.pop(buffer_key,None)
            st.session_state.pop('_asset_image_cache',None)
            st.rerun()
        except Exception as exc:
            logging.getLogger(__name__).exception('Image save failed')
            st.error('圖片儲存未完成：'+str(exc)+'；已上傳的附件可能需要清理。')

def handwriting_dimensions(content):
    match=re.search(r'<!--\s*handwriting-size:(\d+)x(\d+)\s*-->',content)
    return (int(match.group(1)),int(match.group(2))) if match else (1200,680)

@st.dialog('建立手寫稿 · 紙張大小')
def handwriting_creation_dialog():
    pending=st.session_state.get('pending_handwrite')
    if not pending:return
    with st.form('handwriting_dimensions_form'):
        title=st.text_input('手寫稿名稱',value=pending['title'])
        m=st.number_input('紙張寬度 m（像素）',min_value=200,max_value=6000,value=1200,step=100)
        n=st.number_input('紙張高度 n（像素）',min_value=200,max_value=6000,value=680,step=100)
        count=st.number_input('建立份數（1–20）',min_value=1,max_value=20,value=1,step=1,key='handwrite_batch_count')
        ok=st.form_submit_button('建立手寫稿',type='primary')
    if ok:
        try:
            op=operation_progress('建立手寫稿');op(25,'檢查紙張尺寸')
            created=[insert_note('HANDWRITE',title.strip() or '新手寫稿',pending['parent'],content=f'<!-- handwriting-size:{m}x{n} --><!-- handwriting-pages:{count} -->',position=len(children_index.get(pending['parent'],[])))]
            op(100,'建立完成')
            st.session_state.pop('pending_handwrite',None)
            st.session_state.selected=created[0]['id'];st.rerun()
        except Exception as exc:st.error('建立失敗：'+str(exc))

handwriting_component=components.declare_component('ainote_handwriting',path=str(Path(__file__).parent/'components'/'handwriting'))
def handwriting_editor(note,assets):
    content=note.get('content') or ''
    dims=handwriting_dimensions(content)
    match=re.search(r'<!--\s*handwriting-pages:(\d+)\s*-->',content)
    count=max(1,min(20,int(match.group(1)))) if match else 1
    page=st.selectbox('手寫稿頁面',list(range(1,count+1)),format_func=lambda n:f'第 {n} / {count} 頁',key='hw_page_'+note['id']) if count>1 else 1
    # One HANDWRITE database component contains independent image snapshots per page.
    refs=dict((int(n),aid) for n,aid in re.findall(r'!\[手寫稿-(\d+)\]\(asset://([0-9a-fA-F-]{36})\)',content))
    legacy=re.search(r'!\[手寫稿\]\(asset://([0-9a-fA-F-]{36})\)',content)
    if legacy and 1 not in refs:refs[1]=legacy.group(1)
    aid=refs.get(page)
    initial_image=asset_url(aid,assets) if aid else None
    locked_key='hw_locked_'+note['id']
    pending_key='_hw_lock_pending_'+note['id']
    if st.session_state.pop(pending_key,False):
        st.session_state[locked_key]=True
    if locked_key not in st.session_state:st.session_state[locked_key]=bool(refs)
    locked=st.checkbox('屏蔽觸控（防止誤觸；取消勾選可繼續編輯）',key=locked_key)
    event=handwriting_component(key=f'handwrite_{note["id"]}_{page}',width_px=dims[0],height_px=dims[1],image_url=initial_image,locked=locked,default=None,height=510)
    seen_key=f'_hw_seen_{note["id"]}_{page}'
    if isinstance(event,dict) and event.get('action')=='save' and event.get('nonce')!=st.session_state.get(seen_key):
        st.session_state[seen_key]=event['nonce']
        progress=operation_progress('儲存手寫稿')
        try:
            progress(10,'解析畫布')
            raw=base64.b64decode(event['data'].split(',',1)[-1],validate=True)
            progress(30,'上傳畫布至 Storage')
            new_id=upload_image(raw,note['id'])
            progress(70,'寫入手寫稿引用')
            new=re.sub(r'!\[手寫稿-'+str(page)+r'\]\(asset://[0-9a-fA-F-]{36}\)', '',content).strip()
            if page==1:new=re.sub(r'!\[手寫稿\]\(asset://[0-9a-fA-F-]{36}\)', '',new).strip()
            new=(new+'\n' if new else '')+f'![手寫稿-{page}](asset://{new_id})'
            update_note(note['id'],content=new)
            progress(100,'完成並驗證')
            st.session_state[pending_key]=True
            st.session_state['_hw_notice_'+note['id']]=True
            st.rerun()
        except Exception as exc:st.error('手寫稿儲存失敗：'+str(exc))
    if st.session_state.pop('_hw_notice_'+note['id'],False):st.success('手寫稿已儲存並進入屏蔽觸控狀態')

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
            raw=asset_url(match.group(2),assets)
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

def import_group(raw, parent=None):
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
                created=insert_note('SUBFILE' if oid==rootid and parent else n['kind'],str(n.get('title','未命名'))[:200],parent if oid==rootid and parent else mapping.get(p),str(n.get('content',''))[:500000],bool(n.get('has_page')) or bool(oid==rootid and parent),int(n.get('position',0)))
                mapping[oid]=created['id'];del remaining[oid];progress=True
            if not progress:raise ValueError('樹狀結構存在循環或遺失父節點')
        # Rehydrate referenced images and remap asset IDs.
        remap={}
        for filename in names:
            if not filename.startswith('assets/') or filename.endswith('/') or '..' in Path(filename).parts:continue
            oldasset=Path(filename).stem
            if not re.fullmatch(r'[0-9a-fA-F-]{36}',oldasset):continue
            image=z.read(filename)
            try:
                linked=next((mapping[oid] for oid,n in old.items() if 'asset://'+oldasset in str(n.get('content',''))),mapping[rootid])
                remap[oldasset]=upload_image(image,linked)
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
    with st.status('正在讀取工作區…',expanded=False) as load_status:
        notes=fetch_notes()
        load_status.update(label='工作區讀取完成',state='complete')
except Exception as exc:
    logging.getLogger(__name__).exception('Database read failed')
    st.error('無法讀取資料庫。請開啟 Streamlit Cloud → Manage app → Logs 檢查詳細原因。')
    st.code(f'Error type: {type(exc).__name__}')
    st.stop()
byid={n['id']:n for n in notes}
active_notes=[n for n in notes if not n.get('is_deleted')]
children_index=defaultdict(list)
for _node in active_notes:children_index[_node.get('parent_id')].append(_node)
for _siblings in children_index.values():_siblings.sort(key=lambda x:(x.get('position',0),x.get('created_at') or ''))
roots=[n for n in active_notes if n['kind']=='GROUP' and not n['parent_id']]
if st.session_state.get('selected') not in {n['id'] for n in active_notes}:st.session_state['selected']=roots[0]['id'] if roots else None
selected=byid.get(st.session_state['selected'])

@st.dialog('建立表格',width='small')
def table_creation_dialog():
    pending=st.session_state.get('pending_table')
    if not pending:return
    with st.form('table_creation_dialog_form'):
        title=st.text_input('表格名稱',value=pending.get('title') or '新表格')
        left,right=st.columns(2)
        m=left.number_input('資料列數 M',min_value=1,max_value=50,value=3,step=1)
        n=right.number_input('欄數 N',min_value=1,max_value=30,value=3,step=1)
        left,right=st.columns(2)
        w=left.number_input('格寬 X（px）',min_value=60,max_value=600,value=TABLE_DEFAULT_WIDTH)
        h=right.number_input('格高 Y（px）',min_value=28,max_value=240,value=TABLE_DEFAULT_HEIGHT)
        ok=st.form_submit_button('確認建立',type='primary')
    if ok:
        try:
            op=operation_progress('建立表格');op(20,'驗證尺寸')
            created=insert_note('TABLE',title.strip() or '新表格',pending['parent'],content=table_with_dimensions(m,n,w,h),position=len(children_index.get(pending['parent'],[])))
            op(100,'資料庫建立完成')
            st.session_state.pop('pending_table',None)
            st.session_state.selected=created['id']
            st.rerun()
        except Exception as exc:st.error('建立表格失敗：'+str(exc))
    if st.button('取消',key='cancel_table_modal'):
        st.session_state.pop('pending_table',None)
        st.rerun()

@st.dialog('導入本地文件做為子文件',width='large')
def import_child_dialog():
        if st.session_state.get('import_child_target'):
            import_target=st.session_state.import_child_target
            if import_target not in byid or byid[import_target]['kind'] not in CONTAINERS:
                st.session_state.pop('import_child_target',None)
            else:
                st.markdown('**導入本地文件做為子文件**')
                st.caption('目標：'+byid[import_target]['title']+'｜支援 .md、.txt、.ainote 與符合格式的 .zip')
                local_files=st.file_uploader('選擇本地文件（可多選）',type=['md','markdown','txt','ainote','zip'],accept_multiple_files=True,key='import_child_files')
                a,b=st.columns(2)
                with a:
                    if st.button('確認導入',key='confirm_import_child',width='stretch'):
                        if not local_files:st.warning('請先選擇文件')
                        else:
                            try:
                                if len(local_files)>20:raise ValueError('每次最多導入 20 份文件')
                                op=operation_progress('導入子文件')
                                created=[]
                                for i,file in enumerate(local_files):
                                    data=file.getvalue()
                                    if len(data)>50*1024*1024:raise ValueError(file.name+' 超過大小限制')
                                    ext=Path(file.name).suffix.lower()
                                    if ext in ('.ainote','.zip'):
                                        new_id=import_group(data,parent=import_target)
                                    else:
                                        try:content=data.decode('utf-8-sig')
                                        except UnicodeDecodeError:raise ValueError(file.name+' 不是 UTF-8 文字檔')
                                        if len(content)>500000:raise ValueError(file.name+' 內容過長')
                                        new_id=insert_note('SUBFILE',Path(file.name).stem,import_target,has_page=True)['id']
                                        insert_note('MARKDOWN',Path(file.name).name,new_id,content=content)
                                    created.append(new_id)
                                    op(int(100*(i+1)/len(local_files)),f'已導入 {i+1}/{len(local_files)}')
                                st.session_state.selected=created[-1]
                                st.session_state.pop('import_child_target',None)
                                st.session_state['operation_notice']=f'成功導入 {len(created)} 份子文件'
                                st.rerun()
                            except Exception as exc:st.error('導入失敗：'+str(exc)+'。先前成功導入的文件仍保留，請檢查 Explorer。')
                with b:
                    if st.button('取消導入',key='cancel_import_child',width='stretch'):
                        st.session_state.pop('import_child_target',None)
                        st.rerun()

@st.dialog('快速定位',width='large')
def quick_navigation_dialog():
    nav_root=st.session_state.get('quick_nav_root')
    if nav_root not in byid:
        st.session_state.pop('quick_nav_root',None)
        return
    root=byid[nav_root]
    if root['kind'] not in CONTAINERS:root=byid.get(root.get('parent_id'),root)
    def nav_children(node,depth=0,visited=None):
        visited=set() if visited is None else visited
        if node['id'] in visited:return []
        visited.add(node['id'])
        result=[(node,depth)]
        for child in sorted(children_index.get(node['id'],[]),key=lambda n:(n.get('position',0),n.get('title',''))):
            if child['kind'] in CONTAINERS:result+=nav_children(child,depth+1,visited)
            else:result.append((child,depth+1))
        return result
    targets=nav_children(root)
    options={node['id']:('　'*min(depth,7))+node['title'] for node,depth in targets}
    with st.form('quick_navigation_form'):
        choice=st.selectbox('選擇要定位的文件',list(options),format_func=lambda x:options[x])
        left,right=st.columns(2)
        confirm=left.form_submit_button('定位',type='primary',width='stretch')
        cancel=right.form_submit_button('取消',width='stretch')
    if confirm:
        st.session_state.selected=choice
        st.session_state['nav_target']=choice
        st.session_state['nav_focus']=choice
        st.session_state['main_page']='📝 筆記工作區'
        st.session_state.pop('quick_nav_root',None)
        st.rerun()
    if cancel:
        st.session_state.pop('quick_nav_root',None)
        st.rerun()

def download_filename(title):
    name=re.sub(r'[\\\\/:*?"<>|\\x00-\\x1f]+','_',str(title or '')).strip(' .')
    return (name[:150] or '未命名')+'.'+st.session_state.get('download_format','ainote')

with st.sidebar:
    st.title('📚 BV-Text')
    with st.popover('☰ 功能選單',width='stretch'):
        st.caption('建立組別')
        newgroup=st.text_input('組別名稱',key='newgroup')
        if st.button('＋ 創建新組別',width='stretch'):
            if newgroup.strip():
                try:
                    progress=operation_progress('建立組別');progress(30,'送出新增請求')
                    r=insert_note('GROUP',newgroup.strip(),has_page=False)
                    progress(100,'建立完成')
                    st.session_state['creation_notice']='已建立組別：'+r['title']
                    st.session_state.selected=r['id'];st.rerun()
                except Exception as exc:st.error('建立失敗：'+str(exc))
        uploaded=st.file_uploader('開啟本地組別 (.ainote / .zip)',type=['ainote','zip'],key='import')
        if uploaded and st.button('匯入組別'):
            try:st.session_state.selected=import_group(uploaded.getvalue());st.rerun()
            except Exception as e:st.error(f'匯入失敗：{e}')
        if selected:
            rootid=get_ancestors(selected['id'],byid)[-1]
            root=byid[rootid]
            if root['kind']=='GROUP':
                try:st.download_button('↓ 下載當前組別',data=export_group(root,notes),file_name=download_filename(root['title']),mime='application/zip',width='stretch')
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
            op_progress=operation_progress('檔案操作') if action not in ('select','quick_nav','import_child') else None
            if op_progress:op_progress(15,'正在處理 '+str(action))
            if action=='select' and nid in byid:
                st.session_state.selected=nid
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
                if kind=='HANDWRITE' and parent and title:
                    st.session_state.pending_handwrite={'title':title,'parent':parent}
                    st.session_state.selected=parent
                    st.rerun()
                if kind=='TABLE' and parent and title:
                    st.session_state.pending_table={'title':title,'parent':parent}
                    st.session_state.selected=parent
                    st.rerun()
                if kind in KINDS and title and (kind=='GROUP' or parent):
                    new=insert_note(kind,title,parent,has_page=kind=='SUBFILE',position=len([x for x in active_notes if x['parent_id']==parent]))
                    st.session_state.selected=new['id']
            elif action in ('move','paste','copy'):
                if nid not in byid:raise ValueError('來源文件不存在或已被刪除')
                source=byid[nid]
                dest=target if target in byid and byid[target]['kind'] in CONTAINERS else None
                if not dest:raise ValueError('請選擇目標組別或子文件')
                if action=='move' or (action=='paste' and event.get('cut')):
                    if dest in subtree(nid,notes):raise ValueError('不能移入自己或自己的子節點')
                    if source['kind']!='GROUP' and get_ancestors(dest,byid)[-1]!=get_ancestors(nid,byid)[-1]:raise ValueError('一般文件移動僅限同一組別；跨組別請使用複製')
                    if source['parent_id']!=dest:
                        update_note(nid,parent_id=dest,kind='SUBFILE' if source['kind']=='GROUP' else source['kind'],has_page=True if source['kind']=='GROUP' else source['has_page'],position=len([x for x in active_notes if x['parent_id']==dest]))
                    st.session_state.selected=nid
                else:
                    copied_id=clone_note(nid,dest)
                    st.session_state.selected=copied_id
            elif action=='import_child':
                if target not in byid or byid[target]['kind'] not in CONTAINERS:raise ValueError('請選擇組別或子文件')
                st.session_state.import_child_target=target
            elif action=='delete' and nid in byid:delete_note(nid)
            elif action=='restore' and nid in byid:restore_note(nid)
            elif action=='reorder' and nid in byid and target in byid:
                a,b=byid[nid],byid[target]
                if a['parent_id']==b['parent_id']:
                    siblings=sorted([n for n in active_notes if n['parent_id']==a['parent_id']],key=lambda n:(n['position'],n['created_at']))
                    ids=[n['id'] for n in siblings if n['id']!=nid];ids.insert(ids.index(target),nid)
                    for i,ident in enumerate(ids):update_note(ident,position=i)
            if op_progress:
                op_progress(100,'操作完成')
                st.session_state['operation_notice']='操作完成：'+str(action)
            st.rerun()
        except Exception as exc:
            logging.getLogger(__name__).exception('Explorer action failed')
            st.error(f'檔案操作失敗：{type(exc).__name__}。請至 Manage app → Logs 查看詳情。')

            st.rerun()
    if st.session_state.get('creation_notice'):
        st.success(st.session_state.pop('creation_notice'))
    if st.session_state.get('operation_notice'):
        st.success(st.session_state.pop('operation_notice'))
    page_choice=st.radio('頁面', ['📝 筆記工作區','📅 行程表','⚙️ 設定'],key='main_page',horizontal=True)
    st.divider()
    if st.button('登出',width='stretch'):
        for k in ['user_id','access_token','refresh_token','selected','remember_enabled']:st.session_state.pop(k,None)
        st.session_state.skip_auto_login=True
        remember_action('clear')
        st.rerun()

if st.session_state.get('import_child_target'):
    import_child_dialog()
elif st.session_state.get('quick_nav_root'):
    quick_navigation_dialog()

if st.session_state.get('main_page')=='📅 行程表':
    st.title('📅 行程表')
    st.caption('點選日期可查看或新增行程；滑鼠停留日期按鈕可查看當日行程簡表。')
    try:
        cards=c.table('schedule_cards').select('id,title,scheduled_at,details').eq('owner_id',uid).order('scheduled_at').execute().data or []
    except Exception as exc:
        st.error('無法載入行程表。請先執行專案內 migrations/20261011_schedule_cards.sql，並確認 RLS 權限。')
        st.code(str(exc))
        st.stop()
    def parse_card_day(card):
        try:return datetime.fromisoformat(card['scheduled_at'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).date()
        except Exception:return None
    def parse_card_clock(card):
        try:return datetime.fromisoformat(card['scheduled_at'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).strftime('%H:%M')
        except Exception:return '--:--'
    schedule_by_day=defaultdict(list)
    for card in cards:
        d=parse_card_day(card)
        if d:schedule_by_day[d].append(card)
    for entries in schedule_by_day.values():entries.sort(key=lambda x:x['scheduled_at'])
    if 'schedule_target' not in st.session_state:st.session_state.schedule_target=date.today()
    if 'schedule_selected' not in st.session_state:st.session_state.schedule_selected=date.today()
    left,right=st.columns([1.7,1],gap='large')
    with left:
        target=st.date_input('目標月份（Target）',key='schedule_target')
        weeks=calendar.monthcalendar(target.year,target.month)
        st.markdown(f'### {target.year} 年 {target.month} 月')
        headings=st.columns([0.8]+[1]*len(weeks))
        headings[0].markdown('**星期 / 週**')
        for wi,col in enumerate(headings[1:],1):col.markdown(f'**第 {wi} 週**')
        # Requested orientation: X = weeks, Y = weekdays.
        for weekday in range(7):
            cols=st.columns([0.8]+[1]*len(weeks))
            cols[0].markdown('**'+['週一','週二','週三','週四','週五','週六','週日'][weekday]+'**')
            for wi,week in enumerate(weeks):
                daynum=week[weekday]
                if not daynum:cols[wi+1].write('—');continue
                d=date(target.year,target.month,daynum)
                entries=schedule_by_day.get(d,[])
                tip='\n'.join(f"{x['title']} · {parse_card_clock(x)}" for x in entries) if entries else '當日無行程'
                caption=f'{daynum}'+(f' ·{len(entries)}' if entries else '')
                if cols[wi+1].button(caption,key=f'schedule_day_{d.isoformat()}',help=tip,use_container_width=True,type='primary' if d==st.session_state.schedule_selected else 'secondary'):
                    st.session_state.schedule_selected=d
                    st.rerun()
    with right:
        st.markdown('### 當日行程卡')
        chosen=st.date_input('查詢日期',key='schedule_selected')
        top_n=st.number_input('顯示最上方 N 張',min_value=1,max_value=100,value=5,step=1,key='schedule_top_n')
        today_cards=schedule_by_day.get(chosen,[])
        st.caption(f'{chosen.isoformat()} · 共 {len(today_cards)} 張，顯示 {min(len(today_cards),int(top_n))} 張')
        with st.container(height=410,border=True):
            for item in today_cards[:int(top_n)]:
                with st.container(border=True):
                    st.markdown('**'+item['title'].replace('*',r'\*')+'**')
                    st.caption('排定時間：'+parse_card_clock(item))
                    if item.get('details'):st.write(item['details'])
                    if st.button('刪除',key='schedule_delete_'+item['id']):
                        try:
                            c.table('schedule_cards').delete().eq('id',item['id']).eq('owner_id',uid).execute()
                            st.rerun()
                        except Exception as exc:st.error('刪除失敗：'+str(exc))
            if not today_cards:st.info('當日沒有行程。')
        with st.expander('＋ 建立新行程',expanded=False):
            with st.form('schedule_create',clear_on_submit=True):
                title=st.text_input('標題',max_chars=200)
                planned=st.time_input('排定時間',value=dt_time(9,0),step=900)
                details=st.text_area('詳細內容（可留空）',max_chars=10000)
                submit=st.form_submit_button('建立行程',type='primary')
            if submit:
                if not title.strip():st.warning('請輸入標題')
                else:
                    try:
                        local_dt=datetime.combine(chosen,planned).replace(tzinfo=timezone(timedelta(hours=8)))
                        c.table('schedule_cards').insert({'owner_id':uid,'title':title.strip(),'scheduled_at':local_dt.isoformat(),'details':details}).execute()
                        st.success('行程已建立')
                        st.rerun()
                    except Exception as exc:st.error('建立失敗：'+str(exc))
    st.stop()

if st.session_state.get('main_page')=='⚙️ 設定':
    st.title('⚙️ 設定')
    st.caption("帳號管理 · 資源回收區 · 本地備份")
    st.selectbox('下載檔案格式',options=['ainote','zip'],key='download_format',help='兩種副檔名使用相同的 AINOTE ZIP 封裝結構。')
    st.info("瀏覽器不能自行建立 D 槽資料夾。建議先建立 D:\\AInoteManagement，再授權此資料夾；不支援時改用下載。")
    with st.container():
        st.markdown('#### 資源回收區')
        recycle_limit=st.number_input('最近顯示筆數 N',min_value=1,max_value=100,value=3,step=1,key='recycle_limit')
        recycle_search=st.text_input('搜尋回收區文件',placeholder='輸入文件名稱',key='recycle_search').strip().casefold()
        deleted_roots=[n for n in notes if n.get('is_deleted') and (not n['parent_id'] or not byid.get(n['parent_id'],{}).get('is_deleted'))]
        deleted_roots.sort(key=lambda n:n.get('deleted_at') or n.get('updated_at') or n.get('created_at') or '',reverse=True)
        matched=[n for n in deleted_roots if recycle_search in n.get('title','').casefold()]
        st.caption(f'符合條件 {len(matched)} 項；顯示最近 {min(int(recycle_limit),len(matched))} 項')
        for n in matched[:int(recycle_limit)]:
            cc=st.columns([3,1]);cc[0].caption(n['title'])
            if cc[1].button('還原',key='restore_'+n['id']):
                try:restore_note(n['id']);st.rerun()
                except Exception as exc:st.error('還原失敗：'+str(exc))
    with st.container():
        st.markdown('#### 預設儲存路徑')
        st.caption('在支援的瀏覽器選擇本機資料夾，之後優先寫入該資料夾。瀏覽器可能要求重新授權；手機或不支援的瀏覽器改用下載。')
        local_component(mode='settings',key='local_save_settings_v1',default=None)
    with st.container():
        st.markdown('#### 帳號註銷')
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
                        for session_key in ['user_id','access_token','refresh_token','selected']:
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
    st.stop()

DEMO_GUIDE = """# BV-Text 使用說明書

## AINOTE網頁格式：AI提示詞（請整段複製給 AI）

> 你是 BV-Text / AI-NOTE 文件封裝助手。請根據我指定的主題製作繁體中文教學文件，**輸出真正的 ZIP 壓縮檔（可命名 `.zip` 或 `.ainote`）**，不能只將 Markdown 改副檔名。**排版規則：只有 `#` 用於章節標題、`##` 用於小節標題；內文不要使用 `###` 或更大標題，重點只用 `**粗體**`。**每節包含定義、例子、Markdown 表格、適當示意圖片及說明。所有圖片都要實際放入 ZIP，不能只給外部網址。
>
> **封裝規格（v1）**：ZIP 根目錄必須有 `manifest.json`、`structure.json`；可以有 `documents/<note-id>.md` 與 `assets/<asset-id>.<副檔名>`。`manifest.json` 是 JSON 物件，包含 `format: "ainote"`、`version: 1`、`root_id: <GROUP UUID>`、`name: <組別名稱>`。`structure.json` 是節點 JSON 陣列；每個節點要有唯一 `id`（UUID 字串）、`parent_id`（根節點為 null）、`kind`、`title`、`content`、`position`、`has_page`。根節點必須為 `GROUP`，其餘節點的 `parent_id` 必須指向存在的父節點。`GROUP` 只能作為根節點，`SUBFILE` 為資料夾／子文件，`MARKDOWN`、`TABLE`、`GRAPH`、`HANDWRITE` 為內容區塊。請將文字與 Markdown 表格放入 `MARKDOWN` 或 `TABLE` 的 `content`，並同步寫入 `documents/<id>.md`。圖片應放在 `assets/<圖片UUID>.png` 等路徑，節點內容以 `![圖片說明](asset://<圖片UUID>)` 引用。每個圖片 UUID 必須和 ZIP 內檔名相同；所有引用必須存在。
>
> **資料一致性**：請勿依賴外部圖片連結、絕對路徑或不存在的媒體。檢查 ZIP 可解壓、manifest 正確、所有 ID 唯一、父子關係無循環、圖片檔案實際存在。輸出前最好使用我提供的現有 `.ainote` 範例做匯入相容性測試。請提供下載 ZIP，並列出章節目錄、表格清單、圖片清單。若無法建立或驗證 ZIP，請明確說明，不要宣稱可直接匯入。

**最小目錄示意：**

```text
lesson.ainote  （實際是 ZIP）
├── manifest.json
├── structure.json
├── documents/
│   └── <note-uuid>.md
└── assets/
    └── <image-uuid>.png
```

**manifest.json 範例：**

```json
{"format":"ainote","version":1,"root_id":"11111111-1111-4111-8111-111111111111","name":"網路安全"}
```

**structure.json 範例（精簡示意，UUID 請自行產生）：**

```json
[
  {"id":"11111111-1111-4111-8111-111111111111","parent_id":null,"kind":"GROUP","title":"網路安全","content":"","position":0,"has_page":false},
  {"id":"22222222-2222-4222-8222-222222222222","parent_id":"11111111-1111-4111-8111-111111111111","kind":"SUBFILE","title":"第一章","content":"","position":0,"has_page":true},
  {"id":"33333333-3333-4333-8333-333333333333","parent_id":"22222222-2222-4222-8222-222222222222","kind":"MARKDOWN","title":"防火牆","content":"# 第一章｜網路安全\n## 1.1 防火牆\n**防火牆**用於過濾封包。","position":0,"has_page":false}
]
```

**匯入注意事項：** `.ainote` 與 `.zip` 使用相同的 ZIP 封裝，但不是任意 ZIP 都能匯入。匯入器要求 `format=ainote`、`version=1`、有效的 `GROUP` 根節點及可追蹤的父子關係。`documents/` 是方便檢視的 Markdown 副本，**匯入時以 `structure.json` 內的 `content` 為準**；`assets/` 依 `asset://UUID` 重新上傳到私有 Storage。若圖片上傳失敗，原始封裝可能只部分匯入，請先用測試組別驗證。

**文件排版範例：**

# 第一章｜網路安全

## 1.1 防火牆

**防火牆（Firewall）**：依安全規則過濾網路流量。

| 設備 | 用途 |
|---|---|
| Firewall | 封包過濾 |
| WAF | HTTP 應用層防護 |

圖片示例：在 ZIP 內附 `network-diagram.png`，並以匯入器支援的資產引用方式連結，不要使用未打包的本地絕對路徑。

# AInoteManagement 使用說明書

## 一、文件結構

- **GROUP（組別）**：最上層筆記集合，可匯出為 `.ainote`。
- **SUBFILE（子文件）**：組別內的子層級，能容納多個內容區塊。
- **MARKDOWN（文字）**：支援 Markdown 筆記。
- **GRAPH（圖片）**：獨立圖片區塊，可上傳照片。
- **TABLE（表格）**：可選取儲存格並套用公式。
- **HANDWRITE（手寫稿）**：畫布式手寫筆記，可設定寬高。

例如：`我的第一份筆記（GROUP） → 課堂筆記（SUBFILE） → 文字 / 圖片 / 表格 / 手寫稿`。左側 Explorer 可建立、選取、重新命名、移動或刪除節點。圖片組件可一次上傳最多 20 張照片；手寫稿組件可包含 1–20 頁。

## 二、表格運算式語法

在表格選取要填入的範圍，輸入公式；`row` 與 `column` **從 0 起算**。`@N` 代表保留 N 位小數（0–15），可省略。

| 用途 | 範例 |
|---|---|
| 四則運算 | `row*2+column` |
| 指定精度 | `row/3@2` |
| 比較條件 | `row<=3` |
| 條件分支 | `choose(row<3,1,0)` |
| 等差求和 1+…+row | `row*(row+1)/2@0` |
| 遞迴求和 | `choose(row<=0,0,row+f(row-1,column))@0` |
| Fibonacci | `choose(row<=1,row,f(row-1,column)+f(row-2,column))@0` |
| 遞迴終止 | `f(row-1,column).stop(row<0)` |
| 指定終止值 | `f(row-1,column).stop(row<=1,row)` |
| 矩陣範圍引用 | `A[0,0][2,2]` |
| 矩陣加法 | `A[0,0][1,1]+A[2,0][3,1]` |
| 舊版相容格式 | `f(row,column)=(row*2+column)<3>` |

`choose(條件,成立時,否則時)` 只計算選中的分支；`f(列,欄)` 呼叫同一公式在其他座標的值。矩陣 `*` 依矩陣乘法規則運算。**目前不保證支援 `sum(A[...][...])` 聚合命令**；需要求和時可使用上述數列公式。計算失敗會中止，不應套用部分結果。

## 三、儲存機制

1. **編輯中**：文字與表格的變更可能先保存在頁面工作階段，尚未代表雲端持久化。
2. **按「存儲」**：先產生本地 `.ainote` 備份（本地資料夾模式須確認寫入成功），再寫入 Supabase PostgreSQL，最後重新讀取驗證。
3. **瀏覽器下載模式限制**：網頁能觸發下載，但不能確認檔案已實際寫入磁碟；請自行確認下載位置及檔案。
4. **圖片／手寫稿**：媒體檔案儲存於私有 Supabase Storage `note-images`，筆記資料透過 `asset://` 參照；這類媒體有獨立儲存操作，不能假設與文字存儲按鈕完全相同。
5. **匯出／匯入**：組別可匯出 `.ainote`（ZIP 格式，含筆記與可取得的媒體資產）；可從功能選單重新匯入。
6. **刪除／回收區**：一般刪除採軟刪除，可由回收區管理；實際資料是否永久保存仍受 Supabase 專案、權限、配額及備份政策影響。

**重要：** 雲端存儲不等於永久保存。建議定期下載 `.ainote` 備份，並確認瀏覽器下載完成。
"""

if not selected:
    st.title('歡迎使用 BV-Text')
    st.info('目前沒有組別。')
    if st.button('＋ 新建組別文件',type='primary'):
        try:
            op=operation_progress('建立範例組別');op(20,'建立組別')
            root=insert_note('GROUP','我的第一份筆記')
            op(65,'建立使用說明書')
            insert_note('MARKDOWN','使用說明書',root['id'],content=DEMO_GUIDE)
            op(100,'建立完成');st.session_state.selected=root['id'];st.rerun()
        except Exception as exc:st.error('建立失敗：'+str(exc))
    st.stop()

# The GROUP is the browsing unit. Editing remains at the selected workspace level.
group=selected
while group.get('parent_id') and group['kind']!='GROUP':
    group=byid.get(group['parent_id'],group)
    if group['kind']=='GROUP':break
workspace=selected if selected['kind'] in CONTAINERS else byid.get(selected.get('parent_id'),selected)
workspace_id=workspace['id']
workspace_blocks=sorted(
    [n for n in children_index.get(workspace_id,[]) if n['kind'] not in CONTAINERS],
    key=lambda n:(n.get('position',0),n.get('created_at',''))
)
assets={}
# Load asset metadata only if the group/workspace contains image references.
needs_assets=any('asset://' in (n.get('content') or '') for n in active_notes if n['kind'] in ('GRAPH','HANDWRITE'))
if needs_assets:
    try:
        assets={a['id']:a for a in c.table('assets').select('id,storage_path,mime_type,note_id').eq('owner_id',uid).execute().data}
    except Exception:
        logging.getLogger(__name__).exception('Asset list failed')

# 文件關閉不使用頂部標籤列；關閉是先完整本地備份，再移入回收區。
if selected:
    st.caption('關閉文件會先在授權資料夾建立本地備份，再從網站工作臺移入回收區。')
    try:
        close_drafts={}
        for draft_note in active_notes:
            dk='block_content_'+draft_note['id']
            if dk in st.session_state:close_drafts[draft_note['id']]=st.session_state[dk]
        close_bytes=export_group(group,active_notes,close_drafts)
        close_b64=base64.b64encode(close_bytes).decode('ascii')
        close_err=None
    except Exception as exc:
        close_b64='';close_err=str(exc)
    close_event=local_component(mode='close',data=close_b64,
        filename=download_filename(group['title']),
        disabled=bool(close_err),key='close_local_'+workspace_id,default=None)
    if close_err:st.error('無法準備關閉備份：'+close_err)
    if isinstance(close_event,dict) and close_event.get('token')!=st.session_state.get('close_last_token_'+workspace_id):
        st.session_state['close_last_token_'+workspace_id]=close_event.get('token')
        if close_event.get('action')=='saved':
            if close_event.get('method')!='folder':
                st.error('關閉需要確認本地檔案已寫入。請先在設定中心授權本地資料夾。')
            else:
                try:
                    op=operation_progress('關閉文件');op(35,'本地備份完成')
                    delete_note(selected['id'])
                    op(90,'已移入回收區，重新載入工作臺')
                    st.session_state.selected=None
                    st.session_state.pop('open_tabs',None)
                    op(100,'關閉完成');st.rerun()
                except Exception as exc:st.error('關閉失敗：'+str(exc))
        elif close_event.get('action')=='error':st.error('本地備份失敗：'+close_event.get('message','未知錯誤'))
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
    focus_id=st.session_state.pop('nav_focus',None)
    if focus_id in byid and focus_id!=group['id']:
        focus=byid[focus_id]
        st.success('已定位至：'+focus['title'])
        with st.container(border=True):
            st.markdown('### '+focus['title'])
            if focus['kind'] in ('MARKDOWN','SUBFILE') and focus.get('content'):
                show_markdown(focus['content'],assets)
            elif focus['kind'] in ('GRAPH','TABLE','HANDWRITE'):
                st.caption('已選取此內容區塊。切換至編輯模式可操作該區塊；下方保留完整文件內容。')
            else:st.caption('已選取此子文件。')
    # Build one stable table of contents for the whole group, preserving Explorer order.
    def ordered_children(parent_id):
        return sorted(children_index.get(parent_id,[]),
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
            if node['kind'] in ('GRAPH','TABLE','HANDWRITE') and node.get('title'):
                st.caption(('🖼️ ' if node['kind']=='GRAPH' else '✍️ ' if node['kind']=='HANDWRITE' else '▦ ')+node['title'])
            if node['kind']=='TABLE':render_table(node.get('content') or '')
            elif (node.get('content') or '').strip():show_markdown(node['content'],assets)
else:
    st.title(workspace['title'])
    # GROUP/SUBFILE are structural folders; content lives in child documents only.
    draft_keys=[]
    for block in workspace_blocks:
        st.markdown('#### '+('🖼️ ' if block['kind']=='GRAPH' else '✍️ ' if block['kind']=='HANDWRITE' else '▦ ' if block['kind']=='TABLE' else '📄 ')+block['title'])
        if block['kind']=='HANDWRITE':
            handwriting_editor(block,assets)
        elif block['kind']=='GRAPH':
            image_editor(block,assets,block['id'])
        elif block['kind']=='TABLE':
            original=markdown_dataframe(block.get('content') or '')
            if original.empty and not len(original.columns):original=pd.DataFrame([['']*3 for _ in range(3)],columns=['欄位 1','欄位 2','欄位 3'])
            sheet_key='sheet_'+block['id']
            cell_w,cell_h=table_dimensions(block.get('content') or '')
            revision=st.session_state.get('_matrix_revision_'+block['id'],0)
            ev=matrix_component(cells=original.fillna('').astype(str).values.tolist(),headers=[str(x) for x in original.columns],width=cell_w,height=cell_h,align=table_alignment(block.get('content')),revision=revision,error=st.session_state.get('_matrix_error_'+block['id'],''),errorId=st.session_state.get('_matrix_error_id_'+block['id'],0),key='matrix_'+block['id'],default=None)
            if isinstance(ev,dict) and ev.get('nonce')!=st.session_state.get('_matrix_nonce_'+block['id']):
                st.session_state['_matrix_nonce_'+block['id']]=ev.get('nonce')
                if ev.get('action') in ('save','formula','format'):
                    try:
                        op=operation_progress('表格'+('矩陣計算' if ev['action']=='formula' else '數值格式' if ev['action']=='format' else '更新'))
                        op(20,'檢查資料')
                        values=ev['cells'];headers=ev['headers']
                        if len(values)>50 or len(headers)>30 or any(len(row)!=len(headers) for row in values):raise ValueError('表格尺寸無效')
                        if ev['action']=='format':
                            top,left,bottom,right=ev.get('selection',[])
                            if not (0<=top<=bottom<len(values) and 0<=left<=right<len(headers)):raise ValueError('選取範圍無效')
                            mode=ev.get('formatMode')
                            digits=int(ev.get('digits',2))
                            if mode not in ('decimal','significant') or not 0<=digits<=15 or (mode=='significant' and digits<1):raise ValueError('位數設定無效')
                            for r in range(top,bottom+1):
                                for c in range(left,right+1):
                                    raw=str(values[r][c]).strip()
                                    if not raw:continue
                                    try:
                                        number=float(raw)
                                    except ValueError:
                                        continue
                                    if not __import__('math').isfinite(number):continue
                                    values[r][c]=(f'{number:.{digits}f}' if mode=='decimal' else f'{number:.{digits}g}')
                        if ev['action']=='formula':
                            st.session_state['_matrix_error_'+block['id']]=''
                            op(50,'執行安全矩陣運算')
                            results=calculate(ev.get('formula',''),values,ev.get('selection',[]))
                            top,left,bottom,right=ev['selection']
                            for i,row in enumerate(results):
                                for j,val in enumerate(row):
                                    if top+i<len(values) and left+j<len(headers):
                                        values[top+i][left+j]='NaN' if isinstance(val,float) and pd.isna(val) else str(val)
                        op(75,'儲存表格')
                        frame=pd.DataFrame(values,columns=headers)
                        content=with_table_alignment(keep_table_dimensions(dataframe_markdown(frame),cell_w,cell_h),ev.get('align','left'))
                        update_note(block['id'],content=content)
                        st.session_state['_matrix_revision_'+block['id']]=revision+1
                        op(100,'重新讀取並驗證完成')
                        st.session_state[report_key]={'successes':1,'total':1,'failures':[],'names':[block['title']],'saved_at':datetime.now(timezone.utc).isoformat()}
                        st.rerun()
                    except Exception as exc:
                        st.session_state['_matrix_error_'+block['id']]=str(exc)
                        st.session_state['_matrix_error_id_'+block['id']]=st.session_state.get('_matrix_error_id_'+block['id'],0)+1
                        st.error('表格運算或儲存失敗：'+str(exc))
                        st.rerun()
            draft_keys.append((block['id'],sheet_key,'matrix'))
        else:
            text_key='block_content_'+block['id']
            st.text_area('Markdown：'+block['title'],value=block.get('content') or '',
                height=190,key=text_key,label_visibility='collapsed')
            if st.button('💾 儲存文件：'+block['title'],key='save_text_inline_'+block['id']):
                try:
                    op=operation_progress('更新文件');op(25,'寫入資料庫')
                    update_note(block['id'],content=st.session_state[text_key])
                    op(100,'已寫入並驗證')
                    st.session_state[report_key]={'successes':1,'total':1,'failures':[],
                        'names':[block['title']],'saved_at':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                    st.rerun()
                except Exception as exc:
                    logging.getLogger(__name__).exception('Text save failed')
                    st.error('文件儲存失敗：'+type(exc).__name__+'：'+str(exc))
            draft_keys.append((block['id'],text_key,'text'))
    # Independent actions: local backup never triggers a cloud write.
    draft_values={}
    for note_id,field_key,field_type in draft_keys:
        if field_type=='matrix':
            continue
        if field_type=='table':
            frame=st.session_state.get('_editor_result_'+field_key)
            if frame is not None:
                draft_values[note_id]=keep_table_dimensions(dataframe_markdown(frame),*table_dimensions(byid[note_id].get('content') or ''))
        else:
            draft_values[note_id]=st.session_state.get(field_key,byid[note_id].get('content') or '')
    st.markdown('#### 儲存')
    try:
        local_zip=export_group(group,active_notes,draft_values)
        local_b64=base64.b64encode(local_zip).decode('ascii')
        backup_error=None
    except Exception as exc:
        local_b64='';backup_error=str(exc)
    if backup_error:st.error('無法建立本地備份：'+backup_error)
    save_key='pipeline_'+workspace_id
    save_event=local_component(mode='pipeline',data=local_b64,
        filename=download_filename(group['title']),
        disabled=bool(backup_error),key='local_pipeline_'+workspace_id,default=None)
    if isinstance(save_event,dict) and save_event.get('token')!=st.session_state.get('pipeline_last_token_'+workspace_id):
        if save_event.get('token'):
            st.session_state['pipeline_last_token_'+workspace_id]=save_event['token']
            if save_event.get('action')=='saved':
                st.session_state[save_key]={'stage':'local_ok','method':save_event.get('method'),'draft':dict(draft_values)}
                st.rerun()
            elif save_event.get('action')=='error':
                st.session_state[save_key]={'stage':'failed','error':save_event.get('message','本地儲存失敗')}
                st.rerun()
    pipeline=st.session_state.get(save_key,{})
    if pipeline.get('stage')=='local_ok':
        progress=operation_progress('存儲流程')
        progress(35,'本地備份已完成；準備上傳資料庫')
        failures=[];draft=pipeline['draft'];total=len(draft)
        for index,(note_id,content) in enumerate(draft.items()):
            try:update_note(note_id,content=content)
            except Exception as exc:failures.append((byid.get(note_id,{}).get('title',note_id),str(exc)))
            progress(35+int(45*(index+1)/max(1,total)),f'雲端上傳及驗證 {index+1}/{total}')
        if failures:
            st.session_state[save_key]={'stage':'failed','error':str(failures)}
            progress(80,'部分文件未成功，請檢查錯誤')
        else:
            progress(90,'重新讀取資料庫')
            try:
                refreshed=fetch_notes()
                if any(next((n.get('content') for n in refreshed if n['id']==nid),None)!=value for nid,value in draft.items()):
                    raise RuntimeError('重新讀取後內容不一致')
                progress(100,'本地、雲端、重新載入完成')
                st.session_state[save_key]={'stage':'done','count':total,'method':pipeline.get('method')}
                st.session_state[report_key]={'successes':total,'total':total,'failures':[],'names':[byid.get(nid,{}).get('title',nid) for nid in draft],'saved_at':datetime.now(timezone.utc).isoformat()}
                st.rerun()
            except Exception as exc:st.session_state[save_key]={'stage':'failed','error':str(exc)}
    if pipeline.get('stage')=='done':
        st.progress(100,text='存儲完成：本地備份 → 雲端寫入 → 重新載入驗證')
        st.success(f"已完成 {pipeline.get('count',0)} 個文件的儲存。" )
    elif st.session_state.get(save_key,{}).get('stage')=='failed':
        st.error('存儲流程未完成：'+str(st.session_state[save_key].get('error')))
    st.caption('本地資料夾模式確認寫入後才上傳；瀏覽器下載模式只能確認已啟動下載，無法確認磁碟寫入完成。')
    t1,t2,t3,t4=st.tabs(['🖼️ 圖片','▦ 表格','📄 Markdown','✍️ 手寫稿'])
    with t1:
        photo_title=st.text_input('圖片名稱',value='新圖片',key='graph_title_'+workspace_id)
        st.caption('每次建立一個圖片組件；組件內可一次上傳 1–20 張照片。')
        if st.button('新增圖片組件',key='new_graph_'+workspace_id):
            try:
                created=insert_note('GRAPH',photo_title.strip() or '新圖片',workspace_id,position=len(workspace_blocks))
                st.session_state.selected=created['id']
                st.rerun()
            except Exception as exc:st.error('新增失敗：'+str(exc))
    with t2:
        if st.button('＋ 建立表格',key='open_table_modal_'+workspace_id):
            st.session_state.pending_table={'title':'新表格','parent':workspace_id}
            st.rerun()
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
    with t4:
        if st.button('＋ 建立手寫稿',key='new_handwrite_'+workspace_id):
            st.session_state.pending_handwrite={'title':'新手寫稿','parent':workspace_id}
            st.rerun()
st.divider()
st.caption('BV-Text v3.2.1 · 組別瀏覽 · 工作區儲存 · 圖片貼上 · Excel 式表格')

if st.session_state.get("pending_table"):
    table_creation_dialog()

if st.session_state.get('pending_handwrite'):
    handwriting_creation_dialog()
