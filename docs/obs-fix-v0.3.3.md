# Race Operations OBS connection fix v0.3.3 — DVR PC only

The v0.3.2 monitor opened and closed an OBS connection on every status sample. That caused repeated client connect/disconnect notifications even with healthy OBS. This update keeps one authenticated OBS WebSocket session across samples. A dedicated monitoring thread reads GetRecordStatus about every 3 seconds, independently of cloud heartbeat delays. It handles OBS ping/pong, reconnects only on transport/protocol failure or config changes, and backs off failed connections from 5 to 60 seconds. A missing recording field stays Unknown without intentionally cycling the valid connection.

## Immediate mitigation

On OBS/DVR PC in Administrator PowerShell:

```
Stop-ScheduledTask -TaskName 'Race Operations DVR Agent'
```

OBS and Judge Cues keep running. DVR dashboard status becomes Unknown as telemetry ages. If the actual Judge Cues OBS connection still drops with our agent stopped, investigate that separately; do not restart OBS or the recording pipeline to fix monitoring.

## Apply

Extract this package on OBS/DVR PC, open Administrator PowerShell in its directory:

```
Unblock-File .\Update-DVR-Agent.ps1
.\Update-DVR-Agent.ps1
```

No cloud update is needed; compatible with cloud v0.3.2. Tokens, configuration, boot task settings and recording workflow are preserved. Only monitoring task/files are updated. One short-lived validation process may create a connection during installation; after task startup the connection should stay open. Verify notifications do not repeat on every poll. A genuine OBS closure/config change still requires reconnection.

No OBS application restart, scene changes, recording start/stop or Judge Cues restart occurs. Local secret settings are read from the same existing Judge Cues config. No credential values are sent to cloud. Cloud transport remains as previously configured. On failed upgrade the prior monitoring files are restored but the monitoring task is disabled to avoid restoring the repeated connections; a successful update enables/starts it again.

## Verify

Watch OBS connections/notifications for at least one minute. Expect one persistent monitor connection plus the existing Judge Cues connection. Dashboard should show OBS Connected and Idle/Recording according to actual state. Local sanitized status is at C:\ProgramData\RaceOperationsDvrAgent\status.json and reports 0.3.3. On reconnect backoff the state remains Unknown for recording, never Idle by inference. Probe samples older than 15 seconds become Unknown. Unimplemented DVR action controls remain disabled.

Automated tests verify persistent reuse/one identification, retry backoff, real loopback WebSocket handshake and consecutive GetRecordStatus reads on one socket, explicit recording states and no secret projection. Live Windows/OBS verification remains necessary.
