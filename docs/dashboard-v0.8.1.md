# Dashboard UI 0.8.1

Uses the Commentator Desk source palette from dougkling/RaceBot `app/commentator.html`: charcoal #111719, slate #1a2225, warm gold #f0c36a, muted green #8dd4aa, Segoe UI and rounded panels. Compact monospace labels and service-level cards add a technical console appearance.

Desktop uses a cloud column and a wider DVR card grid. At 1100px host sections stack; at 600px service cards become one column, controls expand to full width and navigation stays touch-friendly. Long diagnostics and action IDs wrap. Expandable diagnostics retain their state through polling, and keyboard focus is restored. Status badges retain text labels in addition to color. The header no longer claims v0.4.0 or disabled DVR controls; UI and backend versions are separate.

Recovery permissions, command payloads, confirmation dialogs, recording guards and backend behavior are unchanged. Buttons live inside their service cards. RaceBot and Commentator keep their shared recovery control on the Commentator card. Summary counts use the same displayed evidence as the cards; stale agents show unknown. Sign-in expiry clears status and activity from view.

## Deployment

For an existing v0.8.0 cloud installation, extract `RaceOperations-Dashboard-Update-v0.8.1.zip`, run Administrator PowerShell in that folder, then:

```powershell
Unblock-File .\Update-Dashboard.ps1
.\Update-Dashboard.ps1
```

Update the cloud PC only. Refresh desktop with Ctrl+F5 and reload mobile. The updater verifies the backend and package hashes, backs up the two web files, replaces them atomically per file, and restores the backup on error. No agent or application restarts are required. `UI-MANIFEST.json` is included beside the updater; when using repository source, generate its SHA256 entries from `web/index.html` and `web/app.js` before invoking it.

## Validation

`node tests/test_dashboard_browser.js` (Playwright/Chromium) checks 1440, 768, 390 and 320px layouts, all 14 service cards, horizontal overflow including expanded diagnostics, disabled controls, confirmation requests, dialog sizing, polling state and session expiry. `node tests/test_connector_ui.js` checks the existing evidence helpers. No live recovery commands are sent by these checks.
