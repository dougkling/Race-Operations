"""Outbound-only, monitoring-only RaceDVR agent compatible with cloud v0.3.0."""
import argparse,json,time,urllib.request,urllib.error
from pathlib import Path
from obs_monitor import monitor_sample as obs_probe
from uploader_monitor import monitor_sample as uploader_probe
from urllib.parse import urlsplit
VERSION='0.4.2'
CHECKS=[('judge-cues','http://127.0.0.1:8766/health',True),('review-status','http://127.0.0.1:8765/health',False),('iis','http://127.0.0.1/index.asp',False)]
PENDING=['connector','disk-network','pilot-review','scoring','health-monitor']
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

def collect(open_url=None):
 open_url=open_url or opener().open;rows=[]
 for cid,url,require_ok in CHECKS:
  row={'id':cid,'status':'red'};start=time.monotonic()
  try:
   with open_url(url,timeout=3) as r:
    body=r.read(65536);row['status']='green' if r.status==200 else 'red'
    if require_ok and row['status']=='green':
     try:row['status']='green' if json.loads(body).get('ok') is True else 'yellow'
     except (ValueError,AttributeError):row['status']='yellow'
   row['latencyMs']=round((time.monotonic()-start)*1000)
  except (OSError,ValueError):pass
  rows.append(row)
 return {'hostId':'dvr','agentVersion':'0.3.0','components':rows+[obs_probe(),uploader_probe()]+[{'id':i,'status':'unknown'} for i in PENDING]}

def send(config,payload):
 req=urllib.request.Request(config['serverUrl'].rstrip('/')+'/api/heartbeat',data=json.dumps(payload).encode('utf-8'),headers={'Authorization':'Bearer '+config['token'],'Content-Type':'application/json'})
 with opener().open(req,timeout=10) as r:
  result=json.loads(r.read(65536))
  if result.get('ok') is not True:raise ValueError('Heartbeat not accepted')
 # Intentionally ignore commands: no command execution code exists in this agent.

def run(config,folder):
 validate(config)
 while True:
  sample=collect();report={'version':VERSION,'lastAttempt':time.time(),'components':sample['components']}
  try:send(config,sample);report['cloudAccepted']=True
  except urllib.error.HTTPError as e:report.update(cloudAccepted=False,error='http_'+str(e.code))
  except Exception:report.update(cloudAccepted=False,error='cloud_unreachable_or_invalid_response')
  try:
   temp=folder/'status.tmp';temp.write_text(json.dumps(report,indent=2),encoding='utf-8');temp.replace(folder/'status.json')
  except OSError:pass
  time.sleep(10)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--once',action='store_true');a=p.parse_args();path=Path(a.config);cfg=json.loads(path.read_text(encoding='utf-8'));validate(cfg)
 if a.once:
  try:send(cfg,collect());print('DVR heartbeat accepted. No commands executed.')
  except Exception:raise SystemExit('DVR heartbeat failed. Check cloud access and enrollment token; no secrets displayed.')
 else:run(cfg,path.parent)
