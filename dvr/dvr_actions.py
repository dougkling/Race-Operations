"""Fixed DVR action catalog shared by backend and agent; no browser-supplied commands."""
ACTIONS = {
 'dvr-judge-cues-restart': ('judge-cues', 'Restart Judge Cues'),
 'dvr-review-status-restart': ('review-status', 'Restart Review Status'),
 'dvr-iis-restart': ('iis', 'Restart IIS Judge Review'),
 'dvr-uploader-restart': ('uploader', 'Restart S3 Uploader'),
 'dvr-connector-restart': ('connector', 'Restart Cloud Connector'),
 'dvr-obs-restart': ('obs', 'Restart OBS Studio'),
 'dvr-health-run': ('health-monitor', 'Run system health check'),
}
def guard(action, rows, capabilities, link=None):
 if action not in ACTIONS: return False, 'Unknown DVR action'
 target=ACTIONS[action][0]
 if action not in capabilities: return False, 'Local recovery target not verified; see DVR updater output'
 row=rows.get(target,{})
 if action=='dvr-health-run':
  if row.get('taskState') in ('Running','Queued'): return False, 'Health check already running'
  return True, 'Run the existing check and refresh its saved report'
 if target=='connector':
  if link is None: return False, 'Cloud proxy connection evidence unavailable'
  if link is True: return False, 'Target is green'
 else:
  if row.get('status')=='green': return False, 'Target is green'
  if row.get('status') not in ('red','yellow'): return False, 'Target health is unknown'
 if target in ('judge-cues','obs'):
  obs=rows.get('obs',{})
  # An absent OBS process cannot be recording. Unknown process evidence never counts as absent.
  stopped=type(obs.get('processCount')) is int and obs['processCount']==0
  if not stopped and (obs.get('recording') is not False or obs.get('obsConnected') is not True):
   return False, 'Recording active or unknown; recovery blocked'
  if rows.get('judge-cues',{}).get('recording') is True: return False, 'Judge Cues reports an active recording'
 return True, 'Only this component will restart; confirm no critical judging transaction is in progress'
