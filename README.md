# Race Operations

Windows management dashboard and outbound DVR monitoring agent for RaceBot, Commentator Desk and RaceDVR.

## Current source

| Part | Version | Purpose |
| --- | --- | --- |
| Cloud dashboard/backend/agent | 0.3.2 | Health reporting, shared RaceBot + Commentator recovery, independent DVR cloud proxy recovery |
| OBS/DVR agent | 0.3.3 | Judge Cues, Review Status, IIS and persistent read-only OBS connection/recording monitoring |

The DVR agent sends compatibility agentVersion 0.3.0 to the backend and records its own 0.3.3 package version in local status. Both are deliberate.

## Layout

- `cloud/`: backend, local cloud agent, dashboard, first-install and update scripts.
- `dvr/`: outbound-only agent, read-only OBS client, first-install and update scripts.
- `tests/`: portable backend/action/protocol tests.
- `docs/`: rollout history, deployment notes and verification status.

No third-party Python dependencies. Python 3.10+ is required. PowerShell deployment scripts target Windows and require Administrator execution. Linux tests cannot validate Windows Task Scheduler, ACLs or real application restarts.

## Existing deployments

On cloud PC, in `cloud/`:

```powershell
Unblock-File .\Update-Cloud.ps1
.\Update-Cloud.ps1
```

On OBS/DVR PC, in `dvr/`:

```powershell
Unblock-File .\Update-DVR-Agent.ps1
.\Update-DVR-Agent.ps1
```

These scripts use protected backups and preserve enrollment tokens, profiles, startup tasks and application settings. Cloud update requires the existing verified RaceBot, Commentator and proxy probes; it blocks pending actions. Read the update-specific documents before changing a host. Only management tasks restart during upgrades. No automatic application restart occurs during installation.

## First installation

Cloud `Install-Cloud.ps1 -PythonPath <full-machine-Python-path>` installs into C:\ProgramData\RaceOperations with loopback port 8799, two SYSTEM boot tasks and generated local credentials. It refuses existing deployments. Component probes and recovery features start disabled; component URLs, command boundaries and safeguards must be verified before enabling them. Existing installations should use Update-Cloud.ps1, not reinstall. Existing cloud deployments verified in this project use the PitWall bundled Python 3.13.16 executable.

DVR `Install-DVR-Agent.ps1` installs into C:\ProgramData\RaceOperationsDvrAgent and requires a cloud v0.3.0-compatible endpoint, C:\DVR, the Judge Cues task and a machine-wide Python. Current source adds direct OBS monitoring and requires obs_monitor.py beside dvr-agent.py. Enrollment uses the generated DVR token from cloud config, never the administrator token. The installer supports the owner's current exact HTTP cloud endpoint; other remote origins require HTTPS. Both new-install paths require live Windows verification; documented updates are the deployed path used so far.

## Networking and credentials

Backend remains bound to 127.0.0.1:8799. The deployed Windows host forwards port 80 to that listener using Windows portproxy/IP Helper. This network configuration is not provisioned or modified by the update scripts. The owner manages AWS security-group restrictions. The current HTTP transport provides no confidentiality; replacing it with authenticated TLS remains pending. The known deployment address appears in DVR installer/validation code and is not a credential; generalize it before deploying elsewhere.

Never commit installed config directories, bearer/admin tokens, OBS passwords, AWS credentials, state/audit databases, screenshots containing credentials or local backups. The OBS password is read locally from the protected Judge Cues configuration. Server serializes only allowlisted status fields. Generated configs belong on hosts, not in this source tree.

## Tests

```bash
python -m unittest discover -s tests -v
node --check cloud/web/app.js
```

Tests use temporary synthetic credentials and a local mock OBS server. Actual machine credentials are not needed. See docs/deployment-status.md for tested live behavior and outstanding validation.

## Repository and maintenance

Canonical repository: https://github.com/dougkling/DroneRaceTools, under `race-operations/`. This is the management dashboard/agent project only; application source remains in its own repositories. Use feature branches and pull requests for changes, run the portable tests, retain deployment instructions and report live-host verification separately from automated tests. Never sync installed credentials/state into Git. Pushing source does not automatically update either Windows machine.

No unattended production deployment is configured. Windows updates use the checked-in cloud/DVR update scripts after validation. No license has been selected for redistribution.
