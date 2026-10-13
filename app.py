import ast
import operator
import calendar
import base64
import html
import io
import json
import logging
import math
import os
import re
import uuid
import zipfile
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone, date, time as dt_time, timedelta
from pathlib import Path
import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import cairosvg
from supabase import create_client
from matrix_engine import calculate
from local_backend import LocalDB
from manual_sync import pull_from_cloud,push_to_cloud
import streamlit.components.v1 as components

st.set_page_config(page_title='BV-Text',page_icon='📚',layout='wide',initial_sidebar_state='expanded')
KINDS=['GROUP','SUBFILE','GRAPH','HANDWRITE','COMPOSITE']
CONTAINERS=['GROUP','SUBFILE']
MAX_IMAGE=10*1024*1024
local_component=components.declare_component('ainote_local_save',path=str(Path(__file__).parent/'components'/'local_save'))
auto_load_component=components.declare_component('bv_auto_load_v630',path=str(Path(__file__).parent/'components'/'auto_load'))
matrix_component=components.declare_component('ainote_matrix_table',path=str(Path(__file__).parent/'components'/'matrix_table'))
paste_component=components.declare_component('paste_image',path=str(Path(__file__).parent/'components'/'paste_widget'))
composite_component=components.declare_component('bv_composite_editor',path=str(Path(__file__).parent/'components'/'composite_editor'))
composite_reader_component=components.declare_component('bv_composite_reader',path=str(Path(__file__).parent/'components'/'composite_reader'))
reader_paste_component=components.declare_component('bv_reader_paste',path=str(Path(__file__).parent/'components'/'reader_paste'))
rich_paste_component=components.declare_component('bv_rich_paste',path=str(Path(__file__).parent/'components'/'rich_paste'))
schedule_calendar_component=components.declare_component('bv_schedule_calendar',path=str(Path(__file__).parent/'components'/'schedule_calendar'))
schedule_cards_component=components.declare_component('bv_schedule_cards_v631',path=str(Path(__file__).parent/'components'/'schedule_cards'))
section_scroll_component=components.declare_component('bv_section_scroll',path=str(Path(__file__).parent/'components'/'section_scroll'))

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
    st.caption('個人 Markdown 筆記、樹狀文件與圖片管理 · 本地優先')
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

cloud_client=api()
uid=current_user()
# Explicit storage mode: browser on hosted websites, sqlite on local installations.
STORAGE_MODE=(config('BV_TEXT_STORAGE_MODE') or ('browser' if os.getenv('STREAMLIT_SHARING_MODE') else 'sqlite')).lower()
if STORAGE_MODE not in ('browser','sqlite'):
    st.error('BV_TEXT_STORAGE_MODE 必須為 browser 或 sqlite');st.stop()
if STORAGE_MODE=='sqlite':
    # This directory is on the machine RUNNING Streamlit, not necessarily the viewer's computer.
    db_root=Path(config('BV_TEXT_DATA_DIR') or (Path.home()/ 'BV-Text-Data')).expanduser().resolve()
    local_db=st.session_state.get('_local_db')
    if local_db is None or local_db.path!=str(db_root/'bvtext.sqlite3'):
        local_db=LocalDB(db_root/'bvtext.sqlite3')
        st.session_state['_local_db']=local_db
else:
    local_db=st.session_state.get('_local_db_browser')
    if local_db is None:
        local_db=LocalDB()
        st.session_state['_local_db_browser']=local_db
    browser_component=components.declare_component('bvtext_browser_db',path=str(Path(__file__).parent/'components'/'browser_db'))
    # Read IndexedDB before allowing edits. Never overwrite an existing browser workspace on first render.
    if st.session_state.get('_browser_loaded_uid')!=uid:
        result=browser_component(user_id=uid,mode='load',revision='init',key='browser_database_v1',default=None)
        if not isinstance(result,dict):
            st.info('正在載入瀏覽器 IndexedDB 工作區…');st.stop()
        if not result.get('ok'):
            st.error('無法讀取 IndexedDB：'+str(result.get('error')));st.stop()
        if result.get('snapshot'):
            try:local_db.import_snapshot(uid,result['snapshot'])
            except Exception as exc:st.error('本地資料還原失敗：'+str(exc));st.stop()
        st.session_state['_browser_loaded_uid']=uid
        st.rerun()
    # Changes are flushed through the browser component on subsequent reruns.
    revision=st.session_state.get('_browser_revision',0)
    if revision:
        result=browser_component(user_id=uid,mode='save',revision=revision,snapshot=local_db.export_snapshot(uid),key='browser_database_v1',default=None)
        if not isinstance(result,dict) or result.get('revision')!=revision:
            st.warning('本地資料正在寫入 IndexedDB；請等待完成再關閉分頁。')
        elif not result.get('ok'):
            st.error('IndexedDB 寫入失敗：'+str(result.get('error')))
c=local_db
# Fail fast if a stale local backend was deployed.
if not hasattr(c.storage, 'from_'):
    st.error('本地儲存模組版本不一致：請重新部署 v3.9.2 並重新啟動應用程式。')
    st.stop()

def mark_local_change():
    if STORAGE_MODE=='browser':st.session_state['_browser_revision']=st.session_state.get('_browser_revision',0)+1
local_db.on_change=mark_local_change


def fetch_notes():
    return c.table('notes').select('*').eq('owner_id',uid).order('position').execute().data

def insert_note(kind,title,parent=None,content='',has_page=False,position=0):
    payload={'owner_id':uid,'parent_id':parent,'kind':kind,'title':title[:200], 'content':content,'has_page':has_page,'position':position}
    result=c.table('notes').insert(payload).execute().data
    if not result:raise RuntimeError('建立失敗：資料庫未回傳新文件')
    return result[0]

def priority_siblings(parent, exclude=None):
    """Current active siblings in display order, with stable creation-time tie break."""
    rows=c.table('notes').select('*').eq('owner_id',uid).eq('parent_id',parent).eq('is_deleted',False).execute().data or []
    return sorted([r for r in rows if r['id']!=exclude],key=lambda r:(int(r.get('position') or 0),str(r.get('created_at') or ''),r['id']))

def apply_priority_order(parent, ordered_ids):
    """Persist contiguous 1-based priority within a folder."""
    for index,note_id in enumerate(ordered_ids,1):
        update_note(note_id,position=index)

def place_after(note_id, target_id):
    """Move a node to immediately after target, shifting subsequent priorities."""
    source=byid[note_id];target_node=byid[target_id]
    if note_id==target_id: return
    if target_id in subtree(note_id,notes):raise ValueError('不可移入自己的子節點')
    destination=target_node['parent_id']
    if source['kind']=='GROUP' and destination is not None:
        new_kind='SUBFILE';new_has_page=True
    else:new_kind=source['kind'];new_has_page=source['has_page']
    if source['kind']!='GROUP' and destination is not None and get_ancestors(destination,byid)[-1]!=get_ancestors(note_id,byid)[-1]:
        raise ValueError('一般文件跨組別請使用複製')
    old_parent=source['parent_id']
    target_siblings=priority_siblings(destination,exclude=note_id)
    ordered=[r['id'] for r in target_siblings]
    ordered.insert(ordered.index(target_id)+1,note_id)
    update_note(note_id,parent_id=destination,kind=new_kind,has_page=new_has_page)
    apply_priority_order(destination,ordered)
    if old_parent!=destination:apply_priority_order(old_parent,[r['id'] for r in priority_siblings(old_parent)])

def place_new_after(note_id,target_id):
    """Insert a newly created node after its sibling without relying on stale in-memory byid."""
    target=c.table('notes').select('*').eq('owner_id',uid).eq('id',target_id).execute().data
    if not target:raise ValueError('插入目標不存在')
    parent=target[0]['parent_id']
    ordered=[r['id'] for r in priority_siblings(parent,exclude=note_id)]
    ordered.insert(ordered.index(target_id)+1,note_id)
    apply_priority_order(parent,ordered)

def set_priority(note_id,rank):
    parent=byid[note_id]['parent_id']
    ordered=[r['id'] for r in priority_siblings(parent,exclude=note_id)]
    rank=max(1,min(int(rank),len(ordered)+1))
    ordered.insert(rank-1,note_id)
    apply_priority_order(parent,ordered)

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
    if re.search(br'<!\s*(?:DOCTYPE|ENTITY)',raw[:4096],re.I):raise ValueError('圖片不得包含 DOCTYPE 或 ENTITY')
    # ChatGPT diagrams are often copied as SVG. Pillow cannot open SVG, so
    # validate and sanitize the vector document, then retain it as SVG. It is
    # displayed only as an image; external resources and active content are
    # removed before it reaches Storage.
    if raw.lstrip().startswith(b'<') and re.search(br'<\s*svg(?:\s|>)',raw[:4096],re.I):
        try:
            root=ET.fromstring(raw)
            if root.tag.split('}')[-1].lower()!='svg':raise ValueError('無效的 SVG 圖片')
            for parent in root.iter():
                for child in list(parent):
                    if child.tag.split('}')[-1].lower() in ('script','iframe','object','embed','form'):
                        parent.remove(child)
                for name,value in list(parent.attrib.items()):
                    local=name.split('}')[-1].lower()
                    if local.startswith('on'):
                        del parent.attrib[name]
                    elif local in ('href','src') and not value.strip().startswith(('#','data:image/')):
                        del parent.attrib[name]
                    elif local=='style':
                        parent.attrib[name]=re.sub(r'url\([^)]*\)|@import[^;]*;?', '',value,flags=re.I)
                if parent.tag.split('}')[-1].lower()=='style' and parent.text:
                    parent.text=re.sub(r'url\([^)]*\)|@import[^;]*;?', '',parent.text,flags=re.I)
            viewbox=root.get('viewBox') or root.get('viewbox') or ''
            nums=[float(x) for x in re.split(r'[ ,]+',viewbox.strip()) if x]
            if len(nums)==4 and nums[2]>0 and nums[3]>0:
                width,height=nums[2],nums[3]
            else:
                def dimension(value,default):
                    match=re.match(r'^\s*(\d+(?:\.\d+)?)\s*(?:px)?\s*$',value or '')
                    return float(match.group(1)) if match else default
                width=dimension(root.get('width'),800)
                height=dimension(root.get('height'),450)
            if not math.isfinite(width) or not math.isfinite(height) or width<=0 or height<=0 or width*height>25_000_000:raise ValueError('SVG 尺寸無效或過大')
            return ET.tostring(root,encoding='utf-8'),'image/svg+xml','svg'
        except ValueError:raise
        except Exception as exc:raise ValueError('HRC-SVG-002: SVG 圖表格式無效，請檢查原始碼或改用 PNG') from exc
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
        if STORAGE_MODE in ('sqlite','browser'):return None
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
    import base64
    def replace(match):
        alt,aid=match.group(1),match.group(2)
        raw=asset_image(aid,assets)
        if not raw:return f'**[圖片無法讀取：{alt}]**'
        mime=(assets.get(aid) or {}).get('mime_type') or 'image/png'
        if mime not in ('image/png','image/jpeg','image/gif','image/webp','image/svg+xml'):mime='image/png'
        return f'![{alt}](data:{mime};base64,{base64.b64encode(raw).decode("ascii")})'
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
            if pending.get('after'):place_new_after(created[0]['id'],pending['after'])
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
    # Use the same authenticated asset bytes as the browsing view. Local
    # SQLite/IndexedDB storage cannot produce a signed remote image URL.
    initial_image=None
    if aid:
        image_data=asset_image(aid,assets)
        if image_data:
            mime=(assets.get(aid) or {}).get('mime_type') or 'image/webp'
            initial_image=f'data:{mime};base64,{base64.b64encode(image_data).decode("ascii")}'
        else:
            st.error('已保存的手寫稿圖片無法讀取，請勿在空白畫布上覆寫；請先檢查本地資料。')
    locked_key='hw_locked_'+note['id']
    pending_key='_hw_lock_pending_'+note['id']
    if st.session_state.pop(pending_key,False):
        st.session_state[locked_key]=True
    if locked_key not in st.session_state:st.session_state[locked_key]=bool(refs)
    locked=st.checkbox('屏蔽觸控（防止誤觸；取消勾選可繼續編輯）',key=locked_key)
    event=handwriting_component(key=f'handwrite_{note["id"]}_{page}',width_px=dims[0],height_px=dims[1],image_url=initial_image,locked=locked,load_error=bool(aid and not initial_image),default=None,height=510)
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
    # Composite section delimiters are structural metadata, not visible text.
    content=re.sub(r'(?m)^\s*//\[([^\]\n]+)\]//\s*$',lambda m:'\n### '+m.group(1).strip()+'\n',content)
    # Also normalize inline section markers; browsing must never expose //[...]//.
    content=re.sub(r'//\[([^\]\n]+)\]//',lambda m:m.group(1).strip(),content)
    # Normalize nested display delimiters for rendering only, not persisted content.
    content=re.sub(r'\\\[\s*\$\$([\s\S]*?)\$\$\s*\\\]',lambda m:'$$'+m.group(1)+'$$',content)
    content=re.sub(r'\$\$\s*\\\[([\s\S]*?)\\\]\s*\$\$',lambda m:'$$'+m.group(1)+'$$',content)
    # Streamlit Markdown renders standard LaTeX $...$ and $$...$$.
    content=re.sub(r'\\\[([\s\S]*?)\\\]',lambda m:'\n\n$$'+m.group(1)+'$$\n\n',content)
    content=re.sub(r'\\\((.*?)\\\)',lambda m:'$'+m.group(1)+'$',content)
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
/* Mobile markdown tables: preserve columns and enable horizontal scrolling. */
[data-testid="stMarkdownContainer"]{min-width:0;max-width:100%}
[data-testid="stMarkdownContainer"] table{display:block;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;white-space:nowrap;border-collapse:collapse}
[data-testid="stMarkdownContainer"] table th,[data-testid="stMarkdownContainer"] table td{min-width:85px;padding:7px 10px;white-space:normal;overflow-wrap:anywhere}

html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"]{max-width:100%;overflow-x:hidden!important}
[data-testid="stMain"], [data-testid="stMainBlockContainer"], .block-container{min-width:0!important;max-width:100%!important;box-sizing:border-box!important}
.block-container{padding:1.25rem clamp(.75rem,3vw,2rem) 3rem!important}
[data-testid="stHorizontalBlock"]{min-width:0!important;max-width:100%!important;flex-wrap:wrap!important}
[data-testid="column"]{min-width:0!important;max-width:100%!important}
[data-testid="stSidebar"]{width:min(310px,85vw)!important;min-width:0!important}
[data-testid="stSidebar"] iframe{width:100%!important;max-width:100%!important}
[data-testid="stSidebarContent"]{overflow-x:hidden!important}
/* Keep popovers/dialogs above schedule-card frames. */
[data-testid="stPopoverBody"], [data-testid="stDialog"], [role="dialog"]{z-index:100000!important}
[data-testid="stExpander"]{isolation:auto}
/* Use an inline expander instead of a floating popover inside the sidebar.
   The sidebar scroll container clips portal/popover content regardless of z-index. */
[data-testid="stSidebar"]{overflow:hidden!important}
[data-testid="stSidebarContent"]{overflow-x:hidden!important;overflow-y:auto!important}
[data-testid="stSidebar"] [data-testid="stExpander"]{position:relative!important;z-index:auto!important}


[data-testid="stTextArea"] textarea{width:100%!important;max-width:100%!important;box-sizing:border-box!important}
.stButton button{border-radius:8px}
</style>''',unsafe_allow_html=True)

# Sidebar dismiss: attach a document-level outside-click handler when component
# iframe and host share origin. Streamlit's native sidebar toggle remains available.
components.html("""<script>
try {
 const d=window.parent.document;
 if(!d.__bvSidebarDismiss){d.__bvSidebarDismiss=true;
 d.addEventListener('pointerdown',function(e){
   const sidebar=d.querySelector('[data-testid="stSidebar"]');
   if(!sidebar||sidebar.contains(e.target))return;
   const collapse=sidebar.querySelector('[data-testid="stSidebarCollapseButton"] button,button[aria-label*="Close sidebar"],button[aria-label*="關閉側邊欄"]');
   const expanded=sidebar.getAttribute('aria-expanded');
   if(collapse && expanded!=='false')collapse.click();
 },true);}
} catch(e) { /* Cross-origin host: retain Streamlit native behavior. */ }
</script>""",height=0)

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
# Background autoload mounts on every workspace page, not only the Settings screen.
_auto_event=auto_load_component(mode='background',ack=st.session_state.get('_auto_load_ack',[]),key='auto_load_background_v631',default=None)
if isinstance(_auto_event,dict) and _auto_event.get('nonce')!=st.session_state.get('_auto_load_nonce'):
    st.session_state['_auto_load_nonce']=_auto_event.get('nonce')
    if _auto_event.get('action')=='batch':
        reports=[];acks=[]
        for f in _auto_event.get('files',[])[:30]:
            try:
                name=str(f.get('name',''))
                payload=base64.b64decode(f['data'],validate=True)
                if len(payload)>15*1024*1024:raise ValueError('超過 15 MB')
                ext=Path(name).suffix.lower()
                if name.endswith('.bvcalendar.json'):
                    rows=read_schedule_backup(payload)
                    restore_schedule_backup(rows,'合併行程（相同 ID 更新）')
                elif ext in ('.ainote','.zip'):import_group(payload)
                elif ext in ('.md','.txt','.markdown'):
                    text_data=payload.decode('utf-8-sig')
                    if len(text_data)>500000:raise ValueError('文本過長')
                    insert_note('MARKDOWN',Path(name).name,None,content=text_data)
                else:continue
                reports.append(name+'：載入成功')
                acks.append({'name':name,'digest':f.get('digest')})
            except Exception as exc:reports.append(str(f.get('name'))+'：'+str(exc)[:120])
        st.session_state['_auto_load_report']=reports
        st.session_state['_auto_load_ack']=acks
        st.rerun()
roots=[n for n in active_notes if not n['parent_id']]
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
            if pending.get('after'):place_new_after(created['id'],pending['after'])
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

@st.dialog('新增文件',width='small')
def v43_new_file_dialog(parent_id):
    st.caption('請選擇文件類型')
    choice=st.radio('文件類型',['圖文文件','圖片','手寫稿'],horizontal=True)
    title=st.text_input('文件名稱',value='新'+choice)
    if st.button('建立',type='primary',use_container_width=True):
        kind={'圖文文件':'COMPOSITE','圖片':'GRAPH','手寫稿':'HANDWRITE'}[choice]
        if kind=='HANDWRITE':
            st.session_state.pending_handwrite={'title':title.strip(),'parent':parent_id,'after':None}
        else:
            new=insert_note(kind,title.strip() or '新文件',parent_id,position=len(children_index.get(parent_id,[]))+1)
            st.session_state.selected=new['id']
        st.session_state.pop('new_file_parent',None)
        st.session_state.pop('_new_file_dialog_open',None)
        st.rerun()

def v431_commit_focus_before_navigation():
    """Persist focused text draft before navigating away; leave focus intact on failure."""
    fid=st.session_state.get('full_edit_id')
    if not fid:return
    current=byid.get(fid)
    if current and current.get('kind') in ('MARKDOWN','SUBFILE','GROUP'):
        key='v43_draft_'+fid
        value=st.session_state.get(key,current.get('content') or '')
        if value!=(current.get('content') or ''):
            update_note(fid,content=value)
    st.session_state.pop('full_edit_id',None)
    st.session_state.pop('v43_draft_'+fid,None)
    st.session_state.pop('v43_confirm_back',None)

def v431_change_page():
    try:
        v431_commit_focus_before_navigation()
        st.session_state.pop('full_read_id',None)
    except Exception as exc:
        st.session_state['v431_navigation_error']='跳轉前儲存失敗：'+str(exc)
        st.session_state['main_page']='📝 筆記工作區'


@st.dialog('功能',width='large')
def explorer_functions_dialog():
    st.caption('檔案匯入與匯出')
    uploaded=st.file_uploader('開啟本地組別 (.ainote / .zip)',type=['ainote','zip'],key='import')
    if uploaded and st.button('匯入組別',key='dialog_import_group'):
        try:
            st.session_state.selected=import_group(uploaded.getvalue())
            st.session_state.pop('_explorer_show_functions_dialog',None)
            st.rerun()
        except Exception as exc:st.error('匯入失敗：'+str(exc))
    if selected:
        rootid=get_ancestors(selected['id'],byid)[-1]
        root=byid[rootid]
        if root['kind']=='GROUP':
            try:
                st.download_button('↓ 下載當前組別',data=export_group(root,notes),file_name=download_filename(root['title']),mime='application/zip',width='stretch')
            except Exception as exc:st.warning('暫時無法匯出：'+str(exc))
    st.caption('本地儲存路徑由瀏覽器下載設定決定；雲端網頁不能直接設定任意本地磁碟路徑。')
    if st.button('關閉',key='close_functions_dialog',width='stretch'):
        st.session_state.pop('_explorer_show_functions_dialog',None)
        st.rerun()

with st.sidebar:
    st.title('📚 BV-Text')
    st.subheader('EXPLORER')
    # Keep last active document and workspace mode in the URL across browser refreshes.
    try:
        if not st.session_state.get('_nav_url_restored'):
            st.session_state['_nav_url_restored']=True
            requested=st.query_params.get('doc')
            if requested and requested in byid and not byid[requested].get('is_deleted'):
                st.session_state.selected=requested
                mode=st.query_params.get('area','workspace')
                if mode=='edit':st.session_state.full_edit_id=requested
                elif mode=='read':st.session_state.full_read_id=requested
                st.rerun()
        active_id=st.session_state.get('full_edit_id') or st.session_state.get('full_read_id') or st.session_state.get('selected')
        if active_id in byid and not byid[active_id].get('is_deleted'):
            area='edit' if st.session_state.get('full_edit_id') else 'read' if st.session_state.get('full_read_id') else 'workspace'
            if st.query_params.get('doc')!=active_id or st.query_params.get('area')!=area:
                st.query_params['doc']=active_id
                st.query_params['area']=area
    except Exception:pass

    if st.session_state.pop('_explorer_close_sidebar',False):
        components.html("""<script>
        try { const d=window.parent.document;
          const sidebar=d.querySelector('[data-testid=\"stSidebar\"]');
          const btn=sidebar?.querySelector('[data-testid=\"stSidebarCollapseButton\"] button')
             || sidebar?.querySelector('button[aria-label*=\"Close sidebar\"]');
          if(btn)btn.click();
        } catch(e) { console.warn('Sidebar close unavailable',e); }
        </script>""",height=0)
    explorer=components.declare_component('ainote_explorer',path=str(Path(__file__).parent/'components'/'explorer'))
    payload=[{'id':n['id'],'parent_id':n['parent_id'],'kind':n['kind'],'title':n['title'],'position':n['position'],'headings':[]} for n in active_notes if n['kind']!='TABLE']
    event=explorer(nodes=payload,selected=st.session_state.get('selected'),key='explorer_v11',default=None,height=385)
    if event and event.get('event_id')!=st.session_state.get('last_explorer_event'):
        st.session_state.last_explorer_event=event.get('event_id')
        action=event.get('action');nid=event.get('id');target=event.get('target')
        try:
            op_progress=operation_progress('檔案操作') if action not in ('select','quick_nav','import_child') else None
            if op_progress:op_progress(15,'正在處理 '+str(action))
            if action=='open_functions':
                st.session_state['_explorer_show_functions_dialog']=True
                st.rerun()
            if action=='close_sidebar':
                st.session_state['_explorer_close_sidebar']=True
            if action in ('select','full_edit','full_read','quick_nav','toc_nav','toc_edit_nav','toc_browse_nav') and nid in byid:
                st.session_state['main_page']='📝 筆記工作區'
                # Every Explorer navigation commits the current focused draft, even
                # when navigating to the same node or changing reading mode.
                v431_commit_focus_before_navigation()
                st.session_state.pop('full_read_id',None)
            if action=='toc_remove' and nid in byid:
                # Browser-local IndexedDB TOC is deleted in the Explorer component.
                pass
            if action=='toc_nav' and nid in byid:
                st.session_state.selected=nid
                st.session_state.full_edit_id=nid
                st.session_state['_composite_toc_target_'+nid]=event.get('toc_id')
            elif action=='toc_browse_nav' and nid in byid:
                st.session_state.selected=nid
                st.session_state.full_read_id=nid
                st.session_state['_composite_browse_target_'+nid]=event.get('toc_id')
            elif action=='select' and nid in byid:
                st.session_state.selected=nid
            elif action=='full_edit' and nid in byid:
                st.session_state.full_edit_id=nid
                st.session_state.selected=nid
            elif action=='full_read' and nid in byid:
                st.session_state.full_read_id=nid
                st.session_state.selected=nid
            elif action=='workspace_save' and nid in byid:
                st.session_state.workspace_save_requested=True
            elif action=='workspace_close' and nid in byid:
                st.session_state.workspace_close_requested=nid
            elif action=='new_file_dialog' and (nid in byid or event.get('root')):
                st.session_state.new_file_parent=(nid if nid in byid and byid[nid]['kind'] in CONTAINERS else byid[nid]['parent_id'] if nid in byid else None)
                st.session_state['_new_file_dialog_open']=True
            elif action=='quick_nav' and nid in byid:
                st.session_state.quick_nav_root=nid
                st.session_state.selected=nid
            elif action=='rename' and nid in byid:
                title=str(event.get('title','')).strip()
                if title:update_note(nid,title=title[:200])
            elif action=='create':
                kind=event.get('kind');title=str(event.get('title','')).strip()
                parent=target if target in byid and byid[target]['kind'] in CONTAINERS else None
                after=event.get('after') if event.get('after') in byid else None
                if after and byid[after]['parent_id']!=parent:raise ValueError('插入位置必須與目標文件位於同一層')
                if kind=='GROUP':parent=None
                if kind=='HANDWRITE' and parent and title:
                    st.session_state.pending_handwrite={'title':title,'parent':parent,'after':after}
                    st.session_state.selected=parent
                    st.rerun()
                if kind=='TABLE' and parent and title:
                    st.session_state.pending_table={'title':title,'parent':parent,'after':after}
                    st.session_state.selected=parent
                    st.rerun()
                if kind in KINDS and title and (kind=='GROUP' or parent or kind in ('MARKDOWN','COMPOSITE')):
                    new=insert_note(kind,title,parent,has_page=kind=='SUBFILE',position=len([x for x in active_notes if x['parent_id']==parent])+1)
                    if after:place_new_after(new['id'],after)
                    st.session_state.selected=new['id']
            elif action=='duplicate' and nid in byid:
                source=byid[nid]
                if source['kind']=='GROUP' and source['parent_id'] is None:
                    raise ValueError('ROOT 不支援 Ctrl+D 複製；請使用 ROOT 匯出與匯入')
                new_id=clone_note(nid,source['parent_id'])
                st.session_state.selected=new_id
            elif action=='priority' and nid in byid:
                set_priority(nid,event.get('priority',1))
            elif action=='move_after' and nid in byid and target in byid:
                place_after(nid,target)
                st.session_state.selected=nid
            elif action in ('move','paste','copy'):
                if nid not in byid:raise ValueError('來源文件不存在或已被刪除')
                source=byid[nid]
                dest=target if target in byid and byid[target]['kind'] in CONTAINERS else None
                if not dest:raise ValueError('請選擇目標組別或子文件')
                if action=='move' or (action=='paste' and event.get('cut')):
                    if dest in subtree(nid,notes):raise ValueError('不能移入自己或自己的子節點')
                    if source['kind']!='GROUP' and get_ancestors(dest,byid)[-1]!=get_ancestors(nid,byid)[-1]:raise ValueError('一般文件移動僅限同一組別；跨組別請使用複製')
                    if source['parent_id']!=dest:
                        update_note(nid,parent_id=dest,kind='SUBFILE' if source['kind']=='GROUP' else source['kind'],has_page=True if source['kind']=='GROUP' else source['has_page'],position=len([x for x in active_notes if x['parent_id']==dest])+1)
                    if source['parent_id']!=dest:
                        apply_priority_order(source['parent_id'],[r['id'] for r in priority_siblings(source['parent_id'],exclude=nid)])
                        apply_priority_order(dest,[r['id'] for r in priority_siblings(dest)])
                    st.session_state.selected=nid
                else:
                    copied_id=clone_note(nid,dest)
                    st.session_state.selected=copied_id
            elif action=='import_child':
                if target not in byid or byid[target]['kind'] not in CONTAINERS:raise ValueError('請選擇組別或子文件')
                st.session_state.import_child_target=target
            elif action=='batch_delete':
                ids=event.get('ids') or []
                if not isinstance(ids,list) or len(ids)>200 or not ids or len(set(ids))!=len(ids):raise ValueError('批量選取數量無效')
                if any(x not in byid for x in ids):raise ValueError('部分選取文件不存在')
                for x in ids:delete_note(x)
            elif action=='batch_paste':
                ids=event.get('ids') or []
                dest=event.get('target');is_cut=bool(event.get('cut'))
                if not isinstance(ids,list) or len(ids)>100 or not ids or len(set(ids))!=len(ids):raise ValueError('批量貼上數量無效')
                if dest not in byid or byid[dest]['kind'] not in CONTAINERS:raise ValueError('目標必須為資料夾')
                if any(x not in byid for x in ids):raise ValueError('來源不存在')
                if any(any(x!=y and x in subtree(y,notes) for y in ids) for x in ids):raise ValueError('不能同時操作父節點與其子節點')
                if is_cut:
                    for x in ids:
                        source=byid[x]
                        if dest in subtree(x,notes):raise ValueError('不能移入自身子節點')
                        if source['kind']=='GROUP' and source['parent_id'] is None:raise ValueError('根組別不支援剪下到其他組別')
                        if get_ancestors(dest,byid)[-1]!=get_ancestors(x,byid)[-1]:raise ValueError('跨組別請使用複製')
                    for x in ids:
                        source=byid[x]
                        if source['parent_id']!=dest:update_note(x,parent_id=dest,position=len(priority_siblings(dest))+1)
                else:
                    for x in ids:clone_note(x,dest)
            elif action=='delete' and nid in byid:delete_note(nid)
            elif action=='delete_forever' and nid in byid:
                ids=list(subtree(nid,notes))
                for x in reversed(ids):
                    c.table('notes').delete().eq('id',x).eq('owner_id',uid).execute()
            elif action=='restore' and nid in byid:restore_note(nid)
            elif action=='reorder' and nid in byid and target in byid:
                a,b=byid[nid],byid[target]
                if a['parent_id']==b['parent_id']:
                    siblings=sorted([n for n in active_notes if n['parent_id']==a['parent_id']],key=lambda n:(n['position'],n['created_at']))
                    ids=[n['id'] for n in siblings if n['id']!=nid];ids.insert(ids.index(target),nid)
                    apply_priority_order(a['parent_id'],ids)
            if op_progress:
                op_progress(100,'操作完成')
                st.session_state['operation_notice']='操作完成：'+str(action)
            st.rerun()
        except Exception as exc:
            logging.getLogger(__name__).exception('Explorer action failed')
            st.error('檔案操作或跳轉前儲存失敗：'+str(exc))

    if st.session_state.get('creation_notice'):
        st.success(st.session_state.pop('creation_notice'))
    if st.session_state.get('operation_notice'):
        st.success(st.session_state.pop('operation_notice'))
    page_choice=st.radio('頁面', ['📝 筆記工作區','📅 行程表','⚙️ 設定'],key='main_page',horizontal=True,on_change=v431_change_page)
    if st.session_state.get('v431_navigation_error'):st.error(st.session_state.pop('v431_navigation_error'))
    if page_choice!='📝 筆記工作區':st.session_state.pop('full_read_id',None)
    st.divider()
    st.divider()
    st.caption('本地優先 · '+('SQLite：'+str(db_root) if STORAGE_MODE=='sqlite' else 'IndexedDB：目前瀏覽器'))
    with st.expander('☁️ 手動雲端同步（不自動上傳）'):
        st.warning('雲端同步可能產生 Supabase 流量。下載雲端資料會取代目前本地資料，請先備份。')
        confirm_upload=st.checkbox('我確認要將本地資料上傳到 Supabase',key='sync_upload_confirm')
        if st.button('↑ 手動上傳雲端',disabled=not confirm_upload,key='sync_upload_button'):
            try:
                result=push_to_cloud(cloud_client,local_db,uid)
                st.success('已上傳：'+str(result))
            except Exception as exc:st.error('雲端上傳失敗：'+str(exc))
        confirm_download=st.checkbox('我確認要以雲端資料覆蓋本地資料',key='sync_download_confirm')
        if st.button('↓ 手動下載雲端',disabled=not confirm_download,key='sync_download_button'):
            try:
                result=pull_from_cloud(cloud_client,local_db,uid)
                mark_local_change()
                st.success('已下載：'+str(result))
                st.rerun()
            except Exception as exc:st.error('雲端下載失敗：'+str(exc))
        if STORAGE_MODE=='browser':
            st.download_button('下載本地快照 JSON',data=json.dumps(local_db.export_snapshot(uid),ensure_ascii=False),file_name='BV-Text-local-backup.json',mime='application/json')
    if st.button('登出',width='stretch'):
        for k in ['user_id','access_token','refresh_token','selected','remember_enabled']:st.session_state.pop(k,None)
        st.session_state.skip_auto_login=True
        remember_action('clear')
        st.rerun()

# v4.6: modal ROOT backup; Explorer removal only after confirmed local save.
if st.session_state.get('_explorer_show_functions_dialog'):
    explorer_functions_dialog()
if st.session_state.get('_new_file_dialog_open'):
    v43_new_file_dialog(st.session_state.get('new_file_parent'))

@st.dialog('保存並關閉 ROOT',width='large')
def v46_close_root_dialog(root_id):
    root=byid.get(root_id)
    if not root or root.get('kind')!='GROUP':
        st.session_state.pop('workspace_close_requested',None)
        return
    st.write('將整個 ROOT「'+root['title']+'」保存至本地，再從目前 Explorer 關閉。')
    st.caption('PC 優先寫入授權資料夾；手機可能使用瀏覽器下載。下載啟動不代表檔案已落地。')
    overrides={}
    for node in notes:
        nid=node['id']
        for key in ('v43_draft_'+nid,'edit_'+nid,'text_'+nid,'block_content_'+nid):
            if isinstance(st.session_state.get(key),str):
                overrides[nid]=st.session_state[key]
                break
    try:
        payload=export_group(root,notes,overrides)
        result=local_component(mode='close',data=base64.b64encode(payload).decode('ascii'),filename=download_filename(root['title']),key='root_close_modal_'+root_id,default=None)
        if isinstance(result,dict) and result.get('action')=='saved':
            st.session_state['v46_close_saved_'+root_id]=result.get('method')
        if isinstance(result,dict) and result.get('action')=='error':
            st.error('保存失敗：'+str(result.get('message','')))
        method=st.session_state.get('v46_close_saved_'+root_id)
        if method:
            if method=='folder':st.success('已寫入本地檔案。可關閉 ROOT。')
            else:st.warning('已啟動下載，請先在裝置確認檔案存在且可開啟。')
            verified=st.checkbox('我已確認本地備份完整，可從 Explorer 關閉此 ROOT',key='v46_verified_'+root_id)
            if st.button('確認關閉 ROOT',type='primary',disabled=not verified,key='v46_finish_'+root_id):
                # Close persistently: remove the ROOT subtree from active workspace.
                # Soft deletion keeps a recoverable copy in the recycle bin.
                closed_ids=subtree(root_id,notes)
                set_deleted(root_id,True)
                for closed_id in closed_ids:
                    for prefix in ('v43_draft_','edit_','text_','block_content_','_composite_toc_target_','_composite_browse_target_'):
                        st.session_state.pop(prefix+closed_id,None)
                for k in ('workspace_close_requested','full_edit_id','full_read_id','v46_hidden_roots'):
                    st.session_state.pop(k,None)
                st.session_state.selected=None
                st.session_state.pop('v46_close_saved_'+root_id,None)
                st.session_state.pop('v46_verified_'+root_id,None)
                st.rerun()
    except Exception as exc:st.error('建立 ROOT 備份失敗：'+str(exc))
    if st.button('取消',key='v46_cancel_close'):
        st.session_state.pop('workspace_close_requested',None)
        st.rerun()
close_target=st.session_state.get('workspace_close_requested')
if close_target and close_target in byid:
    root_id=get_ancestors(close_target,byid)[-1]
    v46_close_root_dialog(root_id)

if st.session_state.get('import_child_target'):
    import_child_dialog()
elif st.session_state.get('quick_nav_root'):
    quick_navigation_dialog()

_SCHEDULE_OPERATORS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}
def schedule_expression(expr,d):
    """Evaluate only bounded numeric expressions involving d, no Python execution."""
    if len(expr)>90:raise ValueError('運算式過長（最多 90 字元）')
    tree=ast.parse(expr,mode='eval')
    def visit(node,depth=0):
        if depth>12:raise ValueError('運算式過於複雜')
        if isinstance(node,ast.Expression):return visit(node.body,depth+1)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return node.value
        if isinstance(node,ast.Name) and node.id=='d':return d
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            value=visit(node.operand,depth+1)
            return value if isinstance(node.op,ast.UAdd) else -value
        if isinstance(node,ast.BinOp) and type(node.op) in _SCHEDULE_OPERATORS:
            a,b=visit(node.left,depth+1),visit(node.right,depth+1)
            if abs(a)>100000000 or abs(b)>100000000:raise ValueError('數值過大')
            result=_SCHEDULE_OPERATORS[type(node.op)](a,b)
            if not isinstance(result,(int,float)) or not -100000000<=result<=100000000:raise ValueError('結果超出範圍')
            return result
        raise ValueError('只允許數字、d、+、-、*、/、//、% 與括號')
    result=visit(tree)
    return str(int(result)) if float(result).is_integer() else f'{result:.8g}'

def schedule_title_for_day(template,d):
    return re.sub(r'\(([^()]*)\)',lambda m:schedule_expression(m.group(1),d),template)

def create_schedule_series(start_day,title,days,no_time,planned,details):
    if not 1<=days<=365:raise ValueError('連續天數必須介於 1～365')
    # Prevalidate the complete batch before inserting any row.
    payload=[]
    batch_id=uuid.uuid4().hex if days>1 else None
    for d in range(days):
        current=start_day+timedelta(days=d)
        resolved=schedule_title_for_day(title.strip(),d)
        if not resolved.strip() or len(resolved)>200:raise ValueError(f'第 {d+1} 天標題為空或超過 200 字元')
        timestamp=None if no_time else datetime.combine(current,planned).replace(tzinfo=timezone(timedelta(hours=8))).isoformat()
        payload.append({'owner_id':uid,'title':resolved,'schedule_date':current.isoformat(),'scheduled_at':timestamp,'details':details,'batch_tag':title.strip() if days>1 else None,'batch_id':batch_id})
    created=[]
    try:
        for row in payload:
            result=c.table('schedule_cards').insert(row).execute().data
            if not result:raise RuntimeError('資料庫未確認新增成功')
            created.append(result[0]['id'])
    except Exception:
        for item_id in created:
            try:c.table('schedule_cards').delete().eq('id',item_id).eq('owner_id',uid).execute()
            except Exception:logging.getLogger(__name__).exception('Rollback schedule card failed')
        raise
    return len(created)

@st.dialog('快捷建立行程',width='large')
def schedule_quick_create_dialog():
    day=st.session_state.get('schedule_quick_day')
    if not day:return
    st.caption(f'排定日期：{day.isoformat()}（臺灣時間）')
    with st.form('schedule_quick_create_form'):
        title=st.text_input('標題',max_chars=200)
        no_time=st.checkbox('無指定時間',key='quick_no_time')
        planned=st.time_input('排定時間（無指定時間時忽略）',value=st.session_state.get('schedule_quick_time',datetime.now().time().replace(second=0,microsecond=0)),step=900)
        details=st.text_area('詳細內容（可留空）',max_chars=10000)
        days=st.number_input('連續建立天數',min_value=1,max_value=365,value=1,step=1,key='quick_schedule_days')
        st.caption('標題可使用 (10+d)、(501+20*d) 等算式；第一天 d=0。')
        a,b=st.columns(2)
        submit=a.form_submit_button('建立行程',type='primary',use_container_width=True)
        cancel=b.form_submit_button('取消',use_container_width=True)
    if cancel:
        st.session_state.pop('schedule_quick_day',None)
        st.rerun()
    if submit:
        if not title.strip():st.warning('請輸入標題');return
        try:
            create_schedule_series(day,title,int(days),no_time,planned,details)
            st.session_state.schedule_selected=day
            st.session_state.pop('schedule_quick_day',None)
            st.rerun()
        except Exception as exc:st.error('建立失敗：'+str(exc))

@st.dialog('編輯行程卡',width='large')
def schedule_edit_dialog(card):
    original_date=date.fromisoformat(card['schedule_date']) if card.get('schedule_date') else date.today()
    old_clock=dt_time(9,0)
    if card.get('scheduled_at'):
        try:old_clock=datetime.fromisoformat(card['scheduled_at'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).time().replace(second=0,microsecond=0)
        except (ValueError,TypeError):pass
    with st.form('schedule_edit_form'):
        new_title=st.text_input('標題',value=card.get('title') or '',max_chars=200)
        new_date=st.date_input('日期',value=original_date)
        no_time=st.checkbox('無指定時間',value=not bool(card.get('scheduled_at')),key='edit_no_time_'+str(card['id']))
        new_clock=st.time_input('排定時間（勾選無指定時間時，此欄值不會保存）',value=old_clock,step=900,key='edit_clock_'+str(card['id']))
        new_details=st.text_area('詳細內容',value=card.get('details') or '',max_chars=10000)
        new_completed=st.checkbox('已完成',value=bool(card.get('is_completed')))
        submitted=st.form_submit_button('儲存修改',type='primary')
    if submitted:
        if not new_title.strip():
            st.error('請輸入標題');return
        when=None if no_time else datetime.combine(new_date,new_clock).replace(tzinfo=timezone(timedelta(hours=8))).isoformat()
        try:
            c.table('schedule_cards').update({'title':new_title.strip(),'schedule_date':new_date.isoformat(),'scheduled_at':when,'details':new_details,'is_completed':new_completed}).eq('id',card['id']).eq('owner_id',uid).execute()
            st.session_state.schedule_selected=new_date
            st.session_state.pop('schedule_edit_id',None)
            st.rerun()
        except Exception as exc:st.error('修改失敗：'+str(exc))

SCHEDULE_BACKUP_FIELDS=('id','title','schedule_date','scheduled_at','details','created_at','is_completed','batch_tag','batch_id')
def make_schedule_backup(cards,tasks=None,checks=None):
    return json.dumps({'format':'bvtext.schedule','version':2,'exported_at':datetime.now(timezone.utc).isoformat(),
                       'daily_tasks':tasks or [],'daily_task_checks':checks or [],
                       'cards':[{k:row.get(k) for k in SCHEDULE_BACKUP_FIELDS} for row in cards]},
                      ensure_ascii=False,indent=2).encode('utf-8')
def read_schedule_backup(raw):
    if len(raw)>10*1024*1024:raise ValueError('備份檔案不可超過 10 MB')
    doc=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(doc,dict) or doc.get('format')!='bvtext.schedule' or doc.get('version') not in (1,2):
        raise ValueError('不支援的行程表格式或版本')
    rows=doc.get('cards')
    if not isinstance(rows,list) or len(rows)>20000:raise ValueError('行程卡數量或格式不正確')
    cleaned=[];ids=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError('行程卡資料格式不正確')
        rid=str(uuid.UUID(str(row.get('id'))))
        if rid in ids:raise ValueError('備份內含重複行程卡 ID')
        ids.add(rid)
        day=date.fromisoformat(str(row['schedule_date']))
        if row.get('scheduled_at'):datetime.fromisoformat(str(row['scheduled_at']).replace('Z','+00:00'))
        title=row.get('title')
        if not isinstance(title,str) or not title.strip() or len(title)>200:raise ValueError('行程卡標題不正確')
        details=row.get('details') or ''
        if not isinstance(details,str) or len(details)>50000:raise ValueError('行程內容不正確')
        cleaned.append({'id':rid,'owner_id':uid,'title':title,'schedule_date':day.isoformat(),
                        'scheduled_at':row.get('scheduled_at'),'details':details,
                        'created_at':row.get('created_at') or datetime.now(timezone.utc).isoformat(),
                        'is_completed':bool(row.get('is_completed')),
                        'batch_tag':row.get('batch_tag'),'batch_id':row.get('batch_id')})
    st.session_state['_schedule_import_daily']=(doc.get('daily_tasks',[]),doc.get('daily_task_checks',[])) if doc.get('version')==2 else ([],[])
    return cleaned
def restore_schedule_backup(rows,mode):
    # One SQLite transaction: no partial imports on errors.
    with local_db.lock,local_db.conn:
        if mode=='取代現有行程表':
            local_db.conn.execute('DELETE FROM schedule_cards WHERE owner_id=?',(uid,))
        if mode=='取代現有行程表':
            local_db.conn.execute('DELETE FROM daily_task_checks WHERE owner_id=?',(uid,))
            local_db.conn.execute('DELETE FROM daily_tasks WHERE owner_id=?',(uid,))
        tasks,checks=st.session_state.get('_schedule_import_daily',([],[]))
        for table,entries,fields in [('daily_tasks',tasks,('id','owner_id','title','no_time','task_time','details','created_at')),('daily_task_checks',checks,('id','owner_id','task_id','task_date','is_completed','created_at'))]:
            if not isinstance(entries,list) or len(entries)>20000:raise ValueError('每日任務備份格式不正確')
            for item in entries:
                if not isinstance(item,dict) or item.get('owner_id')!=uid:raise ValueError('每日任務帳號不符')
                cols=[k for k in fields if k in item]
                if 'id' not in cols:raise ValueError('每日任務缺少 ID')
                local_db.conn.execute('INSERT OR REPLACE INTO '+table+' ('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')',[int(item[k]) if k in ('no_time','is_completed') else item[k] for k in cols])
        for row in rows:
            cols=list(row)
            existing=local_db.conn.execute('SELECT owner_id FROM schedule_cards WHERE id=?',(row['id'],)).fetchone()
            if existing and existing['owner_id']!=uid:raise ValueError('行程卡 ID 與其他帳號衝突')
            local_db.conn.execute('INSERT OR REPLACE INTO schedule_cards ('+','.join(cols)+') VALUES ('+
                                  ','.join('?' for _ in cols)+')',[int(row[k]) if k=='is_completed' else row[k] for k in cols])
    mark_local_change()

# Dialogs must be invoked from the root Streamlit layout context.
# Invoking them inside calendar widgets/containers can raise
# StreamlitInvalidLayoutContextError on Streamlit Cloud.
if st.session_state.get('main_page')=='📅 行程表':
    if st.session_state.get('schedule_quick_day'):
        schedule_quick_create_dialog()
    if st.session_state.get('schedule_edit_id'):
        try:
            _dialog_cards=c.table('schedule_cards').select('*').eq('owner_id',uid).eq('id',st.session_state['schedule_edit_id']).execute().data or []
            if _dialog_cards:schedule_edit_dialog(_dialog_cards[0])
            else:st.session_state.pop('schedule_edit_id',None)
        except Exception as _dialog_exc:
            st.error('無法載入行程編輯視窗：'+str(_dialog_exc))

if st.session_state.get('main_page')=='📅 行程表':
    st.title('📅 行程表')
    st.caption('行程卡編輯後會先保存在本機 SQLite 或瀏覽器 IndexedDB。下方可另外匯出獨立的行程表備份，並從本地檔案還原。')
    try:
        schedule_backup_cards=c.table('schedule_cards').select('*').eq('owner_id',uid).execute().data or []
        schedule_backup_bytes=make_schedule_backup(schedule_backup_cards,c.table('daily_tasks').select('*').eq('owner_id',uid).execute().data or [],c.table('daily_task_checks').select('*').eq('owner_id',uid).execute().data or [])
    except Exception as exc:
        st.error('無法準備行程表備份：'+str(exc))
        schedule_backup_bytes=None
    with st.expander('💾 保存行程表到本地',expanded=False):
        st.caption('與筆記相同：桌面瀏覽器優先寫入已授權的本地資料夾；手機瀏覽器改為下載。請確認下載檔案確實存在。')
        if schedule_backup_bytes is not None:
            schedule_event=local_component(mode='schedule',data=base64.b64encode(schedule_backup_bytes).decode('ascii'),
                filename='BV-Text-Schedule-'+date.today().isoformat()+'.bvcalendar.json',
                key='schedule_local_backup_v1',default=None)
            if isinstance(schedule_event,dict) and schedule_event.get('token')!=st.session_state.get('schedule_last_save_token'):
                st.session_state.schedule_last_save_token=schedule_event['token']
                if schedule_event.get('action')=='saved':
                    if schedule_event.get('method')=='folder':st.success('行程表已寫入授權的本地資料夾。')
                    else:st.info('已啟動下載，請確認手機下載項目內有備份檔案。')
                elif schedule_event.get('action')=='error':st.error('行程表保存失敗：'+str(schedule_event.get('message')))
            st.download_button('⬇️ 直接下載行程表 JSON',data=schedule_backup_bytes,
                file_name='BV-Text-Schedule-'+date.today().isoformat()+'.bvcalendar.json',
                mime='application/json',key='schedule_download_fallback')
    with st.expander('📂 從本地選擇行程表載入',expanded=False):
        upload=st.file_uploader('選擇先前保存的 .bvcalendar.json 行程表備份',
                                type=['json'],key='schedule_import_file')
        import_mode=st.radio('載入方式',['合併行程（相同 ID 更新）','取代現有行程表'],key='schedule_import_mode',
                             help='合併不刪除既有行程；取代會刪除本帳號原有的全部行程卡。')
        if upload is not None:
            try:
                import_rows=read_schedule_backup(upload.getvalue())
                st.info(f'檔案驗證通過：包含 {len(import_rows)} 張行程卡。')
                if import_mode=='取代現有行程表':
                    st.warning(f'取代模式將移除目前 {len(schedule_backup_cards)} 張行程卡。請先保存備份。')
                confirm_import=st.checkbox('我確認要載入此行程表',key='schedule_import_confirm')
                if st.button('載入行程表',disabled=not confirm_import,key='schedule_import_apply',type='primary'):
                    restore_schedule_backup(import_rows,import_mode)
                    st.session_state.pop('schedule_import_file',None)
                    st.session_state.pop('schedule_import_confirm',None)
                    st.success(f'已載入 {len(import_rows)} 張行程卡。')
                    st.rerun()
            except Exception as exc:st.error('無法載入行程表：'+str(exc))
    st.caption('點選日期可查看或新增行程；滑鼠停留日期按鈕可查看當日行程簡表。')
    try:
        cards=c.table('schedule_cards').select('id,title,schedule_date,scheduled_at,details,created_at,is_completed,batch_tag,batch_id').eq('owner_id',uid).execute().data or []
    except Exception as exc:
        st.error('無法載入行程表。請先執行專案內 migrations/20261011_schedule_cards.sql，並確認 RLS 權限。')
        st.code(str(exc))
        st.stop()
    def parse_card_day(card):
        try:return date.fromisoformat(card['schedule_date']) if card.get('schedule_date') else datetime.fromisoformat(card['scheduled_at'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).date()
        except Exception:return None
    def parse_card_clock(card):
        if not card.get('scheduled_at'):return '無指定時間'
        try:return datetime.fromisoformat(card['scheduled_at'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).strftime('%H:%M')
        except Exception:return '--:--'
    schedule_by_day=defaultdict(list)
    for card in cards:
        d=parse_card_day(card)
        if d:schedule_by_day[d].append(card)
    # 每日內無時間者優先，接著依指定時間、建立順序。
    def schedule_sort_key(item):
        if not item.get('scheduled_at'):
            return (0,item.get('created_at') or '',item['id'])
        return (1,parse_card_clock(item),item.get('created_at') or '',item['id'])
    for entries in schedule_by_day.values():entries.sort(key=schedule_sort_key)
    if 'schedule_target' not in st.session_state:st.session_state.schedule_target=date.today()
    if 'schedule_selected' not in st.session_state:st.session_state.schedule_selected=date.today()
    left,right=st.columns([1.7,1],gap='large')
    with left:
        target=st.date_input('目標月份（Target）',key='schedule_target')
        weeks=calendar.monthcalendar(target.year,target.month)
        st.markdown(f'### {target.year} 年 {target.month} 月')
        st.caption('橫軸：星期一至星期日；縱軸：週次。左鍵查看，右鍵快捷建立行程。')
        display_mode=st.radio('月曆格子顯示', ['顯示日期','顯示待處理項目數'],horizontal=True,key='schedule_display_mode')
        days=[]
        for wi,week in enumerate(weeks):
            days.append([{'day':date(target.year,target.month,num).isoformat(),
                          'number':num,
                          'count':len(schedule_by_day.get(date(target.year,target.month,num),[])),
                          'pending':sum(not item.get('is_completed',False) for item in schedule_by_day.get(date(target.year,target.month,num),[])),
                          'tip':'\n'.join(f"{x['title']} · {parse_card_clock(x)}" for x in schedule_by_day.get(date(target.year,target.month,num),[])) or '當日無行程'} if num else None for num in week])
        event=schedule_calendar_component(today=date.today().isoformat(),weeks=days,display_mode='pending' if display_mode=='顯示待處理項目數' else 'date',selected=st.session_state.schedule_selected.isoformat(),key=f'schedule_calendar_{target.year}_{target.month}',default=None)
        if isinstance(event,dict) and event.get('id')!=st.session_state.get('schedule_calendar_event_id'):
            st.session_state.schedule_calendar_event_id=event.get('id')
            try:
                clicked=date.fromisoformat(event['day'])
                st.session_state.schedule_selected=clicked
                if event.get('action')=='create':
                    st.session_state.schedule_quick_day=clicked
                    st.session_state.schedule_quick_time=datetime.now(timezone(timedelta(hours=8))).time().replace(second=0,microsecond=0)
                st.rerun()
            except (ValueError,KeyError,TypeError):pass
        st.divider()
        st.markdown('### 每日任務')
        st.caption('每日任務獨立於行程卡，不計入日曆的行程數量。勾選狀態依日期分別保存。')
        daily_day=st.session_state.schedule_selected.isoformat()
        try:
            daily_templates=c.table('daily_tasks').select('*').eq('owner_id',uid).execute().data or []
            daily_checks=c.table('daily_task_checks').select('*').eq('owner_id',uid).eq('task_date',daily_day).execute().data or []
        except Exception as exc:
            daily_templates=[];daily_checks=[]
            st.error('每日任務資料無法載入，請確認已完成 v4.1 資料表升級：'+str(exc))
        checked_ids={x['task_id'] for x in daily_checks if x.get('is_completed')}
        daily_order=sorted(daily_templates,key=lambda x:(not bool(x.get('no_time')),x.get('task_time') or '',x.get('created_at') or '',x['id']))
        daily_payload=[{'id':x['id'],'title':x['title'],'details':x.get('details') or '',
                        'day':daily_day,'clock':'無指定時間' if x.get('no_time') else str(x.get('task_time') or '09:00'),
                        'completed':x['id'] in checked_ids,'tag':''} for x in daily_order]
        daily_event=schedule_cards_component(cards=daily_payload,key='daily_compact_cards_v632',default=None)
        if isinstance(daily_event,dict) and daily_event.get('nonce')!=st.session_state.get('_daily_card_event_nonce'):
            st.session_state['_daily_card_event_nonce']=daily_event.get('nonce')
            task=next((x for x in daily_templates if x['id']==daily_event.get('id')),None)
            if task:
                action=daily_event.get('action')
                if action=='edit':
                    st.session_state['daily_task_choice']=task['title']+' · '+task['id'][:8];st.rerun()
                elif action=='delete':
                    st.session_state['_daily_delete_target']=task['id'];st.rerun()
                elif action=='complete':
                    done=bool(daily_event.get('value'))
                    try:
                        old=next((x for x in daily_checks if x['task_id']==task['id']),None)
                        if old:c.table('daily_task_checks').update({'is_completed':done}).eq('id',old['id']).eq('owner_id',uid).execute()
                        else:c.table('daily_task_checks').insert({'owner_id':uid,'task_id':task['id'],'task_date':daily_day,'is_completed':done}).execute()
                        st.rerun()
                    except Exception as exc:st.error('儲存每日完成狀態失敗：'+str(exc))
        if st.session_state.get('_daily_delete_target'):
            target=st.session_state['_daily_delete_target']
            if any(x['id']==target for x in daily_templates):
                st.warning('確定刪除此每日任務？')
                dc1,dc2=st.columns(2)
                if dc1.button('確認刪除每日任務',key='daily_delete_confirm_v632'):
                    c.table('daily_task_checks').delete().eq('task_id',target).eq('owner_id',uid).execute()
                    c.table('daily_tasks').delete().eq('id',target).eq('owner_id',uid).execute()
                    st.session_state.pop('_daily_delete_target',None);st.rerun()
                if dc2.button('取消刪除',key='daily_delete_cancel_v632'):
                    st.session_state.pop('_daily_delete_target',None);st.rerun()
        with st.expander('⚙️ 每日任務設定／新增／編輯／刪除',expanded=False):
            choices={'＋ 新增每日任務':None,**{x['title']+' · '+x['id'][:8]:x for x in daily_templates}}
            choice=st.selectbox('選擇每日任務',list(choices),key='daily_task_choice')
            target_edit=st.session_state.pop('_daily_edit_target',None)
            if target_edit:
                for option,item in choices.items():
                    if item and item['id']==target_edit:
                        choice=option;break
            editing_task=choices[choice]
            with st.form('daily_task_form_'+(editing_task['id'] if editing_task else 'new')):
                task_title=st.text_input('任務標題',value=(editing_task or {}).get('title') or '',max_chars=200)
                task_no_time=st.checkbox('無指定時間',value=bool((editing_task or {}).get('no_time',True)))
                try:task_clock=dt_time.fromisoformat((editing_task or {}).get('task_time') or '09:00')
                except ValueError:task_clock=dt_time(9,0)
                task_time=st.time_input('時間（無指定時間時忽略）',value=task_clock,step=900)
                task_details=st.text_area('詳細內容',value=(editing_task or {}).get('details') or '',max_chars=10000)
                ca,cb=st.columns(2)
                save_task=ca.form_submit_button('儲存每日任務',type='primary')
                delete_task=cb.form_submit_button('刪除每日任務',disabled=editing_task is None)
            if save_task:
                if not task_title.strip():st.warning('請輸入任務標題')
                else:
                    values={'title':task_title.strip(),'no_time':task_no_time,'task_time':None if task_no_time else task_time.strftime('%H:%M'),'details':task_details}
                    try:
                        if editing_task:c.table('daily_tasks').update(values).eq('id',editing_task['id']).eq('owner_id',uid).execute()
                        else:c.table('daily_tasks').insert({'owner_id':uid,**values}).execute()
                        st.rerun()
                    except Exception as exc:st.error('儲存每日任務失敗：'+str(exc))
            if delete_task and editing_task:
                try:
                    c.table('daily_task_checks').delete().eq('task_id',editing_task['id']).eq('owner_id',uid).execute()
                    c.table('daily_tasks').delete().eq('id',editing_task['id']).eq('owner_id',uid).execute()
                    st.rerun()
                except Exception as exc:st.error('刪除每日任務失敗：'+str(exc))
    with right:
        st.markdown('### 全部行程卡（依距離目前時間排序）')
        with st.expander('⋯ 行程選項',expanded=False):
            st.markdown('**批量刪除**')
            tagged={x['batch_tag'] for x in cards if x.get('batch_tag')}
            if tagged:
                tag=st.selectbox('選擇批量建立時的原始標題',sorted(tagged),key='schedule_batch_delete_tag')
                tagged_cards=[x for x in cards if x.get('batch_tag')==tag]
                st.caption(f'符合此標籤：{len(tagged_cards)} 張（涵蓋不同日期，包含已編輯標題的卡片）')
                if len({x.get('batch_id') for x in tagged_cards if x.get('batch_id')})>1:
                    st.caption('不同批次使用同一個原始標題時，也會一併選取。')
                confirm=st.checkbox('確認刪除以上所有符合標籤的行程卡',key='schedule_batch_delete_confirm')
                if st.button('刪除所選標題的所有行程',type='primary',disabled=not confirm,key='schedule_batch_delete_action'):
                    deleted=0
                    try:
                        for card in tagged_cards:
                            c.table('schedule_cards').delete().eq('id',card['id']).eq('owner_id',uid).execute()
                            deleted+=1
                        st.toast(f'已刪除 {deleted} 張行程卡')
                        st.rerun()
                    except Exception as exc:
                        st.error(f'已刪除 {deleted}/{len(tagged_cards)} 張，後續刪除失敗：{exc}')
            else:st.caption('目前沒有帶批量建立標籤的行程卡。')
        chosen=st.date_input('查詢日期',key='schedule_selected')
        top_n=st.number_input('顯示最上方 N 張',min_value=1,max_value=100,value=5,step=1,key='schedule_top_n')
        now_tw=datetime.now(timezone(timedelta(hours=8)))
        def upcoming_sort_key(item):
            day=parse_card_day(item)
            if day is None:return (float('inf'),1,'',item.get('created_at') or '',item['id'])
            clock=dt_time(0,0)
            if item.get('scheduled_at'):
                try:clock=datetime.fromisoformat(item['scheduled_at'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).time()
                except (ValueError,TypeError):pass
            moment=datetime.combine(day,clock).replace(tzinfo=timezone(timedelta(hours=8)))
            return (abs((moment-now_tw).total_seconds()),0 if not item.get('scheduled_at') else 1,day.isoformat(),item.get('created_at') or '',item['id'])
        today_cards=sorted(cards,key=upcoming_sort_key)
        st.caption(f'所有日期共 {len(today_cards)} 張，依與現在時間的距離排序，顯示 {min(len(today_cards),int(top_n))} 張；無時間者視為當天 00:00')
        schedule_card_payload=[{'id':item['id'],'title':item['title'],'details':item.get('details') or '',
                                'day':str(item.get('schedule_date') or ''),'clock':parse_card_clock(item),
                                'completed':bool(item.get('is_completed')),'tag':item.get('batch_tag') or ''}
                               for item in today_cards[:int(top_n)]]
        card_event=schedule_cards_component(cards=schedule_card_payload,key='schedule_compact_cards_v631',default=None)
        if isinstance(card_event,dict) and card_event.get('nonce')!=st.session_state.get('_schedule_card_event_nonce'):
            st.session_state['_schedule_card_event_nonce']=card_event.get('nonce')
            target=next((item for item in cards if item['id']==card_event.get('id')),None)
            if target:
                action=card_event.get('action')
                if action=='edit':
                    st.session_state.schedule_edit_id=target['id'];st.rerun()
                elif action=='complete':
                    try:
                        c.table('schedule_cards').update({'is_completed':bool(card_event.get('value'))}).eq('id',target['id']).eq('owner_id',uid).execute()
                        st.rerun()
                    except Exception as exc:st.error('更新狀態失敗：'+str(exc))
                elif action=='delete':
                    st.session_state['_schedule_delete_pending']=target['id'];st.rerun()
        pending_delete=st.session_state.get('_schedule_delete_pending')
        if pending_delete and any(x['id']==pending_delete for x in cards):
            with st.container(border=True):
                st.warning('確定刪除此行程卡？')
                dc1,dc2=st.columns(2)
                if dc1.button('確認刪除',key='schedule_delete_confirm_v631'):
                    try:
                        c.table('schedule_cards').delete().eq('id',pending_delete).eq('owner_id',uid).execute()
                        st.session_state.pop('_schedule_delete_pending',None);st.rerun()
                    except Exception as exc:st.error('刪除失敗：'+str(exc))
                if dc2.button('取消',key='schedule_delete_cancel_v631'):
                    st.session_state.pop('_schedule_delete_pending',None);st.rerun()
        with st.expander('＋ 建立新行程',expanded=False):
            with st.form('schedule_create',clear_on_submit=True):
                title=st.text_input('標題',max_chars=200)
                no_time=st.checkbox('無指定時間',key='schedule_create_no_time')
                planned=st.time_input('排定時間（無指定時間時忽略）',value=dt_time(9,0),step=900)
                details=st.text_area('詳細內容（可留空）',max_chars=10000)
                days=st.number_input('連續建立天數',min_value=1,max_value=365,value=1,step=1,key='schedule_create_days')
                st.caption('支援 (10+d)、(501+20*d)；第一天 d=0。')
                submit=st.form_submit_button('建立行程',type='primary')
            if submit:
                if not title.strip():st.warning('請輸入標題')
                else:
                    try:
                        total=create_schedule_series(chosen,title,int(days),no_time,planned,details)
                        st.success(f'已建立 {total} 張行程卡')
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
        if STORAGE_MODE=='sqlite':
            path_col,open_col=st.columns([4,1])
            path_col.code(str(db_root))
            if open_col.button('📂 開啟資料夾',key='open_sqlite_folder'):
                try:
                    import subprocess,sys
                    db_root.mkdir(parents=True,exist_ok=True)
                    if sys.platform=='win32':os.startfile(str(db_root))
                    elif sys.platform=='darwin':subprocess.Popen(['open',str(db_root)])
                    else:subprocess.Popen(['xdg-open',str(db_root)])
                    st.success('已要求本機開啟資料夾')
                except Exception as exc:st.error('無法開啟資料夾：'+str(exc))
        else:
            st.caption('IndexedDB 位於瀏覽器內，沒有可由網站直接開啟的 Windows 固定路徑。下方按鈕可開啟瀏覽器資料夾選擇器。')
        local_component(mode='settings',key='local_save_settings_v1',default=None)
    with st.container():
        st.markdown('#### 自動 Load 路徑（與儲存路徑分開）')
        st.caption('可在下方關閉自動載入。啟用後重新整理頁面會掃描指定資料夾中的 FOLD 備份、文件與行程表；需保留瀏覽器資料夾讀取權限。')
        auto_load_component(mode='settings',key='auto_load_settings_v631',default=None)
        if st.session_state.get('_auto_load_report'):
            st.caption('最近一次自動載入：')
            for report in st.session_state['_auto_load_report'][:30]:st.caption(report)
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

DEMO_GUIDE = '# BV-Text 使用者操作指南\n\n## 1. 開始使用\n開啟 BV-Text 後進入筆記工作臺。若尚無文件，可以建立「空 FOLD」或「教學 FOLD」。FOLD 是資料夾，FILE 是可編輯的內容；教學 FOLD 會包含本操作指南。\n\n## 2. 文件類型\n- **圖文文件**：編輯文字、標題、清單、Markdown 表格及圖片。\n- **圖片**：上傳與檢視照片。\n- **手寫稿**：使用畫布手寫、繪圖與管理多頁內容。\n\n## 3. 新增文件\n1. 在左側 Explorer 選取 FOLD。\n2. 右鍵選擇「新增文件」，再次右鍵展開子選單，選擇圖文文件、圖片或手寫稿。\n3. 直接點擊「新增文件」則會在畫面中央顯示小型類型選擇視窗。\n4. 輸入名稱並建立。手機使用觸控選單操作。\n\n## 4. 單一編輯\n1. 選取 FILE，開啟完全單一編輯。\n2. 編輯區置於畫面中央，上方提供「儲存」「返回」「更多操作」。\n3. 「儲存」保存變更而不離開；「返回」遇到未儲存內容時會要求確認。\n4. 頁面下方的「提交」會儲存後關閉。\n5. 工作臺編輯模式僅顯示節點標題及輸入框；保存增量更新與關閉可由右鍵選單操作。\n\n## 5. 完全單一閱讀\n- 對 FILE 開啟：閱讀單一文件。\n- 對 FOLD 開啟：依節點優先權將其下所有文件串成連續長頁面。\n- 閱讀不會更改文件內容；結束時返回原工作臺。\n\n## 6. 文件操作\n1. 在 Explorer 對 FOLD 或 FILE 右鍵。\n2. 選擇「文件操作」並再次右鍵展開。\n3. 可調整節點優先權、複製、剪下、移動、貼上、移動回收桶或永久刪除。\n4. 永久刪除無法依賴回收桶復原，操作前先匯出備份。\n\n## 7. 瀏覽與快速定位\n切換至瀏覽模式，選擇快速定位的目標段落。系統會嘗試捲動至目前頁面的對應位置；若瀏覽器限制自動捲動，可點擊段落連結。\n\n## 8. 保存與備份\n- 增量儲存會保存編輯中的變更。\n- 本地備份可下載 `.ainote` 文件，或在瀏覽器支援且取得授權時寫入本地資料夾。\n- 可以從本機選擇 `.ainote` 或支援的 ZIP 文件重新匯入。\n- 手機瀏覽器可能改用下載，請確認下載檔案實際存在。\n- 建議定期保存獨立備份，勿只依賴單一瀏覽器或雲端。\n\n## 9. 行程表\n1. 開啟行程表，選擇日期並建立行程卡。\n2. 可設定連續建立天數；標題運算式中的 `d` 從 0 起算。\n3. 例如 `ipas複習第(10+d)張` 連續三天會得到第 10、11、12 張。\n4. 批量建立時保留原始標題 Tag，可依 Tag 批量刪除。\n5. 行程表可以保存為本地 JSON 備份，也可選擇備份檔案載入。\n\n## 10. 常見問題\n**儲存後沒有下載檔案？** 檢查瀏覽器下載設定與權限，必要時使用直接下載。\n\n**關閉頁面後找不到內容？** 確認先前已完成儲存，並檢查本地備份。\n\n**手機無法寫入指定資料夾？** 部分瀏覽器不支援資料夾寫入 API，請使用下載方式。\n\n**舊表格怎麼辦？** v4.3 將移除獨立 TABLE 類型。升級前先匯出備份，確認資料不再需要後再執行清理。\n'

if not selected:
    st.title('歡迎使用 BV-Text')
    st.info('目前沒有組別。')
    creation_type=st.radio('新增文件類型',options=['空 FOLD','教學 FOLD'],horizontal=True,key='empty_workspace_creation_type',help='兩種模式都只建立一個根 FOLD，不會產生子 FOLD。')
    creation_title=st.text_input('FOLD 名稱',value='我的第一份筆記' if creation_type=='教學 FOLD' else '新 FOLD',key='empty_workspace_creation_title')
    if st.button('＋ 新增文件',type='primary',key='empty_workspace_create'):
        if not creation_title.strip():
            st.warning('請輸入 FOLD 名稱。')
        else:
            try:
                op=operation_progress('建立 FOLD');op(20,'建立根節點')
                root=insert_note('GROUP',creation_title.strip(),has_page=False)
                if creation_type=='教學 FOLD':
                    op(65,'建立教學 FILE')
                    insert_note('COMPOSITE','使用說明書',root['id'],content=DEMO_GUIDE,position=1)
                op(100,'建立完成')
                st.session_state.selected=root['id']
                st.rerun()
            except Exception as exc:
                st.error('建立失敗：'+str(exc))
    st.stop()

# The GROUP is the browsing unit. Editing remains at the selected workspace level.
group=selected
while group.get('parent_id') and group['kind']!='GROUP':
    group=byid.get(group['parent_id'],group)
    if group['kind']=='GROUP':break
workspace=selected if selected['kind'] in CONTAINERS else byid.get(selected.get('parent_id'),selected)
workspace_id=workspace['id']
workspace_blocks=sorted(
    [n for n in children_index.get(workspace_id,[]) if n['kind'] not in CONTAINERS and n['kind']!='TABLE'],
    key=lambda n:(n.get('position',0),n.get('created_at',''))
)
assets={}
# Load asset metadata only if the group/workspace contains image references.
needs_assets=any('asset://' in (n.get('content') or '') for n in active_notes if n['kind'] in ('GRAPH','HANDWRITE','COMPOSITE','MARKDOWN'))
if needs_assets:
    try:
        assets={a['id']:a for a in c.table('assets').select('id,storage_path,mime_type,note_id').eq('owner_id',uid).execute().data}
    except Exception:
        logging.getLogger(__name__).exception('Asset list failed')

# Map persisted asset references to browser-readable signed URLs for the rich editor.
# The Markdown source retains asset:// identifiers, never expiring URLs.
def composite_asset_urls(content):
    """Embed owned assets directly: no signed URL, browser auth or iframe CORS dependency."""
    import base64
    ids=set(re.findall(r'asset://([0-9a-fA-F-]{36})',str(content or '')))
    result={}
    for aid in ids:
        raw=asset_image(aid,assets)
        if raw:
            mime=(assets.get(aid) or {}).get('mime_type') or 'image/png'
            if raw.lstrip().startswith(b'<svg') or (raw.lstrip().startswith(b'<?xml') and b'<svg' in raw[:500]):
                mime='image/svg+xml'
            if mime not in ('image/png','image/jpeg','image/gif','image/webp','image/svg+xml'):
                mime='image/png'
            result[aid]='data:'+mime+';base64,'+base64.b64encode(raw).decode('ascii')
    return result

# 本地備份與關閉操作保留在 Explorer 右鍵選單；不在編輯頁面頂部顯示。

def selected_source_line(content, selection):
    """Match a selected rendered phrase to its original Markdown line; reject ambiguity."""
    needle=' '.join(str(selection or '').split()).strip()
    if not needle or len(needle)>500:return None
    lines=content.splitlines(keepends=True)
    matches=[]
    for i,line in enumerate(lines):
        plain=re.sub(r'(?<!\\)[*_`#>\[\]]','',line)
        if needle in ' '.join(plain.split()) or needle in ' '.join(line.split()):matches.append(i)
    return matches[0] if len(matches)==1 else None

SPLIT_META_RE=re.compile(r'(?m)^<!-- bv-split:(upper|lower):([0-9a-f-]{36}):([0-9a-f-]{36}):([A-Za-z0-9_-]+) -->\n?')
def split_meta(content):
    m=SPLIT_META_RE.search(content or '')
    if not m:return None
    try:
        import base64
        name=base64.urlsafe_b64decode(m.group(4)+'='*(-len(m.group(4))%4)).decode('utf-8')
        return m.group(1),m.group(2),m.group(3),name
    except Exception:return None

EDITOR_MODE_RE=re.compile(r'^<!-- bv-editor-mode:(HRC|COM|MD) -->\n?')
def editor_mode(content):
    m=EDITOR_MODE_RE.match(content or '')
    return 'HRC'
def with_editor_mode(content,mode):
    content=EDITOR_MODE_RE.sub('',content or '')
    return content
def save_composite_event(note_id,event):
    converted=str(event.get('markdown',''))
    image_items=event.get('images',[])
    if not isinstance(image_items,list):raise ValueError('HRC-SAVE-001: 圖片資料清單格式無效')
    references={int(i) for i in re.findall(r'clipboard-image://(\d+)(?!\d)',converted)}
    if any(i>=len(image_items) for i in references):
        raise ValueError('HRC-SAVE-002: 文件引用的圖片未包含於提交資料')
    uploaded_by_digest={}
    for i in sorted(references):
        item=image_items[i]
        data=item.get('data','') if isinstance(item,dict) else ''
        if not data.startswith('data:image/') or ';base64,' not in data:
            raise ValueError(f'HRC-SAVE-003: 圖片 {i} 資料不完整')
        try:raw=base64.b64decode(data.split(';base64,',1)[1],validate=True)
        except Exception as exc:raise ValueError(f'HRC-SAVE-004: 圖片 {i} Base64 解碼失敗') from exc
        import hashlib
        digest=hashlib.sha256(raw).hexdigest()
        if digest not in uploaded_by_digest:
            try:uploaded_by_digest[digest]=upload_image(raw,note_id)
            except Exception as exc:raise ValueError(f'HRC-SAVE-005: 圖片 {i} 上傳失敗：{exc}') from exc
        aid=uploaded_by_digest[digest]
        converted=re.sub(r'clipboard-image://'+str(i)+r'(?![0-9])','asset://'+aid,converted)
    if re.search(r'clipboard-image://\d+',converted):raise ValueError('HRC-SAVE-006: 存在尚未處理的圖片引用')
    converted=with_editor_mode(converted,'HRC')
    update_note(note_id,content=converted)
    return converted


def reader_operation(note,event):
    # TOC entries are maintained by the reader's IndexedDB; no server-side split actions.
    return

def show_composite_reader(note):
    content=note.get('content') or ''
    event=composite_reader_component(documentId=note['id'],content=content,assetUrls=composite_asset_urls(content),revision=note.get('updated_at') or '',tocTargetId=st.session_state.pop('_composite_browse_target_'+note['id'],None),restore=st.session_state.get('_reader_restore_'+note['id']),key='reader_'+note['id'],default=None)
    reader_operation(note,event)

read_id=st.session_state.get('full_read_id')
if read_id and read_id in byid:
    root_read=byid[read_id]
    st.markdown('<style>.block-container{max-width:900px!important;margin:auto!important}</style>',unsafe_allow_html=True)
    head,exit_col=st.columns([7,1])
    with head:st.title('完全單一閱讀 · '+root_read['title'])
    with exit_col:
        if st.button('↩ 返回',key='v43_read_exit'):
            st.session_state.pop('full_read_id',None);st.rerun()
    def walk_read(n,seen=None):
        seen=set() if seen is None else seen
        if n['id'] in seen:return
        seen.add(n['id'])
        if n['kind'] in CONTAINERS:
            if n['id']!=read_id:st.header(n['title'])
            for child in sorted(children_index.get(n['id'],[]),key=lambda x:(x.get('position',0),x.get('created_at') or '')):
                walk_read(child,seen)
        elif n['kind']!='TABLE':
            st.subheader(n['title'])
            if n.get('content'):
                if n['kind']=='COMPOSITE':
                    show_composite_reader(n)
                else:
                    show_markdown(n['content'],assets)
            else:st.caption('此文件尚無內容')
    walk_read(root_read)
    st.stop()
# Full-focus editor: the Streamlit sidebar remains available for navigation.
full_id=st.session_state.get('full_edit_id')
if full_id and full_id in byid:
    full_note=byid[full_id]
    st.markdown('<style>.block-container{max-width:900px!important;margin:auto!important;padding-top:1.5rem!important}</style>',unsafe_allow_html=True)
    draft_key='v43_draft_'+full_id
    original=full_note.get('content') or ''
    if draft_key not in st.session_state:st.session_state[draft_key]=original
    draft=st.session_state[draft_key]
    dirty=draft!=original
    def save_focus():
        value=st.session_state.get(draft_key,original)
        if full_note['kind']!='COMPOSITE' and value!=original:update_note(full_id,content=value)
    focus_heading_col,focus_save_col,focus_back_col=st.columns([6,1,1])
    with focus_heading_col:st.subheader('編輯 · '+full_note['title'])
    with focus_save_col:
        if st.button('💾 儲存',key='v43_save'):
            try:save_focus();st.success('已儲存')
            except Exception as exc:st.error('儲存失敗：'+str(exc))
    with focus_back_col:
        if st.button('↩ 返回',key='v43_back'):
            if dirty:st.session_state['v43_confirm_back']=True
            else:st.session_state.pop('full_edit_id',None);st.session_state.pop(draft_key,None);st.rerun()
    if st.session_state.get('v43_confirm_back'):
        st.warning('有尚未儲存的內容，確定要返回嗎？')
        x,y,z=st.columns(3)
        with x:
            if st.button('儲存並返回'):
                try:save_focus();st.session_state.pop('full_edit_id',None);st.session_state.pop(draft_key,None);st.session_state.pop('v43_confirm_back',None);st.rerun()
                except Exception as exc:st.error(str(exc))
        with y:
            if st.button('不儲存返回'):
                st.session_state.pop('full_edit_id',None);st.session_state.pop(draft_key,None);st.session_state.pop('v43_confirm_back',None);st.rerun()
        with z:
            if st.button('取消返回'):st.session_state.pop('v43_confirm_back',None);st.rerun()
    with st.popover('⋯ 更多操作'):
        st.caption('文件類型：'+full_note['kind'])
        if st.button('完全單一閱讀',key='v43_read_from_edit'):
            try:
                v431_commit_focus_before_navigation()
                st.session_state.full_read_id=full_id;st.rerun()
            except Exception as exc:st.error('跳轉前儲存失敗：'+str(exc))
    st.divider()
    if full_note['kind']=='COMPOSITE':
        text_key='block_content_'+full_id
        current=str(st.session_state.get(text_key,original) or '')
        event=composite_component(documentId=full_id,content=current,assetUrls=composite_asset_urls(current),revision=st.session_state.get('_composite_rev_'+full_id,0),tocTargetId=st.session_state.get('_composite_toc_target_'+full_id),editorMode=editor_mode(current),submitRequest=st.session_state.get('_submit_request_'+full_id,0),key='focus_composite_'+full_id,default=None)
        if isinstance(event,dict) and event.get('nonce')!=st.session_state.get('_focus_composite_nonce_'+full_id):
            st.session_state['_focus_composite_nonce_'+full_id]=event.get('nonce')
            if event.get('action')=='headings':
                st.session_state[text_key]=str(event.get('markdown',current))
                st.rerun()
            if event.get('action') in ('save','save_close'):
                try:
                    converted=save_composite_event(full_id,event)
                    st.session_state[text_key]=converted
                    st.session_state[draft_key]=converted
                    st.session_state['_composite_rev_'+full_id]=st.session_state.get('_composite_rev_'+full_id,0)+1
                    if event.get('action')=='save_close':
                        st.session_state.pop('_submit_request_'+full_id,None)
                        st.session_state.pop('full_edit_id',None)
                        st.session_state.pop(draft_key,None)
                    st.success('圖文文件已儲存')
                    st.rerun()
                except Exception as exc:st.error('HRC-SAVE-007 圖文文件儲存失敗，仍保留編輯畫面：'+str(exc))
    elif full_note['kind'] in ('MARKDOWN','SUBFILE','GROUP'):
        st.text_area('內容',key=draft_key,height=560,label_visibility='collapsed',placeholder='開始輸入內容…')
    elif full_note['kind']=='GRAPH':image_editor(full_note,assets,full_id)
    elif full_note['kind']=='HANDWRITE':handwriting_editor(full_note,assets)
    else:st.warning('此舊版文件類型已停止編輯。請先備份並遷移內容。')
    st.divider()
    if st.button('✓ 提交（儲存後關閉）',type='primary',use_container_width=True,key='v43_submit'):
        try:
            if full_note['kind']=='COMPOSITE':
                st.session_state['_submit_request_'+full_id]=st.session_state.get('_submit_request_'+full_id,0)+1
                st.info('正在提交圖文文件；儲存成功後自動退出')
                st.rerun()
            else:
                save_focus()
                st.session_state.pop('full_edit_id',None);st.session_state.pop(draft_key,None);st.rerun()
        except Exception as exc:st.error('提交失敗：'+str(exc))
    st.stop()
mode=st.radio('工作模式' ,['瀏覽模式','編輯模式'],horizontal=True,key='workspace_mode')
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
    if focus_id in byid:
        focus=byid[focus_id]
        anchor_id='ainote-'+re.sub(r'[^a-zA-Z0-9-]','',str(focus['id']))
        st.info('快速定位目標：'+focus['title']+'。點擊下方連結跳至該段落。')
        st.markdown(f'[↳ 跳至「{html.escape(focus["title"])}」所在位置](#{anchor_id})')
        section_scroll_component(anchor=anchor_id,key='section_scroll_'+focus['id'],default=None)
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
            if node['kind']=='TABLE':continue
            elif (node.get('content') or '').strip():show_composite_reader(node) if node['kind']=='COMPOSITE' else show_markdown(node['content'],assets)
else:
    st.title(workspace['title'])
    if st.button('⛶ 完全單一編輯',key='full_from_editor'):
        st.session_state.full_edit_id=selected['id'];st.rerun()
    # GROUP/SUBFILE are structural folders; content lives in child documents only.
    draft_keys=[]
    for block in workspace_blocks:
        st.markdown('#### '+('🖼️ ' if block['kind']=='GRAPH' else '✍️ ' if block['kind']=='HANDWRITE' else '📝 ' if block['kind']=='COMPOSITE' else '▦ ' if block['kind']=='TABLE' else '📄 ')+block['title'])
        if block['kind']=='COMPOSITE':
            text_key='block_content_'+block['id']
            current=st.session_state.get(text_key,block.get('content') or '')
            event=composite_component(documentId=block['id'],content=current,assetUrls=composite_asset_urls(current),revision=st.session_state.get('_composite_rev_'+block['id'],0),editorMode=editor_mode(current),key='composite_'+block['id'],default=None)
            if isinstance(event,dict) and event.get('nonce')!=st.session_state.get('_composite_nonce_'+block['id']):
                st.session_state['_composite_nonce_'+block['id']]=event.get('nonce')
                if event.get('action') in ('save','save_close'):
                    try:
                        converted=save_composite_event(block['id'],event)
                        st.session_state[text_key]=converted
                        st.session_state['_composite_rev_'+block['id']]=st.session_state.get('_composite_rev_'+block['id'],0)+1
                        st.success('圖文文件已儲存');st.rerun()
                    except Exception as exc:st.error('圖文文件儲存失敗：'+str(exc))
            draft_keys.append((block['id'],text_key,'text'))
        elif block['kind']=='HANDWRITE':
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
            with st.expander('📋 舊版貼上工具（推薦改用「圖文文件」）'):
                rich_event=rich_paste_component(key='rich_paste_'+block['id'],default=None)
                if isinstance(rich_event,dict) and rich_event.get('nonce'):
                    pending_key='_rich_pending_'+block['id']
                    if st.session_state.get(pending_key,{}).get('nonce')!=rich_event['nonce']:
                        st.session_state[pending_key]=rich_event
                pending=st.session_state.get('_rich_pending_'+block['id'])
                if pending:
                    st.caption('已收到貼上內容，確認後才會更新 Markdown 草稿。')
                    if st.button('套用貼上內容',key='apply_rich_'+block['id']):
                        try:
                            converted=pending.get('markdown','')
                            for i,item in enumerate(pending.get('images',[])):
                                data=item.get('data','')
                                if not data.startswith('data:image/') or ';base64,' not in data:raise ValueError('圖片資料不完整，已中止儲存，避免內容遺失')
                                raw=base64.b64decode(data.split(';base64,',1)[1],validate=True)
                                aid=upload_image(raw,block['id'])
                                converted=converted.replace('clipboard-image://'+str(i),'asset://'+aid)
                            existing=st.session_state.get(text_key,block.get('content') or '')
                            st.session_state[text_key]=(existing.rstrip()+'\n\n'+converted).strip() if existing.strip() else converted
                            del st.session_state['_rich_pending_'+block['id']]
                            st.rerun()
                        except Exception as exc:
                            st.error('轉換貼上內容失敗：'+str(exc))
                    if st.button('取消此次貼上',key='cancel_rich_'+block['id']):
                        del st.session_state['_rich_pending_'+block['id']]
                        st.rerun()
            st.text_area('Markdown：'+block['title'],value=block.get('content') or '',
                height=190,key=text_key,label_visibility='collapsed')
            if False:
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
    # v4.3: workspace save is requested from Explorer context menu, not inline.
    changed={nid:val for nid,val in draft_values.items() if val!=(byid.get(nid,{}).get('content') or '')}
    st.caption(f'偵測到 {len(changed)} 個變更文件。僅更新變更內容，不下載 ZIP。完整備份請使用側邊欄「下載當前組別」。')
    if st.session_state.pop('workspace_save_requested',False) and changed:
        successes=[];failures=[]
        for nid,val in changed.items():
            try:update_note(nid,content=val);successes.append(nid)
            except Exception as exc:failures.append((nid,str(exc)))
        if failures:
            for nid,msg in failures:st.error(f'{byid[nid]["title"]}：{msg}')
        if successes:
            st.success(f'已更新 {len(successes)} 個文件（無本地下載）')
            st.rerun()
    t1,t4,t5=st.tabs(['🖼️ 圖片','✍️ 手寫稿','📝 圖文文件'])
    with t1:
        photo_title=st.text_input('圖片名稱',value='新圖片',key='graph_title_'+workspace_id)
        st.caption('每次建立一個圖片組件；組件內可一次上傳 1–20 張照片。')
        if st.button('新增圖片組件',key='new_graph_'+workspace_id):
            try:
                created=insert_note('GRAPH',photo_title.strip() or '新圖片',workspace_id,position=len(workspace_blocks))
                st.session_state.selected=created['id']
                st.rerun()
            except Exception as exc:st.error('新增失敗：'+str(exc))
    with t4:
        if st.button('＋ 建立手寫稿',key='new_handwrite_'+workspace_id):
            st.session_state.pending_handwrite={'title':'新手寫稿','parent':workspace_id}
            st.rerun()
    with t5:
        composite_name=st.text_input('圖文文件名稱',value='新圖文文件',key='composite_name_'+workspace_id)
        if st.button('＋ 建立圖文文件',key='new_composite_'+workspace_id):
            try:
                created=insert_note('COMPOSITE',composite_name.strip() or '新圖文文件',workspace_id,position=len(workspace_blocks))
                st.session_state.selected=created['id']
                st.rerun()
            except Exception as exc:st.error('新增圖文文件失敗：'+str(exc))
st.divider()
st.caption('BV-Text v4.3.2 · 圖文文件 · 圖片 · 手寫稿 · 完全單一閱讀')


if st.session_state.get('pending_handwrite'):
    handwriting_creation_dialog()
