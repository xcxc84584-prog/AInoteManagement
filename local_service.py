"""Local service snapshots; never access a visitor's filesystem from a remote server."""
import io,json,zipfile
from datetime import datetime,timezone
from pathlib import Path
from local_backend import FIELDS
from schedule_cloud import TABLES,_time

def pack(db,owner,scope='all'):
    snapshot=db.export_snapshot(owner)
    if scope=='schedule':
        snapshot={k:v for k,v in snapshot.items() if k in TABLES}
    elif scope=='notes':
        snapshot={k:v for k,v in snapshot.items() if k in ('notes','assets','media')}
    elif scope!='all':raise ValueError('不支援的備份範圍')
    blob=io.BytesIO()
    with zipfile.ZipFile(blob,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps({'format':'bv-local','version':1,'scope':scope,'created_at':datetime.now(timezone.utc).isoformat()},ensure_ascii=False))
        z.writestr('snapshot.json',json.dumps(snapshot,ensure_ascii=False))
    return blob.getvalue()

def unpack(data,max_bytes=100*1024*1024):
    if len(data)>max_bytes:raise ValueError('備份檔案超過 100 MB 上限')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if sum(x.file_size for x in z.infolist())>max_bytes*3:raise ValueError('解壓縮內容過大')
        meta=json.loads(z.read('manifest.json'))
        if meta.get('format')!='bv-local' or meta.get('version')!=1:raise ValueError('不是支援的本地備份')
        snap=json.loads(z.read('snapshot.json'))
    if not isinstance(snap,dict):raise ValueError('備份格式錯誤')
    return meta,snap

def restore(db,owner,data,scope='all',replace=False):
    meta,snap=unpack(data)
    source_scope=meta['scope']
    if scope=='all' and source_scope!='all':raise ValueError('完整還原需要完整備份')
    if scope=='notes' and source_scope=='schedule':raise ValueError('此備份不含文件')
    if scope=='schedule' and source_scope=='notes':raise ValueError('此備份不含行程表')
    names=list(TABLES) if scope=='schedule' else ['notes','assets'] if scope=='notes' else list(FIELDS)
    current=db.export_snapshot(owner)
    merged={k:current[k] for k in FIELDS}
    merged['media']=current.get('media',{}).copy()
    counts={'added':0,'updated':0,'unchanged':0,'conflicts':0,'removed':0}
    for name in names:
        incoming={str(r['id']):r for r in snap.get(name,[]) if isinstance(r,dict) and r.get('owner_id')==owner and r.get('id')}
        previous={str(r['id']):r for r in current[name]}
        result={} if replace else previous.copy()
        for ident,row in incoming.items():
            old=previous.get(ident)
            if old is None:result[ident]=row;counts['added']+=1
            elif replace or _time(row)>_time(old):result[ident]=row;counts['updated']+=1
            elif row==old:counts['unchanged']+=1
            elif _time(row)==_time(old):counts['conflicts']+=1
            else:counts['unchanged']+=1
        if replace:counts['removed']+=len(previous.keys()-incoming.keys())
        merged[name]=list(result.values())
    if scope!='schedule':merged['media'].update(snap.get('media',{}))
    # Restore all tables together in one local SQLite transaction, preserving other scope.
    db.import_snapshot(owner,merged,replace=True)
    return counts

def tree(rows):
    byid={str(x['id']):x for x in rows if not x.get('is_deleted')}
    children={}
    for item in byid.values():
        parent=str(item.get('parent_id') or '')
        children.setdefault(parent if parent in byid else '',[]).append(item)
    for items in children.values():items.sort(key=lambda x:(x.get('position') or 0,x.get('title') or ''))
    lines=[]
    def visit(pid,depth,seen):
        for item in children.get(pid,[]):
            ident=str(item['id'])
            if ident in seen:continue
            lines.append('  '*depth+('📁 ' if item.get('kind') in ('GROUP','SUBFILE') else '📄 ')+str(item.get('title') or '未命名'))
            visit(ident,depth+1,seen|{ident})
    visit('',0,set())
    return '\n'.join(lines) or '此資料夾目前沒有文件'

def safe_folder(path):
    p=Path(path).expanduser().resolve()
    if not p.is_dir():raise ValueError('資料夾不存在，請先建立資料夾')
    return p
