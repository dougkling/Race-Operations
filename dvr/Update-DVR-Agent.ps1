[CmdletBinding()]param()
$ErrorActionPreference='Stop'
$target='C:\ProgramData\RaceOperationsDvrAgent'
$name='Race Operations DVR Agent'
if(-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Run Administrator PowerShell on the DVR PC.'}
$task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
$python=@($task.Actions)[0].Execute
foreach($p in @($python,"$target\config.json",'C:\ProgramData\RaceDvrJudgeCues\config.json')){if(-not (Test-Path -LiteralPath $p)){throw "Required file missing: $p"}}
$files=@('dvr-agent.py','obs_monitor.py','uploader_monitor.py','disk_monitor.py','health_monitor.py','pilot_monitor.py','dvr_actions.py','dvr_control.py','obs_recovery_guard.py','Invoke-DVR-Recovery.ps1','Invoke-OBS-Recovery.ps1')
foreach($file in $files){
 $path=Join-Path $PSScriptRoot $file
 if($file.EndsWith('.py')){& $python -m py_compile $path;if($LASTEXITCODE -ne 0){throw "Validation failed: $file"}}
 else{$tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors);if($errors.Count){throw "PowerShell validation failed: $file"}}
}
# Do not replace an agent while its recovery worker is acting.
$journal=Join-Path $target 'dvr-actions.sqlite3'
if(Test-Path $journal){
 & $python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); sys.exit(1 if c.execute('SELECT 1 FROM executions WHERE acked=0').fetchone() else 0)" $journal
 if($LASTEXITCODE -ne 0){throw 'Resolve pending DVR actions in the dashboard before updating.'}
}
$cfg=Get-Content "$target\config.json" -Raw | ConvertFrom-Json
if($cfg.hostId -ne 'dvr'){throw 'DVR enrollment required'}
$caps=@()
$fixed=@{'dvr-judge-cues-restart'='Race DVR Judge Cues';'dvr-review-status-restart'='Race DVR Review Status';'dvr-uploader-restart'='Race DVR S3 Uploader';'dvr-health-run'='Race DVR System Health Check'}
foreach($action in $fixed.Keys){
 $found=Get-ScheduledTask -TaskName $fixed[$action] -TaskPath '\' -ErrorAction SilentlyContinue
 if($found -and $found.State -ne 'Disabled'){$caps+=$action}else{Write-Warning "$($fixed[$action]): missing or disabled; control unavailable"}
}
if(Get-Service -Name W3SVC -ErrorAction SilentlyContinue){$caps+='dvr-iis-restart'}
# Discover exactly one connector task with an existing connector.js action target.
$connectors=@(Get-ScheduledTask | Where-Object {
 $_.TaskName -match '(?i)Race.?DVR.*Connector' -and $_.State -ne 'Disabled' -and @($_.Actions).Count -eq 1
} | Where-Object {
 $a=@($_.Actions)[0];$m=[regex]::Match([string]$a.Arguments,'(?i)(?:"([^"]*connector\.js)"|(\S*connector\.js))')
 $scriptPath=if($m.Groups[1].Success){$m.Groups[1].Value}else{$m.Groups[2].Value}
 if($scriptPath -and -not [IO.Path]::IsPathRooted($scriptPath) -and $a.WorkingDirectory){$scriptPath=Join-Path $a.WorkingDirectory $scriptPath}
 $m.Success -and (Test-Path -LiteralPath $scriptPath -PathType Leaf)
})
if($connectors.Count -eq 1){
 $cfg | Add-Member -NotePropertyName connectorTaskName -NotePropertyValue $connectors[0].TaskName -Force
 $cfg | Add-Member -NotePropertyName connectorTaskPath -NotePropertyValue $connectors[0].TaskPath -Force
 $caps+='dvr-connector-restart'
}else{Write-Warning 'Connector task not uniquely verified. Connector restart remains disabled.'}
# Preserve the running OBS executable, arguments and owner; use no guessed user or install path.
$obs=@(Get-CimInstance Win32_Process -Filter "Name='obs64.exe' OR Name='obs32.exe'")
$obsReady=$false
if($obs.Count -eq 1 -and $obs[0].ExecutablePath -and (Test-Path -LiteralPath $obs[0].ExecutablePath)){
 $owner=Invoke-CimMethod -InputObject $obs[0] -MethodName GetOwner
 $line=[string]$obs[0].CommandLine
 $match=[regex]::Match($line,'^\s*(?:"[^"]+"|\S+)(.*)$')
 $arguments=$match.Groups[1].Value.Trim()
 if($owner.ReturnValue -eq 0 -and $owner.User -and $owner.User -ne 'SYSTEM' -and $match.Success){
  # Remove automatic capture flags rather than replaying them during recovery.
  $arguments=[regex]::Replace($arguments,'(?i)(?<!\S)--(?:startrecording|startstreaming|startreplaybuffer|multi)(?=\s|$)','').Trim()
  if($arguments -notmatch '(?i)--start(recording|streaming|replaybuffer)|--multi'){
   $cfg | Add-Member -NotePropertyName obsExecutable -NotePropertyValue ([string]$obs[0].ExecutablePath) -Force
   $cfg | Add-Member -NotePropertyName obsWorkingDirectory -NotePropertyValue (Split-Path $obs[0].ExecutablePath) -Force
   $cfg | Add-Member -NotePropertyName obsArguments -NotePropertyValue $arguments -Force
   $cfg | Add-Member -NotePropertyName obsUser -NotePropertyValue ($owner.Domain+'\'+$owner.User) -Force
   $obsReady=$true
  }
 }
}
# Preserve a previously verified setup if OBS is currently stopped.
if(-not $obsReady -and $obs.Count -eq 0 -and $cfg.obsExecutable -and $cfg.obsUser){
 $obsReady=(Test-Path -LiteralPath $cfg.obsExecutable) -and ($cfg.obsArguments -notmatch '(?i)--start(recording|streaming|replaybuffer)|--multi')
}
if($obsReady){$caps+='dvr-obs-restart'}else{Write-Warning 'OBS desktop launch not verified. Start OBS normally and rerun this updater to enable its control.'}
$cfg | Add-Member -NotePropertyName pythonPath -NotePropertyValue $python -Force
$cfg | Add-Member -NotePropertyName dvrControlsEnabled -NotePropertyValue $true -Force
$cfg | Add-Member -NotePropertyName dvrCapabilities -NotePropertyValue @($caps) -Force
$backup=Join-Path $target ('backups\before-v0.8.0-'+(Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach($file in ($files+@('config.json'))){if(Test-Path (Join-Path $target $file)){Copy-Item (Join-Path $target $file) $backup}}
$healthTask=Get-ScheduledTask -TaskName 'Race DVR System Health Check' -TaskPath '\' -ErrorAction SilentlyContinue
if($healthTask){Export-ScheduledTask -TaskName $healthTask.TaskName -TaskPath '\' | Set-Content (Join-Path $backup 'health-task.xml') -Encoding Unicode}
$oldObsTask=Get-ScheduledTask -TaskName 'Race Operations OBS Recovery' -TaskPath '\' -ErrorAction SilentlyContinue
if($oldObsTask){Export-ScheduledTask -TaskName $oldObsTask.TaskName -TaskPath '\' | Set-Content (Join-Path $backup 'obs-task.xml') -Encoding Unicode}
$stopped=$false
try{
 Stop-ScheduledTask -TaskName $name
 $stopped=$true
 $limit=(Get-Date).AddSeconds(20)
 do{Start-Sleep -Milliseconds 500;$task=Get-ScheduledTask -TaskName $name}while($task.State -eq 'Running' -and (Get-Date) -lt $limit)
 if($task.State -eq 'Running'){throw 'DVR agent did not stop'}
 foreach($file in $files){Copy-Item (Join-Path $PSScriptRoot $file) $target -Force}
 [IO.File]::WriteAllText("$target\config.json",($cfg | ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
 if($obsReady){
  $action=New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$target\Invoke-OBS-Recovery.ps1`"" -WorkingDirectory $target
  $principal=New-ScheduledTaskPrincipal -UserId $cfg.obsUser -LogonType Interactive -RunLevel Highest
  $settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName 'Race Operations OBS Recovery' -TaskPath '\' -Action $action -Principal $principal -Settings $settings -Force | Out-Null
 }
 if($healthTask){
  $boot=@($healthTask.Triggers | Where-Object {$_.CimClass.CimClassName -eq 'MSFT_TaskBootTrigger'})
  $repeat=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
  Set-ScheduledTask -TaskName $healthTask.TaskName -TaskPath '\' -Trigger ($boot+@($repeat)) | Out-Null
 }
 & $python "$target\dvr-agent.py" --config "$target\config.json" --once
 if($LASTEXITCODE -ne 0){throw 'Test heartbeat failed'}
 Enable-ScheduledTask -TaskName $name | Out-Null
 Start-ScheduledTask -TaskName $name
 Write-Host 'DVR agent updated to 0.8.0. Verified recovery controls:'
 $caps | Sort-Object | ForEach-Object {Write-Host "  $_"}
 Write-Host 'No DVR applications restarted during installation. Health check repeats every five minutes.'
 Write-Host "Backup: $backup"
}catch{
 $problem=$_
 if($stopped){
  Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
  foreach($file in ($files+@('config.json'))){
   if(Test-Path (Join-Path $backup $file)){Copy-Item (Join-Path $backup $file) $target -Force}
   else{Remove-Item (Join-Path $target $file) -ErrorAction SilentlyContinue}
  }
  if(Test-Path (Join-Path $backup 'health-task.xml')){Register-ScheduledTask -TaskName 'Race DVR System Health Check' -TaskPath '\' -Xml (Get-Content (Join-Path $backup 'health-task.xml') -Raw) -Force | Out-Null}
  if(Test-Path (Join-Path $backup 'obs-task.xml')){Register-ScheduledTask -TaskName 'Race Operations OBS Recovery' -TaskPath '\' -Xml (Get-Content (Join-Path $backup 'obs-task.xml') -Raw) -Force | Out-Null}
  elseif($obsReady){Unregister-ScheduledTask -TaskName 'Race Operations OBS Recovery' -TaskPath '\' -Confirm:$false -ErrorAction SilentlyContinue}
  Start-ScheduledTask -TaskName $name
  Write-Warning 'Previous agent and configuration restored. Verify dashboard connection.'
 }
 throw $problem
}
