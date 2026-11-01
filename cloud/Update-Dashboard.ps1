[CmdletBinding()]param()
$ErrorActionPreference='Stop'
$target='C:\ProgramData\RaceOperations\web'
if(-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Run Administrator PowerShell on the cloud PC.'}
$health=Invoke-RestMethod 'http://127.0.0.1:8799/health' -TimeoutSec 5
if(-not $health.ok -or $health.version -ne '0.8.0'){throw 'This dashboard update requires the v0.8.0 backend. Install the cloud v0.8.0 update first.'}
$files=@('index.html','app.js')
$manifest=Get-Content (Join-Path $PSScriptRoot 'UI-MANIFEST.json') -Raw | ConvertFrom-Json
foreach($name in $files){
 $source=Join-Path "$PSScriptRoot\web" $name
 if(-not (Test-Path (Join-Path $target $name))){throw "Installed dashboard file missing: $name"}
 if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.$name){throw "Package validation failed: $name"}
}
$backup=Join-Path 'C:\ProgramData\RaceOperations\backups' ('dashboard-before-v0.8.1-'+(Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach($name in $files){Copy-Item (Join-Path $target $name) $backup}
try{
 foreach($name in $files){
  $staged=Join-Path $target ($name+'.new')
  Copy-Item (Join-Path "$PSScriptRoot\web" $name) $staged -Force
  [IO.File]::Replace($staged,(Join-Path $target $name),$null)
 }
 Write-Host 'Dashboard UI updated to 0.8.1. Refresh desktop and mobile browsers.'
 Write-Host 'Use Ctrl+F5 on desktop. No services or applications were restarted.'
 Write-Host "Backup: $backup"
}catch{
 foreach($name in $files){Copy-Item (Join-Path $backup $name) $target -Force;Remove-Item (Join-Path $target ($name+'.new')) -ErrorAction SilentlyContinue}
 throw
}
