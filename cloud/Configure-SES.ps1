[CmdletBinding()]param([string]$Region='us-east-1',[string]$FromAddress,[string]$ToAddress,[switch]$Disable)
$ErrorActionPreference='Stop'
if(-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Run Administrator PowerShell on the cloud PC.'}
$root='C:\ProgramData\RaceOperations'
$path=Join-Path $root 'config\email-alerts.json'
$task=Get-ScheduledTask -TaskName 'Race Operations Backend' -TaskPath '\'
$python=@($task.Actions)[0].Execute
if(-not (Test-Path "$root\email_alerts.py")){throw 'Install the v0.9.0 alerts update first.'}
$utf8=[Text.UTF8Encoding]::new($false)
function Save-AlertConfig($value){
 $temp=$path+'.new'
 # Original config folder is protected. Explicitly protect the staged file before writing credentials.
 [IO.File]::WriteAllText($temp,'{}',$utf8)
 & icacls.exe $temp /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' | Out-Null
 if($LASTEXITCODE -ne 0){Remove-Item $temp -ErrorAction SilentlyContinue;throw 'Unable to protect email configuration.'}
 [IO.File]::WriteAllText($temp,($value | ConvertTo-Json -Depth 5),$utf8)
 Move-Item -LiteralPath $temp -Destination $path -Force
}
if($Disable){
 $cfg=if(Test-Path $path){Get-Content $path -Raw | ConvertFrom-Json}else{[pscustomobject]@{}}
 $cfg | Add-Member -NotePropertyName enabled -NotePropertyValue $false -Force
 Save-AlertConfig $cfg
 Write-Host 'Email sending disabled. Monitoring and mute preferences remain active.'
 return
}
Write-Host "Amazon SES region: $Region (use -Region to change)"
Write-Host 'Use a sender verified in this SES region. In the SES sandbox, verify the recipient too.'
if(-not $FromAddress){$FromAddress=Read-Host 'Verified sender email address'}
if(-not $ToAddress){$ToAddress=Read-Host 'Destination email address for alerts'}
$username=Read-Host 'SES SMTP username (not your AWS console login)'
$secret=Read-Host 'SES SMTP password' -AsSecureString
$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try{$password=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
$cfg=@{enabled=$false;region=$Region;fromAddress=$FromAddress.Trim();toAddress=$ToAddress.Trim();username=$username.Trim();password=$password}
Save-AlertConfig $cfg
$password=$null;$secret=$null
Write-Host "Sending one test email to $ToAddress through SES..."
& $python "$root\email_alerts.py" --config $path --test
if($LASTEXITCODE -ne 0){throw 'SES test did not succeed. Sending remains disabled. Correct SES setup and rerun this script.'}
$cfg.enabled=$true
Save-AlertConfig $cfg
$cfg=$null
Write-Host 'SES accepted the test email. Check your inbox. Automatic red alerts are now enabled.'
Write-Host 'No backend restart required. Refresh the dashboard to see email status.'
