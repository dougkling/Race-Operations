# Configuration and integration contracts

## Private files

| Path | Purpose |
| --- | --- |
| `C:\ProgramData\RaceOperations\config\server.json` | Port, admin-token hash, host tokens, component allowlists, recovery enable flags |
| `...\config\administrator-token.txt` | Local dashboard sign-in secret |
| `...\config\cloud-agent.json` | Cloud enrollment, loopback backend URL, HTTP probes and cloud recovery flags |
| `...\config\dvr-agent.json` | Initially generated DVR token/reference; copy its token privately to DVR enrollment |
| `...\config\email-alerts.json` | SES region/sender/recipient/SMTP credentials/enabled state |
| `...\config\actions.sqlite3` | Persistent action audit, alert incidents and mute preferences |
| `...\config\agent-actions.sqlite3` | Cloud execution journal |
| `C:\ProgramData\RaceOperationsDvrAgent\config.json` | DVR origin/token, discovered recovery capabilities, verified connector/OBS targets |
| `...\dvr-actions.sqlite3` | DVR execution/acknowledgement journal |
| `...\status.json` | Sanitized last DVR attempt/evidence; no token |

Paths abbreviated with `...` continue the preceding installation root. Generated JSON belongs only on protected hosts, never in Git. Write UTF-8 without BOM. Agent/backend configs load at process start; SES settings and mute state refresh without a backend restart.

## Monitor inventory

| Host | Display / internal ID | Actual evidence |
| --- | --- | --- |
| Cloud | Agent connection / `agent-link` | Backend heartbeat receipt |
| Cloud | RaceBot / `racebot` | HTTP 200 from verified loopback 8765 URL |
| Cloud | Commentator Desk / `commentator` | HTTP 200 from verified loopback 8766 URL |
| Cloud | DVR cloud proxy / `cloud-proxy` | `http://127.0.0.1:8767/health`, `ok=true` |
| Cloud | System disk / `disk-space` | Capacity of `C:\` |
| DVR | Agent connection / `agent-link` | Backend heartbeat receipt |
| DVR | DVR Control Server / `judge-cues` | `http://127.0.0.1:8766/health`, `ok=true`; optional recording evidence |
| DVR | Review Status / `review-status` | HTTP 200 on `http://127.0.0.1:8765/health` |
| DVR | IIS Judge Review / `iis` | HTTP 200 on `http://127.0.0.1/index.asp` |
| DVR | OBS Studio / `obs` | Persistent authenticated OBS v5 WebSocket `GetRecordStatus`; process inventory |
| DVR | S3 Uploader / `uploader` | Task state and most recently modified bounded uploader log |
| DVR | Cloud Connector / `connector` | Fresh cloud proxy's `dvrConnected`, independent of DVR heartbeat |
| DVR | DVR disk / `disk-network` | Capacity of `C:\DVR`; ID is historical, not a network test |
| DVR | Pilot Review / `pilot-review` | Public page/manifest and current/archived sample video HEAD checks |
| DVR | System Health Check / `health-monitor` | Existing task state/last result plus bounded report parsing |

The visible map/list has 15 monitors. `scoring` may exist as an unknown heartbeat component, but the scoring workstation is a separate grey UI area with no active agent or controls. No monitor directly certifies OpenAI, YouTube, Discord, the Internet, LiveTime, race tracking or the S3 bucket itself.

## Fixed application dependencies

- RaceBot/Commentator recovery invokes only `C:\Program Files\PitWall\manager\PitWall.ps1 -Command restart` using Windows PowerShell. Both applications restart.
- Proxy recovery targets root task `Race DVR Judge Proxy`.
- DVR task names: `Race DVR Judge Cues`, `Race DVR Review Status`, `Race DVR S3 Uploader`, `Race DVR System Health Check`. IIS uses `W3SVC`.
- Connector discovery requires exactly one enabled matching Race DVR connector task with a verified `connector.js` action. The task name/path is retained locally.
- OBS configuration: `C:\ProgramData\RaceDvrJudgeCues\config.json`, `unification.obs.enabled/url/password`. Only loopback WebSocket URLs are accepted. Monitoring has no start/stop recording requests.
- OBS recovery uses the verified executable, working directory, arguments and desktop owner. Auto-record/stream/replay/multi flags are stripped. It requires a logged-in interactive user.
- Uploader logs: `C:\ProgramData\RaceDvrS3Uploader\Logs\uploader-*.log`. The known writer uses local wall time with a literal Z suffix; parsing uses local timezone/DST rules, including conservative fall-back ambiguity handling.
- Health report: `C:\ProgramData\RaceDvrHealthMonitor\Logs\RaceDvr-Health-Latest.log`. Parser expects one timezone-qualified timestamp and one `RESULT:` summary; only known check names leave the host.
- Pilot Review base: `https://race-dvr-public.s3.us-east-1.amazonaws.com/pilot-review/`. Manifest fields include `version`, `generatedAt`, `races`; sample paths stay within the expected races prefix. HEAD checks validate MP4 type and exact manifest size. No AWS credentials are read.

## Timers and guards

| Setting | Source behavior |
| --- | --- |
| Dashboard refresh | 5 seconds |
| Cloud agent loop | 5 seconds after collection/reporting |
| DVR agent loop | 10 seconds after collection/reporting |
| Host evidence stale | 45 seconds |
| Agent red grace after backend startup | 60 seconds, then alert delay |
| Uploader warning | Heartbeat older than 900 seconds |
| Health report stale | 900 seconds |
| Scheduled health check | Every 5 minutes after DVR updater |
| Pilot page/manifest/sample probe | Every 300 seconds; stale worker evidence after 600 seconds |
| Red email delay | 30 continuous seconds |
| Recovery cooldown | 120 seconds per action |
| Queued command lifetime | 60 seconds |
| Admin session | 8 hours |

Disk warning: below 15% **or** 10 GiB free. Critical: below 5% **or** 2 GiB. Backend recomputes disk health from validated byte counts.

Unknown is not healthy. Stale host component rows become unknown; connector state may remain known from the fresh cloud proxy. Previously seen disconnected agents can go red. One recovery action may be pending globally. DVR actions require v0.8.0 and advertised, locally discovered capabilities. Green targets are blocked except the on-demand health-check task. OBS/control-server recovery additionally blocks active/unknown recording unless OBS is confirmed absent, and always blocks a positive Judge Cues recording indication.

## API contracts

Browser: `/api/login`, `/api/status`, `/api/monitor-mute`, and allowlisted `/api/actions/<action>`. Mutations require session and CSRF; recovery additionally requires the exact confirmation label and UUID request ID. Agent: `/api/heartbeat` and `/api/action-result`, using separate host-bound bearer tokens. Reusing a request ID does not execute twice. No generic shell/host reboot endpoint exists. Public `/health` exposes backend readiness, not application health.

Display renaming must not change `judge-cues` or its confirmation payload without coordinated backend/agent changes. Cloud `/control` is not the DVR Stream Deck WebSocket; the DVR endpoint is local port 8766 `/control`. The existing HTTP health probe does not authenticate or exercise that socket.


## AI health and recovery v0.10.0

See [the AI monitor contract, installation, validation and rollback](ai-monitor-v0.10.0.md). This supersedes earlier statements that AI monitoring is absent. Actual Windows deployment and live email acceptance remain separate from automated source tests.
