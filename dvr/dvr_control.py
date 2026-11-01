"""Allowlisted local recovery with persistent deduplication and post-action verification."""
import json, os, re, sqlite3, subprocess, threading, time
from pathlib import Path
from dvr_actions import ACTIONS, guard
PS=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
SCRIPT=Path(__file__).with_name('Invoke-DVR-Recovery.ps1')


def inventory(runner=subprocess.run):
 if os.name!='nt':return {'obsProcessCount':None}
 command="[pscustomobject]@{obsProcessCount=@(Get-Process -Name obs64,obs32 -ErrorAction SilentlyContinue).Count} | ConvertTo-Json -Compress"
 try:
  r=runner([PS,'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=5)
  data=json.loads(r.stdout)
  return data if r.returncode==0 and type(data.get('obsProcessCount')) is int else {'obsProcessCount':None}
 except Exception:return {'obsProcessCount':None}


def perform(config, action, probe, link, runner=subprocess.run, sleep=time.sleep, clock=time.monotonic):
 if config.get('dvrControlsEnabled') is not True:return 'skipped','agent_controls_disabled'
 if action not in ACTIONS:return 'skipped','preflight_blocked'
 # Probe immediately before acting; use only locally registered capabilities.
 rows={c['id']:c for c in probe()['components']}
 allowed,reason=guard(action,rows,config.get('dvrCapabilities',[]),link())
 if not allowed:return 'skipped','already_healthy' if reason=='Target is green' else 'preflight_blocked'
 if os.name!='nt':return 'skipped','preflight_blocked'
 began=time.time()
 try:
  r=runner([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(SCRIPT),'-Action',action],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90,check=False)
  if r.returncode!=0:return 'failed','local_action_failed'
 except subprocess.TimeoutExpired:return 'indeterminate','execution_uncertain'
 except OSError:return 'failed','local_action_failed'
 target=ACTIONS[action][0];deadline=clock()+(660 if target=='uploader' else 120)
 while clock()<deadline:
  rows={c['id']:c for c in probe()['components']};row=rows.get(target,{})
  if target=='health-monitor':
   # A fresh completed report, even with warnings, is a successful refresh.
   if row.get('lastRunEpoch',0)>=int(began) and row.get('taskState')=='Ready' and row.get('reportAgeSeconds') is not None and row['reportAgeSeconds']<120:
    return ('succeeded','health_check_completed') if row.get('lastTaskResult')==0 else ('failed','health_check_failed')
  elif target=='connector':
   if link() is True:return 'succeeded','component_recovered'
  elif target=='uploader':
   if row.get('status')=='green' and type(row.get('lastEventAgeSeconds')) in (int,float) and row['lastEventAgeSeconds']<=time.time()-began:return 'succeeded','component_recovered'
  elif row.get('status')=='green':return 'succeeded','component_recovered'
  sleep(3)
 return 'failed','recovery_timeout'


class Executor:
 def __init__(self,config,journal,probe,link):
  self.config=config;self.probe=probe;self.link=link
  self.db=sqlite3.connect(journal,check_same_thread=False);self.lock=threading.Lock();self.busy=False
  self.db.execute('CREATE TABLE IF NOT EXISTS executions (id TEXT PRIMARY KEY,state TEXT,result TEXT,acked INTEGER NOT NULL DEFAULT 0)')
  self.db.execute("UPDATE executions SET state='indeterminate',result='execution_uncertain' WHERE state='running'");self.db.commit()
 def accept(self,command):
  if not isinstance(command,dict) or command.get('action') not in ACTIONS:return
  jid=command.get('id')
  if not isinstance(jid,str) or not re.fullmatch('[a-f0-9-]{36}',jid):return
  with self.lock:
   if self.busy or self.db.execute('SELECT 1 FROM executions WHERE id=?',(jid,)).fetchone():return
   # Commit before invoking the target: a crash must never replay a restart.
   self.db.execute('INSERT INTO executions VALUES (?,?,?,0)',(jid,'running','executing'));self.db.commit();self.busy=True
  threading.Thread(target=self.execute,args=(jid,command['action']),daemon=True).start()
 def execute(self,jid,action):
  try:state,result=perform(self.config,action,self.probe,self.link)
  except Exception:state,result='indeterminate','execution_uncertain'
  with self.lock:
   self.db.execute('UPDATE executions SET state=?,result=? WHERE id=?',(state,result,jid));self.db.commit();self.busy=False
 def reports(self):
  with self.lock:return list(self.db.execute('SELECT id,state,result FROM executions WHERE acked=0'))
 def acknowledged(self,jid,status):
  if status=='running':return
  with self.lock:
   self.db.execute('UPDATE executions SET acked=1 WHERE id=? AND state=?',(jid,status));self.db.commit()
