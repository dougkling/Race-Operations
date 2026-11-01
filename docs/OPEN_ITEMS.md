# Open items and deployment limits

## Repository publication

- The owner created `dougkling/Race-Operations` and authorized temporary public publication on 2026-11-01. The owner plans to change visibility later.
- All 14 authentic source snapshots are imported on `feature/standalone-import`; source, documentation and CI are being published through a PR. Check the PR/Actions state for final merge and check results.
- The local Git handoff preserves 14 annotated `source-revision/*` tags. Remote tags and enforcement are pending: the connected API has no tag-creation or repository-administration operation.
- Enable `main` protection, require PRs and passing `portable`/`powershell` checks, prohibit force push/deletion; verify enforcement. Protect accepted release/source tags against changes. Policy documents alone do not enforce these settings.
- Do not relabel source recovery as historical release certification. Full Windows deployment acceptance remains separate from CI.
- Update the old DroneRaceTools landing page after the standalone PR is merged. Preserve its original history.

## Product work

- Finish/test/package the RaceBot AI-only reconnect draft; not in stable main.
- Implement scoring PC agent/status/controls. Placeholders remain grey.
- Add an actual authenticated DVR `/control` WebSocket health test if requested; HTTP reachability is not that test.
- AI/YouTube/Discord integration health, direct LiveTime/race tracking/Internet/S3 bucket monitoring remain absent.
- Add independent external monitoring for total cloud/backend failure.
- Generalize deployment-specific public S3 URL, task names, paths and the fixed PitWall updater prerequisites before supporting another installation.
- Replace the legacy HTTP management transport with verified TLS when the operator schedules it. Do not broaden the historical HTTP exception.
- Per-operator identities/roles and audit retention policy remain unfinished.

## Acceptance evidence still required

- Fresh Windows install and native PowerShell parser/execution; the new DVR installer origin/compatibility change is source-validated but not installed on a live host here.
- Exact deployed-folder hashes matched to the source commit; no current Windows host snapshot was available for this import.
- Reboot without RDP and OBS interactive-user recovery; full Windows rollback exercise.
- Live SES inbox delivery and complete outage/mute/recovery acceptance after the final source/package is installed.
- Current account/package status and licensing decision for redistribution.

These are separate from historical operator-reported successes. No code was deployed to a Windows production PC during repository preparation.
