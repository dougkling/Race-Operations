#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param([string]$RollbackFrom)
$ErrorActionPreference = 'Stop'
$root = 'C:\ProgramData\RaceOperations'
$deploymentPath = 'C:\ProgramData\PitWall\deployment.json'
$manager = 'C:\Program Files\PitWall\manager\PitWall.ps1'
$d = Get-Content -LiteralPath $deploymentPath -Raw | ConvertFrom-Json
$python = Join-Path $d.current_release 'venv\Scripts\python.exe'
$names = @('Race Operations Backend','Race Operations Cloud Agent',$d.task_name)
$previous = @{}
foreach ($name in $names) { $previous[$name] = (Get-ScheduledTask -TaskName $name -TaskPath '\' -ErrorAction Stop).State }
foreach ($p in @($python,$manager,"$root\config\server.json","$root\config\cloud-agent.json","$root\config\administrator-token.txt")) {
 if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Required installed file missing: $p" }
}
function Run-Python([string[]]$Arguments) {
 & $python @Arguments
 if ($LASTEXITCODE -ne 0) { throw 'AI update check failed. Read the message immediately above.' }
}
function Stop-Management {
 foreach ($name in $names[0..1]) { Stop-ScheduledTask -TaskName $name -TaskPath '\' }
 $limit = (Get-Date).AddSeconds(20)
 do {
  $running = @($names[0..1] | ForEach-Object { Get-ScheduledTask -TaskName $_ -TaskPath '\' } | Where-Object State -eq 'Running')
  if ($running.Count -eq 0) { return }
  Start-Sleep -Milliseconds 500
 } while ((Get-Date) -lt $limit)
 throw 'Monitoring tasks did not stop; no forced termination attempted.'
}
function Stop-Apps {
 powershell.exe -NoProfile -ExecutionPolicy Bypass -File $manager stop
 if ($LASTEXITCODE -ne 0) { throw 'RaceBot manager could not stop its applications.' }
}
function Start-All {
 powershell.exe -NoProfile -ExecutionPolicy Bypass -File $manager start
 if ($LASTEXITCODE -ne 0) { throw 'RaceBot manager could not start its applications.' }
 foreach ($name in $names[0..1]) { Start-ScheduledTask -TaskName $name -TaskPath '\' }
}
function Restore-TaskStates {
 if ($previous[$d.task_name] -eq 'Running') {
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File $manager start
 }
 foreach ($name in $names[0..1]) { if ($previous[$name] -eq 'Running') { Start-ScheduledTask -TaskName $name -TaskPath '\' } }
}
if ($RollbackFrom) {
 $backup = (Resolve-Path -LiteralPath $RollbackFrom).Path
 $expected = [IO.Path]::GetFullPath((Join-Path $root 'backups')) + '\'
 if (-not $backup.StartsWith($expected,[StringComparison]::OrdinalIgnoreCase)) { throw 'Use the AI update backup folder printed during installation.' }
 $helper = Join-Path $backup 'ai_update.py'
 if (-not (Test-Path -LiteralPath $helper)) { throw 'AI rollback helper missing from backup.' }
 try { Stop-Management; Stop-Apps; Run-Python @($helper,'rollback','--folder',$backup); Restore-TaskStates }
 catch { Restore-TaskStates; throw }
 Write-Host 'AI monitoring update rolled back. Refresh the monitoring page.'
 return
}
$payloadText = '__PAYLOAD__'
if ($payloadText.StartsWith('__PAYLOAD')) { throw 'Use the generated Update-RaceBot-AI-Monitor.ps1 download; this file is its source template.' }
$backup = Join-Path $root ('backups\ai-monitor-' + (Get-Date -Format yyyyMMdd-HHmmss) + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
$null = New-Item -ItemType Directory -Path $backup
# Backups include private runtime configuration: restrict before writing anything.
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true,$false)
foreach ($sidText in @('S-1-5-18','S-1-5-32-544')) {
 $sid = New-Object Security.Principal.SecurityIdentifier($sidText)
 $rule = New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit, ObjectInherit','None','Allow')
 $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $backup -AclObject $acl
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = Join-Path $backup 'payload.zip'
[IO.File]::WriteAllBytes($zip,[Convert]::FromBase64String($payloadText))
$payload = Join-Path $backup 'payload'
[IO.Compression.ZipFile]::ExtractToDirectory($zip,$payload)
$helper = Join-Path $payload 'ai_update.py'
Copy-Item -LiteralPath $helper -Destination (Join-Path $backup 'ai_update.py')
Run-Python @($helper,'prepare','--payload',$payload,'--folder',$backup)
Write-Host "Validated before stopping services. Backup: $backup"
$stopping = $false
$applied = $false
try {
 $stopping = $true
 Stop-Management
 # Check pending actions after stopping dispatch; preserve all audit history.
 Run-Python @((Join-Path $payload 'check-pending.py'),(Join-Path $root 'config\actions.sqlite3'))
 Stop-Apps
 $applied = $true
 Run-Python @($helper,'apply','--folder',$backup)
 Start-All
 $ready = $false
 for ($i=0; $i -lt 45; $i++) {
  Start-Sleep -Seconds 2
  $checkOutput = & $python $helper verify --folder $backup
  if ($LASTEXITCODE -eq 0) { $checkOutput | ForEach-Object { Write-Host $_ }; $ready=$true; break }
 }
 if (-not $ready) { throw 'Updated monitoring did not pass its readiness check.' }
 Write-Host 'PASS RaceBot AI monitor and recovery v0.10.0 installed.' -ForegroundColor Green
 Write-Host 'Refresh Race Operations with Ctrl+F5. Sign in again.'
 Write-Host 'AI tests run every five minutes and use small API requests. Existing SES settings and per-monitor mutes are retained.'
 Write-Host 'AI reconnect is enabled only on failure. The shared restart also handles failed AI health.'
 Write-Host "Rollback: rerun this script with -RollbackFrom '$backup'"
} catch {
 $problem = $_
 if ($applied) {
  try { Stop-Management; Stop-Apps; Run-Python @($helper,'rollback','--folder',$backup) }
  catch { Write-Warning "Automatic rollback did not finish. Preserve backup: $backup"; throw }
 }
 if ($stopping) { Restore-TaskStates }
 throw $problem
}
