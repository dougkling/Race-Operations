[CmdletBinding()]param([string]$PythonPath,[Parameter(Mandatory=$true)][string]$ServerUrl,[switch]$AllowLegacyHttp)
$ErrorActionPreference = 'Stop'
$ServerUrl=$ServerUrl.TrimEnd('/')
$uri=$null
if(-not [Uri]::TryCreate($ServerUrl,[UriKind]::Absolute,[ref]$uri) -or -not $uri.Host -or $uri.UserInfo -or $uri.Query -or $uri.Fragment -or $uri.AbsolutePath -ne '/') { throw 'ServerUrl must be a server origin without credentials or a path.' }
$legacyHttp=$AllowLegacyHttp -and $ServerUrl -eq 'http://98.84.103.79'
if($uri.Scheme -ne 'https' -and -not $legacyHttp){throw 'HTTPS is required. Only the existing operator deployment permits -AllowLegacyHttp with its exact legacy address.'}
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
$health = Invoke-RestMethod ($ServerUrl+'/health') -TimeoutSec 10
if (-not $health.ok -or $health.version -notin @('0.3.0','0.3.2','0.4.0','0.4.1','0.5.0','0.6.0','0.7.0','0.8.0','0.9.0','0.10.0')) { throw 'Expected compatible cloud backend was not reachable.' }
if($legacyHttp){Write-Warning 'Legacy HTTP selected. The DVR bearer token travels unencrypted.'}
Write-Host 'Paste the DVR agent token, NOT the dashboard administrator token. It will not be displayed.'
$secure = Read-Host 'DVR agent token' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
if ($token.Length -lt 20) { throw 'Token is too short.' }
New-Item -ItemType Directory -Path $target | Out-Null
& icacls.exe $target /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Failed to protect installation folder. Agent not installed.' }
Copy-Item "$PSScriptRoot\dvr-agent.py","$PSScriptRoot\obs_monitor.py","$PSScriptRoot\uploader_monitor.py","$PSScriptRoot\disk_monitor.py","$PSScriptRoot\health_monitor.py","$PSScriptRoot\pilot_monitor.py","$PSScriptRoot\dvr_actions.py","$PSScriptRoot\dvr_control.py","$PSScriptRoot\obs_recovery_guard.py","$PSScriptRoot\Invoke-DVR-Recovery.ps1","$PSScriptRoot\Invoke-OBS-Recovery.ps1" $target
$config = @{hostId='dvr';serverUrl=$ServerUrl;allowHttp=[bool]$legacyHttp;token=$token}
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

Write-Host 'Run Update-DVR-Agent.ps1 after enrollment to discover and enable recovery controls.'
