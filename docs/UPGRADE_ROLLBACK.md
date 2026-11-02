# Upgrade and rollback

## Choose the correct path

| Change | Host / command | Management restart | Application impact |
| --- | --- | --- | --- |
| Dashboard/map only, backend already 0.9.0 | Cloud `cloud\Update-Dashboard.ps1` | None | Web files only |
| Add/update alerts from backend 0.8.0/0.9.0 | Cloud `cloud\Update-Alerts.ps1` | Backend | No application restart |
| Full cloud management update | Cloud `cloud\Update-Cloud.ps1` | Backend and cloud agent | Does not restart RaceBot/Commentator/proxy |
| DVR agent/recovery discovery | DVR `dvr\Update-DVR-Agent.ps1` | DVR agent | Updates management/recovery task definitions; no application restart |

Use Administrator PowerShell, extract the complete matching package and unblock files. Keep source/package hashes and read the release-specific notes. Do not mix files from different versions. The dashboard installer verifies `UI-MANIFEST.json`; build it from the reviewed source using `tools/build_packages.py` if modifying UI files.

Before updating, confirm no pending recovery action. The scripts refuse pending jobs where supported. Keep installed configs, databases and private backups outside Git. Full cloud updater has fixed PitWall Python/manager/proxy prerequisites. Older first-install scripts are not upgrade tools.

## Backup locations and automatic rollback

Cloud backups are under `C:\ProgramData\RaceOperations\backups`; DVR backups under `C:\ProgramData\RaceOperationsDvrAgent\backups`. They inherit protected installation access. Treat them as sensitive: some include config tokens, SMTP information or databases.

Dashboard replacement backs up both web files and uses a non-null replacement-backup path for Windows PowerShell compatibility. On failure, it restores both files. The full cloud and DVR scripts back up the relevant modules/configs and restore them on failed startup/enrollment. DVR recovery also saves/restores affected task XML. Alerts update retains its backward-compatible SQLite additions to preserve incident evidence.

Rollback paths have not been exercised here on a fresh Windows VM. Always verify the actual error, task states and startup health; automatic rollback output is not proof the applications recovered.

## Manual rollback

1. Record the failed version, error and selected backup path. Check whether the script already restored it.
2. Stop only the affected Race Operations management task(s), and verify they have actually stopped before replacing files. Do not kill RaceBot/OBS processes as a management rollback shortcut.
3. Restore the exact files recorded in the relevant updater's backup list. Preserve owner/ACLs and use the matching config version. For a UI rollback, restore only `index.html`/`app.js` to the cloud `web` directory.
4. For DVR changes, restore the saved health-check/OBS-recovery task XML if task definitions changed. Do not replace application task identities with guessed names.
5. Restart management tasks, check `/health`, fresh cloud/DVR heartbeat and dashboard versions. Recheck OBS recording truth and connector state.
6. Reload the browser with Ctrl+F5 and sign in if the backend restarted.

Do **not** casually overwrite action/alert databases from an old backup: this can lose audit evidence, mute preferences and incident deduplication. If a database restore is unavoidable, keep agents stopped, preserve the current files, inspect queued/dispatched/running jobs, and reconcile possibly executed commands before restarting. An indeterminate action must never be blindly replayed.

## Git workflow

Use a feature branch, relevant automated checks, a reviewed PR and an immutable release tag. Package the exact reviewed commit. Never force-push `main` or move old release/source-revision tags. Existing historical ZIPs and incomplete drafts are not automatically full deployable releases. GitHub publication does not deploy either Windows PC.


## AI health and recovery v0.10.0

See [the AI monitor contract, installation, validation and rollback](ai-monitor-v0.10.0.md). This supersedes earlier statements that AI monitoring is absent. Actual Windows deployment and live email acceptance remain separate from automated source tests.
