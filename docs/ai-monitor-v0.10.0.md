# RaceBot AI monitoring and recovery v0.10.0

This closes the failure where RaceBot's HTTP page remained green while OpenAI requests timed out. It does not add YouTube, Discord, Desk research, Internet or race-timing health checks.

## Install on the existing cloud Windows server

Download the generated `Update-RaceBot-AI-Monitor.ps1`, then run Administrator Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Update-RaceBot-AI-Monitor.ps1"
```

This narrow update requires the existing Race Operations v0.9.0 backend/cloud agent v0.7.0/UI v0.9.2 source baseline, the existing PitWall deployment manifest and startup task, and its installed Python runtime. It also accepts its own installed v0.10.0 files. An unexpected local monitoring edit is rejected before stopping services. RaceBot's app.py is patched through unique insertion points instead of replacing the entire file, preserving other installed features.

Before stopping services the updater verifies embedded checksums, Python syntax and configuration, builds a protected backup and validates every insertion. It then stops the two monitoring tasks, refuses pending recovery jobs, stops RaceBot/Commentator through their manager, installs files and starts the tasks. Readiness requires the private AI endpoint and a fresh authenticated cloud-agent heartbeat, not a successful provider response: a genuine provider failure is allowed to install as red. It preserves API/OAuth/Discord credentials, models, chat configuration, databases, alert mutes and SES settings. Restarting the shared application task can require reconnecting live chat integrations.

The updater prints the backup path. Roll back with the same downloaded script:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Update-RaceBot-AI-Monitor.ps1 -RollbackFrom 'C:\ProgramData\RaceOperations\backups\ai-monitor-TIMESTAMP-ID'
```

Rollback refuses later/concurrent source edits and retains action/alert databases. It restores previous task running/stopped states. No OBS, DVR or scoring application is controlled by this update. Failed readiness attempts restore the protected file/config backups automatically.

## Evidence and cost

- `RaceBot AI` is a separate Cloud PC row and clickable topology node. HTTP reachability remains its own RaceBot monitor.
- Live moderation, generation and search failures are recorded immediately. A successful moderation request does not clear a generation failure; tool-free probes do not clear search failures. A stalled request is failed after 75 seconds.
- Startup and five-minute periodic probes make one moderation call and one tiny tool-free generation call using the configured chat model. They run in a separate daemon thread, never post chat and never consume/reset the application conversation budget. They incur normal API usage: up to 288 scheduled probe cycles per 24 hours, plus explicitly requested reconnects. A failed moderation stops that cycle before generation. No real credentials/provider calls are used in automated tests.
- Green requires actual completed moderation and generation evidence; a configured key is insufficient. Evidence over 15 minutes old or unavailable authorization becomes unknown, never green. Failed evidence stays red until the affected stage succeeds or credentials/model change triggers fresh checks.
- The Cloud agent reads the sanitized health projection every poll. No prompt, raw provider error, OpenAI credential or chat content enters Race Operations.
- Existing SES delivery sends one email when this new monitor is red for 30 seconds, unless muted. Existing SES setup must already be enabled; installation prints its mode and does not send a test email. Unknown evidence is not recovery and does not reset an incident. Existing independent cloud-outage limitations remain.

## Controls

`Reconnect RaceBot AI` is enabled only for fresh red AI evidence from the updated cloud agent. It requires the normal monitoring login, CSRF token, exact confirmation, unique request ID, durable execution journal, cloud host identity and 120-second cooldown. It reloads the existing key (environment precedence retained), tests moderation/generation, and waits for that request's completed result. It neither saves/replaces credentials nor publishes chat. Chat history, selected integrations and session budgets are retained. In-flight drafts are invalidated only if credentials changed.

`Restart RaceBot + Commentator` also becomes eligible when AI is red even if both HTTP pages respond. It uses the established PitWall manager, explicitly interrupts both apps and checks both HTTP and configured AI health before reporting success. Use it if AI reconnect cannot clear a stalled worker. There is no automatic restart loop.

Neither control can fix provider outages, exhausted billing quota, rate limits, invalid models or session-budget exhaustion. Check the reason displayed and resolve that cause.

## Private local contract

RaceBot exposes GET `/api/ops/ai-health` and POST `/api/ops/ai-reconnect` on its existing port 8765. Both require the actual peer and exact Host to be loopback, plus a constant-time checked independent Bearer token. Forwarded headers are not trusted. The updater creates/reuses a 64-hex token in the existing protected PitWall data directory; the cloud configuration stores its path, not the OpenAI key. POST accepts only a bounded requestId body, failed evidence and cooldown; GET never triggers a paid call.

Cloud adapter uses a fixed loopback URL, disables environment proxies and redirects, bounds response size and validates schema, timestamps, reasons and freshness before projection. The backend again sanitizes heartbeat fields. Recovery failures and uncertain results remain audited and never auto-replayed.

## Source and verification

Source spans `dougkling/RaceBot` (AI evidence/API hook) and `dougkling/Race-Operations` (agent/backend/UI/alerts and transactional updater). Build from matched reviewed checkouts using:

```bash
python tools/build_ai_update.py --racebot ../RaceBot --output dist
```

The generated script contains a checksum-verified embedded payload; SHA256 accompanies it. Linux automated tests exercise failure propagation, stale/unknown evidence, stage isolation, local authorization, scoped CSRF-protected recovery, deduplication, cooldown, email incidents, surgical upgrades and rollback. Browser tests cover the new row/map and failure-only button. Windows PowerShell parsing is checked in CI. Native Windows task/ACL/rollback execution, actual installed-source parity, live provider calls and SES inbox delivery require installation acceptance; they are not claimed by portable tests.

### Constructor compatibility correction

The first updater expected the older two-argument OpenAI constructor. The corrected patch inserts monitoring independently of the constructor signature, preserving the installed timeout argument and self.timeout. Patch replay recognizes inserted content before testing the old anchor. The correction was verified against both saved Windows master ZIP versions and against the already patched source, including repeated installation. A failed insertion preflight changed no live files and stopped no services; replace the downloaded updater and rerun without rollback.
