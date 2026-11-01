[CmdletBinding()]param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run Administrator PowerShell on the OBS/DVR PC.' }
if (-not (Test-Path 'C:\DVR')) { throw 'C:\DVR is missing. This installer is for the OBS/DVR PC, not the cloud host.' }
Get-ScheduledTask -TaskName 'Race DVR Judge Cues' -ErrorAction Stop | Out-Null
$target = 'C:\ProgramData\RaceOperationsDvrAgent'
$taskName = 'Race Operations DVR Agent'
if ((Test-Path $target) -or (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)) { throw 'Existing DVR agent installation found. No files overwritten.' }
if (-not $PythonPath) {
 $candidates = @('C:\Python314\python.exe','C:\Python313\python.exe','C:\Python312\python.exe')
 $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
 if ($cmd -and $cmd.Source -notmatch 'WindowsApps') { $candidates += $cmd.Source }
 $PythonPath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $PythonPath -or -not (Test-Path -LiteralPath $PythonPath)) { throw 'Machine-wide Python 3.10+ required. Run again with -PythonPath pointing to its full executable path.' }
& $PythonPath -c 'import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
& $PythonPath -m py_compile "$PSScriptRoot\dvr-agent.py"
if ($LASTEXITCODE -ne 0) { throw 'Agent syntax check failed.' }
# Only public health fields; no enrollment token is sent in this preflight.
$health = Invoke-RestMethod 'http://98.84.103.79/health' -TimeoutSec 10
if (-not $health.ok -or $health.version -notin @('0.3.0','0.3.2','0.4.0','0.4.1')) { throw 'Expected compatible cloud backend was not reachable.' }
Write-Host 'This agent uses your current HTTP cloud endpoint. The DVR bearer token travels unencrypted.'
Write-Host 'Paste the DVR agent token, NOT the dashboard administrator token. It will not be displayed.'
$secure = Read-Host 'DVR agent token' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
if ($token.Length -lt 20) { throw 'Token is too short.' }
New-Item -ItemType Directory -Path $target | Out-Null
& icacls.exe $target /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Failed to protect installation folder. Agent not installed.' }
Copy-Item "$PSScriptRoot\dvr-agent.py","$PSScriptRoot\obs_monitor.py","$PSScriptRoot\uploader_monitor.py" $target
$config = @{hostId='dvr';serverUrl='http://98.84.103.79';allowHttp=$true;token=$token}
[System.IO.File]::WriteAllText("$target\config.json",($config | ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
$token=$null; $config=$null; $secure=$null
# Validate actual enrollment and local probes before creating a startup task.
& $PythonPath "$target\dvr-agent.py" --config "$target\config.json" --once
if ($LASTEXITCODE -ne 0) { throw "Enrollment failed; no task created. Protected files retained at $target. Do not paste config contents into chat." }
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument ('"' + $target + '\dvr-agent.py" --config "' + $target + '\config.json"') -WorkingDirectory $target
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $taskName -Action $action -Settings $settings -Principal $principal -Trigger (New-ScheduledTaskTrigger -AtStartup) | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host 'Installed. DVR agent starts at boot without login. Check cloud dashboard in about 15 seconds.'
Write-Host 'Judge Cues, Review Status and IIS HTTP checks plus OBS and uploader read-only monitoring are enabled. No application was changed or restarted.'
Write-Host "Sanitized agent status: $target\status.json"
