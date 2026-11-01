# Health-check observation v0.6.0

Observe root task Race DVR System Health Check and C:\ProgramData\RaceDvrHealthMonitor\Logs\RaceDvr-Health-Latest.log. Poll every 30 seconds, task query timeout five seconds, report bounded to 512 KiB. Read-only: do not run the checker, change its triggers or modify application scripts. Existing checker remains authoritative for its checks.

Ready with exit 0 and a matching successful report is green only with no warnings/failures. Warnings are yellow. A failed task/report is red; running/queued is yellow and does not interpret the scheduler's running code as an exit failure. Disabled, stale (over 24 hours), future clock or mismatched report/run is yellow. Missing/invalid evidence is Unknown. Report start must match task last run within two minutes. Manual reports that do not match task runs cannot turn the scheduled check green. No next-run/cadence assumption is made; 24 hours is an explicit freshness warning, not an automatic rerun schedule.

Only summary counts, numeric times/results and fixed allowlisted warning check names leave the DVR. No raw reports, recovery commands, AWS paths, credentials or uploader log tail are forwarded. The timestamp includes its explicit offset, unlike the older uploader format. UI clears evidence for stale/disconnected DVR agents.

## Observed evidence

Operator ran the task under SYSTEM October 29 at 15:43:29 local; it returned Ready, result 0, log modified 15:43:40. Earlier interactive report: 23 pass, 3 warning, zero failures; warnings were Judge Cues version mismatch (1.7.14 vs expected 1.7.1), graphics metadata unavailable, and heat tracking disarmed. Current OBS connection boolean was true despite an old integration message saying disconnected. We do not classify from that message. Previous October 24 failure remains unexplained. Operator verified v0.5.0 disk monitoring works.

## Deploy

Extract Cloud v0.6.0 ZIP, run Administrator PowerShell Unblock-File .\Update-Cloud.ps1 then .\Update-Cloud.ps1. Then extract DVR v0.6.0 ZIP and run Unblock-File .\Update-DVR-Agent.ps1 then .\Update-DVR-Agent.ps1. Only management tasks restart. Refresh Ctrl+F5. Expect yellow for the existing warnings, or stale if the report has aged over 24 hours. No need to restart applications to clear an expected warning. Windows rollout pending.
