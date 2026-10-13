"""Client-side LAN relay calls (from the machine running Streamlit)."""
import ipaddress,requests,socket
from urllib.parse import urlsplit

def _endpoint(url):
 parsed=urlsplit(url.strip())
 if parsed.scheme!='http' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:raise ValueError('只允許 http://局域網IP:埠號')
 try:
  addresses=socket.getaddrinfo(parsed.hostname,parsed.port or 80,type=socket.SOCK_STREAM)
  if not addresses or any(not ipaddress.ip_address(a[4][0]).is_private for a in addresses):raise ValueError('僅允許私人局域網 IP')
 except socket.gaierror as exc:raise ValueError('無法解析 LAN 主機') from exc
 return parsed.geturl().rstrip('/')+'/snapshot'

def send(url,token,owner,snapshot):
 r=requests.post(_endpoint(url),headers={'X-BV-LAN-Token':token},json={'owner_id':owner,'snapshot':snapshot},timeout=90)
 r.raise_for_status();return r.json()

def receive(url,token,owner):
 r=requests.get(_endpoint(url),headers={'X-BV-LAN-Token':token},timeout=90)
 r.raise_for_status();data=r.json()
 if data.get('owner_id')!=owner:raise ValueError('帳號 UID 不一致，已拒絕匯入')
 return data['snapshot']
