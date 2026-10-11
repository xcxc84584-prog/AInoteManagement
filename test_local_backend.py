import tempfile
from pathlib import Path
from local_backend import LocalDB

def test_sqlite_roundtrip():
 with tempfile.TemporaryDirectory() as td:
  db=LocalDB(Path(td)/'store.sqlite3')
  uid='user-1'
  root=db.table('notes').insert({'owner_id':uid,'kind':'GROUP','title':'測試','content':'原始'}).execute().data[0]
  assert db.table('notes').select('*').eq('owner_id',uid).execute().data[0]['title']=='測試'
  db.table('notes').update({'content':'已更新'}).eq('id',root['id']).eq('owner_id',uid).execute()
  assert db.table('notes').select('content').eq('id',root['id']).execute().data[0]['content']=='已更新'
  db.table('schedule_cards').insert({'owner_id':uid,'title':'無時間','schedule_date':'2026-10-11','scheduled_at':None}).execute()
  path=uid+'/image.webp'
  assert not callable(db.storage), 'storage must be an object, not a method'
  db.storage.from_('note-images').upload(path,b'hello')
  db.table('assets').insert({'owner_id':uid,'note_id':root['id'],'storage_path':path,'mime_type':'image/webp'}).execute()
  snap=db.export_snapshot(uid)
  restored=LocalDB()
  restored.import_snapshot(uid,snap)
  assert restored.storage.from_('note-images').download(path)==b'hello'
  restored.storage.from_('note-images').remove([path])
  try:restored.storage.from_('note-images').download(path);assert False
  except FileNotFoundError:pass
  assert len(restored.table('schedule_cards').select('*').eq('owner_id',uid).execute().data)==1
  restored.table('notes').delete().eq('id',root['id']).execute()
  assert not restored.table('notes').select('*').eq('owner_id',uid).execute().data
  db.close()
  reopened=LocalDB(Path(td)/'store.sqlite3')
  assert reopened.table('notes').select('*').eq('owner_id',uid).execute().data[0]['content']=='已更新'
  reopened.close()
if __name__=='__main__':test_sqlite_roundtrip();print('LocalDB tests passed')
