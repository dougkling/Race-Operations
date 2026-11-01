# Run in Administrator Windows PowerShell 5.1. No application services are modified.
[CmdletBinding()]param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run Administrator PowerShell.' }
if (-not $PythonPath) { $PythonPath = (Get-Command python.exe -ErrorAction Stop).Source }
& $PythonPath -c "import sys; assert sys.version_info >= (3,10)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ required; provide -PythonPath with its full path.' }
$target = 'C:\ProgramData\RaceOperations'
if (Test-Path $target) { throw 'Target exists. Installer will not overwrite an existing deployment.' }
foreach ($name in @('Race Operations Backend','Race Operations Cloud Agent')) { if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw "Task exists: $name" } }
if (Get-NetTCPConnection -State Listen -LocalPort 8799 -ErrorAction SilentlyContinue) { throw 'Port 8799 is occupied.' }
New-Item -ItemType Directory -Path $target | Out-Null
# Protect application/config directory before creating secrets or tasks.
& icacls.exe $target /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Failed to protect installation directory.' }
Copy-Item "$PSScriptRoot\server.py","$PSScriptRoot\agent.py","$PSScriptRoot\setup.py" $target
Copy-Item "$PSScriptRoot\web" $target -Recurse
& $PythonPath "$target\setup.py"
if ($LASTEXITCODE -ne 0) { throw 'Configuration generation failed.' }
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
foreach ($spec in @(@('Race Operations Backend','server.py','server.json'),@('Race Operations Cloud Agent','agent.py','cloud-agent.json'))) {
 $arguments = '"' + $target + '\' + $spec[1] + '" --config "' + $target + '\config\' + $spec[2] + '"'
 $action = New-ScheduledTaskAction -Execute $PythonPath -Argument $arguments -WorkingDirectory $target
 Register-ScheduledTask -TaskName $spec[0] -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
 Start-ScheduledTask -TaskName $spec[0]
}
Write-Host 'Installed. On the cloud PC open http://127.0.0.1:8799'
Write-Host 'Read the local admin token from C:\ProgramData\RaceOperations\config\administrator-token.txt'
Write-Host 'No inbound firewall rules were created. All application probes and controls remain disabled.'
