"""Observe the existing health-check task and bounded report; never execute it."""
import json,os,re,subprocess,time
from datetime import datetime
from pathlib import Path
REPORT=Path(r'C:\ProgramData\RaceDvrHealthMonitor\Logs\RaceDvr-Health-Latest.log')
PS=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
MAX_AGE=86400
CHECK_NAMES=('Judge Cues health endpoint','Graphics race source','Heat tracking arm state','S3 manifest','OBS WebSocket','Review Status integration','Uploader log freshness','DVR disk space','Race Review file','IIS Race Review HTTP','Uploader process','Uploader configuration','Recording layout metadata')
REASONS=('healthy','warnings','failed','running','disabled','stale','report_missing','report_invalid','report_mismatch','task_unknown','clock_warning')

def task_info():
 if os.name!='nt':return None
 command="$ErrorActionPreference='Stop'; $t=Get-ScheduledTask -TaskName 'Race DVR System Health Check' -TaskPath '\\'; $i=$t | Get-ScheduledTaskInfo; [pscustomobject]@{state=[string]$t.State;result=[long]$i.LastTaskResult;lastRun=([DateTimeOffset]$i.LastRunTime.ToUniversalTime()).ToUnixTimeSeconds()} | ConvertTo-Json -Compress"
 try:
  r=subprocess.run([PS,'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=5,check=False)
  data=json.loads(r.stdout) if r.returncode==0 else None
  if not isinstance(data,dict) or data.get('state') not in ('Ready','Running','Disabled','Queued'):return None
  if type(data.get('result')) is not int or not 0<=data['result']<=4294967295:return None
  if type(data.get('lastRun')) is not int:return None
  return data
 except (OSError,ValueError,subprocess.TimeoutExpired):return None

def parse_report(text):
 # Ignore appended uploader log and recovery commands; export only known check names.
 prefix=text.split('Latest uploader log:',1)[0]
 stamps=re.findall(r'^\s*(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d\d:\d\d)\s*$',prefix,re.M)
 summaries=re.findall(r'^RESULT: (REQUIRED SERVICES HEALTHY|ATTENTION REQUIRED) \((\d+) pass, (\d+) warning, (\d+) failure\)\s*$',prefix,re.M)
 if len(stamps)!=1 or len(summaries)!=1:raise ValueError('Invalid report')
 stamp=datetime.strptime(stamps[0],'%Y-%m-%d %H:%M:%S %z').timestamp()
 label,passes,warnings,failures=summaries[0];counts=list(map(int,(passes,warnings,failures)))
 if max(counts)>10000:raise ValueError('Invalid counts')
 names=[name for name in CHECK_NAMES if re.search(r'^'+re.escape(name)+r'\s+WARN\s',prefix,re.M)]
 return stamp,counts,label,names

def probe(report=REPORT,now=None,get_task=task_info):
 now=time.time() if now is None else now
 row={'id':'health-monitor','status':'unknown','healthReason':'task_unknown','taskState':'unknown','lastTaskResult':None,'lastRunEpoch':None,'reportAgeSeconds':None,'passes':None,'warnings':None,'failures':None,'warningChecks':[]}
 info=get_task()
 if info is None:return row
 row.update(taskState=info['state'],lastTaskResult=info['result'],lastRunEpoch=info['lastRun'])
 try:
  with Path(report).open('rb') as f:raw=f.read(524289)
  if len(raw)>524288:raise ValueError('Oversize report')
  stamp,counts,label,names=parse_report(raw.decode('utf-8-sig'))
  row.update(reportAgeSeconds=max(0,int(now-stamp)),passes=counts[0],warnings=counts[1],failures=counts[2],warningChecks=names)
  reason='clock_warning' if stamp>now+60 or info['lastRun']>now+60 else 'report_mismatch' if abs(stamp-info['lastRun'])>120 else 'stale' if now-stamp>MAX_AGE else 'failed' if label=='ATTENTION REQUIRED' else 'warnings' if counts[1] or counts[2] else 'healthy'
 except OSError:reason='report_missing'
 except (ValueError,UnicodeError):reason='report_invalid'
 if info['state'] in ('Running','Queued'):reason='running'
 elif info['state']=='Disabled':reason='disabled'
 elif info['result']!=0:reason='failed'
 row.update(healthReason=reason,status='green' if reason=='healthy' else 'red' if reason=='failed' else 'unknown' if reason in ('report_missing','report_invalid') else 'yellow')
 return row

_cache=None;_at=0
def monitor_sample():
 global _cache,_at
 if _cache is None or time.monotonic()-_at>=30:_cache=probe();_at=time.monotonic()
 row=dict(_cache)
 if row['reportAgeSeconds'] is not None:
  row['reportAgeSeconds']+=int(time.monotonic()-_at)
  if row['healthReason'] in ('healthy','warnings') and row['reportAgeSeconds']>MAX_AGE:row.update(status='yellow',healthReason='stale')
 return row
