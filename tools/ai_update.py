"""Transactional update planner: no service control, no provider calls, no secrets printed."""
import argparse
import ast
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import urllib.request


def digest(data):return hashlib.sha256(data).hexdigest()
def normalized(data):return data.decode('utf-8-sig').replace('\r\n','\n')
def text_digest(data):return digest(normalized(data).encode())

def patch_app(text, changes):
    for index,change in enumerate(changes,1):
        before,after=change['before'],change['after']
        old_count,new_count=text.count(before),text.count(after)
        if new_count==1 and old_count<=1:
            continue
        if old_count==1 and new_count==0:
            text=text.replace(before,after,1)
        else:
            raise ValueError('Installed RaceBot differs at AI insertion point '+str(index)+'. No live files changed.')
    ast.parse(text)
    return text


def prepare(payload, target, deployment, folder):
    payload,target,folder=Path(payload),Path(target),Path(folder)
    d=json.loads(Path(deployment).read_text(encoding='utf-8-sig'))
    release=Path(d['current_release']);data=Path(d['data_dir'])
    app=release/'app/app.py'
    manifest=json.loads((payload/'manifest.json').read_text())
    for name,expected in manifest['payload'].items():
        if digest((payload/name).read_bytes())!=expected:raise ValueError('Payload checksum mismatch')
    updates={}
    changes=json.loads((payload/'app-patch.json').read_text())
    updates[app]=patch_app(normalized(app.read_bytes()),changes).encode()
    ai=release/'app/ai_health.py'
    new=(payload/'racebot/ai_health.py').read_bytes()
    if ai.exists() and text_digest(ai.read_bytes())!=text_digest(new):raise ValueError('AI module has local changes')
    updates[ai]=new
    for name,baseline in manifest['operations'].items():
        path=target/name;new=(payload/'operations'/name).read_bytes()
        if path.exists():
            if text_digest(path.read_bytes()) not in (baseline,text_digest(new)):
                raise ValueError('Installed monitoring file differs from supported baseline: '+name)
        elif baseline is not None:
            raise ValueError('Required monitoring file missing: '+name)
        updates[path]=new
    server_path=target/'config/server.json';agent_path=target/'config/cloud-agent.json'
    server=json.loads(server_path.read_text(encoding='utf-8-sig'))
    agent=json.loads(agent_path.read_text(encoding='utf-8-sig'))
    if agent.get('hostId')!='cloud':raise ValueError('Cloud agent required')
    clouds=[h for h in server['hosts'] if h.get('id')=='cloud']
    if len(clouds)!=1:raise ValueError('Exactly one cloud host required')
    for config in (clouds[0],agent):
        entries=[c for c in config['components'] if c.get('id')=='racebot-ai']
        if len(entries)>1:raise ValueError('Duplicate AI monitor configuration')
        if not entries:
            config['components'].append({'id':'racebot-ai','enabled':True,'probe':'ai'})
        else:entries[0].update(enabled=True,probe='ai')
    for config in (server,agent):
        config['aiReconnectEnabled']=True
        config['pitwallRestartEnabled']=True
    token_path=data/'ai-monitor-token'
    if token_path.exists():
        token=token_path.read_text().strip()
        if not re.fullmatch(r'[a-f0-9]{64}',token):raise ValueError('Existing monitor token is invalid')
    else:token=secrets.token_hex(32)
    agent['aiMonitorTokenFile']=str(token_path)
    updates[token_path]=(token+'\n').encode()
    updates[server_path]=(json.dumps(server,indent=2)+'\n').encode()
    updates[agent_path]=(json.dumps(agent,indent=2)+'\n').encode()
    folder.mkdir(parents=True,exist_ok=True)
    plan=[]
    for i,(path,body) in enumerate(updates.items()):
        if path.suffix=='.py':ast.parse(body.decode('utf-8-sig'))
        existed=path.exists();old=path.read_bytes() if existed else None
        staged=folder/('staged-'+str(i));staged.write_bytes(body)
        backup=folder/('before-'+str(i))
        if existed:backup.write_bytes(old)
        plan.append({'target':str(path),'staged':str(staged),'backup':str(backup),
                     'before':digest(old) if existed else None,'after':digest(body)})
    (folder/'plan.json').write_text(json.dumps(plan,indent=2))
    print('Validated AI update; '+str(len(plan))+' files. Existing credentials and model settings retained.')


def apply(folder):
    plan=json.loads((Path(folder)/'plan.json').read_text())
    # Recheck every preimage before the first mutation.
    for item in plan:
        p=Path(item['target'])
        actual=digest(p.read_bytes()) if p.exists() else None
        if actual!=item['before']:raise ValueError('An installed file changed after validation; no files changed')
        if digest(Path(item['staged']).read_bytes())!=item['after']:raise ValueError('Staging checksum mismatch')
    for item in plan:
        p=Path(item['target']);temp=p.with_name(p.name+'.ai-update.tmp')
        temp.write_bytes(Path(item['staged']).read_bytes());os.replace(temp,p)
        if digest(p.read_bytes())!=item['after']:raise ValueError('Installed checksum mismatch')
    print('Installed AI monitoring and recovery files.')


def rollback(folder):
    plan=json.loads((Path(folder)/'plan.json').read_text())
    # Do not clobber concurrent edits or subsequent updates.
    for item in plan:
        p=Path(item['target']);current=digest(p.read_bytes()) if p.exists() else None
        if current not in (item['before'],item['after']):raise ValueError('Rollback stopped: installed file changed after update')
    for item in reversed(plan):
        p=Path(item['target'])
        if item['before'] is None:p.unlink(missing_ok=True)
        else:
            body=Path(item['backup']).read_bytes()
            if digest(body)!=item['before']:raise ValueError('Backup checksum mismatch')
            temp=p.with_name(p.name+'.ai-rollback.tmp');temp.write_bytes(body);os.replace(temp,p)
    print('Previous application and monitoring files restored; audit databases retained.')


def verify(target,deployment):
    target=Path(target);d=json.loads(Path(deployment).read_text(encoding='utf-8-sig'))
    token=(Path(d['data_dir'])/'ai-monitor-token').read_text().strip()
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def get(url,data=None,headers=None):
        q=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,headers=headers or {})
        with opener.open(q,timeout=4) as r:return json.load(r)
    ai=get('http://127.0.0.1:8765/api/ops/ai-health',headers={'Authorization':'Bearer '+token})
    if ai.get('schema')!=1:raise ValueError('AI endpoint schema did not verify')
    admin=(target/'config/administrator-token.txt').read_text().strip()
    get('http://127.0.0.1:8799/api/login',{'token':admin})
    state=get('http://127.0.0.1:8799/api/status')
    if state.get('version')!='0.10.0':raise ValueError('Updated backend not running')
    cloud=next(h for h in state['hosts'] if h['id']=='cloud')
    if not cloud['connected'] or cloud.get('sample',{}).get('agentVersion')!='0.10.0':raise ValueError('Updated cloud agent heartbeat not received')
    row=next(c for c in cloud['sample']['components'] if c['id']=='racebot-ai')
    if row.get('aiReason')=='monitor_unavailable':raise ValueError('AI monitor is not communicating')
    print('PASS AI endpoint, authenticated monitoring heartbeat and recovery integration. AI state: '+row['status'])
    print('Email alert configuration: '+state.get('alerts',{}).get('mode','unknown'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','apply','rollback','verify'))
    parser.add_argument('--payload');parser.add_argument('--target',default=r'C:\ProgramData\RaceOperations')
    parser.add_argument('--deployment',default=r'C:\ProgramData\PitWall\deployment.json');parser.add_argument('--folder',required=True)
    args=parser.parse_args()
    try:
        if args.action=='prepare':prepare(args.payload,args.target,args.deployment,args.folder)
        elif args.action=='verify':verify(args.target,args.deployment)
        else:globals()[args.action](args.folder)
    except Exception as error:
        # No config values, token paths or provider response bodies in output.
        print('UPDATE FAILED: '+(str(error) if isinstance(error,ValueError) else type(error).__name__))
        raise SystemExit(1)
