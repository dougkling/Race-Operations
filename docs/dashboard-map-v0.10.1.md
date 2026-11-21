# Race Operations Dashboard Map v0.10.1

Dashboard-only update for the existing Cloud PC installation, backend v0.9.0 or v0.10.0.

## Install

1. Extract the ZIP on the Cloud Windows PC.
2. Open Administrator PowerShell in the extracted folder containing Update-Dashboard.ps1.
3. Run:

```powershell
Get-ChildItem -Recurse -File | Unblock-File
.\Update-Dashboard.ps1
```

Refresh desktop with Ctrl+F5 and reload the phone browser. No service restart is needed. No DVR PC update is required. The updater verifies the UI file hashes and backs up the installed web files before replacing them. Backend configuration, credentials, alerts, recordings and recovery controls are preserved.

## Changes and acceptance

The map fits the phone width. Expand map opens a full-screen live viewer with pinch zoom, drag, zoom buttons and Fit. Close/Escape returns to the overview; tap a live indicator to open its exact monitor section. All 16 live monitors retain their evidence and mute state; Scoring remains grey. Normal page scrolling works outside the expanded map.

Browser CI passed at 320, 390, 768 and 1440 pixels, including pinch/drag input, focus, refresh and link behavior. Portable validation passed (188 tests, six platform skips); Windows PowerShell syntax checks passed for the preceding UI commit. Live installation and physical phone acceptance remain operator checks.

## Rollback

The updater prints its backup folder beneath C:\ProgramData\RaceOperations\backups, named dashboard-before-v0.10.1-TIMESTAMP. To restore, substitute the exact printed path:

```powershell
$backup = 'C:\ProgramData\RaceOperations\backups\dashboard-before-v0.10.1-TIMESTAMP'
Copy-Item "$backup\index.html", "$backup\app.js" 'C:\ProgramData\RaceOperations\web' -Force
```

Refresh both browsers. The updater also restores the backup automatically if file replacement fails. BUILD.json records source revision and per-file SHA256 hashes.
