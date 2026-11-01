# Cloud-observed connector monitoring v0.4.1

The operator verified cloud proxy v1.0.2 health returns ok=true, dvrConnected=true, remoteJudges=0. Uploaded connector v1.0.2 sends relayPing every five seconds on its existing authenticated relay. Its logs only report connection transitions. Neither logs nor proxy health expose heartbeat freshness.

Cloud agent reuses its existing loopback proxy health request. It forwards only a strict boolean dvrConnected and bounded integer remoteJudges. The dashboard Cloud Connector row uses fresh cloud-agent evidence: green when a healthy proxy reports connected, red when it reports disconnected, unknown when proxy/agent evidence is unavailable, stale, missing or malformed. Zero judges is valid idle. This is proxy-reported connection state, not a heartbeat or end-to-end delivery test. A disconnected DVR management agent does not invalidate independent fresh cloud observation.

No application files, relay connections, task controls or restart eligibility change. The DVR agent may remain at its existing version. Existing OBS persistent socket fix remains untouched. Cloud v0.4.1 includes earlier uploader display support; actual uploader collection still requires DVR v0.4.0.

## Rollout

In an authenticated DroneRaceTools checkout on the cloud PC, run Administrator PowerShell:

```powershell
git pull --ff-only
.\race-operations\cloud\Update-Cloud.ps1
```

Refresh with Ctrl+F5 and sign in again. Expect Cloud Connector green, Proxy reports connected, Remote judges: 0, Heartbeat age unavailable. Verify /health reports 0.4.1. The updater backs up the existing management deployment and restarts only management tasks. Source publication is not Windows deployment. Live validation pending.

Tests cover strict types, malformed/missing/unavailable responses, stale cloud evidence, zero judges, safe field projection and unchanged proxy restart eligibility. Do not stop the connector for testing during active judging.
