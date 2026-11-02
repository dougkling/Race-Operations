# Full installation guide

## 1. Scope and prerequisites

Race Operations manages **existing applications**. It does not install RaceBot, Commentator, Race DVR, OBS, IIS, uploader, connector or the DVR health checker. Install/validate those from their own repositories first. This source targets Doug's verified Race DVR task/path layout; it is not a universal discovery system.

| Host | Requirements |
| --- | --- |
| Cloud Windows PC | RaceBot/PitWall manager; RaceBot local 8765; Commentator local 8766; judge proxy local 8767; machine-wide Python 3.10+; Windows PowerShell 5.1; Administrator access |
| OBS / DVR PC | Race DVR installation; `C:\DVR`; Judge Cues, Review Status, IIS, uploader and connector; OBS local v5 WebSocket; machine-wide Python 3.10+; Administrator access |
| Browser | Modern desktop/mobile browser with management endpoint access |
| Optional email | SES SMTP sending credentials, verified sender identity and outbound TCP 587 |

Keep Cloud, DVR and Scoring PCs distinct. Python must be accessible to SYSTEM; do not use a Microsoft Store alias. Existing cloud deployments use `C:\Program Files\PitWall\runtime\Python-3.13.16\python.exe`. The full cloud updater expects that path and the PitWall manager; a different layout requires reviewing/adapting those fixed prerequisites first.

Download a reviewed tag/commit or built package, extract locally and run `Get-ChildItem -Recurse -File | Unblock-File`. Choose fresh install or update based on actual existing tasks/directories. Installers refuse to overwrite an existing target. Do not launch a duplicate RaceBot instance.

## 2. Install cloud management

In Administrator PowerShell in the `cloud` folder:

```powershell
.\Install-Cloud.ps1 -PythonPath 'C:\Program Files\PitWall\runtime\Python-3.13.16\python.exe'
Invoke-RestMethod 'http://127.0.0.1:8799/health'
Get-ScheduledTask -TaskName 'Race Operations Backend','Race Operations Cloud Agent' |
    Select-Object TaskName,State
```

Expected health: `ok=True`, version `0.9.0`. The installer protects `C:\ProgramData\RaceOperations` for SYSTEM/Administrators, generates private tokens/configuration, and creates two SYSTEM startup tasks with restart-on-failure. It creates no inbound firewall rules. HTTP application probes and recovery flags start disabled; cloud disk capacity is collected independently.

Open `http://127.0.0.1:8799` locally. Read `config\administrator-token.txt` on that PC and use it to sign in. Do not put that token in Git, email or support chat. The cloud and DVR enrollment tokens are separate from the administrator token.

## 3. Enable verified cloud monitors

Verify these existing endpoints/tasks first:

```powershell
Invoke-WebRequest 'http://127.0.0.1:8765/' -UseBasicParsing | Select-Object StatusCode
Invoke-WebRequest 'http://127.0.0.1:8766/' -UseBasicParsing | Select-Object StatusCode
Invoke-RestMethod 'http://127.0.0.1:8767/health'
Get-ScheduledTask -TaskName 'Race DVR Judge Proxy' -TaskPath '\' |
    Select-Object TaskName,TaskPath,State
```

Back up `config\cloud-agent.json` inside the protected installation. Edit it elevated, preserving token, host ID, server URL and unrelated fields. Set these component profiles:

| id | enabled | probe | url | requireOk |
| --- | --- | --- | --- | --- |
| racebot | true | http | `http://127.0.0.1:8765/` | false/omitted |
| commentator | true | http | `http://127.0.0.1:8766/` | false/omitted |
| cloud-proxy | true | http | `http://127.0.0.1:8767/health` | true |

Write JSON as UTF-8 without BOM. Restart only the cloud management agent to load it:

```powershell
Stop-ScheduledTask -TaskName 'Race Operations Cloud Agent' -TaskPath '\'
Start-ScheduledTask -TaskName 'Race Operations Cloud Agent' -TaskPath '\'
```

Confirm a fresh dashboard sample. RaceBot/Commentator green means HTTP reachability, not working AI/YouTube/Discord. Proxy `ok` and `dvrConnected` supply the connector evidence.

## 4. Remote access

Backend listens on **127.0.0.1:8799 only**. Installers do not provision DNS, certificates, reverse proxy, Windows inbound rules or AWS security groups. A new deployment must provide a trusted HTTPS reverse proxy to the loopback backend, preserve `/api/*`, and restrict access to authorized networks. Verify `/health` and the certificate chain from the DVR PC before transferring enrollment credentials; do not disable TLS validation.

The historical operator deployment forwards TCP 80 using Windows portproxy/IP Helper with AWS source restrictions. It is not recreated by this installer. Inspect using `netsh interface portproxy show all` and `Get-Service iphlpsvc`. HTTP does not protect tokens or sessions in transit. The DVR agent only permits that exact historical HTTP origin, with explicit opt-in; use HTTPS elsewhere.

Do not expose RaceBot, Commentator or OBS local ports as part of this management setup.

## 5. Enroll the DVR PC

On the cloud PC, obtain the DVR token from protected `config\dvr-agent.json`; it must match the `dvr` host token in `config\server.json`. Transfer it privately. Do not use the administrator token.

In Administrator PowerShell in `dvr`, replace the hostname/Python path with verified values:

```powershell
.\Install-DVR-Agent.ps1 -PythonPath 'C:\Python313\python.exe' `
    -ServerUrl 'https://your-verified-management-hostname'
```

Only for the existing historical deployment:

```powershell
.\Install-DVR-Agent.ps1 -PythonPath 'C:\Python313\python.exe' `
    -ServerUrl 'http://98.84.103.79' -AllowLegacyHttp
```

The installer accepts the current v0.9.0 backend, prompts securely for the token, protects `C:\ProgramData\RaceOperationsDvrAgent`, copies the modules, and validates a one-shot heartbeat before creating `Race Operations DVR Agent`. Failed enrollment retains protected files for diagnosis and does not create a startup task. Investigate before manually removing any installation files.

Verify within about 15 seconds:

```powershell
Get-ScheduledTask -TaskName 'Race Operations DVR Agent' | Select-Object TaskName,State
Get-Content 'C:\ProgramData\RaceOperationsDvrAgent\status.json' -Raw | ConvertFrom-Json |
    Select-Object version,cloudAccepted,error,lastAttempt
```

The one-shot heartbeat executes no commands and advertises a compatibility version; the normal loop reports 0.8.0. Do not repeatedly run `--once` alongside the normal agent: it temporarily replaces the sample with one without recovery capabilities.

## 6. Verify dependencies and enable recovery

Check [CONFIGURATION.md](CONFIGURATION.md) for fixed endpoint, file and task contracts. OBS credentials come from local `RaceDvrJudgeCues\config.json`, `unification.obs`. The uploader and health checker must produce recognized logs/reports. Pilot Review must use the existing public S3 schema.

Start OBS normally in the intended logged-in desktop. On the DVR PC run:

```powershell
.\Update-DVR-Agent.ps1
```

The updater discovers fixed tasks, one unambiguous connector task and the actual OBS executable/arguments/owner. Unverified controls remain disabled. It registers an interactive `Race Operations OBS Recovery` task and makes the existing health-check task repeat every five minutes while preserving boot triggers. Only the DVR management agent restarts during installation; OBS recording is not started.

After verifying targets, enable these JSON booleans on the cloud PC:

- `config\server.json`: `pitwallRestartEnabled`, `proxyRestartEnabled`, `dvrControlsEnabled` = `true`.
- `config\cloud-agent.json`: `pitwallRestartEnabled`, `proxyRestartEnabled` = `true`.

Back up each file first, preserve tokens/host lists, and restart the two management tasks after editing. The full cloud updater can enable proxy/DVR flags on a verified existing layout; shared RaceBot recovery still requires its enable flag on both sides. Recording guards and per-target health checks continue to apply.

## 7. SES alerts

On the cloud PC, in the `cloud` package folder:

```powershell
.\Configure-SES.ps1 -Region us-east-1
```

Use SES **IAM SMTP sending credentials** for that region. Mail Manager ingress credentials for a `mail-manager-smtp.amazonaws.com` endpoint do not work with this sender. It uses `email-smtp.<region>.amazonaws.com`, STARTTLS TCP 587. Verify the sender identity in that region; while in the sandbox, verify the recipient too.

The script sends one test email and enables alerts only after SES accepts it. Verify the inbox separately. Credentials are stored in protected `config\email-alerts.json`. The operator previously obtained acceptance with `doug@multigp.com` as sender and recipient; that does not establish any other verified identity. Never copy credentials from chat or historical archives.

See [alerts-v0.9.0.md](alerts-v0.9.0.md). Mute suppresses email only; status and recovery controls remain active.

## 8. Production acceptance

1. Check both agents, version fields and each actual application endpoint against dashboard evidence.
2. Confirm OBS Idle/Recording tracks the real application. Never test restart during recording.
3. Verify fresh health reports across multiple five-minute runs; treat a graphics-source warning separately from an outage.
4. Safely stop a noncritical service, confirm red, invoke one recovery and verify application reconnection.
5. Test one muted incident and one unmuted incident; verify activity and inbox delivery.
6. Test every map link, saved collapse and mobile PC selector. Scoring remains grey.
7. During maintenance, reboot each host and confirm management returns without RDP login. OBS GUI recovery still needs its verified logged-in user.
8. Record installed file hashes/source revision, private backups and operator results.

Automated tests do not certify a fresh Windows installation, live recovery, firewall/TLS setup or SES delivery.


## AI health and recovery v0.10.0

See [the AI monitor contract, installation, validation and rollback](ai-monitor-v0.10.0.md). This supersedes earlier statements that AI monitoring is absent. Actual Windows deployment and live email acceptance remain separate from automated source tests.
