# Race Operations — AI maintainer handoff

Owner: Doug Kling. Prepared 2026-11-01. Standalone repository (temporarily public by owner request): `dougkling/Race-Operations`. Original source: `dougkling/DroneRaceTools/race-operations` through commit `b095a71fdfeefc348c21d75412410336e8e0ade8`, with last feature commit `bceae031a8428c77b5c4d045b932ab643df25065`. Source matches the published UI 0.9.2/backend 0.9.0/cloud agent 0.7.0/DVR agent 0.8.0 baseline, except the documented DVR installer and Python 3.10 Pilot Review timestamp compatibility corrections.

## User intent and workflow

This is the NOC control center for separate cloud, OBS/DVR and future scoring PCs. Doug needs clear host ownership, visible health, email muting beside statuses, guarded restart controls and mobile usability. The top map follows the supplied architecture drawing; every live status links to its detailed row. Collapse is remembered locally. Scoring stays grey until implemented. Do not turn placeholders green.

GitHub is the requested source of truth after publication. Keep complete installation/deployment documentation and source together, retain authentic history, use separate repositories (this one temporarily public by owner request), feature branches/PRs and immutable release tags. Do not invent ten old releases to satisfy a count. Fourteen genuine source revisions were recovered with matching blob hashes and original commit/date provenance. See SOURCE_HISTORY.md/JSON.

## Code map

| File/group | Responsibility |
| --- | --- |
| `cloud/server.py` | Loopback HTTP server, sessions/CSRF, host-bound heartbeat projection, action queue/audit, eligibility |
| `cloud/agent.py` | Loopback application probes, cloud disk, fixed PitWall/proxy recovery, durable execution journal |
| `cloud/email_alerts.py` | Persistent mute/incident state, SES SMTP delivery, test/config CLI |
| `cloud/setup.py` | One-time secret/config generation; refuses nonempty config |
| `cloud/web/app.js`, `index.html` | NOC service rows, controls, map, mobile positioning, focus/state persistence |
| `dvr/dvr-agent.py` | Outbound heartbeat loop, sanitized status file, command intake/results |
| `dvr/obs_monitor.py` | Persistent authenticated read-only OBS v5 session; GetRecordStatus only |
| `dvr/*_monitor.py` | Uploader, disk, health-report and public Pilot Review observations |
| `dvr/dvr_control.py` | Fixed recovery execution, journal, local preflight and post-action evidence |
| `cloud/dvr_actions.py`, `dvr/dvr_actions.py` | Identical allowlisted action catalog/recording guards |
| `dvr/Invoke-OBS-Recovery.ps1` | Verified interactive-user OBS launch, guarded against recording |
| `dvr/Invoke-DVR-Recovery.ps1` | Fixed task/service operations |
| `cloud/*.ps1`, `dvr/*Install*.ps1`, `*Update*.ps1` | Protected installation, upgrade, target discovery, backups/rollback |
| `tests/`, `tools/`, `.github/workflows/validate.yml` | Portable checks, browser tests, deterministic packaging and CI definition |

## Facts to preserve

- RaceBot and Commentator share one restart group through the existing PitWall manager. The cloud proxy has its own task/recovery.
- `judge-cues` is displayed as DVR Control Server. The Stream Deck control WebSocket is on the DVR's local 8766 `/control`, not on the cloud scoring/OBS service. Current monitor only tests HTTP health.
- Cloud and DVR reuse some local port numbers; always name the host. OBS WebSocket is 4455 on the DVR PC.
- Agent stale threshold is 45 seconds. Stale component health is unknown; connector status is independently derived from fresh cloud proxy evidence.
- Green restart targets are disabled. Health-check execution is an explicit exception. Unknown recording blocks recovery; confirmed absent OBS is handled by the existing guard. Never remove those conditions casually.
- OBS monitoring was changed to a persistent session after repeated connect/disconnect notifications. Do not revert to a connection per UI poll.
- Uploader logs contain machine-local wall time with a literal Z. Preserve DST-aware parsing.
- The old health task had only a boot trigger; the DVR updater adds five-minute repetition. A 15-minute-old report is stale.
- SES Mail Manager ingress credentials were mistakenly tried during setup. The actual sender uses regional SES IAM SMTP sending credentials. Operator reported a successful SES test with his verified email. Credentials are not in source.
- Per-monitor mute affects email only. One email per red incident after 30 seconds; unknown is not recovery. No recovery emails, reminders or independent cloud-outage watchdog.
- UI map lines/ports are static topology. Pilot Review is a page/manifest/sample check from the DVR, not a direct S3 bucket monitor.

## Verified vs unverified

Operator conversation reports: cloud/shared/proxy recovery worked; DVR controls were tested across the discussion; connector went red and recovered after restart; health report recovered after a transient failed run; SES accepted the test message. These reports do not establish current live-host file hashes. No live Windows hosts were accessed during this import.

Current automated evidence is in VERIFICATION.md. Historical deployment-status.md is a chronological record with superseded pending statements; use current source/contracts and current open-items document for present scope. Fresh Windows setup, native parser/execution, production rollback, reboot behavior and exact installed-to-Git parity need separate evidence.

## Pending AI reconnect request

Doug requested a dedicated RaceBot AI connection restart. Existing RaceBot creates API calls from its configured key; `ai_ready` means a key exists, not verified API connectivity. The development draft adds a local-only key-reload/access-test protocol, cloud adapter and backend action. It was interrupted before UI wiring, installer/rollback, full tests, cross-repository publication or deployment. It is retained on `development/racebot-ai-reconnect`, not stable main.

Before completing it: compare actual deployed RaceBot source, validate authenticated/loopback request boundaries, preserve chat/recording state, test missing/stale credentials, concurrency/deduplication, failure redaction, uncertain outcomes and provider responses; add the dashboard control and explicit AI evidence; create a narrow supported updater and rollback; coordinate the corresponding RaceBot repository change. Do not claim API access tests cure rate limits, quota exhaustion, model/config errors or session budgets. Do not copy credentials into Race Operations.

## First actions for the next maintainer

Read INSTALLATION.md, CONFIGURATION.md, UPGRADE_ROLLBACK.md, OPEN_ITEMS.md and CONTRIBUTING.md. Check branch/status and use a feature branch. Run relevant tests before edits and record failures honestly. Confirm whether this source was published and branch protection enabled. Match installed files to a commit before touching a live event host. Do not use source-import tags as proof of fresh deployment acceptance.


## v0.10.0 AI monitor implementation

The new implementation supersedes the unfinished historical AI draft described above. It records real moderation/generation/search outcomes, runs bounded five-minute paid probes, exports private loopback evidence, integrates a separate cloud monitor/email incident, and enables authenticated failure-only AI reconnect and shared application restart. See ai-monitor-v0.10.0.md for source, installation, cost, preservation, rollback and acceptance limits. Legacy development/racebot-ai-reconnect remains historical; do not merge it over this implementation.
