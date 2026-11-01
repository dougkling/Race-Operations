# Uploader monitoring v0.4.0

Read-only enhancement for the current cloud and DVR deployment. Source and updates are maintained in dougkling/DroneRaceTools under race-operations. No new credentials are needed and existing configs/boot tasks/OBS persistent session behavior are preserved.

## Evidence and status

Exact root task: `Race DVR S3 Uploader`. The agent queries state only, without retrieving task arguments/config/AWS credentials. Task not running is red. Task query failed/unknown remains Unknown. A running task alone is not sufficient for green.

Read at most 128 KiB from the most recently modified `uploader-*.log` under C:\ProgramData\RaceDvrS3Uploader\Logs. Active file names may reflect process startup date, so never require today's filename. Timestamps ending Z are interpreted as UTC. Recent heartbeat plus Running is green. Missing/stale heartbeat, latest parsed error, unreadable log or future timestamp is yellow. Warning threshold is 900 seconds, chosen from operator-observed roughly 6–10 minute heartbeat intervals. Previous 180-second planning value was not used because it would false-alert this installation. No log-age or heartbeat is inferred from the DVR heartbeat itself.

Current evidence is refreshed at most every 30 seconds. The dashboard displays task state, heartbeat age, recent operation and reason. Scanned zero files is valid idle evidence, not an error. Recent operations are sanitized categories (idle, uploading, upload_complete, archive_verified, manifest_published, started, error, unknown). No raw log line, filename, credentials or error text reaches the cloud. No upload percentages are generated; quiet AWS copies may legitimately take a long time. A stale heartbeat while uploading is an attention warning, not proof of uploader failure.

This release does NOT calculate S3 backlog, oldest pending age, byte progress, object integrity, manifest lag, final log errors outside the bounded tail, or SYSTEM credential validity. Those remain later work. It adds no uploader restart and does not change recording/application tasks.

## Rollout from a Git checkout

Use a current checkout of the private DroneRaceTools repository. Source publication does not update either host automatically; no Windows execution channel or unattended Git deployment is configured.

1. Pull main with your existing GitHub credentials. In `race-operations/cloud`, run `Unblock-File .\Update-Cloud.ps1` then `.\Update-Cloud.ps1` in Administrator PowerShell on the cloud PC. Expected health version 0.4.0. Refresh browser and sign in. Cloud task actions are unchanged.
2. On DVR PC, pull main. In `race-operations/dvr`, run `Unblock-File .\Update-DVR-Agent.ps1` then `.\Update-DVR-Agent.ps1` in Administrator PowerShell. Only agent task is restarted; updater backs up old files and preserves enrollment. Expected sanitized local status version 0.4.0. OBS monitor establishes its single persistent connection again after the management-agent restart.
3. Wait about 30 seconds. Uploader should show Running and a heartbeat age consistent with the log. If current heartbeat exceeds 15 minutes, yellow is expected; inspect actual worker progress instead of assuming a task failure. Existing HTTP checks should remain green and OBS status should remain stable.

Deployment still needs live Windows verification. Diagnostic command: `Get-Content 'C:\ProgramData\RaceOperationsDvrAgent\status.json'` (sanitized status only, never config). Do not stop an uploader during live operations merely to test monitoring.
