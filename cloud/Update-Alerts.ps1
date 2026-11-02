[CmdletBinding()]param()
$ErrorActionPreference='Stop'
if(-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Run Administrator PowerShell on the cloud PC.'}
$root='C:\ProgramData\RaceOperations'
$task=Get-ScheduledTask -TaskName 'Race Operations Backend' -TaskPath '\'
$python=@($task.Actions)[0].Execute
$health=Invoke-RestMethod 'http://127.0.0.1:8799/health' -TimeoutSec 5
if(-not $health.ok -or $health.version -notin @('0.8.0','0.9.0','0.10.0')){throw 'Cloud backend v0.8.0 or v0.9.0 required.'}
$files=@('server.py','email_alerts.py','ai_monitor.py','dvr_actions.py','web\index.html','web\app.js','Configure-SES.ps1')
foreach($name in @('server.py','email_alerts.py','ai_monitor.py','dvr_actions.py')){
 & $python -m py_compile (Join-Path $PSScriptRoot $name)
 if($LASTEXITCODE -ne 0){throw "Source validation failed: $name"}
}
$db=Join-Path $root 'config\actions.sqlite3'
$backup=Join-Path $root ('backups\before-alerts-v0.9.0-'+(Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path "$backup\web" -Force | Out-Null
foreach($name in $files){$p=Join-Path $root $name;if(Test-Path $p){Copy-Item $p (Join-Path $backup $name)}}
$stopped=$false
try{
 Stop-ScheduledTask -TaskName 'Race Operations Backend' -TaskPath '\'
 $stopped=$true;$limit=(Get-Date).AddSeconds(20)
 do{Start-Sleep -Milliseconds 500;$task=Get-ScheduledTask -TaskName 'Race Operations Backend' -TaskPath '\'}while($task.State -eq 'Running' -and (Get-Date) -lt $limit)
 if($task.State -eq 'Running'){throw 'Backend did not stop. No process will be force-killed.'}
 if(Test-Path $db){
  & $python (Join-Path $PSScriptRoot 'check-pending.py') $db
  if($LASTEXITCODE -ne 0){throw 'Resolve pending recovery actions before updating.'}
  Copy-Item $db (Join-Path $backup 'actions.sqlite3')
 }
 foreach($name in $files){Copy-Item (Join-Path $PSScriptRoot $name) (Join-Path $root $name) -Force}
 Start-ScheduledTask -TaskName 'Race Operations Backend' -TaskPath '\'
 $ok=$false
 for($i=0;$i -lt 20;$i++){Start-Sleep -Seconds 1;try{$h=Invoke-RestMethod 'http://127.0.0.1:8799/health' -TimeoutSec 2;if($h.ok -and $h.version -eq '0.10.0'){$ok=$true;break}}catch{}}
 if(-not $ok){throw 'Updated backend did not pass its startup check.'}
 Write-Host 'v0.10.0 installed. Mute toggles are active. Configure SES to enable email sending.'
 Write-Host 'Only the dashboard backend restarted. No RaceBot, Commentator, OBS or DVR application restarted.'
 Write-Host 'Refresh with Ctrl+F5 and sign in again.'
 Write-Host "Backup: $backup"
}catch{
 $problem=$_
 if($stopped){
  Stop-ScheduledTask -TaskName 'Race Operations Backend' -TaskPath '\' -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
  foreach($name in $files){$p=Join-Path $backup $name;if(Test-Path $p){Copy-Item $p (Join-Path $root $name) -Force}else{Remove-Item (Join-Path $root $name) -ErrorAction SilentlyContinue}}
  # Added SQLite tables are backwards compatible; retain any audit/alert evidence.
  Start-ScheduledTask -TaskName 'Race Operations Backend' -TaskPath '\'
  Write-Warning 'Previous backend and dashboard files restored.'
 }
 throw $problem
}
