[CmdletBinding()]param()
$ErrorActionPreference='Stop'
$cfg=Get-Content (Join-Path $PSScriptRoot 'config.json') -Raw | ConvertFrom-Json
if(-not $cfg.dvrControlsEnabled -or 'dvr-obs-restart' -notin $cfg.dvrCapabilities){throw 'OBS control not configured'}
if(-not (Test-Path -LiteralPath $cfg.obsExecutable)){throw 'OBS executable missing'}
# A second local, authenticated recording check runs inside the interactive session.
& $cfg.pythonPath (Join-Path $PSScriptRoot 'obs_recovery_guard.py')
if($LASTEXITCODE -ne 0){throw 'Recording active or unknown'}
$processes=@(Get-Process -Name obs64,obs32 -ErrorAction SilentlyContinue)
if($processes.Count -gt 1){throw 'Multiple OBS processes; refusing ambiguous recovery'}
foreach($process in $processes){
 if($process.Path -ne $cfg.obsExecutable){throw 'OBS executable differs from verified launch target'}
 if(-not $process.CloseMainWindow()){throw 'OBS did not accept graceful close'}
 if(-not $process.WaitForExit(20000)){throw 'OBS did not exit; no forced termination attempted'}
}
$argsText=[string]$cfg.obsArguments
# Do not replay arguments that automatically start a recording, replay buffer or stream.
if($argsText -match '(?i)--start(recording|streaming|replaybuffer)|--multi'){throw 'Unsafe OBS launch arguments'}
$start=@{FilePath=$cfg.obsExecutable;WorkingDirectory=$cfg.obsWorkingDirectory;ErrorAction='Stop'}
if($argsText){$start.ArgumentList=$argsText}
Start-Process @start | Out-Null
