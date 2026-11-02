# Open items and deployment limits

## Repository publication

- The owner created `dougkling/Race-Operations` and authorized temporary public publication on 2026-11-01. The owner plans to change visibility later.
- Source, full documentation and CI are published on main through [PR #1](https://github.com/dougkling/Race-Operations/pull/1), merged at `b8ce1b6104789bfd99b77b349519ae540c5f2e85`. All 14 authentic source snapshots are preserved.
- The source-tags workflow successfully created the 14 annotated remote source-revision tags (run 41332498951). It refuses to overwrite existing tags. Repository-level tag/branch protection still requires administration access.
- Enable `main` protection, require PRs and passing `portable`/`powershell` checks, prohibit force push/deletion; verify enforcement. Protect accepted release/source tags against changes. Policy documents alone do not enforce these settings.
- Do not relabel source recovery as historical release certification. Full Windows deployment acceptance remains separate from CI.
- The old DroneRaceTools landing page now links here through merged PR #14; its original source and history remain intact.

## Product work

- Accept the v0.10.0 AI monitor/reconnect updater on the live Windows server and verify the configured SES inbox. See ai-monitor-v0.10.0.md.
- Implement scoring PC agent/status/controls. Placeholders remain grey.
- Add an actual authenticated DVR `/control` WebSocket health test if requested; HTTP reachability is not that test.
- YouTube/Discord and Commentator research integration health, direct LiveTime/race tracking/Internet/S3 bucket monitoring remain absent.
- Add independent external monitoring for total cloud/backend failure.
- Generalize deployment-specific public S3 URL, task names, paths and the fixed PitWall updater prerequisites before supporting another installation.
- Replace the legacy HTTP management transport with verified TLS when the operator schedules it. Do not broaden the historical HTTP exception.
- Per-operator identities/roles and audit retention policy remain unfinished.

## Acceptance evidence still required

- Fresh Windows install and native PowerShell execution (Windows syntax parsing passed CI); the new DVR installer origin/compatibility change is source-validated but not installed on a live host here.
- Exact deployed-folder hashes matched to the source commit; no current Windows host snapshot was available for this import.
- Reboot without RDP and OBS interactive-user recovery; full Windows rollback exercise.
- Live SES inbox delivery and complete outage/mute/recovery acceptance after the final source/package is installed.
- Current account/package status and licensing decision for redistribution.

These are separate from historical operator-reported successes. No code was deployed to a Windows production PC during repository preparation.
