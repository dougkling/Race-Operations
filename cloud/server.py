"""Race Operations backend with host-scoped, allowlisted recovery actions."""
import argparse,hashlib,hmac,json,secrets,sqlite3,threading,time,re
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
VERSION='0.8.0'
COMPATIBLE_AGENTS=('0.3.0','0.3.2','0.4.0','0.4.1','0.5.0','0.6.0','0.7.0','0.8.0')
from dvr_actions import ACTIONS as DVR_ACTIONS, guard as dvr_guard

def action_host(action):return 'dvr' if action in DVR_ACTIONS else 'cloud'

class Store:
 def __init__(self,config,db_path):
  self.config=config;self.lock=threading.RLock();self.samples={};self.sessions={}
  self.db=sqlite3.connect(db_path,check_same_thread=False)
  self.db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, actor TEXT, created REAL, state TEXT, pre TEXT, result TEXT)');self.db.execute('CREATE TABLE IF NOT EXISTS events (at REAL,id TEXT,state TEXT,result TEXT)');self.db.commit()
  if 'action' not in [r[1] for r in self.db.execute('PRAGMA table_info(jobs)')]:
   self.db.execute("ALTER TABLE jobs ADD COLUMN action TEXT NOT NULL DEFAULT 'pitwall-restart'");self.db.commit()
 def audit(self,jid,state,result=''):
  self.db.execute('UPDATE jobs SET state=?,result=? WHERE id=?',(state,result,jid));self.db.execute('INSERT INTO events VALUES (?,?,?,?)',(time.time(),jid,state,result));self.db.commit()
 def jobs(self):
  return [dict(zip(['id','actor','created','state','pre','result','action'],r)) for r in self.db.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 15')]
 def eligible(self,action='pitwall-restart'):
  if action in DVR_ACTIONS:return self.dvr_eligible(action)
  sample=self.samples.get('cloud',{});states={c['id']:c['status'] for c in sample.get('components',[])}
  flag='proxyRestartEnabled' if action=='proxy-restart' else 'pitwallRestartEnabled'
  targets=('cloud-proxy',) if action=='proxy-restart' else ('racebot','commentator')
  if not self.config.get(flag):return False,'Restart is not enabled for this target'
  if time.time()-sample.get('received',0)>45:return False,'Cloud agent is disconnected'
  if sample.get('agentVersion') not in COMPATIBLE_AGENTS:return False,'Cloud agent update is required'
  if any(states.get(k) not in ('green','yellow','red') for k in targets):return False,'Target health checks must be enabled and known'
  if not any(states.get(k) in ('yellow','red') for k in targets):return False,'Target is green'
  if self.db.execute("SELECT 1 FROM jobs WHERE state IN ('queued','dispatched','running')").fetchone():return False,'A restart is already pending; do not retry'
  row=self.db.execute('SELECT MAX(created) FROM jobs WHERE action=?',(action,)).fetchone()
  if row[0] and time.time()-row[0]<120:return False,'Restart cooldown: 120 seconds'
  return True,('Remote judges will disconnect temporarily; verify no critical judging transaction is in progress' if action=='proxy-restart' else 'Both RaceBot and Commentator will be interrupted')

 def connector_link(self):
  cloud=self.samples.get('cloud',{})
  if time.time()-cloud.get('received',0)>45:return None
  proxy=next((c for c in cloud.get('components',[]) if c['id']=='cloud-proxy'),{})
  return proxy.get('dvrConnected') if proxy.get('status')=='green' else None
 def dvr_eligible(self,action):
  sample=self.samples.get('dvr',{})
  if self.config.get('dvrControlsEnabled') is not True:return False,'DVR controls not enabled on backend'
  if time.time()-sample.get('received',0)>45:return False,'DVR agent is disconnected'
  if sample.get('agentVersion')!='0.8.0':return False,'DVR agent v0.8.0 required'
  ok,reason=dvr_guard(action,{c['id']:c for c in sample.get('components',[])},sample.get('capabilities',[]),self.connector_link())
  if not ok:return ok,reason
  if self.db.execute("SELECT 1 FROM jobs WHERE state IN ('queued','dispatched','running')").fetchone():return False,'An action is already pending; do not retry'
  last=self.db.execute('SELECT MAX(created) FROM jobs WHERE action=?',(action,)).fetchone()[0]
  if last and time.time()-last<120:return False,'Action cooldown: 120 seconds'
  return True,reason

def make_server(config,db_path,port=None):
 state=Store(config,db_path)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,code,data,ctype='application/json',cookie=None):
   raw=data.encode('utf-8') if isinstance(data,str) else json.dumps(data).encode('utf-8');self.send_response(code)
   for k,v in {'Content-Type':ctype,'Content-Length':str(len(raw)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; form-action 'none'; frame-ancestors 'none'"}.items():self.send_header(k,v)
   if cookie:self.send_header('Set-Cookie',cookie)
   self.end_headers();self.wfile.write(raw)
  def session(self):
   cookies=dict(v.strip().split('=',1) for v in self.headers.get('Cookie','').split(';') if '=' in v)
   s=state.sessions.get(cookies.get('raceops',''))
   return s if s and s['expires']>time.time() else None
  def body(self):
   n=int(self.headers.get('Content-Length','0'))
   if n<1 or n>65536:raise ValueError()
   data=json.loads(self.rfile.read(n))
   if not isinstance(data,dict):raise ValueError()
   return data
  def agent(self):
   a=self.headers.get('Authorization','')
   return next((h for h in config['hosts'] if hmac.compare_digest(a,'Bearer '+h['token'])),None)
  def do_GET(self):
   path=urlsplit(self.path).path
   if path=='/health':return self.send(200,{'ok':True,'version':VERSION,'controlsEnabled':bool(config.get('pitwallRestartEnabled') or config.get('proxyRestartEnabled') or config.get('dvrControlsEnabled'))})
   if path in ('/','/app.js'):
    f='index.html' if path=='/' else 'app.js'
    return self.send(200,(Path(__file__).parent/'web'/f).read_text(encoding='utf-8'),'text/html; charset=utf-8' if path=='/' else 'text/javascript; charset=utf-8')
   if path=='/api/status':
    with state.lock:
     s=self.session()
     if not s:return self.send(401,{'error':'Sign in required'})
     hosts=[{'id':h['id'],'name':h['name'],'connected':time.time()-state.samples.get(h['id'],{}).get('received',0)<45,'sample':state.samples.get(h['id'])} for h in config['hosts']]
     allowed,reason=state.eligible()
     proxy_allowed,proxy_reason=state.eligible('proxy-restart')
     return self.send(200,{'hosts':hosts,'csrf':s['csrf'],'restartAllowed':allowed,'restartReason':reason,'proxyRestartAllowed':proxy_allowed,'proxyRestartReason':proxy_reason,'dvrActions':{a:{'allowed':state.eligible(a)[0],'reason':state.eligible(a)[1],'label':v[1],'target':v[0]} for a,v in DVR_ACTIONS.items()},'jobs':state.jobs(),'version':VERSION})
   return self.send(404,{'error':'Not found'})
  def do_POST(self):
   try:
    with state.lock:
     if self.path=='/api/login':
      b=self.body();supplied=hashlib.sha256(str(b.get('token','')).encode()).hexdigest()
      if not hmac.compare_digest(supplied,config['adminTokenHash']):return self.send(401,{'error':'Invalid token'})
      sid=secrets.token_urlsafe(32);state.sessions={k:v for k,v in state.sessions.items() if v['expires']>time.time()};state.sessions[sid]={'expires':time.time()+28800,'csrf':secrets.token_urlsafe(32),'actor':'administrator'}
      return self.send(200,{'ok':True},cookie='raceops='+sid+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
     if self.path in ('/api/actions/pitwall-restart','/api/actions/proxy-restart') or self.path in ['/api/actions/'+a for a in DVR_ACTIONS]:
      action=self.path.rsplit('/',1)[1]
      confirmation=DVR_ACTIONS[action][1] if action in DVR_ACTIONS else 'Restart DVR cloud proxy' if action=='proxy-restart' else 'Restart RaceBot + Commentator'
      s=self.session()
      if not s:return self.send(401,{'error':'Sign in required'})
      if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):return self.send(403,{'error':'Invalid CSRF token'})
      b=self.body();jid=b.get('requestId','')
      if not isinstance(jid,str) or not re.fullmatch('[a-f0-9-]{36}',jid) or b.get('confirmation')!=confirmation:return self.send(400,{'error':'Explicit confirmation required'})
      prior=state.db.execute('SELECT state,action FROM jobs WHERE id=?',(jid,)).fetchone()
      if prior:
       if prior[1]!=action:return self.send(409,{'error':'Request ID belongs to another target'})
       return self.send(200,{'id':jid,'state':prior[0]})
      allowed,reason=state.eligible(action)
      if not allowed:return self.send(409,{'error':reason})
      state.db.execute('INSERT INTO jobs (id,actor,created,state,pre,result,action) VALUES (?,?,?,?,?,?,?)',(jid,s['actor'],time.time(),'queued',json.dumps(state.samples[action_host(action)]['components']),'',action));state.audit(jid,'queued','operator_confirmed')
      return self.send(202,{'id':jid,'state':'queued'})
     if self.path in ('/api/heartbeat','/api/action-result'):
      host=self.agent()
      if not host:return self.send(401,{'error':'Unauthorized agent'})
      b=self.body()
      if b.get('hostId')!=host['id']:return self.send(403,{'error':'Host identity mismatch'})
      if self.path=='/api/action-result':
       row=state.db.execute('SELECT state,action FROM jobs WHERE id=?',(b.get('id',''),)).fetchone()
       if not row:return self.send(404,{'error':'Unknown action'})
       if host['id']!=action_host(row[1]):return self.send(403,{'error':'Wrong host'})
       if row[0] in ('dispatched','running'):
        outcome=b.get('state');result=b.get('result')
        if outcome not in ('running','succeeded','failed','skipped','indeterminate') or result not in ('executing','both_http_checks_passed','manager_failed','recovery_timeout','already_healthy','unsafe_preflight','execution_uncertain','agent_controls_disabled','proxy_health_passed','task_restart_failed','component_recovered','health_check_completed','health_check_failed','preflight_blocked','local_action_failed'):return self.send(400,{'error':'Invalid action result'})
        state.audit(b['id'],outcome,result)
       return self.send(200,{'ok':True})
      allowed={c['id'] for c in host['components']};components=[]
      for c in b.get('components',[]):
       if isinstance(c,dict) and c.get('id') in allowed:
        clean={'id':c['id'],'status':c.get('status') if c.get('status') in ('green','yellow','red','unknown') else 'unknown','latencyMs':c.get('latencyMs') if isinstance(c.get('latencyMs'),(float,int)) else None}
        if (host['id'],c['id']) in (('cloud','disk-space'),('dvr','disk-network')):
         total=c.get('totalBytes');free=c.get('freeBytes')
         valid=type(total) is int and type(free) is int and 0<total<=2**60 and 0<=free<=total
         clean.update(totalBytes=total if valid else None,freeBytes=free if valid else None,freePercent=round(100*free/total,1) if valid else None)
         if valid:
          percent=100*free/total
          clean['status']='red' if free<2*1024**3 or percent<5 else 'yellow' if free<10*1024**3 or percent<15 else 'green'
         else:clean['status']='unknown'
        if host['id']=='cloud' and c['id']=='cloud-proxy':
         clean['dvrConnected']=c.get('dvrConnected') if type(c.get('dvrConnected')) is bool else None
         count=c.get('remoteJudges');clean['remoteJudges']=count if type(count) is int and 0<=count<=100000 else None
        if host['id']=='dvr' and c['id']=='judge-cues':
         clean['recording']=c.get('recording') if type(c.get('recording')) is bool else None
        if host['id']=='dvr' and c['id']=='obs':
         count=c.get('processCount');clean['processCount']=count if type(count) is int and 0<=count<1000 else None
         for key in ('obsConnected','recording','recordingPaused'):clean[key]=c.get(key) if type(c.get(key)) is bool else None
         duration=c.get('recordingSeconds');clean['recordingSeconds']=duration if type(duration) in (int,float) and 0<=duration<31536000 else None
        if host['id']=='dvr' and c['id']=='pilot-review':
         clean['pilotReason']=c.get('pilotReason') if c.get('pilotReason') in ('checking','unavailable','stale','manifest_unavailable','page_unavailable','clock_warning','video_failed','healthy') else 'unavailable'
         for key in ('pageOk','manifestOk'):clean[key]=c.get(key) if type(c.get(key)) is bool else None
         for key in ('raceCount','manifestAgeSeconds','lastCheckedEpoch'):
          value=c.get(key);clean[key]=value if type(value) is int and 0<=value<=4294967295 else None
         for key in ('currentVideo','archivedVideo'):clean[key]=c.get(key) if c.get(key) in ('pass','failed','absent','unknown') else 'unknown'
        if host['id']=='dvr' and c['id']=='health-monitor':
         clean['taskState']=c.get('taskState') if c.get('taskState') in ('Ready','Running','Disabled','Queued','unknown') else 'unknown'
         clean['healthReason']=c.get('healthReason') if c.get('healthReason') in ('healthy','warnings','failed','running','disabled','stale','report_missing','report_invalid','report_mismatch','task_unknown','clock_warning') else 'task_unknown'
         for key in ('lastTaskResult','lastRunEpoch','reportAgeSeconds','passes','warnings','failures'):
          value=c.get(key);clean[key]=value if type(value) is int and 0<=value<=4294967295 else None
         allowed_warnings=('Judge Cues health endpoint','Graphics race source','Heat tracking arm state','S3 manifest','OBS WebSocket','Review Status integration','Uploader log freshness','DVR disk space','Race Review file','IIS Race Review HTTP','Uploader process','Uploader configuration','Recording layout metadata')
         names=c.get('warningChecks');clean['warningChecks']=[name for name in allowed_warnings if isinstance(names,list) and name in names]
        if host['id']=='dvr' and c['id']=='uploader':
         clean['taskState']=c.get('taskState') if c.get('taskState') in ('Running','Ready','Disabled','Queued','unknown') else 'unknown'
         clean['operation']=c.get('operation') if c.get('operation') in ('idle','uploading','upload_complete','archive_verified','manifest_published','started','error','unknown') else 'unknown'
         clean['uploaderReason']=c.get('uploaderReason') if c.get('uploaderReason') in ('healthy','clock_warning','recent_error','heartbeat_missing','heartbeat_stale','log_unavailable','task_unknown','task_not_running') else 'task_unknown'
         for key in ('heartbeatAgeSeconds','lastEventAgeSeconds','filesScanned','heartbeatWarningSeconds'):
          value=c.get(key);clean[key]=value if type(value) in (int,float) and 0<=value<=2147483647 else None
        components.append(clean)
      state.samples[host['id']]={'received':time.time(),'components':components,'agentVersion':b.get('agentVersion') if b.get('agentVersion') in COMPATIBLE_AGENTS else 'older','capabilities':[a for a in DVR_ACTIONS if isinstance(b.get('capabilities'),list) and a in b['capabilities']] if host['id']=='dvr' else []}
      commands=[]
      if b.get('agentVersion') in COMPATIBLE_AGENTS:
       rows=state.db.execute("SELECT id,created,action FROM jobs WHERE state='queued' ORDER BY created").fetchall()
       for row in rows:
        if action_host(row[2])!=host['id']:continue
        if host['id']=='dvr' and b.get('agentVersion')!='0.8.0':continue
        if time.time()-row[1]>60:state.audit(row[0],'skipped','queue_expired')
        else:
         state.audit(row[0],'dispatched','awaiting_agent');commands=[{'id':row[0],'action':row[2]}]
        break
      return self.send(200,{'ok':True,'commands':commands,'connectorConnected':state.connector_link() if host['id']=='dvr' else None})
     return self.send(404,{'error':'Not found'})
   except (ValueError,TypeError,KeyError):return self.send(400,{'error':'Invalid request'})
   except sqlite3.Error:return self.send(503,{'error':'Audit store unavailable; action not confirmed'})
 server=ThreadingHTTPServer(('127.0.0.1',config['port'] if port is None else port),Handler);server.state=state;return server
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();cp=Path(a.config);cfg=json.loads(cp.read_text(encoding='utf-8'));make_server(cfg,cp.parent/'actions.sqlite3').serve_forever()
