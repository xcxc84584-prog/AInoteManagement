"""Explicit schedule-only transfer. IDs are stable; no note records are touched."""
from datetime import datetime,timezone
from local_backend import FIELDS
TABLES=('daily_tasks','daily_task_checks','schedule_cards')
def _time(row):
 value=row.get('updated_at') or row.get('created_at') or ''
 try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
 except (ValueError,TypeError):return datetime.min.replace(tzinfo=timezone.utc)
def _rows(backend,owner,table):
 return backend.table(table).select('*').eq('owner_id',owner).execute().data or []
def transfer_schedule(cloud,local,owner,direction,replace=False,progress=None):
 if direction not in ('upload','download'):raise ValueError('方向錯誤')
 source,target=(local,cloud) if direction=='upload' else (cloud,local)
 source_rows={t:_rows(source,owner,t) for t in TABLES}
 target_rows={t:_rows(target,owner,t) for t in TABLES}
 # Determine everything before changing anything; on equal timestamps conflicting data is kept at destination.
 chosen={};counts={'added':0,'updated':0,'unchanged':0,'conflicts':0,'removed':0}
 for table in TABLES:
  old={str(r['id']):r for r in target_rows[table]}
  chosen[table]=[]
  for row in source_rows[table]:
   rid=str(row['id']);prev=old.get(rid)
   if prev is None:chosen[table].append(row);counts['added']+=1
   elif replace or _time(row)>_time(prev):chosen[table].append(row);counts['updated']+=1
   elif row==prev:counts['unchanged']+=1
   elif _time(row)==_time(prev):counts['conflicts']+=1
   else:counts['unchanged']+=1
  if replace:counts['removed']+=len(set(old)-{str(r['id']) for r in source_rows[table]})
 # Local replacement is atomic. Cloud REST has no cross-table transaction; report partial failures.
 if target is local:
  with local.lock,local.conn:
   if replace:
    for table in ('daily_task_checks','daily_tasks','schedule_cards'):
     local.conn.execute('DELETE FROM '+table+' WHERE owner_id=?',(owner,))
   for table in TABLES:
    for row in chosen[table]:
     cols=[k for k in FIELDS[table] if k in row]
     local.conn.execute('INSERT OR REPLACE INTO '+table+' ('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')',[row[k] for k in cols])
   if progress:progress(1,'行程表下載完成')
 else:
  if replace:
   for table in ('daily_task_checks','daily_tasks','schedule_cards'):
    for row in target_rows[table]:cloud.table(table).delete().eq('owner_id',owner).eq('id',row['id']).execute()
  total=sum(map(len,chosen.values()));done=0
  for table in TABLES:
   for row in chosen[table]:
    cloud.table(table).upsert(row,on_conflict='id').execute();done+=1
    if progress:progress(done/max(total,1),'上傳 '+table)
  if progress:progress(1,'行程表上傳完成')
 return counts
