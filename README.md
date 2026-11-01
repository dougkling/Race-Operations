# Race Operations

Windows operations dashboard for RaceBot, Commentator Desk and the Race DVR PC: live health, clickable topology, per-monitor email muting, SES alerts and operator-confirmed recovery.

Standalone repository: **dougkling/Race-Operations**. Public temporarily at the owner's request; the owner plans to make it private later. Extracted from `dougkling/DroneRaceTools/race-operations`, preserving authentic source revisions. See [publication/open items](docs/OPEN_ITEMS.md).

| Component | Version | Host |
| --- | --- | --- |
| NOC dashboard and live map | 0.9.2 | Cloud PC; desktop/mobile browser |
| Backend and SES alerts | 0.9.0 | Cloud Windows PC |
| Cloud agent | 0.7.0 | Cloud Windows PC |
| DVR monitoring/recovery agent | 0.8.0 | OBS / DVR PC |
| Scoring PC | Pending | Grey placeholders only |

Versions are intentionally independent. This import adds documentation, source history, packaging and a DVR installer compatibility correction; it is not evidence of a new production deployment.

## Documentation

- [Full installation](docs/INSTALLATION.md): prerequisites, cloud bootstrap, probes, network access, DVR enrollment, recovery and SES.
- [Upgrade and rollback](docs/UPGRADE_ROLLBACK.md).
- [Configuration and integration contracts](docs/CONFIGURATION.md).
- [Architecture](docs/ARCHITECTURE.md) and [operations runbook](docs/OPERATIONS.md).
- [AI handoff](docs/AI_HANDOFF.md), [verification](docs/VERIFICATION.md), [open items](docs/OPEN_ITEMS.md), [source history](docs/SOURCE_HISTORY.md) and [changelog](CHANGELOG.md).

## Existing deployment: map/UI update

On the **cloud PC**, with backend v0.9.0 already installed, open Administrator PowerShell in `cloud`:

```powershell
Get-ChildItem -Recurse -File | Unblock-File
.\Update-Dashboard.ps1
```

Reload desktop with Ctrl+F5 and reload mobile. This updater replaces only the web files. Read the upgrade guide for backend/DVR changes; never use a fresh installer over an existing deployment.

## Development

Production runtime: Python 3.10+ standard library, Windows PowerShell 5.1 and Administrator rights for deployment. Node/Playwright are test-only dependencies.

```bash
python tools/validate.py
npm ci --ignore-scripts
npx playwright install chromium
python tools/validate.py --browser
python tools/build_packages.py --output dist
```

Tests use synthetic credentials, mocks and local test servers. They do not restart production applications or send real email. Native Task Scheduler, ACLs, OBS desktop launch and live SES delivery require operator acceptance.

## Operational boundaries

RaceBot and Commentator share a restart group. The cloud proxy and verified DVR services have separate recovery actions. Commands require authentication, CSRF, explicit confirmation, current evidence and action-specific guards. Execution journals prevent replay. OBS recovery requires known idle recording state and a verified interactive desktop launch.

The map uses the same 15 monitors as the rows below. It does not test each drawn connection. DVR Control Server is the display name for `judge-cues`; HTTP health does not test the Stream Deck `/control` WebSocket. Scoring, direct Internet/LiveTime/race-tracking/S3 bucket monitoring and AI-only reconnect are unfinished.

Keep production tokens, SMTP/OBS credentials, databases, logs and backups outside Git. New remote deployments require TLS; the exact existing HTTP deployment remains an explicit compatibility exception. No redistribution license has been selected.
