"""LAN snapshot relay. Run on a trusted private network only; no Supabase data transport."""
import argparse,json,os,secrets,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
MAX_BYTES=200*1024*1024

def serve(host='0.0.0.0',port=8765,token=None,directory=None):
 token=token or os.environ.get('BV_LAN_TOKEN') or secrets.token_urlsafe(24)
 root=Path(directory or (Path.home()/'BV-Text-LAN')).resolve();root.mkdir(parents=True,exist_ok=True)
 lock=threading.Lock()
 class Handler(BaseHTTPRequestHandler):
  def _respond(self,code,data):
   raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
  def _authorized(self):
   if not secrets.compare_digest(self.headers.get('X-BV-LAN-Token',''),token):self._respond(403,{'error':'Invalid LAN token'});return False
   return True
  def do_GET(self):
   if not self._authorized():return
   if self.path!='/snapshot':return self._respond(404,{'error':'Not found'})
   with lock:
    file=root/'snapshot.json'
    if not file.exists():return self._respond(404,{'error':'No snapshot uploaded'})
    try:data=json.loads(file.read_text('utf-8'))
    except Exception:return self._respond(500,{'error':'Corrupt snapshot'})
   self._respond(200,data)
  def do_POST(self):
   if not self._authorized():return
   if self.path!='/snapshot':return self._respond(404,{'error':'Not found'})
   try:size=int(self.headers.get('Content-Length','0'))
   except ValueError:return self._respond(400,{'error':'Invalid length'})
   if not 0<size<=MAX_BYTES:return self._respond(413,{'error':'Snapshot too large'})
   try:
    data=json.loads(self.rfile.read(size))
    if not isinstance(data,dict) or not isinstance(data.get('owner_id'),str) or not isinstance(data.get('snapshot'),dict):raise ValueError('Invalid snapshot')
    raw=json.dumps(data,ensure_ascii=False).encode()
    with lock:
     temp=root/'snapshot.tmp';temp.write_bytes(raw);temp.replace(root/'snapshot.json')
    self._respond(200,{'ok':True,'bytes':len(raw)})
   except Exception as exc:self._respond(400,{'error':str(exc)})
 print(f'LAN relay on http://{host}:{port} | token: {token}',flush=True)
 ThreadingHTTPServer((host,port),Handler).serve_forever()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--host',default='0.0.0.0');p.add_argument('--port',type=int,default=8765);p.add_argument('--token');p.add_argument('--directory');a=p.parse_args();serve(a.host,a.port,a.token,a.directory)
