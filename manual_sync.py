"""Explicit cloud import/export. All network writes occur inside push_to_cloud()."""
from pathlib import Path
from local_backend import FIELDS

def pull_from_cloud(cloud,local,owner):
 snapshot={}
 for table in FIELDS:
  snapshot[table]=cloud.table(table).select('*').eq('owner_id',owner).execute().data or []
 media={}
 for a in snapshot['assets']:
  try:
   import base64
   media[a['storage_path']]=base64.b64encode(cloud.storage.from_('note-images').download(a['storage_path'])).decode('ascii')
  except Exception as exc:raise RuntimeError('下載圖片失敗：'+a['storage_path']) from exc
 snapshot['media']=media
 local.import_snapshot(owner,snapshot,replace=True)
 return {k:len(snapshot[k]) for k in FIELDS}

def push_to_cloud(cloud,local,owner):
 snapshot=local.export_snapshot(owner)
 # Do not delete cloud-only records: conservative merge to avoid irreversible data loss.
 for table in ('notes','assets','schedule_cards'):
  for row in snapshot[table]:
   # Keep ownership; never upload data for another user.
   if row['owner_id']!=owner:continue
   cloud.table(table).upsert(row,on_conflict='id').execute()
 for a in snapshot['assets']:
  path=a['storage_path']
  if path not in snapshot['media']:continue
  import base64
  cloud.storage.from_('note-images').upload(path,base64.b64decode(snapshot['media'][path]),{'content-type':a.get('mime_type') or 'application/octet-stream','upsert':'true'})
 return {k:len(snapshot[k]) for k in FIELDS}
