[CmdletBinding()]param()
$ErrorActionPreference = 'Stop'
$target = 'C:\ProgramData\RaceOperations'
$python = 'C:\Program Files\PitWall\runtime\Python-3.13.16\python.exe'
$manager = 'C:\Program Files\PitWall\manager\PitWall.ps1'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run Administrator PowerShell.' }
foreach ($p in @($python,$manager,"$target\config\server.json","$target\config\cloud-agent.json")) { if (-not (Test-Path -LiteralPath $p)) { throw "Required file missing: $p" } }
foreach ($name in @('Race Operations Backend','Race Operations Cloud Agent')) { Get-ScheduledTask -TaskName $name -ErrorAction Stop | Out-Null }
Get-ScheduledTask -TaskName 'Race DVR Judge Proxy' -TaskPath '\' -ErrorAction Stop | Out-Null
# Parse existing manager without executing it. Require its documented restart command.
$pt = $null; $pe = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($manager,[ref]$pt,[ref]$pe)
if ($pe.Count -gt 0 -or $ast.ParamBlock.Extent.Text -notmatch "'restart'") { throw 'Manager restart parameter could not be verified.' }
foreach ($f in @('server.py','agent.py','disk_monitor.py','dvr_actions.py')) {
 & $python -m py_compile (Join-Path $PSScriptRoot $f)
 if ($LASTEXITCODE -ne 0) { throw "Python validation failed: $f" }
}
$serverConfig = Get-Content "$target\config\server.json" -Raw | ConvertFrom-Json
$agentConfig = Get-Content "$target\config\cloud-agent.json" -Raw | ConvertFrom-Json
if ($agentConfig.hostId -ne 'cloud') { throw 'This updater is for the cloud PC only.' }
foreach ($id in @('racebot','commentator')) {
 $c = @($agentConfig.components | Where-Object { $_.id -eq $id })
 if ($c.Count -ne 1 -or -not $c[0].enabled -or $c[0].probe -ne 'http') { throw "Enable and verify $id monitoring first." }
}
$proxy = @($agentConfig.components | Where-Object { $_.id -eq 'cloud-proxy' })
if ($proxy.Count -ne 1 -or -not $proxy[0].enabled -or $proxy[0].probe -ne 'http' -or $proxy[0].url -ne 'http://127.0.0.1:8767/health' -or -not $proxy[0].requireOk) { throw 'Verified cloud proxy health profile is required.' }
$db = Join-Path $target 'config\actions.sqlite3'
if (Test-Path $db) {
 & $python (Join-Path $PSScriptRoot 'check-pending.py') $db
 if ($LASTEXITCODE -ne 0) { throw 'Resolve the pending action before updating.' }
}
# Copy the files/config to an inherited protected backup folder; do not regenerate tokens.
$backup = Join-Path $target ('backups\before-v0.8.0-' + (Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item "$target\server.py","$target\agent.py" $backup
if(Test-Path "$target\dvr_actions.py"){Copy-Item "$target\dvr_actions.py" $backup}
if (Test-Path "$target\disk_monitor.py") { Copy-Item "$target\disk_monitor.py" $backup }
Copy-Item "$target\web" $backup -Recurse
Copy-Item "$target\config\server.json","$target\config\cloud-agent.json" $backup
$stopped = $false
try {
 Stop-ScheduledTask -TaskName 'Race Operations Cloud Agent'
 Stop-ScheduledTask -TaskName 'Race Operations Backend'
 $stopped = $true
 $deadline = (Get-Date).AddSeconds(20)
 do {
  Start-Sleep -Milliseconds 500
  $running = @(Get-ScheduledTask -TaskName 'Race Operations Backend','Race Operations Cloud Agent' | Where-Object State -eq 'Running').Count
 } while ($running -gt 0 -and (Get-Date) -lt $deadline)
 if ($running -gt 0) { throw 'Management tasks did not stop. No forced process termination will be attempted.' }
 if (Test-Path $db) { Copy-Item -LiteralPath $db -Destination (Join-Path $backup 'actions.sqlite3') }
 Copy-Item "$PSScriptRoot\server.py","$PSScriptRoot\agent.py","$PSScriptRoot\disk_monitor.py","$PSScriptRoot\dvr_actions.py" $target -Force
 Copy-Item "$PSScriptRoot\web\index.html","$PSScriptRoot\web\app.js" "$target\web" -Force
 $serverConfig | Add-Member -NotePropertyName dvrControlsEnabled -NotePropertyValue $true -Force
 $dvrHost=@($serverConfig.hosts | Where-Object { $_.id -eq 'dvr' })[0]
 if(-not $dvrHost){throw 'DVR host enrollment required'}
 foreach($id in @('judge-cues','review-status','iis','obs','uploader','connector','health-monitor','pilot-review','disk-network','scoring')){
  if(-not @($dvrHost.components | Where-Object { $_.id -eq $id }).Count){$dvrHost.components=@($dvrHost.components)+@([pscustomobject]@{id=$id;enabled=$true})}
 }
 $serverConfig | Add-Member -NotePropertyName proxyRestartEnabled -NotePropertyValue $true -Force
 $agentConfig | Add-Member -NotePropertyName proxyRestartEnabled -NotePropertyValue $true -Force
 $cloudHost = @($serverConfig.hosts | Where-Object { $_.id -eq 'cloud' })[0]
 if (-not @($cloudHost.components | Where-Object { $_.id -eq 'disk-space' }).Count) { $cloudHost.components = @($cloudHost.components) + @([pscustomobject]@{id='disk-space';enabled=$true;probe='disk'}) }
 $utf8 = [System.Text.UTF8Encoding]::new($false)
 [System.IO.File]::WriteAllText("$target\config\server.json",($serverConfig | ConvertTo-Json -Depth 30),$utf8)
 [System.IO.File]::WriteAllText("$target\config\cloud-agent.json",($agentConfig | ConvertTo-Json -Depth 30),$utf8)
 Start-ScheduledTask -TaskName 'Race Operations Backend'
 Start-ScheduledTask -TaskName 'Race Operations Cloud Agent'
 $healthy = $false
 for ($i=0; $i -lt 20; $i++) {
  Start-Sleep -Seconds 1
  try { $h = Invoke-RestMethod 'http://127.0.0.1:8799/health' -TimeoutSec 2; if ($h.ok -and $h.version -eq '0.8.0') { $healthy=$true; break } } catch {}
 }
 if (-not $healthy) { throw 'Updated backend did not pass its startup check.' }
 Write-Host 'Updated to v0.8.0. Refresh dashboard with Ctrl+F5 and sign in again.'
 Write-Host 'Each restart control is disabled while its target is green. A failing health check enables that control.'
 Write-Host "Backup: $backup"
 Write-Host 'No RaceBot, Commentator or DVR application was restarted by this update.'
} catch {
 $problem = $_
 if ($stopped) {
  Stop-ScheduledTask -TaskName 'Race Operations Cloud Agent' -ErrorAction SilentlyContinue
  Stop-ScheduledTask -TaskName 'Race Operations Backend' -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
  Copy-Item "$backup\server.py","$backup\agent.py" $target -Force
  if(Test-Path "$backup\dvr_actions.py"){Copy-Item "$backup\dvr_actions.py" $target -Force}
  if (Test-Path "$backup\disk_monitor.py") { Copy-Item "$backup\disk_monitor.py" $target -Force } else { Remove-Item "$target\disk_monitor.py" -ErrorAction SilentlyContinue }
  Copy-Item "$backup\web\*" "$target\web" -Force
  Copy-Item "$backup\server.json","$backup\cloud-agent.json" "$target\config" -Force
  if (Test-Path (Join-Path $backup 'actions.sqlite3')) { Copy-Item (Join-Path $backup 'actions.sqlite3') $db -Force }
  Start-ScheduledTask -TaskName 'Race Operations Backend'
  Start-ScheduledTask -TaskName 'Race Operations Cloud Agent'
  Write-Warning 'Previous management files restored. Verify backend health before continuing.'
 }
 throw $problem
}
