"""Explicit cloud import/export. All network writes occur inside push_to_cloud()."""
from pathlib import Path
from local_backend import FIELDS

def pull_from_cloud(cloud,local,owner,progress=None):
 snapshot={}
 for i,table in enumerate(FIELDS):
  if progress:progress((i+1)/(len(FIELDS)+2), '下載 '+table)
  snapshot[table]=cloud.table(table).select('*').eq('owner_id',owner).execute().data or []
 media={}
 for j,a in enumerate(snapshot['assets']):
  if progress:progress((len(FIELDS)+1+j/max(len(snapshot['assets']),1))/(len(FIELDS)+2),'下載圖片')
  try:
   import base64
   media[a['storage_path']]=base64.b64encode(cloud.storage.from_('note-images').download(a['storage_path'])).decode('ascii')
  except Exception as exc:raise RuntimeError('下載圖片失敗：'+a['storage_path']) from exc
 snapshot['media']=media
 if progress:progress(.97,'寫入本地資料')
 local.import_snapshot(owner,snapshot,replace=True)
 return {k:len(snapshot[k]) for k in FIELDS}

def push_to_cloud(cloud,local,owner,progress=None):
 """Merge local data into cloud without producing dangling asset foreign keys."""
 snapshot=local.export_snapshot(owner)
 notes={r['id']:r for r in snapshot.get('notes',[]) if r.get('owner_id')==owner}
 pending=dict(notes);ordered=[];done=set()
 while pending:
  ready=[r for r in pending.values() if not r.get('parent_id') or r['parent_id'] in done or r['parent_id'] not in pending]
  if not ready:raise RuntimeError('文件父子關係形成循環，請修正本地 Explorer 結構後再同步')
  for r in ready:
   ordered.append(r);done.add(r['id']);pending.pop(r['id'])
 # A failed notes write must never be followed by an assets write.
 for i,row in enumerate(ordered):
  if progress:progress(.05+.35*(i+1)/max(len(ordered),1),'上傳筆記')
  try:
   cloud.table('notes').upsert(row,on_conflict='id').execute()
  except Exception as exc:
   if 'notes_parent_id_fkey' in str(exc):
    raise RuntimeError('父節點不存在於雲端，文件 '+str(row.get('title'))+' 的 parent_id='+str(row.get('parent_id'))) from exc
   if 'notes_kind_check' in str(exc):
    raise RuntimeError('Supabase notes_kind_check 尚未允許圖文文件 COMPOSITE。請先執行 sql/migration_v4_7.sql；本地資料不會被刪除。') from exc
   raise RuntimeError('筆記同步失敗（'+str(row.get('title'))+'，id='+str(row['id'])+'）：'+str(exc)) from exc
 # Read back the actual persisted IDs, not just the upsert response.
 cloud_ids=set()
 for row in ordered:
  found=cloud.table('notes').select('id').eq('owner_id',owner).eq('id',row['id']).limit(1).execute().data or []
  if not found:raise RuntimeError('HRC-SYNC-23503: 筆記寫入後無法驗證，已停止圖片同步：'+str(row['id']))
  cloud_ids.add(row['id'])
 # Some local snapshots contain assets left behind after their note was deleted.
 # Preserve those assets but clear their optional note_id instead of inserting a broken FK.
 orphan_count=0
 for i,row in enumerate(snapshot.get('assets',[])):
  if progress:progress(.5+.2*(i+1)/max(len(snapshot.get('assets',[])),1),'同步資產')
  if row.get('owner_id')!=owner:continue
  asset=dict(row)
  nid=asset.get('note_id')
  if nid and nid not in cloud_ids:
   found=cloud.table('notes').select('id').eq('owner_id',owner).eq('id',nid).limit(1).execute().data or []
   if not found:
    asset['note_id']=None
    orphan_count+=1
  try:cloud.table('assets').upsert(asset,on_conflict='id').execute()
  except Exception as exc:raise RuntimeError('HRC-SYNC-ASSET: 資產同步失敗（id='+str(asset.get('id'))+'，note_id='+str(asset.get('note_id'))+'）：'+str(exc)) from exc
 for i,row in enumerate(snapshot.get('schedule_cards',[])):
  if progress:progress(.72+.06*(i+1)/max(len(snapshot.get('schedule_cards',[])),1),'同步行程')
  if row.get('owner_id')==owner:cloud.table('schedule_cards').upsert(row,on_conflict='id').execute()
 for i,a in enumerate(snapshot.get('assets',[])):
  if progress:progress(.8+.15*(i+1)/max(len(snapshot.get('assets',[])),1),'上傳圖片')
  if a.get('owner_id')!=owner:continue
  path=a['storage_path']
  if path not in snapshot.get('media',{}):continue
  import base64
  cloud.storage.from_('note-images').upload(path,base64.b64decode(snapshot['media'][path]),{'content-type':a.get('mime_type') or 'application/octet-stream','upsert':'true'})
 result={k:len(snapshot.get(k,[])) for k in FIELDS}
 result['orphan_assets_detached']=orphan_count
 return result


def clear_cloud(cloud,owner,progress=None):
 """Remove only current user's records; never use service role or disable RLS."""
 assets=cloud.table('assets').select('storage_path').eq('owner_id',owner).execute().data or []
 # Child rows first, then notes and storage objects. Failure is reported rather than hidden.
 order=['daily_task_checks','daily_tasks','assets','schedule_cards','notes']
 counts={}
 for i,table in enumerate(order):
  if progress:progress((i+1)/(len(order)+2),'刪除 '+table)
  rows=cloud.table(table).select('id').eq('owner_id',owner).execute().data or []
  for row in rows:
   cloud.table(table).delete().eq('owner_id',owner).eq('id',row['id']).execute()
  counts[table]=len(rows)
 paths=list({a['storage_path'] for a in assets if a.get('storage_path','').startswith(owner+'/')})
 for j in range(0,len(paths),100):
  cloud.storage.from_('note-images').remove(paths[j:j+100])
 if progress:progress(1,'雲端資料刪除完成')
 return counts

def remove_exact_duplicates(cloud,owner,progress=None):
 """Deduplicate only byte-for-byte identical logical content; avoid collapsing distinct notes."""
 import json
 tables=['notes','schedule_cards','daily_tasks','daily_task_checks','assets']
 removed={}
 for i,table in enumerate(tables):
  rows=cloud.table(table).select('*').eq('owner_id',owner).execute().data or []
  # Keep IDs out of comparison, but preserve relational integrity: do not remove referenced notes/tasks/assets.
  if table in ('notes','daily_tasks','assets'):
   removed[table]=0
   if progress:progress((i+1)/len(tables),'檢查 '+table)
   continue
  seen={}; victims=[]
  for row in sorted(rows,key=lambda r:str(r.get('created_at') or ''),reverse=True):
   signature=json.dumps({k:v for k,v in row.items() if k not in ('id','created_at')},sort_keys=True,default=str)
   if signature in seen:victims.append(row['id'])
   else:seen[signature]=row['id']
  for rid in victims:cloud.table(table).delete().eq('owner_id',owner).eq('id',rid).execute()
  removed[table]=len(victims)
  if progress:progress((i+1)/len(tables),'清理 '+table)
 return removed
