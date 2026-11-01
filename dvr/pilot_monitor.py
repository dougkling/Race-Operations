"""Public S3 availability probes; bounded JSON and HEAD-only sample videos."""
import json,time,threading,urllib.request,re
from datetime import datetime,timezone
from urllib.parse import urlsplit,urljoin,unquote
BASE='https://race-dvr-public.s3.us-east-1.amazonaws.com/pilot-review/'
INTERVAL=300
STALE=600
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):return None

def empty(reason='checking'):
 return {'id':'pilot-review','status':'unknown','pilotReason':reason,'pageOk':None,'manifestOk':None,'raceCount':None,'manifestAgeSeconds':None,'currentVideo':'unknown','archivedVideo':'unknown','lastCheckedEpoch':None}

def request(url,method='GET',limit=0):
 # No bearer, AWS credentials, environment proxy or cross-origin redirects.
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 req=urllib.request.Request(url,method=method,headers={'Cache-Control':'no-cache','User-Agent':'RaceOperations/0.7.0'})
 with opener.open(req,timeout=5) as response:
  if response.status!=200:raise ValueError('Unexpected status')
  body=response.read(limit+1) if method=='GET' else b''
  if len(body)>limit:raise ValueError('Response too large')
  return body,response.headers

def parse_manifest(body,now):
 data=json.loads(body.decode('utf-8-sig'))
 if not isinstance(data,dict) or not isinstance(data.get('version'),str) or not isinstance(data.get('races'),list) or len(data['races'])>20000:raise ValueError('Invalid manifest')
 value=data.get('generatedAt')
 if not isinstance(value,str):raise ValueError('Timestamp missing')
 # .NET manifests use seven fractional digits; Python 3.10 accepts at most six.
 value=re.sub(r'(\.\d{6})\d+(?=[+-]|$)',r'\1',value.replace('Z','+00:00'))
 generated=datetime.fromisoformat(value)
 if generated.tzinfo is None:raise ValueError('Timestamp lacks zone')
 return data['races'],max(0,int(now-generated.timestamp())),generated.timestamp()>now+60

def video_url(race):
 if not isinstance(race,dict):raise ValueError('Invalid race')
 path=race.get('url');key=race.get('key');size=race.get('size')
 if not isinstance(path,str) or not isinstance(key,str) or type(size) is not int or not 0<size<=2**53:raise ValueError('Invalid video fields')
 parsed=urlsplit(path)
 if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or '\\' in path:raise ValueError('Only relative object paths')
 url=urljoin(BASE,path);decoded=unquote(urlsplit(url).path)
 if not decoded.startswith('/pilot-review/races/') or not decoded.lower().endswith('.mp4') or decoded!='/'+key or any(x in ('.','..') for x in decoded.split('/')):raise ValueError('Invalid video object path')
 return url,size

def probe(fetch=request,now=None):
 now=time.time() if now is None else now;row=empty();row['lastCheckedEpoch']=int(now)
 suffix='?check='+str(int(now))
 try:
  body,headers=fetch(BASE+'index.html'+suffix,'GET',1048576)
  if not body or b'<html' not in body.lower():raise ValueError('Invalid page')
  row['pageOk']=True
 except (OSError,ValueError):row['pageOk']=False
 try:
  body,headers=fetch(BASE+'manifest.json'+suffix,'GET',4194304)
  races,age,future=parse_manifest(body,now);row.update(manifestOk=True,raceCount=len(races),manifestAgeSeconds=age)
 except (OSError,ValueError,TypeError):
  row.update(manifestOk=False,status='yellow' if row['pageOk'] else 'red',pilotReason='manifest_unavailable');return row
 # Schema validated before making any object requests.
 if any(not isinstance(race,dict) for race in races):row.update(status='yellow',manifestOk=False,pilotReason='manifest_unavailable');return row
 for field,archived in (('currentVideo',False),('archivedVideo',True)):
  race=next((r for r in races if bool(r.get('archive'))==archived),None)
  if race is None:row[field]='absent';continue
  try:
   url,size=video_url(race);_,headers=fetch(url+suffix,'HEAD',0)
   content_type=headers.get('Content-Type','').split(';',1)[0].strip().lower()
   row[field]='pass' if content_type=='video/mp4' and int(headers.get('Content-Length','-1'))==size else 'failed'
  except (OSError,ValueError,TypeError):row[field]='failed'
 reason='page_unavailable' if not row['pageOk'] else 'clock_warning' if future else 'video_failed' if 'failed' in (row['currentVideo'],row['archivedVideo']) else 'healthy'
 row.update(status='green' if reason=='healthy' else 'yellow',pilotReason=reason)
 return row

class Monitor:
 def __init__(self,check=probe,clock=time.monotonic):self.check=check;self.clock=clock;self.lock=threading.Lock();self.row=empty();self.at=None;self.started=False
 def start(self):
  with self.lock:
   if self.started:return
   self.started=True
  threading.Thread(target=self.run,daemon=True).start()
 def run(self):
  while True:
   started=self.clock()
   try:row=self.check()
   except Exception:row=empty('unavailable')
   with self.lock:self.row=row;self.at=started
   time.sleep(INTERVAL)
 def snapshot(self):
  with self.lock:row=dict(self.row);at=self.at
  if at is None:return row
  elapsed=max(0,int(self.clock()-at))
  if row['manifestAgeSeconds'] is not None:row['manifestAgeSeconds']+=elapsed
  if elapsed>STALE:return empty('stale')
  return row
_monitor=Monitor()
def monitor_sample():
 _monitor.start();return _monitor.snapshot()
