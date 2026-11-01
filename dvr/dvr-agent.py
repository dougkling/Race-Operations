"""Outbound RaceDVR monitoring and allowlisted recovery agent."""
import argparse,json,time,urllib.request,urllib.error,threading
from pathlib import Path
from pilot_monitor import monitor_sample as pilot_probe
from health_monitor import monitor_sample as health_probe
from disk_monitor import sample as disk_sample
from obs_monitor import monitor_sample as obs_probe
from uploader_monitor import monitor_sample as uploader_probe
from urllib.parse import urlsplit
from dvr_control import Executor, inventory
import health_monitor, uploader_monitor
VERSION='0.8.0'
_collect_lock=threading.Lock()
_link=None
_link_at=0
def link_state():return _link if time.monotonic()-_link_at<45 else None
CHECKS=[('judge-cues','http://127.0.0.1:8766/health',True),('review-status','http://127.0.0.1:8765/health',False),('iis','http://127.0.0.1/index.asp',False)]
PENDING=['connector','scoring']
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):return None

def opener():return urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
def validate(config):
 if config.get('hostId')!='dvr' or not isinstance(config.get('token'),str) or len(config['token'])<20:raise ValueError('Valid DVR enrollment required')
 u=urlsplit(config.get('serverUrl',''))
 if u.username or u.password or u.query or u.fragment or u.path not in ('','/'):raise ValueError('Server URL must be an origin without credentials')
 if u.scheme=='https':return
 if config.get('allowHttp') is True and config.get('serverUrl').rstrip('/')=='http://98.84.103.79':return
 raise ValueError('HTTPS required except explicitly configured current cloud HTTP endpoint')

def collect(open_url=None, fresh=False):
 with _collect_lock:
  if fresh:
   health_monitor._at=0;uploader_monitor._at=0
  return _collect(open_url)

def _collect(open_url=None):
 open_url=open_url or opener().open;rows=[]
 for cid,url,require_ok in CHECKS:
  row={'id':cid,'status':'red'};start=time.monotonic()
  try:
   with open_url(url,timeout=3) as r:
    body=r.read(65536);row['status']='green' if r.status==200 else 'red'
    if require_ok and row['status']=='green':
     try:
      health=json.loads(body);row['status']='green' if health.get('ok') is True else 'yellow'
      recording=health.get('integration',{}).get('recording');row['recording']=recording if type(recording) is bool else None
     except (ValueError,AttributeError):row['status']='yellow'
   row['latencyMs']=round((time.monotonic()-start)*1000)
  except (OSError,ValueError):pass
  rows.append(row)
 obs=obs_probe();obs['processCount']=inventory().get('obsProcessCount')
 return {'hostId':'dvr','agentVersion':VERSION,'components':rows+[obs,uploader_probe(),disk_sample('disk-network',recordings=True),health_probe(),pilot_probe()]+[{'id':i,'status':'unknown'} for i in PENDING]}

def send(config,payload,path='/api/heartbeat'):
 global _link,_link_at
 req=urllib.request.Request(config['serverUrl'].rstrip('/')+path,data=json.dumps(payload).encode('utf-8'),headers={'Authorization':'Bearer '+config['token'],'Content-Type':'application/json'})
 with opener().open(req,timeout=10) as r:
  result=json.loads(r.read(65536))
  if result.get('ok') is not True:raise ValueError('Heartbeat not accepted')
 if path=='/api/heartbeat':
  _link=result.get('connectorConnected') if type(result.get('connectorConnected')) is bool else None;_link_at=time.monotonic()
 return result

def run(config,folder):
 validate(config)
 executor=Executor(config,folder/'dvr-actions.sqlite3',lambda:collect(fresh=True),link_state)
 while True:
  sample=collect();sample['capabilities']=config.get('dvrCapabilities',[]) if config.get('dvrControlsEnabled') is True else [];report={'version':VERSION,'lastAttempt':time.time(),'components':sample['components']}
  try:
   answer=send(config,sample);report['cloudAccepted']=True
   for command in answer.get('commands',[]):executor.accept(command)
   for jid,status,result in executor.reports():
    send(config,{'hostId':'dvr','id':jid,'state':status,'result':result},'/api/action-result');executor.acknowledged(jid,status)
  except urllib.error.HTTPError as e:report.update(cloudAccepted=False,error='http_'+str(e.code))
  except Exception:report.update(cloudAccepted=False,error='cloud_unreachable_or_invalid_response')
  try:
   temp=folder/'status.tmp';temp.write_text(json.dumps(report,indent=2),encoding='utf-8');temp.replace(folder/'status.json')
  except OSError:pass
  time.sleep(10)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--once',action='store_true');a=p.parse_args();path=Path(a.config);cfg=json.loads(path.read_text(encoding='utf-8'));validate(cfg)
 if a.once:
  try:send(cfg,dict(collect(),agentVersion='0.7.0'));print('DVR heartbeat accepted. No commands executed.')
  except Exception:raise SystemExit('DVR heartbeat failed. Check cloud access and enrollment token; no secrets displayed.')
 else:run(cfg,path.parent)
