import base64
import io
import json
import logging
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
from PIL import Image, ImageOps
from supabase import create_client
import streamlit.components.v1 as components

st.set_page_config(page_title='AInoteManagement',page_icon='📚',layout='wide',initial_sidebar_state='expanded')
KINDS=['GROUP','SUBFILE','MARKDOWN','GRAPH','TABLE']
CONTAINERS=['GROUP','SUBFILE']
MAX_IMAGE=10*1024*1024

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
            submit=st.form_submit_button('登入',use_container_width=True)
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
            submit2=st.form_submit_button('建立帳號',use_container_width=True)
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
    c.table('notes').update(values).eq('id',nid).eq('owner_id',uid).execute()

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
    a=assets.get(asset_id)
    if not a:return None
    try:return c.storage.from_('note-images').create_signed_url(a['storage_path'],3600)['signedURL']
    except Exception:return None

def signed_markdown(content,assets):
    # Signed URLs are generated only for assets owned by the logged-in user.
    def replace(match):
        alt,asset_id=match.group(1),match.group(2)
        url=asset_url(asset_id,assets)
        return f'![{alt}]({url})' if url else f'**[圖片無法讀取：{alt}]**'
    return re.sub(r'!\[([^\]]*)\]\(asset://([0-9a-fA-F-]{36})\)',replace,content or '')

def table_markdown(rows,cols):
    if not (1<=rows<=50 and 1<=cols<=30):raise ValueError('表格尺寸必須為 1–50 列、1–30 欄')
    header='| '+' | '.join(f'欄位 {i+1}' for i in range(cols))+' |'
    separator='| '+' | '.join('---' for _ in range(cols))+' |'
    body=['| '+' | '.join(' ' for _ in range(cols))+' |' for _ in range(rows)]
    return '\n'.join([header,separator,*body])

def show_markdown(content,assets):
    # Resolve private asset identifiers without embedding unsafe HTML.
    parts=re.split(r'(!\[[^\]]*\]\(asset://[0-9a-fA-F-]{36}\))',content)
    for part in parts:
        match=re.fullmatch(r'!\[([^\]]*)\]\(asset://([0-9a-fA-F-]{36})\)',part)
        if match:
            src=asset_url(match.group(2),assets)
            if src:st.image(src,caption=match.group(1) or None,use_container_width=False)
            else:st.warning('圖片不存在或無法存取')
        elif part:st.markdown(part)

def export_group(root,notes):
    ids=subtree(root['id'],notes)
    selected=[n for n in notes if n['id'] in ids]
    assets=c.table('assets').select('*').eq('owner_id',uid).execute().data
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps({'format':'ainote','version':1,'root_id':root['id'],'name':root['title']},ensure_ascii=False,indent=2))
        z.writestr('structure.json',json.dumps(selected,ensure_ascii=False,indent=2))
        for n in selected:z.writestr('documents/'+n['id']+'.md',n['content'])
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
    with st.popover('☰ 功能選單',use_container_width=True):
        st.caption('建立組別')
        newgroup=st.text_input('組別名稱',key='newgroup')
        if st.button('＋ 創建新組別',use_container_width=True):
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
                try:st.download_button('↓ 下載當前組別',data=export_group(root,notes),file_name='AInote_'+root['id']+'.ainote',mime='application/zip',use_container_width=True)
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
            elif action=='rename' and nid in byid:
                title=str(event.get('title','')).strip()
                if title:update_note(nid,title=title[:200])
            elif action=='create':
                kind=event.get('kind');title=str(event.get('title','')).strip()
                parent=target if target in byid and byid[target]['kind'] in CONTAINERS else None
                if kind=='GROUP':parent=None
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
    with st.expander('資源回收區'):
        deleted_roots=[n for n in notes if n.get('is_deleted') and (not n['parent_id'] or not byid.get(n['parent_id'],{}).get('is_deleted'))]
        for n in deleted_roots:
            cc=st.columns([3,1]);cc[0].caption(n['title'])
            if cc[1].button('還原',key='restore_'+n['id']):
                try:restore_note(n['id']);st.rerun()
                except Exception as exc:
                    logging.getLogger(__name__).exception('Restore failed')
                    st.error('還原失敗：'+type(exc).__name__)
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
    if st.button('登出',use_container_width=True):
        for k in ['user_id','access_token','refresh_token','selected','remember_enabled']:st.session_state.pop(k,None)
        st.session_state.skip_auto_login=True
        remember_action('clear')
        st.rerun()

if not selected:
    st.title('歡迎使用 AInoteManagement')
    st.info('請在左側「功能選單」建立第一個組別，或匯入 .ainote 檔案。')
    st.stop()

# A workspace is the container's own Markdown plus its immediate non-container children.
# Selecting a leaf opens the same workspace as its siblings.
workspace=selected if selected['kind'] in CONTAINERS else byid.get(selected['parent_id'],selected)
workspace_id=workspace['id']
workspace_blocks=sorted(
    [n for n in active_notes if n.get('parent_id')==workspace_id and n['kind'] not in CONTAINERS],
    key=lambda n:(n.get('position',0),n.get('created_at',''))
)
assets={}
try:
    assets={a['id']:a for a in c.table('assets').select('*').eq('owner_id',uid).execute().data}
except Exception:
    logging.getLogger(__name__).exception('Asset list failed')

st.caption(' / '.join(byid[x]['title'] for x in reversed(get_ancestors(workspace_id,byid))))
left,right=st.columns([5,2],vertical_alignment='center')
with left:st.title(workspace['title'])
with right:
    mode=st.segmented_control('工作模式',['瀏覽','編輯'],default='瀏覽',key='workspace_mode',label_visibility='collapsed')
st.caption('同一層級的 Markdown、圖片及表格共用此工作區；子資料夾另開工作區。')

def render_block(note):
    content=note.get('content') or ''
    if note['kind']=='GRAPH' and not content.strip():
        st.caption('尚未插入圖片')
    elif content.strip():
        st.markdown(signed_markdown(content,assets))
    else:
        st.caption('尚無內容')

if mode=='瀏覽':
    if workspace.get('content','').strip():
        render_block(workspace)
    for block in workspace_blocks:
        with st.container(border=False):
            if block['title'] and block['kind'] in ('GRAPH','TABLE'):
                st.caption(('🖼️ ' if block['kind']=='GRAPH' else '▦ ')+block['title'])
            render_block(block)
    if not workspace.get('content','').strip() and not workspace_blocks:
        st.info('這個工作區尚無筆記。切換至「編輯」模式即可開始。')
else:
    st.caption('Markdown 編輯 · 儲存後可切換瀏覽模式預覽排版')
    # Edit the container's own Markdown; every direct child is another block in this page.
    with st.form('editor_workspace_'+workspace_id):
        st.markdown('**頁面正文 (.md)**')
        page_content=st.text_area('頁面 Markdown',value=workspace.get('content') or '',
                                  height=250,key='workspace_content_'+workspace_id,
                                  label_visibility='collapsed',placeholder='# 在這裡撰寫 Markdown…')
        if st.form_submit_button('儲存頁面正文'):
            try:
                update_note(workspace_id,content=page_content,has_page=True)
                st.rerun()
            except Exception as exc:
                logging.getLogger(__name__).exception('Save workspace failed')
                st.error('儲存失敗：'+type(exc).__name__)

    for block in workspace_blocks:
        with st.expander(('🖼️ ' if block['kind']=='GRAPH' else '▦ ' if block['kind']=='TABLE' else '📄 ')+block['title'],expanded=True):
            with st.form('editor_block_'+block['id']):
                text=st.text_area('Markdown (.md)',value=block.get('content') or '',height=170,
                                  key='block_content_'+block['id'],label_visibility='collapsed')
                if st.form_submit_button('儲存此區塊'):
                    try:
                        update_note(block['id'],content=text)
                        st.rerun()
                    except Exception as exc:
                        logging.getLogger(__name__).exception('Save block failed')
                        st.error('儲存失敗：'+type(exc).__name__)

    st.divider()
    st.subheader('插入內容')
    t1,t2,t3=st.tabs(['🖼️ 圖片','▦ 表格','📄 Markdown 區塊'])
    with t1:
        st.caption('支援本地圖片、Ctrl+V 貼上截圖及拖曳圖片。上傳後儲存在私人 Supabase Storage。')
        upload=st.file_uploader('從本地選擇圖片',type=['png','jpg','jpeg','webp','gif'],
                                key='image_upload_'+workspace_id)
        paste=components.declare_component('paste_image',path=str(Path(__file__).parent/'components'/'paste_widget'))
        pasted=paste(key='paste_workspace_'+workspace_id,default=None)
        incoming=upload.getvalue() if upload else None
        name=upload.name if upload else '貼上的圖片'
        if incoming is None and isinstance(pasted,dict) and pasted.get('data'):
            try:
                incoming=base64.b64decode(pasted['data'].split(',',1)[1],validate=True)
                name=pasted.get('name') or name
            except Exception:st.warning('剪貼簿圖片格式無效')
        if st.button('插入圖片至此工作區',disabled=not bool(incoming),key='insert_img_'+workspace_id):
            try:
                # Each image gets its own GRAPH block; all blocks render on the same page.
                created=insert_note('GRAPH',name[:200],workspace_id,position=len(workspace_blocks))
                try:
                    asset_id=upload_image(incoming,created['id'])
                    update_note(created['id'],content=f'![{name.replace(chr(93),"")}](asset://{asset_id})')
                except Exception:
                    # Avoid leaving an empty GRAPH block after a failed upload.
                    c.table('notes').delete().eq('id',created['id']).eq('owner_id',uid).execute()
                    raise
                st.success('圖片已加入工作區')
                st.rerun()
            except Exception as exc:
                logging.getLogger(__name__).exception('Insert image failed')
                st.error('圖片上傳失敗：'+type(exc).__name__+'。請查看 Manage app → Logs')
    with t2:
        st.caption('輸入 M × N，其中 M 為資料列數，N 為欄數。')
        col_m,col_n=st.columns(2)
        m=col_m.number_input('M：資料列數',min_value=1,max_value=50,value=3,step=1,key='rows_'+workspace_id)
        n=col_n.number_input('N：欄數',min_value=1,max_value=30,value=3,step=1,key='cols_'+workspace_id)
        table_name=st.text_input('表格名稱',value='新表格',key='table_name_'+workspace_id)
        st.markdown(table_markdown(m,n))
        if st.button('建立 M × N 表格',key='insert_table_'+workspace_id):
            try:
                insert_note('TABLE',table_name.strip() or '新表格',workspace_id,
                            content=table_markdown(m,n),position=len(workspace_blocks))
                st.rerun()
            except Exception as exc:
                logging.getLogger(__name__).exception('Insert table failed')
                st.error('新增表格失敗：'+type(exc).__name__)
    with t3:
        text_name=st.text_input('區塊名稱',value='新段落',key='text_name_'+workspace_id)
        if st.button('新增 Markdown 區塊',key='insert_text_'+workspace_id):
            try:
                insert_note('MARKDOWN',text_name.strip() or '新段落',workspace_id,
                            position=len(workspace_blocks))
                st.rerun()
            except Exception as exc:
                logging.getLogger(__name__).exception('Insert Markdown block failed')
                st.error('新增失敗：'+type(exc).__name__)

st.divider()
st.caption('AInoteManagement v1.4 · 共用工作區 · Markdown 編輯／瀏覽 · 圖片與 M×N 表格')
