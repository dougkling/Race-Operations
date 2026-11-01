"""Read-only scheduled-task and bounded uploader-log evidence. No AWS credentials read."""
import os,re,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
TASK='Race DVR S3 Uploader'
LOGS=Path(r'C:\ProgramData\RaceDvrS3Uploader\Logs')
POWERSHELL=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
STAMP=re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)Z\s')
HEARTBEAT=re.compile(r'Heartbeat: worker healthy; scanned (\d+) video file\(s\)\.')
EVENTS=[('uploading','Uploading '),('upload_complete','Upload complete:'),('archive_verified','Archived S3 object verified:'),('manifest_published','Published manifest with '),('error','[ERROR]'),('started','Race DVR S3 Uploader v')]

def task_state(runner=subprocess.run):
 if os.name!='nt':return 'unknown'
 try:
  result=runner([POWERSHELL,'-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; [string](Get-ScheduledTask -TaskName 'Race DVR S3 Uploader' -TaskPath '\\').State"],capture_output=True,text=True,timeout=5,check=False)
  value=result.stdout.strip()
  return value if result.returncode==0 and value in ('Running','Ready','Disabled','Queued') else 'unknown'
 except Exception:return 'unknown'

def parse_log(text,now,timestamp_basis='utc'):
 if timestamp_basis not in ('utc','local'):raise ValueError('Unsupported timestamp basis')
 heartbeat=None;last=None;scanned=None;operation='unknown';error=False;future=False
 for line in text.splitlines():
  match=STAMP.match(line)
  if not match:continue
  try:
   wall=datetime.strptime(match[1],'%Y-%m-%d %H:%M:%S')
   # Verified uploader writes machine-local wall time with a literal Z suffix.
   # Use the OS date-specific timezone rules, not today's offset or a fixed four hours.
   # During the repeated fall-back hour, prefer the older possible time.
   stamp=min(wall.replace(fold=0).timestamp(),wall.replace(fold=1).timestamp()) if timestamp_basis=='local' else wall.replace(tzinfo=timezone.utc).timestamp()
  except ValueError:continue
  if stamp>now+60:future=True;continue
  hb=HEARTBEAT.search(line)
  if hb:
   heartbeat=stamp;scanned=min(int(hb[1]),2147483647);last=stamp;operation='idle';error=False;continue
  for kind,marker in EVENTS:
   if marker in line:
    last=stamp;operation=kind;error=kind=='error';break
 return {'heartbeatAgeSeconds':max(0,round(now-heartbeat)) if heartbeat is not None else None,'lastEventAgeSeconds':max(0,round(now-last)) if last is not None else None,'filesScanned':scanned,'operation':operation,'clockWarning':future,'recentError':error}

def probe(logs=LOGS,now=None,get_task=task_state,warning=900,timestamp_basis='local'):
 now=time.time() if now is None else now
 row={'id':'uploader','status':'unknown','taskState':get_task(),'heartbeatAgeSeconds':None,'lastEventAgeSeconds':None,'filesScanned':None,'operation':'unknown','heartbeatWarningSeconds':warning,'uploaderReason':'task_unknown'}
 try:
  files=[p for p in Path(logs).glob('uploader-*.log') if p.is_file()]
  if not files:raise OSError()
  latest=max(files,key=lambda p:p.stat().st_mtime)
  with latest.open('rb') as f:
   f.seek(0,2);size=f.tell();offset=max(0,size-131072);f.seek(offset);raw=f.read(131072)
  if offset and b'\n' in raw:raw=raw.split(b'\n',1)[1]
  info=parse_log(raw.decode('utf-8-sig',errors='replace'),now,timestamp_basis)
  row.update({k:info[k] for k in ('heartbeatAgeSeconds','lastEventAgeSeconds','filesScanned','operation')})
  reason='clock_warning' if info['clockWarning'] else 'recent_error' if info['recentError'] else 'heartbeat_missing' if info['heartbeatAgeSeconds'] is None else 'heartbeat_stale' if info['heartbeatAgeSeconds']>warning else 'healthy'
 except OSError:reason='log_unavailable'
 if row['taskState']=='unknown':return row
 if row['taskState']!='Running':row.update(status='red',uploaderReason='task_not_running');return row
 row.update(status='green' if reason=='healthy' else 'yellow',uploaderReason=reason);return row

_cache=None;_at=0
def monitor_sample():
 global _cache,_at
 if _cache is None or time.monotonic()-_at>=30:
  _cache=probe();_at=time.monotonic()
 # Advance displayed ages between local task/log refreshes.
 row=dict(_cache);elapsed=int(time.monotonic()-_at)
 for k in ('heartbeatAgeSeconds','lastEventAgeSeconds'):
  if row[k] is not None:row[k]+=elapsed
 if row['status']=='green' and row['heartbeatAgeSeconds']>row['heartbeatWarningSeconds']:row.update(status='yellow',uploaderReason='heartbeat_stale')
 return row
