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
 # Older cloud databases restrict notes.kind to legacy values.
 # Never remap COMPOSITE into MARKDOWN: that silently corrupts document types.
 kinds={r.get('kind') for r in snapshot.get('notes',[])}
 if 'COMPOSITE' in kinds:
  try:
   cloud.table('notes').select('id').limit(1).execute()
  except Exception as exc:
   raise RuntimeError('無法確認雲端 notes 資料表。請檢查 Supabase 設定。') from exc
 # Do not delete cloud-only records: conservative merge to avoid irreversible data loss.
 for table in ('notes','assets','schedule_cards'):
  for row in snapshot[table]:
   # Keep ownership; never upload data for another user.
   if row['owner_id']!=owner:continue
   try:
    cloud.table(table).upsert(row,on_conflict='id').execute()
   except Exception as exc:
    if table=='notes' and 'notes_kind_check' in str(exc):
     raise RuntimeError('Supabase notes_kind_check 尚未允許圖文文件 COMPOSITE。請先執行 sql/migration_v4_7.sql，再重新上傳；本地資料不會被刪除。') from exc
    raise
 for a in snapshot['assets']:
  path=a['storage_path']
  if path not in snapshot['media']:continue
  import base64
  cloud.storage.from_('note-images').upload(path,base64.b64decode(snapshot['media'][path]),{'content-type':a.get('mime_type') or 'application/octet-stream','upsert':'true'})
 return {k:len(snapshot[k]) for k in FIELDS}
