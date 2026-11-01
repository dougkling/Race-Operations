# Dashboard live map v0.9.2

Adds the Race Operations topology drawing above the monitor sections, using an interactive SVG that scales on desktop and scrolls within its own panel on phones. Phone views open on the DVR and offer buttons to bring Cloud PC, DVR PC, Scoring PC or S3 into view. Scoring PC stays above DVR PC, Cloud PC stays on the right, and S3, Stream Deck, Internet and LiveTime retain their connections and port labels.

The map includes all 15 current live monitors: five Cloud PC monitors and ten DVR monitors, including Pilot Review in the S3 area. Its colors use the same evidence as the monitor rows. OBS shows recording state, disks show free percentage, and muted monitors retain their health color with a MUTED label. A missing or stale agent makes its component evidence unknown; the Cloud Connector still uses the fresh cloud proxy report independently of the DVR agent.

Selecting a live node scrolls to, highlights and focuses its exact monitor row, opening its details. Links support keyboard activation. Collapse map keeps a live status summary visible and remembers the setting in that browser. Polls preserve map focus, scroll position and the collapse setting. A backend error or expired session hides the map along with the service rows.

Scoring PC components remain grey pending setup and link to the grey placeholders below. Race tracking, Internet, LiveTime and the S3 bucket have no direct monitors and are labeled accordingly. Pilot Review reflects the DVR page/manifest/video checks. DVR Control Server still checks the service's HTTP health endpoint; it does not test the /control WebSocket. Connections and ports reproduce the topology drawing; they are not separate live connectivity tests. No new probes are introduced.

## Install on the cloud PC

Requires the v0.9.0 cloud backend. Extract `RaceOperations-Dashboard-Map-v0.9.2.zip`, open Administrator PowerShell in the extracted directory containing `Update-Dashboard.ps1`, then run:

```powershell
Get-ChildItem -Recurse -File | Unblock-File
.\Update-Dashboard.ps1
```

Refresh desktop with Ctrl+F5 and reload mobile. The updater verifies SHA256 hashes, backs up and replaces `web/index.html` and `web/app.js`, and restores them if replacement fails. No backend, agent or application restart is required. Existing alerts, credentials, mute preferences and recovery safeguards are retained. The package does not change the DVR PC.

## Validation

Chromium browser tests use synthetic status at widths 1440, 768, 390 and 320 pixels. They cover all 15 map links and status mappings, keyboard navigation, saved collapse across reloads, recording and disk labels, muted/offline/unknown states, independent connector evidence, focus and map-scroll persistence, contained mobile overflow, recovery confirmation, backend errors and session expiry. The existing connector-evidence checks pass. No live Windows commands, recovery actions or emails are executed by the tests. Installation and live polling still need the operator's cloud-PC verification.
