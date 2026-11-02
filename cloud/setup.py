"""Generate private configuration once. Never overwrites existing settings."""
import hashlib,json,secrets
from pathlib import Path
root=Path(__file__).parent; folder=root/'config';folder.mkdir(exist_ok=True)
if any(folder.iterdir()): raise SystemExit('Existing config found; no changes made.')
admin=secrets.token_urlsafe(32)
profiles={'cloud':[('racebot',8765),('racebot-ai',None),('commentator',8766),('cloud-proxy',None),('disk-space',None)],'dvr':[('judge-cues',8766),('review-status',8765),('iis',80),('obs',None),('uploader',None),('connector',None),('disk-network',None),('pilot-review',None),('scoring',None),('health-monitor',None)]}
hosts=[]
for host,entries in profiles.items():
 token=secrets.token_urlsafe(32); components=[]
 for name,port in entries:
  c={'id':name,'enabled':False,'probe':'http' if port else 'pending'}
  if port:c['url']=f'http://127.0.0.1:{port}'+('/health' if host=='dvr' and port!=80 else '/index.asp' if port==80 else '/')
  if host=='dvr' and port in (8765,8766):c['requireOk']=True
  components.append(c)
 hosts.append({'id':host,'name':'Cloud Windows PC' if host=='cloud' else 'OBS / DVR PC','token':token,'components':components})
 (folder/(host+'-agent.json')).write_text(json.dumps({'hostId':host,'serverUrl':'http://127.0.0.1:8799' if host=='cloud' else 'https://REPLACE-WITH-VERIFIED-CLOUD-HOSTNAME','token':token,'components':components},indent=2))
(folder/'server.json').write_text(json.dumps({'port':8799,'adminTokenHash':hashlib.sha256(admin.encode()).hexdigest(),'hosts':hosts},indent=2))
(folder/'administrator-token.txt').write_text(admin+'\n')
print('Configuration generated. Administrator token is in config/administrator-token.txt. Do not share config files.')
