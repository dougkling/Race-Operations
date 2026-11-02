"""Windows agent: fixed PitWall restart with durable at-most-once execution."""
import argparse,json,time,urllib.request,urllib.error,sqlite3,subprocess,os,threading
from pathlib import Path
from disk_monitor import sample as disk_sample
from ai_monitor import sample as ai_sample, reconnect as ai_reconnect
from urllib.parse import urlparse

def collect(config):
    result=[]
    for c in config['components']:
        if c['id']=='disk-space':continue
        if c['id']=='racebot-ai':
            result.append(ai_sample(config) if c.get('enabled') else {'id':'racebot-ai','status':'unknown'})
            continue
        row={'id':c['id'],'status':'unknown'}
        if c.get('enabled') and c.get('probe')=='http':
            u=urlparse(c['url'])
            if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost') or u.username or u.password: raise ValueError('Only loopback HTTP probes permitted')
            start=time.monotonic()
            try:
                # Prevent environment proxy routing and cross-host redirects.
                class NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self,*args): return None
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
                with opener.open(c['url'],timeout=3) as r:
                    body=r.read(65536); row['status']='green' if r.status==200 else 'red'
                    if c.get('requireOk') and row['status']=='green':
                        health=json.loads(body)
                        row['status']='green' if isinstance(health,dict) and health.get('ok') is True else 'yellow'
                if c['id']=='cloud-proxy' and c['url']=='http://127.0.0.1:8767/health' and row['status']=='green':
                    health=json.loads(body)
                    if isinstance(health,dict) and health.get('ok') is True:
                        row['dvrConnected']=health.get('dvrConnected') if type(health.get('dvrConnected')) is bool else None
                        count=health.get('remoteJudges');row['remoteJudges']=count if type(count) is int and 0<=count<=100000 else None
                row['latencyMs']=round((time.monotonic()-start)*1000)
            except (OSError,ValueError): row['status']='red'
        result.append(row)
    result.append(disk_sample('disk-space'))
    return {'hostId':config['hostId'],'components':result}

VERSION='0.10.0'
MANAGER=r'C:\Program Files\PitWall\manager\PitWall.ps1'
POWERSHELL=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def perform_restart(config,runner=subprocess.run,probe=collect,sleep=time.sleep,clock=time.monotonic):
 if config.get('hostId')!='cloud' or not config.get('pitwallRestartEnabled'):return 'skipped','agent_controls_disabled'
 current={c['id']:c['status'] for c in probe(config)['components']}
 if any(current.get(k) not in ('green','yellow','red') for k in ('racebot','commentator')):return 'skipped','unsafe_preflight'
 if all(current[k]=='green' for k in ('racebot','commentator')) and current.get('racebot-ai')!='red':return 'skipped','already_healthy'
 if not Path(MANAGER).is_file() or os.name!='nt':return 'skipped','unsafe_preflight'
 try:
  # Existing local manager only. Process-scoped policy flag; no machine policy changes.
  r=runner([POWERSHELL,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',MANAGER,'-Command','restart'],cwd=str(Path(MANAGER).parent),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120,check=False)
  if r.returncode!=0:return 'failed','manager_failed'
 except subprocess.TimeoutExpired:return 'indeterminate','execution_uncertain'
 except OSError:return 'failed','manager_failed'
 deadline=clock()+90
 while clock()<deadline:
  statuses={c['id']:c['status'] for c in probe(config)['components']}
  if all(statuses.get(k)=='green' for k in ('racebot','commentator')):
   if 'racebot-ai' not in statuses:return 'succeeded','both_http_checks_passed'
   if statuses.get('racebot-ai')=='green':return 'succeeded','ai_and_http_checks_passed'
  sleep(3)
 return 'failed','recovery_timeout'

PROXY_TASK='Race DVR Judge Proxy'
def perform_proxy_restart(config,runner=subprocess.run,probe=collect,sleep=time.sleep,clock=time.monotonic):
 if config.get('hostId')!='cloud' or not config.get('proxyRestartEnabled'):return 'skipped','agent_controls_disabled'
 profile=next((c for c in config.get('components',[]) if c.get('id')=='cloud-proxy'),{})
 if not profile.get('enabled') or profile.get('url')!='http://127.0.0.1:8767/health' or not profile.get('requireOk'):return 'skipped','unsafe_preflight'
 status=next((c['status'] for c in probe(config)['components'] if c['id']=='cloud-proxy'),'unknown')
 if status=='green':return 'skipped','already_healthy'
 if status not in ('red','yellow') or os.name!='nt':return 'skipped','unsafe_preflight'
 # Fixed task only. No Node process killing, host reboot, or other application control.
 command="$ErrorActionPreference='Stop'; $task=Get-ScheduledTask -TaskName 'Race DVR Judge Proxy' -TaskPath '\\'; Stop-ScheduledTask -InputObject $task; $limit=(Get-Date).AddSeconds(15); do { Start-Sleep -Milliseconds 500; $task=Get-ScheduledTask -TaskName 'Race DVR Judge Proxy' -TaskPath '\\' } while ($task.State -eq 'Running' -and (Get-Date) -lt $limit); if ($task.State -eq 'Running') { throw 'Proxy task did not stop' }; Start-ScheduledTask -InputObject $task"
 try:
  r=runner([POWERSHELL,'-NoProfile','-NonInteractive','-Command',command],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,check=False)
  if r.returncode!=0:return 'failed','task_restart_failed'
 except subprocess.TimeoutExpired:return 'indeterminate','execution_uncertain'
 except OSError:return 'failed','task_restart_failed'
 deadline=clock()+60
 while clock()<deadline:
  state=next((c['status'] for c in probe(config)['components'] if c['id']=='cloud-proxy'),'unknown')
  if state=='green':return 'succeeded','proxy_health_passed'
  sleep(3)
 return 'failed','recovery_timeout'

class Executor:
 def __init__(self,config,journal):
  self.config=config;self.db=sqlite3.connect(journal,check_same_thread=False);self.lock=threading.Lock();self.busy=False
  self.db.execute('CREATE TABLE IF NOT EXISTS executions (id TEXT PRIMARY KEY,state TEXT,result TEXT)')
  # A previous execution may have reached the manager. Never replay after a crash.
  self.db.execute("UPDATE executions SET state='indeterminate',result='execution_uncertain' WHERE state='running'");self.db.commit()
 def accept(self,command):
  if command.get('action') not in ('pitwall-restart','proxy-restart','racebot-ai-reconnect'):return
  jid=command.get('id')
  if not isinstance(jid,str) or len(jid)!=36:return
  with self.lock:
   if self.busy or self.db.execute('SELECT 1 FROM executions WHERE id=?',(jid,)).fetchone():return
   self.db.execute('INSERT INTO executions VALUES (?,?,?)',(jid,'running','executing'));self.db.commit();self.busy=True
  threading.Thread(target=self.execute,args=(jid,command['action']),daemon=True).start()
 def execute(self,jid,action):
  try:
   if action=='racebot-ai-reconnect':status,result=ai_reconnect(self.config,jid)
   else:status,result=(perform_proxy_restart if action=='proxy-restart' else perform_restart)(self.config)
  except Exception:status,result='indeterminate','execution_uncertain'
  with self.lock:
   self.db.execute('UPDATE executions SET state=?,result=? WHERE id=?',(status,result,jid));self.db.commit();self.busy=False
 def reports(self):
  with self.lock:return list(self.db.execute('SELECT id,state,result FROM executions'))
 def acknowledged(self,jid,status):
  if status=='running':return
  with self.lock:self.db.execute('DELETE FROM executions WHERE id=? AND state=?',(jid,status));self.db.commit()
  # Backend never redelivers dispatched commands, so deleted terminal reports cannot replay.

def run(config,journal):
 u=urlparse(config['serverUrl'])
 if u.scheme!='https' and not (u.scheme=='http' and u.hostname in ('127.0.0.1','localhost')):raise ValueError('Remote agent transport requires HTTPS')
 executor=Executor(config,journal)
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args):return None
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 def post(path,payload):
  req=urllib.request.Request(config['serverUrl'].rstrip('/')+path,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+config['token'],'Content-Type':'application/json'})
  with opener.open(req,timeout=10) as r:return json.loads(r.read(65536))
 while True:
  try:
   payload=collect(config);payload['agentVersion']=VERSION
   answer=post('/api/heartbeat',payload)
   for cmd in answer.get('commands',[]):executor.accept(cmd)
   for jid,status,result in executor.reports():
    post('/api/action-result',{'hostId':config['hostId'],'id':jid,'state':status,'result':result});executor.acknowledged(jid,status)
  except Exception:pass
  time.sleep(5)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();cp=Path(a.config);run(json.loads(cp.read_text(encoding='utf-8')),cp.parent/'agent-actions.sqlite3')
