# DVR uploader time correction v0.4.2

Operator evidence: local 2026-10-29 12:27:21 -04:00, UTC 16:27:21; latest heartbeat 12:22:57Z, log modified 12:22:57 local / 16:22:57 UTC. The uploader writes local wall time with a literal Z suffix. v0.4.0 incorrectly treated it as UTC, adding four hours to the displayed age. Actual observed age: 264 seconds.

DVR v0.4.2 explicitly interprets this uploader's timestamps in the machine's local timezone using date-specific OS rules. No fixed offset or automatic offset guessing. True UTC parsing remains available for explicit test/future formats. During a repeated fall-back hour it uses the older possible instant, so a temporary conservative warning is possible. Changing the machine timezone or fixing the uploader itself to true UTC requires revisiting this log-format contract.

The 15-minute stale threshold, task state rules, secret filtering and OBS persistent connection are unchanged. Cloud stays at v0.4.1. No uploader source or log is modified. The installer also accepts the verified cloud v0.4.1 version.

## Deploy on OBS/DVR PC only

Extract RaceOperations-DVR-Update-v0.4.2.zip. In Administrator PowerShell from that folder:

```powershell
Unblock-File .\Update-DVR-Agent.ps1
.\Update-DVR-Agent.ps1
```

Only the management agent restarts. Expect a one-time OBS monitoring reconnect; recording and applications are untouched. Existing tokens and configurations are preserved, with protected backups. Refresh the dashboard; uploader age should match the latest local log heartbeat (normally under 15 minutes). Portable tests passed; live Windows correction awaits operator verification.
