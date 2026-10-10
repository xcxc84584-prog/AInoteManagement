import base64
import io
import json
import logging
import os
import re
import uuid
import zipfile
from datetime import datetime
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

@st.cache_resource
def client(url,key):return create_client(url,key)

url,key=config('SUPABASE_URL'),config('SUPABASE_ANON_KEY')
if not url or not key:
    st.title('📚 AInoteManagement v1.0')
    st.error('尚未設定 Supabase。請先完成 README.md 中的部署設定。')
    st.code('SUPABASE_URL = "https://...supabase.co"\nSUPABASE_ANON_KEY = "..."',language='toml')
    st.stop()
sb=client(url,key)

# Every database and storage call uses the logged-in user's JWT, not a service-role key.
def api():
    c=create_client(url,key)
    c.postgrest.auth(st.session_state['access_token'])
    c.storage._client.headers['Authorization']='Bearer '+st.session_state['access_token']
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
            submit=st.form_submit_button('登入',use_container_width=True)
        if submit:
            try:
                result=sb.auth.sign_in_with_password({'email':email,'password':password})
                st.session_state.update(access_token=result.session.access_token,refresh_token=result.session.refresh_token,user_id=result.user.id)
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
    fresh=sb.auth.refresh_session(st.session_state['refresh_token'])
    st.session_state.update(access_token=fresh.session.access_token,refresh_token=fresh.session.refresh_token,user_id=fresh.user.id)
except Exception:
    for k in ['access_token','refresh_token','user_id']:st.session_state.pop(k,None)
    st.warning('登入已逾時，請重新登入。');st.stop()

c=api()
uid=current_user()

def fetch_notes():
    return c.table('notes').select('*').eq('owner_id',uid).order('position').execute().data

def insert_note(kind,title,parent=None,content='',has_page=False,position=0):
    payload={'owner_id':uid,'parent_id':parent,'kind':kind,'title':title[:200], 'content':content,'has_page':has_page,'position':position}
    return c.table('notes').insert(payload).execute().data[0]

def update_note(nid,**values):
    values['updated_at']=datetime.utcnow().isoformat()+'Z'
    c.table('notes').update(values).eq('id',nid).eq('owner_id',uid).execute()

def delete_note(nid):c.table('notes').delete().eq('id',nid).eq('owner_id',uid).execute()

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
    c.storage.from_('note-images').upload(path,data,{'content-type':mime,'upsert':'false'})
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
.block-container{padding-top:1.2rem}.stButton button{border-radius:8px}
[data-testid="stSidebar"]{min-width:280px}
</style>''',unsafe_allow_html=True)

try:
    notes=fetch_notes()
except Exception as exc:
    logging.getLogger(__name__).exception('Database read failed')
    st.error('無法讀取資料庫。請開啟 Streamlit Cloud → Manage app → Logs 檢查詳細原因。')
    st.code(f'Error type: {type(exc).__name__}')
    st.stop()
byid={n['id']:n for n in notes}
roots=[n for n in notes if n['kind']=='GROUP' and not n['parent_id']]
if st.session_state.get('selected') not in byid:st.session_state['selected']=roots[0]['id'] if roots else None
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
    def tree(parent=None,depth=0):
        for n in sorted((x for x in notes if x['parent_id']==parent),key=lambda x:(x['position'],x['created_at'])):
            label=('📁 ' if n['kind'] in CONTAINERS else {'GRAPH':'🖼️ ','TABLE':'▦ ','MARKDOWN':'📄 '}[n['kind']])+n['title']
            if st.button('　'*depth+label,key='tree_'+n['id'],use_container_width=True,type='primary' if selected and selected['id']==n['id'] else 'secondary'):
                st.session_state.selected=n['id'];st.rerun()
            if n['kind'] in CONTAINERS:tree(n['id'],depth+1)
    tree()
    st.divider()
    if st.button('登出',use_container_width=True):
        for k in ['user_id','access_token','refresh_token','selected']:st.session_state.pop(k,None)
        st.rerun()

if not selected:
    st.title('歡迎使用 AInoteManagement')
    st.info('請在左側「功能選單」建立第一個組別，或匯入 .ainote 檔案。')
    st.stop()

st.caption(' / '.join(byid[x]['title'] for x in reversed(get_ancestors(selected['id'],byid))))
st.title(selected['title'])

with st.expander('文件管理：新增 / 更名 / 移動 / 刪除',expanded=False):
    if selected['kind'] in CONTAINERS:
        with st.form('create_child'):
            col1,col2=st.columns([1,2]);kind=col1.selectbox('類型', ['SUBFILE','MARKDOWN','GRAPH','TABLE'] if selected['kind']=='SUBFILE' else ['SUBFILE','MARKDOWN','GRAPH','TABLE']);title=col2.text_input('新文件名稱')
            has_page=st.checkbox('啟用子文件自身頁面',value=True) if kind=='SUBFILE' else False
            if st.form_submit_button('新增文件') and title.strip():
                try:r=insert_note(kind,title.strip(),selected['id'],has_page=has_page,position=len([n for n in notes if n['parent_id']==selected['id']]));st.session_state.selected=r['id'];st.rerun()
                except Exception:st.error('新增失敗')
    with st.form('rename'):
        renamed=st.text_input('重新命名',value=selected['title'])
        if st.form_submit_button('儲存名稱') and renamed.strip():
            update_note(selected['id'],title=renamed.strip()[:200]);st.rerun()
    if selected['kind']!='GROUP':
        allowed=[n for n in notes if n['kind'] in CONTAINERS and n['id'] not in subtree(selected['id'],notes) and get_ancestors(n['id'],byid)[-1]==get_ancestors(selected['id'],byid)[-1]]
        if allowed:
            dest=st.selectbox('移動至',allowed,format_func=lambda n:n['title'],key='move_target')
            if st.button('移動文件'):
                update_note(selected['id'],parent_id=dest['id']);st.rerun()
    confirm=st.checkbox('我確認要永久刪除此文件及其子文件',key='delete_confirm')
    if st.button('刪除文件',disabled=not confirm):
        try:delete_note(selected['id']);st.session_state.selected=None;st.rerun()
        except Exception:st.error('刪除失敗')

if selected['kind'] in CONTAINERS:
    children=[n for n in notes if n['parent_id']==selected['id']]
    folders=[n for n in children if n['kind'] in CONTAINERS]
    blocks=[n for n in children if n['kind'] not in CONTAINERS]
    if folders:st.caption('下一層子文件：'+ ' · '.join(n['title'] for n in folders))
    enabled=st.toggle('啟用自身頁面',value=selected['has_page'],key='has_page_'+selected['id'])
    if enabled!=selected['has_page']:update_note(selected['id'],has_page=enabled);st.rerun()
    if not enabled and not blocks:
        st.info('此節點目前是資料夾。開啟「啟用自身頁面」即可編輯內容。')
    if enabled:
        with st.form('self_content_'+selected['id']):
            content=st.text_area('自身 Markdown 內容',value=selected['content'],height=180)
            if st.form_submit_button('儲存內容'):update_note(selected['id'],content=content);st.rerun()
        if selected['content']:show_markdown(selected['content'],{})
    if blocks:
        st.subheader('頁面區塊')
        for block in sorted(blocks,key=lambda n:n['position']):
            with st.container(border=True):
                cols=st.columns([7,1,1]);cols[0].markdown('**'+block['title']+'** · '+block['kind'])
                if cols[1].button('↑',key='up_'+block['id']):
                    prev=[b for b in blocks if b['position']<block['position']]
                    if prev:
                        p=max(prev,key=lambda x:x['position']);update_note(p['id'],position=block['position']);update_note(block['id'],position=p['position']);st.rerun()
                if cols[2].button('開啟',key='open_'+block['id']):st.session_state.selected=block['id'];st.rerun()
                if block['kind']=='GRAPH':
                    match=re.search(r'asset://([0-9a-fA-F-]{36})',block['content'])
                    if match:
                        try:
                            assets={a['id']:a for a in c.table('assets').select('*').eq('owner_id',uid).execute().data}
                            show_markdown(block['content'],assets)
                        except Exception:st.warning('圖片載入失敗')
                else:st.markdown(block['content'] or '（空白區塊）')
else:
    tab_edit,tab_preview=st.tabs(['編輯','預覽'])
    with tab_edit:
        with st.form('edit_'+selected['id']):
            content=st.text_area('Markdown 內容',value=selected['content'],height=320)
            if st.form_submit_button('儲存 Markdown',use_container_width=True):update_note(selected['id'],content=content);st.success('已儲存');st.rerun()
        if selected['kind']=='GRAPH':
            st.subheader('圖片插入')
            upload=st.file_uploader('本地上傳圖片',type=['png','jpg','jpeg','webp','gif'],key='image_'+selected['id'])
            paste=components.declare_component('paste_image',path=str(Path(__file__).parent/'components'/'paste_widget'))
            pasted=paste(key='paste_'+selected['id'],default=None)
            incoming=None
            if upload:incoming=upload.getvalue()
            elif pasted and pasted.get('data'):
                try:incoming=base64.b64decode(pasted['data'].split(',',1)[1])
                except Exception:st.error('剪貼簿資料無效')
            if incoming and st.button('儲存圖片並插入 Markdown'):
                try:
                    aid=upload_image(incoming,selected['id'])
                    newcontent=selected['content']+'\n\n![圖片](asset://'+aid+')'
                    update_note(selected['id'],content=newcontent)
                    st.success('圖片已儲存');st.rerun()
                except Exception as e:st.error('圖片儲存失敗：'+str(e))
    with tab_preview:
        try:assets={a['id']:a for a in c.table('assets').select('*').eq('owner_id',uid).execute().data}
        except Exception:assets={}
        show_markdown(selected['content'],assets)

st.divider()
st.caption('AInoteManagement v1.0 · Streamlit + Supabase · 每次修改請按儲存 · 建議定期下載 .ainote 備份')
