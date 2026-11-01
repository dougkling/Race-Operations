[CmdletBinding()]
param([Parameter(Mandatory)][ValidateSet('dvr-judge-cues-restart','dvr-review-status-restart','dvr-iis-restart','dvr-uploader-restart','dvr-connector-restart','dvr-obs-restart','dvr-health-run')][string]$Action)
$ErrorActionPreference='Stop'
$cfg=Get-Content (Join-Path $PSScriptRoot 'config.json') -Raw | ConvertFrom-Json
if(-not $cfg.dvrControlsEnabled -or $Action -notin $cfg.dvrCapabilities){throw 'Local control disabled'}
if($Action -eq 'dvr-judge-cues-restart'){
 & $cfg.pythonPath (Join-Path $PSScriptRoot 'obs_recovery_guard.py')
 if($LASTEXITCODE -ne 0){throw 'Recording or streaming active or unknown'}
}
if($Action -eq 'dvr-iis-restart'){
 $svc=Get-Service -Name W3SVC
 if($svc.Status -eq 'Running'){Restart-Service -Name W3SVC -ErrorAction Stop}else{Start-Service -Name W3SVC -ErrorAction Stop}
 exit 0
}
if($Action -eq 'dvr-obs-restart'){
 # Interactive recovery task handles graceful shutdown and desktop launch. Never launch OBS as SYSTEM.
 $task=Get-ScheduledTask -TaskName 'Race Operations OBS Recovery' -TaskPath '\'
 if($task.State -eq 'Running'){throw 'OBS recovery already running'}
 $old=($task | Get-ScheduledTaskInfo).LastRunTime
 Start-ScheduledTask -InputObject $task
 $deadline=(Get-Date).AddSeconds(60)
 do{
  Start-Sleep -Milliseconds 500
  $task=Get-ScheduledTask -TaskName 'Race Operations OBS Recovery' -TaskPath '\'
  $info=$task | Get-ScheduledTaskInfo
  if($info.LastRunTime -gt $old -and $task.State -ne 'Running'){
   if($info.LastTaskResult -ne 0){throw 'Interactive OBS recovery failed'}
   exit 0
  }
 }while((Get-Date) -lt $deadline)
 throw 'Interactive OBS recovery did not finish; verify logged-in desktop'
}
$names=@{
 'dvr-judge-cues-restart'='Race DVR Judge Cues'
 'dvr-review-status-restart'='Race DVR Review Status'
 'dvr-uploader-restart'='Race DVR S3 Uploader'
 'dvr-health-run'='Race DVR System Health Check'
}
$taskPath='\'
if($Action -eq 'dvr-connector-restart'){
 $name=$cfg.connectorTaskName;$taskPath=$cfg.connectorTaskPath
 if(-not $name -or -not $taskPath){throw 'Connector task not verified'}
}else{$name=$names[$Action]}
$task=Get-ScheduledTask -TaskName $name -TaskPath $taskPath -ErrorAction Stop
if($task.State -eq 'Disabled'){throw 'Task is disabled; enable it locally before recovery'}
if($Action -eq 'dvr-health-run'){
 if($task.State -in @('Running','Queued')){throw 'Health check already running'}
 Start-ScheduledTask -InputObject $task
 exit 0
}
Stop-ScheduledTask -InputObject $task
$deadline=(Get-Date).AddSeconds(20)
do{
 Start-Sleep -Milliseconds 500
 $task=Get-ScheduledTask -TaskName $name -TaskPath $taskPath
}while($task.State -eq 'Running' -and (Get-Date) -lt $deadline)
if($task.State -eq 'Running'){throw 'Task did not stop; no processes will be force-killed'}
Start-ScheduledTask -InputObject $task
