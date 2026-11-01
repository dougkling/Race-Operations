# Race Operations OBS monitoring update v0.3.2

Two updates for the existing cloud backend 0.3.0 and DVR agent 0.3.1. Adds direct read-only OBS WebSocket v5 connection/recording-state monitoring using the DVR's existing Judge Cues OBS configuration. No pip dependencies. No recording or scene mutation requests, OBS restart, or DVR restart actions are added. Tested cloud restart controls remain unchanged.

## 1 — Cloud PC

Extract this ZIP, open Administrator PowerShell in the `cloud` directory:

```
Unblock-File .\Update-Cloud.ps1
.\Update-Cloud.ps1
```

Refresh http://98.84.103.79/ with Ctrl+F5 and sign in. Backend reports 0.3.2 and accepts 0.3.0 compatibility heartbeats, so the existing DVR agent stays connected during rollout. Only Race Operations management tasks restart. Configuration/tokens, boot triggers, port forwarding and firewall settings are preserved. Updater makes protected backups and blocks pending recovery actions. Existing cloud agent is updated to 0.3.2 for compatibility; application restart actions are unchanged.

## 2 — OBS/DVR PC

Extract this same ZIP, open Administrator PowerShell in the `dvr` directory:

```
Unblock-File .\Update-DVR-Agent.ps1
.\Update-DVR-Agent.ps1
```

This uses the existing DVR agent task's Python executable, preserves enrollment config, backs up old agent files and updates only that agent. It reads `C:\ProgramData\RaceDvrJudgeCues\config.json` locally at `unification.obs.enabled`, `.url` and `.password`. No settings are edited. SYSTEM must have read access to that config; unknown configuration/access failure produces Unknown, not Idle. URL must use ws:// on loopback. No remote OBS connection, plaintext secret export, raw reply logging or process launch occurs. Only an outbound read-only websocket session is created. Existing cloud HTTP transport remains unchanged.

## Dashboard interpretation

OBS row shows connection health plus `Recording: RECORDING`, `Recording: Idle`, or `Recording: Unknown`; recording-paused is labeled and duration is shown when recording. `GetRecordStatus` outputActive must be an actual boolean before Idle/Recording is claimed. Failure to read recording state after authentication is yellow/Unknown. Auth/connection failures are red/Unknown. Missing or disabled local config is Unknown. Stale/disconnected agent makes all OBS fields Unknown. An active recording is green because connection and status reads work; the recording label explicitly says RECORDING.

Only booleans and a bounded duration are projected to cloud/UI. No OBS password, URL, raw OBS reply, paths, recording names, application configs or judging metadata are sent. Existing Judge Cues/Review Status/IIS checks remain in place; uploader, connector and other unimplemented checks remain Unknown.

Do not enable Judge Cues recovery yet: authenticated OBS state is only one guard; fresh Judge Cues recording ownership/critical transaction state must also be reconciled before allowing those restarts. The missing Judge Cues integration.recording field remains unresolved. No recording-state-dependent action is implemented by this release.

## Verify on DVR

Wait about 20 seconds after updates, then check dashboard. For a local sanitized view:

```
Get-Content 'C:\ProgramData\RaceOperationsDvrAgent\status.json'
```

While OBS is idle, expect obsConnected=true, recording=false and OBS green. During an already planned recording, expect recording=true and elapsed seconds advancing. Do not start/stop a live recording solely to test monitoring. Observe state returning to Idle at the next normal end. Boot task configuration is preserved; no reboot is required for this update.

Python tests include mocked OBS responses, auth formula, real loopback WebSocket handshake/masked frames/read-only RPC, missing recording state, and prior cloud controls. No Windows host, real OBS installation or PowerShell updater execution is available in build environment, so actual deployment remains to be verified. This small client supports bounded uncompressed JSON text frames, fragmentation and ping/pong; it subscribes to no OBS events and polls approximately every 10 seconds. Unknown is the intended response to incompatible OBS protocol behavior.
