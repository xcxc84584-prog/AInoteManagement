
# Backward-compatible compressed note content. Legacy plain-text cloud rows remain readable.
_COMPRESSED_PREFIX='BVZ1:zlib:'
def _pack_note(row):
 import zlib,base64
 r=dict(row);content=r.get('content')
 if isinstance(content,str) and content and not content.startswith(_COMPRESSED_PREFIX):
  compressed=base64.b64encode(zlib.compress(content.encode('utf-8'),level=6)).decode('ascii')
  if len(compressed)+len(_COMPRESSED_PREFIX)<len(content):r['content']=_COMPRESSED_PREFIX+compressed
 return r
def _unpack_note(row):
 import zlib,base64
 r=dict(row);content=r.get('content')
 if isinstance(content,str) and content.startswith(_COMPRESSED_PREFIX):
  try:r['content']=zlib.decompress(base64.b64decode(content[len(_COMPRESSED_PREFIX):],validate=True),max_length=0).decode('utf-8')
  except TypeError:r['content']=zlib.decompress(base64.b64decode(content[len(_COMPRESSED_PREFIX):],validate=True)).decode('utf-8')
  except Exception as exc:raise RuntimeError('雲端壓縮內容解碼失敗，已停止載入：'+str(r.get('id'))) from exc
 return r

def push_selected_to_cloud(cloud,local,owner,note_id,progress=None):
 """Upload a single note, required ancestors and its assets; no unrelated notes."""
 import base64
 snapshot=local.export_snapshot(owner);byid={r['id']:r for r in snapshot.get('notes',[]) if not r.get('is_deleted')}
 if note_id not in byid:raise ValueError('找不到要雲端化的本地文件')
 chain=[];cur=note_id;visited=set()
 while cur and cur in byid:
  if cur in visited:raise ValueError('父節點循環')
  visited.add(cur);chain.append(byid[cur]);cur=byid[cur].get('parent_id')
 for i,row in enumerate(reversed(chain)):
  cloud.table('notes').upsert(_pack_note(row),on_conflict='id').execute()
  if progress:progress(.1+.55*(i+1)/len(chain),'上傳文件與必要父節點')
 assets=[a for a in snapshot.get('assets',[]) if a.get('note_id')==note_id]
 for i,asset in enumerate(assets):
  cloud.table('assets').upsert(asset,on_conflict='id').execute()
  path=asset.get('storage_path');encoded=snapshot.get('media',{}).get(path)
  if encoded:cloud.storage.from_('note-images').upload(path,base64.b64decode(encoded),{'content-type':asset.get('mime_type') or 'application/octet-stream','upsert':'true'})
  if progress:progress(.65+.3*(i+1)/len(assets),'上傳文件圖片')
 if progress:progress(1,'雲端化完成')
 return {'notes':len(chain),'assets':len(assets)}

"""Explicit cloud import/export. All network writes occur inside push_to_cloud()."""
from pathlib import Path
from local_backend import FIELDS

def pull_from_cloud(cloud,local,owner,progress=None):
 snapshot={}
 for i,table in enumerate(FIELDS):
  if progress:progress((i+1)/(len(FIELDS)+2), '下載 '+table)
  snapshot[table]=cloud.table(table).select('*').eq('owner_id',owner).execute().data or []
  if table=='notes':snapshot[table]=[_unpack_note(r) for r in snapshot[table]]
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
   cloud.table('notes').upsert(_pack_note(row),on_conflict='id').execute()
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
 # Sync daily task templates before dated checks (FK dependency).
 for table in ('daily_tasks','daily_task_checks'):
  records=[r for r in snapshot.get(table,[]) if r.get('owner_id')==owner]
  for index,row in enumerate(records):
   if progress:progress(.78+.02*(index+1)/max(len(records),1),'同步 '+table)
   cloud.table(table).upsert(row,on_conflict='id').execute()
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

def pull_selected_from_cloud(cloud,local,owner,selected_ids,progress=None):
 """Fetch selected notes and required ancestors/assets without replacing unrelated local data."""
 import base64
 selected=set(selected_ids)
 if not selected:return {'notes':0,'assets':0}
 rows=cloud.table('notes').select('*').eq('owner_id',owner).execute().data or []
 byid={r['id']:_unpack_note(r) for r in rows if not r.get('is_deleted')}
 missing=selected-set(byid)
 if missing:raise ValueError('雲端找不到所選文件：'+','.join(sorted(missing)))
 wanted=set(selected)
 for nid in list(selected):
  seen=set();cur=byid[nid]
  while cur.get('parent_id') in byid:
   pid=cur['parent_id']
   if pid in seen:raise ValueError('雲端文件父節點循環')
   seen.add(pid);wanted.add(pid);cur=byid[pid]
 if progress:progress(.15,'已取得文件與父節點')
 assets=cloud.table('assets').select('*').eq('owner_id',owner).execute().data or []
 chosen_assets=[a for a in assets if a.get('note_id') in wanted]
 media={}
 for i,a in enumerate(chosen_assets):
  path=a.get('storage_path')
  if path:
   media[path]=base64.b64encode(cloud.storage.from_('note-images').download(path)).decode('ascii')
  if progress:progress(.2+.55*(i+1)/max(len(chosen_assets),1),'下載相關圖片')
 # Preserve other tables, and preserve unrelated notes/assets by merging IDs.
 snapshot=local.export_snapshot(owner)
 for table,incoming in [('notes',[byid[i] for i in wanted]),('assets',chosen_assets)]:
  merged={r['id']:r for r in snapshot.get(table,[])}
  merged.update({r['id']:r for r in incoming})
  snapshot[table]=list(merged.values())
 snapshot.setdefault('media',{}).update(media)
 if progress:progress(.85,'寫入本地工作區')
 local.import_snapshot(owner,snapshot,replace=True)
 if progress:progress(1,'局部載入完成')
 return {'notes':len(wanted),'assets':len(chosen_assets)}


def _merge_sections(old,new):
 """Merge Markdown sections by heading; latest version wins on matching headings."""
 import re
 def sections(text):
  chunks=[];key='__intro__';buf=[]
  for line in (text or '').splitlines(keepends=True):
   if re.match(r'^#{1,6}\s+\S',line):
    chunks.append((key,''.join(buf)));key=line.strip();buf=[line]
   else:buf.append(line)
  chunks.append((key,''.join(buf)))
  return [(k,v) for k,v in chunks if v]
 older=sections(old);newer=sections(new)
 merged={k:v for k,v in older};order=[k for k,v in older]
 for k,v in newer:
  if k not in merged:order.append(k)
  merged[k]=v
 return ''.join(merged[k] for k in order)


def merge_duplicate_named_notes(cloud,owner,progress=None):
 """Conservative name-based merge; never delete referenced notes without safely migrating links."""
 from collections import defaultdict
 rows=cloud.table('notes').select('*').eq('owner_id',owner).execute().data or []
 groups=defaultdict(list)
 for r in rows:
  if not r.get('is_deleted') and r.get('title'):
   groups[(r.get('parent_id'),r['title'].strip(),r.get('kind'))].append(r)
 dupes=[g for g in groups.values() if len(g)>1]
 result={'merged':0,'removed':0,'skipped':0,'groups':len(dupes)}
 for i,group in enumerate(dupes):
  group.sort(key=lambda r:str(r.get('updated_at') or r.get('created_at') or ''))
  survivor=group[-1]
  # Only text notes with unique section headings can be merged automatically.
  if survivor.get('kind') not in ('COMPOSITE','MD','FILE','TEXT'):
   result['skipped']+=1;continue
  import re
  def headings(content):
   h=re.findall(r'^#{1,6}\s+.+$',content or '',re.M)
   return len(h)==len(set(h))
  if not all(headings(r.get('content')) for r in group):
   result['skipped']+=1;continue
  combined=_unpack_note(group[0]).get('content') or ''
  for r in group[1:]:combined=_merge_sections(combined,_unpack_note(r).get('content') or '')
  try:
   cloud.table('notes').update({'content':_pack_note({'content':combined})['content']}).eq('id',survivor['id']).eq('owner_id',owner).execute()
   for old in group[:-1]:
    # Transfer foreign keys before deletion; restrict updates to the current owner.
    for table,col in [('notes','parent_id'),('assets','note_id')]:
     cloud.table(table).update({col:survivor['id']}).eq('owner_id',owner).eq(col,old['id']).execute()
    cloud.table('notes').delete().eq('owner_id',owner).eq('id',old['id']).execute()
    result['removed']+=1
   result['merged']+=1
  except Exception as exc:
   raise RuntimeError('同名文件合併未完成，請檢查雲端資料（'+str(survivor.get('title'))+'）：'+str(exc)) from exc
  if progress:progress((i+1)/max(len(dupes),1),'合併同名文件')
 if progress:progress(1,'雲端同名文件整理完成')
 return result

def delete_cloud_note_subtree(cloud,owner,note_id,progress=None):
 """Delete one owner's selected note subtree, including asset rows and Storage files."""
 rows=cloud.table('notes').select('id,parent_id').eq('owner_id',owner).execute().data or []
 ids={str(r['id']) for r in rows}
 if str(note_id) not in ids:raise ValueError('雲端文件不存在或無權操作')
 children={}
 for r in rows:children.setdefault(str(r.get('parent_id') or ''),[]).append(str(r['id']))
 ordered=[];seen=set()
 def visit(n):
  if n in seen:return
  seen.add(n)
  for child in children.get(n,[]):visit(child)
  ordered.append(n)
 visit(str(note_id))
 paths=[]
 for i,nid in enumerate(ordered):
  if progress:progress(.1+.65*(i+1)/len(ordered),'刪除雲端文件及附件')
  assets=cloud.table('assets').select('id,storage_path').eq('owner_id',owner).eq('note_id',nid).execute().data or []
  for a in assets:
   if a.get('storage_path'):paths.append(a['storage_path'])
  cloud.table('assets').delete().eq('owner_id',owner).eq('note_id',nid).execute()
  cloud.table('notes').delete().eq('owner_id',owner).eq('id',nid).execute()
 if paths:
  for i in range(0,len(paths),100):cloud.storage.from_('note-images').remove(paths[i:i+100])
 if progress:progress(1,'雲端刪除完成')
 return {'notes':len(ordered),'assets':len(paths)}
