[CmdletBinding()]param()
$ErrorActionPreference='Stop'
$target='C:\ProgramData\RaceOperationsDvrAgent'
$name='Race Operations DVR Agent'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run Administrator PowerShell on the DVR PC.' }
$task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
$python=@($task.Actions)[0].Execute
foreach ($p in @($python,"$target\config.json",'C:\ProgramData\RaceDvrJudgeCues\config.json')) { if (-not (Test-Path -LiteralPath $p)) { throw "Required file missing: $p" } }
foreach ($file in @('dvr-agent.py','obs_monitor.py')) {
 & $python -m py_compile (Join-Path $PSScriptRoot $file)
 if ($LASTEXITCODE -ne 0) { throw "Validation failed: $file" }
}
$backup=Join-Path $target ('backups\before-v0.3.3-'+(Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item "$target\dvr-agent.py" $backup
if(Test-Path "$target\obs_monitor.py"){Copy-Item "$target\obs_monitor.py" $backup}
$stopped=$false
try {
 Stop-ScheduledTask -TaskName $name
 $stopped=$true
 $limit=(Get-Date).AddSeconds(20)
 do {Start-Sleep -Milliseconds 500;$task=Get-ScheduledTask -TaskName $name} while($task.State -eq 'Running' -and (Get-Date) -lt $limit)
 if($task.State -eq 'Running'){throw 'DVR agent did not stop.'}
 Copy-Item "$PSScriptRoot\dvr-agent.py","$PSScriptRoot\obs_monitor.py" $target -Force
 & $python "$target\dvr-agent.py" --config "$target\config.json" --once
 if($LASTEXITCODE -ne 0){throw 'Test heartbeat failed.'}
 Enable-ScheduledTask -TaskName $name | Out-Null
 Start-ScheduledTask -TaskName $name
 Write-Host 'DVR agent updated to 0.3.3. OBS GetRecordStatus monitoring enabled.'
 Write-Host 'No OBS or RaceDVR applications were changed or restarted. No recording commands were sent.'
 Write-Host "Backup: $backup"
} catch {
 if($stopped){
  Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
  Copy-Item "$backup\dvr-agent.py" $target -Force
  if(Test-Path "$backup\obs_monitor.py"){Copy-Item "$backup\obs_monitor.py" $target -Force}
  Disable-ScheduledTask -TaskName $name | Out-Null
  Write-Warning 'Previous files restored; DVR monitoring task left disabled to prevent repeated OBS reconnects. OBS and Judge Cues are unchanged.'
 }
 throw
}
