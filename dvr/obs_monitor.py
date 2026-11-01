"""Minimal loopback OBS v5 read-only client. No recording-control requests exist."""
import base64,hashlib,json,os,socket,struct,time,threading
from pathlib import Path
from urllib.parse import urlsplit
CONFIG=Path(r'C:\ProgramData\RaceDvrJudgeCues\config.json')
class WebSocket:
 def __init__(self,url):
  u=urlsplit(url)
  if u.scheme!='ws' or u.hostname not in ('127.0.0.1','localhost','::1') or u.username or u.password or u.query or u.fragment:raise ValueError('Loopback only')
  self.socket=socket.create_connection((u.hostname,u.port or 4455),timeout=3);self.socket.settimeout(3);self.buffer=b''
  try:
   key=base64.b64encode(os.urandom(16)).decode();host='['+u.hostname+']' if ':' in u.hostname else u.hostname
   request=f'GET {u.path or "/"} HTTP/1.1\r\nHost: {host}:{u.port or 4455}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
   self.socket.sendall(request.encode('ascii'))
   while b'\r\n\r\n' not in self.buffer:
    data=self.socket.recv(4096)
    if not data or len(self.buffer)>16384:raise ValueError('Handshake failed')
    self.buffer+=data
   header,self.buffer=self.buffer.split(b'\r\n\r\n',1);lines=header.decode('ascii').split('\r\n');fields={k.lower():v.strip() for k,v in (line.split(':',1) for line in lines[1:] if ':' in line)}
   expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
   if lines[0].split()[1]!='101' or fields.get('sec-websocket-accept')!=expected or fields.get('upgrade','').lower()!='websocket':raise ValueError('Invalid upgrade')
  except Exception:self.socket.close();raise
 def close(self):self.socket.close()
 def read(self,n):
  while len(self.buffer)<n:
   chunk=self.socket.recv(max(4096,n-len(self.buffer)))
   if not chunk:raise OSError('Connection closed')
   self.buffer+=chunk
  data,self.buffer=self.buffer[:n],self.buffer[n:];return data
 def send_frame(self,payload,opcode=1):
  if len(payload)>65536:raise ValueError('Too large')
  mask=os.urandom(4);n=len(payload);header=bytes([128|opcode,128|n]) if n<126 else bytes([128|opcode,128|126])+struct.pack('!H',n)
  self.socket.sendall(header+mask+bytes(b^mask[i%4] for i,b in enumerate(payload)))
 def send(self,msg):self.send_frame(json.dumps(msg).encode())
 def receive(self):
  chunks=[];size=0;started=False;deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   a,b=self.read(2);op=a&15;final=bool(a&128);n=b&127
   if a&112 or b&128:raise ValueError('Unsupported frame')
   if n==126:n=struct.unpack('!H',self.read(2))[0]
   elif n==127:n=struct.unpack('!Q',self.read(8))[0]
   if n>1048576 or size+n>1048576:raise ValueError('Message too large')
   data=self.read(n)
   if op==8:raise OSError('OBS closed connection')
   if op in (9,10):
    if not final or n>125:raise ValueError('Invalid control frame')
    if op==9:self.send_frame(data,10)
    continue
   if op==1 and not started:started=True
   elif op!=0 or not started:raise ValueError('Unexpected message')
   chunks.append(data);size+=n
   if final:return json.loads(b''.join(chunks).decode('utf-8'))
  raise TimeoutError('OBS response deadline')

def authentication(password,salt,challenge):
 secret=base64.b64encode(hashlib.sha256((password+salt).encode()).digest()).decode()
 return base64.b64encode(hashlib.sha256((secret+challenge).encode()).digest()).decode()

def unknown():
 return {'id':'obs','status':'unknown','obsConnected':None,'recording':None,'recordingPaused':None,'recordingSeconds':None}

class Reader:
 def __init__(self):self.ws=None;self.identity=None;self.retry_at=0;self.failures=0
 def close(self):
  if self.ws:
   try:self.ws.close()
   except Exception:pass
  self.ws=None
 def probe(self,config_path=CONFIG,client=WebSocket):
  result=unknown()
  try:
   cfg=json.loads(Path(config_path).read_text(encoding='utf-8-sig'))['unification']['obs']
   if cfg.get('enabled') is not True:self.close();return result
   url=cfg['url'];password=cfg.get('password','')
   if not isinstance(password,str):self.close();return result
  except Exception:self.close();return result
  identity=(str(config_path),url,hashlib.sha256(password.encode()).digest(),client)
  if identity!=self.identity:
   self.close();self.identity=identity;self.retry_at=0;self.failures=0
  if self.ws is None and time.monotonic()<self.retry_at:
   result.update(status='red',obsConnected=False);return result
  try:
   if self.ws is None:
    self.ws=client(url);hello=self.ws.receive()
    if hello.get('op')!=0:raise ValueError('Expected hello')
    identify={'rpcVersion':1,'eventSubscriptions':0}
    auth=hello.get('d',{}).get('authentication')
    if auth:identify['authentication']=authentication(password,auth['salt'],auth['challenge'])
    self.ws.send({'op':1,'d':identify});identified=self.ws.receive()
    if identified.get('op')!=2:raise ValueError('Identification failed')
   result['obsConnected']=True
   self.ws.send({'op':6,'d':{'requestType':'GetRecordStatus','requestId':'raceops-record-status'}})
   reply=self.ws.receive();d=reply.get('d',{})
   if reply.get('op')!=7 or d.get('requestId')!='raceops-record-status' or d.get('requestType')!='GetRecordStatus':raise ValueError('Invalid response')
   if d.get('requestStatus',{}).get('result') is not True:
    result['status']='yellow';return result
   values=d.get('responseData',{});active=values.get('outputActive');paused=values.get('outputPaused');duration=values.get('outputDuration')
   if type(active) is not bool:
    result['status']='yellow';return result
   result.update(status='green',recording=active,recordingPaused=paused if type(paused) is bool else None,recordingSeconds=round(duration/1000,1) if type(duration) in (int,float) and 0<=duration<31536000000 else None)
   self.failures=0
   # Keep the authenticated session open for subsequent status reads.
  except Exception:
   self.close();self.failures+=1;self.retry_at=time.monotonic()+min(60,5*2**min(self.failures-1,4))
   result.update(status='red',obsConnected=False,recording=None,recordingPaused=None,recordingSeconds=None)
  return result

_reader=Reader()
def probe(config_path=CONFIG,client=WebSocket):return _reader.probe(config_path,client)

class Monitor:
 def __init__(self):
  self.reader=Reader();self.lock=threading.Lock();self.result=unknown();self.updated=0
  threading.Thread(target=self.run,daemon=True).start()
 def run(self):
  while True:
   try:value=self.reader.probe()
   except Exception:self.reader.close();value=unknown()
   with self.lock:self.result=value;self.updated=time.monotonic()
   time.sleep(3)
 def sample(self):
  with self.lock:return dict(self.result) if time.monotonic()-self.updated<15 else unknown()
_monitor=None
_monitor_lock=threading.Lock()
def monitor_sample():
 global _monitor
 with _monitor_lock:
  if _monitor is None:_monitor=Monitor()
 return _monitor.sample()
