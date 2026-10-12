"""Local-first data backend. No Supabase calls occur in local CRUD methods."""
import base64
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace

FIELDS={
 'notes':{'id','owner_id','parent_id','kind','title','content','has_page','position','is_deleted','deleted_at','created_at','updated_at'},
 'assets':{'id','owner_id','note_id','storage_path','mime_type','created_at'},
 'schedule_cards':{'id','owner_id','title','schedule_date','scheduled_at','details','created_at','is_completed','batch_tag','batch_id'},
 'daily_tasks':{'id','owner_id','title','no_time','task_time','details','created_at'},
 'daily_task_checks':{'id','owner_id','task_id','task_date','is_completed','created_at'},
}
BOOL={'has_page','is_deleted','is_completed','no_time'}
def now():return datetime.now(timezone.utc).isoformat()
class LocalDB:
 def __init__(self,path=':memory:'):
  self.path=str(path)
  if path!=':memory:':Path(path).parent.mkdir(parents=True,exist_ok=True)
  self.conn=sqlite3.connect(self.path,check_same_thread=False)
  self.conn.row_factory=sqlite3.Row
  self.lock=threading.RLock()
  self.on_change=None
  with self.lock:
   self.conn.execute('PRAGMA foreign_keys=OFF')
   self.conn.execute('PRAGMA journal_mode=WAL')
   self.conn.executescript('''CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,parent_id TEXT,kind TEXT,title TEXT,content TEXT DEFAULT '',has_page INTEGER DEFAULT 0,position INTEGER DEFAULT 0,is_deleted INTEGER DEFAULT 0,deleted_at TEXT,created_at TEXT,updated_at TEXT);
CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,note_id TEXT,storage_path TEXT,mime_type TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS schedule_cards(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,title TEXT,schedule_date TEXT,scheduled_at TEXT,details TEXT DEFAULT '',created_at TEXT,is_completed INTEGER DEFAULT 0,batch_tag TEXT,batch_id TEXT);
CREATE TABLE IF NOT EXISTS daily_tasks(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,title TEXT NOT NULL,no_time INTEGER DEFAULT 1,task_time TEXT,details TEXT DEFAULT '',created_at TEXT);
CREATE TABLE IF NOT EXISTS daily_task_checks(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,task_id TEXT NOT NULL,task_date TEXT NOT NULL,is_completed INTEGER DEFAULT 0,created_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_check_unique ON daily_task_checks(owner_id,task_id,task_date);
CREATE TABLE IF NOT EXISTS media(path TEXT PRIMARY KEY,content BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS sync_state(key TEXT PRIMARY KEY,value TEXT);
CREATE INDEX IF NOT EXISTS idx_notes_owner ON notes(owner_id,position);
CREATE INDEX IF NOT EXISTS idx_schedule_owner ON schedule_cards(owner_id,schedule_date);''')
   existing={r[1] for r in self.conn.execute('PRAGMA table_info(schedule_cards)')}
   for col in ('batch_tag','batch_id'):
    if col not in existing:self.conn.execute('ALTER TABLE schedule_cards ADD COLUMN '+col+' TEXT')
   self.conn.commit()
 def table(self,name):
  if name not in FIELDS:raise ValueError('Unknown table')
  return Query(self,name)
 @property
 def storage(self):return LocalStorage(self)
 def export_snapshot(self,owner):
  with self.lock:
   result={name:[dict(r) for r in self.conn.execute('SELECT * FROM '+name+' WHERE owner_id=?',(owner,))] for name in FIELDS}
   paths={a['storage_path'] for a in result['assets']}
   result['media']={p:base64.b64encode(self.conn.execute('SELECT content FROM media WHERE path=?',(p,)).fetchone()[0]).decode() for p in paths if self.conn.execute('SELECT 1 FROM media WHERE path=?',(p,)).fetchone()}
   return result
 def import_snapshot(self,owner,snapshot,replace=True):
  if not isinstance(snapshot,dict):raise ValueError('Invalid snapshot')
  with self.lock,self.conn:
   if replace:
    for name in FIELDS:self.conn.execute('DELETE FROM '+name+' WHERE owner_id=?',(owner,))
   for name,fields in FIELDS.items():
    for row in snapshot.get(name,[]):
     if row.get('owner_id')!=owner:continue
     values={k:v for k,v in row.items() if k in fields}
     cols=list(values)
     if not cols:continue
     self.conn.execute('INSERT OR REPLACE INTO '+name+' ('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')',[values[k] for k in cols])
   for path,b64 in snapshot.get('media',{}).items():
    if not path.startswith(owner+'/'):continue
    self.conn.execute('INSERT OR REPLACE INTO media VALUES (?,?)',(path,base64.b64decode(b64,validate=True)))
 def close(self):self.conn.close()
class Query:
 def __init__(self,db,name):self.db=db;self.name=name;self.filters=[];self.action='select';self.payload=None;self.sort=None;self.count=None
 def select(self,*args):return self
 def eq(self,key,value):
  if key not in FIELDS[self.name]:raise ValueError('Invalid field')
  self.filters.append((key,'IS NULL' if value is None else '= ',value));return self
 def in_(self,key,values):
  if key not in FIELDS[self.name]:raise ValueError('Invalid field')
  self.filters.append((key,'IN',list(values)));return self
 def order(self,key,*args,**kwargs):
  if key not in FIELDS[self.name]:raise ValueError('Invalid field')
  self.sort=key;return self
 def limit(self,n):self.count=int(n);return self
 def insert(self,payload):self.action='insert';self.payload=payload;return self
 def update(self,payload):self.action='update';self.payload=payload;return self
 def delete(self):self.action='delete';return self
 def execute(self):
  where=[];args=[]
  for key,op,value in self.filters:
   if op=='IN':
    if not value:where.append('1=0');continue
    where.append(key+' IN ('+','.join('?' for _ in value)+')');args+=value
   elif op=='IS NULL':where.append(key+' IS NULL')
   else:where.append(key+' = ?');args.append(int(value) if isinstance(value,bool) else value)
  clause=' WHERE '+' AND '.join(where) if where else ''
  with self.db.lock,self.db.conn:
   if self.action=='select':
    sql='SELECT * FROM '+self.name+clause+(' ORDER BY '+self.sort if self.sort else '')+(' LIMIT '+str(self.count) if self.count is not None else '')
    rows=self.db.conn.execute(sql,args).fetchall()
   elif self.action=='insert':
    payloads=self.payload if isinstance(self.payload,list) else [self.payload]
    rows=[]
    for p in payloads:
     values={k:(int(v) if k in BOOL and v is not None else v) for k,v in p.items() if k in FIELDS[self.name]}
     values.setdefault('id',str(uuid.uuid4()));values.setdefault('created_at',now())
     if self.name=='notes':values.setdefault('updated_at',now())
     cols=list(values)
     self.db.conn.execute('INSERT INTO '+self.name+' ('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')',[values[k] for k in cols])
     rows.append(self.db.conn.execute('SELECT * FROM '+self.name+' WHERE id=?',(values['id'],)).fetchone())
   else:
    if not self.filters:raise ValueError('Refusing unfiltered mutation')
    if self.action=='delete':
     rows=self.db.conn.execute('SELECT * FROM '+self.name+clause,args).fetchall()
     self.db.conn.execute('DELETE FROM '+self.name+clause,args)
    else:
     values={k:(int(v) if k in BOOL and v is not None else v) for k,v in self.payload.items() if k in FIELDS[self.name] and k!='id'}
     if not values:raise ValueError('No valid update fields')
     cols=list(values)
     self.db.conn.execute('UPDATE '+self.name+' SET '+','.join(k+'=?' for k in cols)+clause,[values[k] for k in cols]+args)
     rows=self.db.conn.execute('SELECT * FROM '+self.name+clause,args).fetchall()
  if self.action!='select' and self.db.on_change:self.db.on_change()
  return SimpleNamespace(data=[{k:(bool(v) if k in BOOL and v is not None else v) for k,v in dict(r).items()} for r in rows])
class LocalStorage:
 def __init__(self,db):self.db=db
 def from_(self,bucket):
  if bucket!='note-images':raise ValueError('Unknown bucket')
  return self
 def upload(self,path,data,*args,**kwargs):
  with self.db.lock,self.db.conn:self.db.conn.execute('INSERT OR REPLACE INTO media VALUES (?,?)',(path,bytes(data)))
  if self.db.on_change:self.db.on_change()
 def download(self,path):
  with self.db.lock:r=self.db.conn.execute('SELECT content FROM media WHERE path=?',(path,)).fetchone()
  if r is None:raise FileNotFoundError(path)
  return bytes(r[0])
 def remove(self,paths):
  with self.db.lock,self.db.conn:
   for p in paths:self.db.conn.execute('DELETE FROM media WHERE path=?',(p,))
  if self.db.on_change:self.db.on_change()
 def create_signed_url(self,*args,**kwargs):return {}
