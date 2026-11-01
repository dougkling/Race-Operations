# DVR recovery v0.8.0

Previously the DVR agent ignored all commands and the dashboard displayed “DVR controls disabled.” This release adds operator-confirmed recovery buttons and execution on the DVR PC.

| Control | Local target | Verification |
|---|---|---|
| Judge Cues | Root task `Race DVR Judge Cues` | Local `/health` reports `ok=true` |
| Review Status | Root task `Race DVR Review Status` | Local port 8765 `/health` returns HTTP 200 |
| IIS Judge Review | Service `W3SVC` | Local `/index.asp` returns HTTP 200 |
| S3 Uploader | Root task `Race DVR S3 Uploader` | Running task, healthy log and a new post-restart event; up to 11 minutes |
| Cloud Connector | Exactly one discovered RaceDVR connector task referencing an existing `connector.js` | Fresh cloud proxy confirms DVR connected |
| OBS Studio | On-demand `Race Operations OBS Recovery` task in verified interactive user session | Authenticated OBS recording-status probe recovers |
| Run system health check | Root task `Race DVR System Health Check` | New completed report; warnings can remain |

Buttons are disabled while healthy or when the agent or target evidence is unknown. The health-check button is available while idle even if the previous report had warnings. A 120-second cooldown and a single pending action prevent overlapping recoveries. The server authenticates and routes actions to the owning host. The local agent rechecks health before acting and journals an action before execution; a crash produces an indeterminate result rather than a replay. The browser cannot supply commands, task names or executable paths.

Judge Cues and OBS actions require idle recording evidence or confirmed absence of OBS. A second authenticated check runs immediately before local recovery; active or unknown streaming also blocks these actions. OBS uses graceful window close only and is never force-killed. A hung OBS process with an inaccessible WebSocket stays blocked for local intervention. OBS recovery does not start a recording, stream, or replay buffer. After Judge Cues recovery, verify the Lead Judge arm state before racing. Remote sessions may disconnect during service recovery.

## Deploy

1. Extract the cloud ZIP on the cloud PC. In Administrator PowerShell run `Unblock-File .\Update-Cloud.ps1` then `.\Update-Cloud.ps1`.
2. Keep OBS open normally on the DVR desktop for discovery. Extract the DVR ZIP there and run `Unblock-File .\Update-DVR-Agent.ps1` then `.\Update-DVR-Agent.ps1` in Administrator PowerShell.
3. Read the verified control list printed by the updater. Missing or ambiguous connector/OBS targets stay disabled with an explanation. OBS discovery preserves its executable, launch arguments and owner locally; automatic capture flags are removed. A verified previous OBS configuration is retained when OBS is stopped.
4. Refresh with Ctrl+F5, sign in if necessary, and allow 30 seconds. Use **Run system health check** as the first non-disruptive end-to-end command test.

The updater backs up files, configuration and affected task definitions, validates source before stopping the management task, and restores them if installation fails. It does not restart any DVR applications. It preserves boot health-check triggers and installs an indefinite five-minute repetition. Reports older than 15 minutes are marked stale. Tokens are preserved, never printed, and no inbound DVR ports are added.

Existing installs use the update packages. Fresh installs require enrollment first, then the updater to enable controls. Install cloud first. The `--once` installation probe uses the monitoring-only protocol version so it cannot consume queued DVR commands.

## Scope and limits

- Scoring Client remains unknown and has no control pending access to the scoring PC.
- Disk capacity and the S3 Pilot Review page are monitored resources, not local processes to restart.
- The DVR agent cannot remotely recover itself when it cannot reach the cloud; its existing Windows task restart policy remains responsible for that case.
- No automatic restart occurs merely because a health check fails. Every action requires a dashboard click and confirmation.
- Windows task operations and OBS desktop behavior cannot be executed in the Linux build environment. The updater performs on-host parsing/discovery; actual Windows recovery remains to be verified after deployment. Automated tests cover routing, authentication, guards, duplicate requests, crash recovery, failure handling and UI requests.
