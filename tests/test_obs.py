import base64,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dvr'))
from obs_monitor import probe,authentication,WebSocket
class FakeOBS:
 replies=[];sent=[]
 def __init__(self,url):self.url=url
 def receive(self):return self.replies.pop(0)
 def send(self,msg):self.sent.append(msg)
 def close(self):pass
class OBS(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'config.json';self.path.write_text(json.dumps({'unification':{'obs':{'enabled':True,'url':'ws://127.0.0.1:4455','password':'PRIVATE'}}}));FakeOBS.sent=[]
 def tearDown(self):self.tmp.cleanup()
 def replies(self,active=False):
  FakeOBS.replies=[{'op':0,'d':{'authentication':{'salt':'salt','challenge':'challenge'}}},{'op':2,'d':{}},{'op':7,'d':{'requestId':'raceops-record-status','requestType':'GetRecordStatus','requestStatus':{'result':True},'responseData':{'outputActive':active,'outputPaused':False,'outputDuration':123000}}}]
 def test_idle_is_explicit_false(self):
  self.replies();r=probe(self.path,FakeOBS);self.assertIs(r['recording'],False);self.assertEqual(r['status'],'green');self.assertNotIn('PRIVATE',json.dumps(r));self.assertEqual(FakeOBS.sent[-1]['d']['requestType'],'GetRecordStatus')
 def test_active_is_recording(self):
  self.replies(True);r=probe(self.path,FakeOBS);self.assertIs(r['recording'],True);self.assertEqual(r['recordingSeconds'],123)
 def test_missing_state_remains_unknown(self):
  self.replies();FakeOBS.replies[-1]['d']['responseData'].pop('outputActive');r=probe(self.path,FakeOBS);self.assertIsNone(r['recording']);self.assertIs(r['obsConnected'],True);self.assertEqual(r['status'],'yellow')
 def test_auth_failure_never_reports_idle(self):
  FakeOBS.replies=[{'op':0,'d':{}},{'op':9}];r=probe(self.path,FakeOBS);self.assertIsNone(r['recording']);self.assertEqual(r['status'],'red')
 def test_missing_config(self):
  r=probe(Path(self.tmp.name)/'missing');self.assertEqual(r['status'],'unknown');self.assertIsNone(r['recording'])
 def test_remote_config_rejected_before_connection(self):
  with self.assertRaises(ValueError):WebSocket('ws://example.com:4455')
 def test_auth_formula(self):
  secret=base64.b64encode(hashlib.sha256(b'PRIVATEsalt').digest());expected=base64.b64encode(hashlib.sha256(secret+b'challenge').digest()).decode();self.assertEqual(authentication('PRIVATE','salt','challenge'),expected)

class WebSocketIntegration(OBS):
 def test_real_socket_handshake_auth_and_read_only_rpc(self):
  import socket,threading,struct
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1];seen=[];errors=[]
  def worker():
   try:
    c,_=listener.accept();c.settimeout(3)
    with c:
     header=b''
     while b'\r\n\r\n' not in header:header+=c.recv(4096)
     fields=dict(line.split(': ',1) for line in header.decode().split('\r\n')[1:] if ': ' in line)
     accept=base64.b64encode(hashlib.sha1((fields['Sec-WebSocket-Key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
     c.sendall(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+'\r\n\r\n').encode())
     def send(msg):
      b=json.dumps(msg).encode();h=bytes([129,len(b)]) if len(b)<126 else bytes([129,126])+struct.pack('!H',len(b));c.sendall(h+b)
     def read(n):
      b=b''
      while len(b)<n:b+=c.recv(n-len(b))
      return b
     def recv():
      a,b=read(2);self.assertTrue(b&128);n=b&127
      if n==126:n=struct.unpack('!H',read(2))[0]
      mask=read(4);data=read(n);return json.loads(bytes(v^mask[i%4] for i,v in enumerate(data)))
     send({'op':0,'d':{'rpcVersion':1,'authentication':{'salt':'salt','challenge':'challenge'}}});ident=recv();self.assertEqual(ident['d']['authentication'],authentication('PRIVATE','salt','challenge'));send({'op':2,'d':{'negotiatedRpcVersion':1}})
     for _ in range(2):
      request=recv();seen.append(request['d']['requestType']);send({'op':7,'d':{'requestId':request['d']['requestId'],'requestType':'GetRecordStatus','requestStatus':{'result':True},'responseData':{'outputActive':False,'outputPaused':False,'outputDuration':0}}})
   except Exception as e:errors.append(e)
   finally:listener.close()
  t=threading.Thread(target=worker,daemon=True);t.start();cfg=json.loads(self.path.read_text());cfg['unification']['obs']['url']='ws://127.0.0.1:'+str(port);self.path.write_text(json.dumps(cfg));r=probe(self.path);r2=probe(self.path);t.join(4)
  self.assertFalse(errors,repr(errors));self.assertEqual(seen,['GetRecordStatus','GetRecordStatus']);self.assertEqual(r2['status'],'green');self.assertEqual(r['status'],'green');self.assertIs(r['recording'],False)

class Persistence(unittest.TestCase):
 def test_failure_backoff_prevents_connection_storm(self):
  from obs_monitor import Reader
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'config.json';path.write_text(json.dumps({'unification':{'obs':{'enabled':True,'url':'ws://127.0.0.1:4455','password':'PRIVATE'}}}));attempts=[]
   def fail(url):attempts.append(url);raise OSError('not available')
   reader=Reader();first=reader.probe(path,fail);second=reader.probe(path,fail)
   self.assertEqual(len(attempts),1);self.assertIsNone(first['recording']);self.assertIsNone(second['recording'])
 def test_reuses_connection_without_reidentifying(self):
  from obs_monitor import Reader
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'config.json';path.write_text(json.dumps({'unification':{'obs':{'enabled':True,'url':'ws://127.0.0.1:4455','password':'PRIVATE'}}}));instances=[];sent=[];closed=[]
   reply={'op':7,'d':{'requestId':'raceops-record-status','requestType':'GetRecordStatus','requestStatus':{'result':True},'responseData':{'outputActive':False}}}
   class Client:
    def __init__(self,url):instances.append(url);self.messages=iter([{'op':0,'d':{}},{'op':2},reply,reply])
    def receive(self):return next(self.messages)
    def send(self,m):sent.append(m)
    def close(self):closed.append(True)
   reader=Reader();reader.probe(path,Client);reader.probe(path,Client)
   self.assertEqual(len(instances),1);self.assertEqual([m['op'] for m in sent],[1,6,6]);self.assertFalse(closed);reader.close()
