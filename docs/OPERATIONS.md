# Operations runbook

## Before production

Check cloud/DVR agent connection and freshness, actual OBS Idle/Recording, disk free space, uploader heartbeat and health-report age. Confirm Pilot Review current/archived sample checks. Scoring remains pending. Check intended SES state and per-monitor Mute toggles; muted red still means unhealthy.

## Restart RaceBot and Commentator

Run in Administrator PowerShell on the **cloud PC**. They share a restart group:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Program Files\PitWall\manager\PitWall.ps1" -Command restart
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Program Files\PitWall\manager\PitWall.ps1" -Command status
```

This command restarts both applications regardless of dashboard health; review live posting/production impact first. The dashboard's shared control is available only for a known degraded/offline target. After restarting, verify actual AI, YouTube and Discord connections in RaceBot; HTTP green does not establish them. AI-only reconnect remains unfinished draft work.

## DVR recovery

Use the control beside the relevant monitor, verify the confirmation and watch the activity result. Restarting Control Server or OBS is blocked while recording/recording evidence is unknown, with a specific confirmed-absent OBS exception. A succeeded job must still be checked in the actual application. Connector recovery must reconnect to the cloud proxy; OBS GUI launch requires its logged-in verified user. Do not retry an indeterminate job until its real outcome is established.

## Stale health report

`Task: Ready` means idle, not continuously polling. Inspect the schedule and last execution:

```powershell
$task = Get-ScheduledTask -TaskName 'Race DVR System Health Check' -TaskPath '\'
$task.Triggers | Select-Object Enabled,StartBoundary,Repetition
$task | Get-ScheduledTaskInfo | Select-Object LastRunTime,LastTaskResult,NextRunTime
```

Use **Run system health check** to generate a fresh report. The DVR updater adds a five-minute repeat. More than 15 minutes of report age is degraded. A restart can briefly produce failures; allow a subsequent check and verify whether it recovers. Do not hide persistent failures by changing report timestamps.

## Agent disconnected or status unknown

On cloud, inspect `Race Operations Backend` and `Race Operations Cloud Agent`, then local `/health`. On DVR inspect `Race Operations DVR Agent` and sanitized `status.json`. Check origin/certificate/network access and token matching privately. Do not paste config files. Stale component evidence is unknown; the connector can remain known from the fresh cloud proxy.

## Email diagnosis

Confirm enabled state, Mute state, continuous red duration, incident history and recipient inbox/spam. SES accepted means SMTP acceptance, not guaranteed delivery. Use the verified regional sender and IAM SMTP sending credentials; Mail Manager ingress credentials are a different service. Avoid repeatedly generating incidents or rerunning the test wizard just to refresh status. Disable email without disabling health checks:

```powershell
.\Configure-SES.ps1 -Disable
```

There are no recovery emails or periodic reminder emails. Total backend outage requires external monitoring.

## Gather support evidence

Provide UI/backend/agent versions, affected host/component, timestamp/timezone, exact sanitized job ID/result, task state/last-run/exit code and report age. Exclude bearer/admin/SMTP/OBS secrets, raw config files and private databases. Record the installed package/commit hash. Follow [UPGRADE_ROLLBACK.md](UPGRADE_ROLLBACK.md) for recovery from a failed update.


## AI health and recovery v0.10.0

See [the AI monitor contract, installation, validation and rollback](ai-monitor-v0.10.0.md). This supersedes earlier statements that AI monitoring is absent. Actual Windows deployment and live email acceptance remain separate from automated source tests.
