# Disk capacity monitoring v0.5.0

Verified paths: cloud C:\ and DVR recording folder C:\DVR. Operator expanded cloud C: to 99 GiB, 72.4 GiB free (73.2%). DVR C: is 231.8 GiB, 67.9 GiB free (29.3%). Both are green under the initial policy.

Each agent reads capacity with shutil.disk_usage using a fixed path. Missing/unreadable paths return Unknown. No disk writes, cleanup, restarts or recording commands are performed by the probe. DVR queries C:\DVR directly, so its volume is used even if the folder later becomes a mount point; this row does not independently certify C: in that case. Free bytes and total bytes are sent; the backend validates and recomputes percentage and severity. Stale agents show Unknown.

Yellow below 15% OR 10 GiB free; red below 5% OR 2 GiB. Thresholds are strictly below; values exactly at boundaries are classified by the other threshold. These are capacity thresholds, not estimated recording time. No bitrate or retention assumptions. The former Disk & Network row is now labeled Disk space; network monitoring remains pending.

## Deployment

Source stays in GitHub; supply deployment ZIPs. Extract cloud v0.5.0 on cloud PC, run Administrator PowerShell: Unblock-File .\Update-Cloud.ps1 then .\Update-Cloud.ps1. Then extract DVR v0.5.0 on OBS/DVR PC and run Unblock-File .\Update-DVR-Agent.ps1 then .\Update-DVR-Agent.ps1. Cloud update adds the allowed disk-space component while preserving existing enrollment. Refresh dashboard with Ctrl+F5. Only management tasks restart; applications remain running. Existing protected backups and failure recovery retained.

Cloud stays compatible with older agents during rollout. DVR keeps compatibility agentVersion 0.3.0. OBS persistent socket and uploader local-time fix retained. Portable capacity/boundary/unavailable/telemetry tests cover the change; live Windows deployment pending.
