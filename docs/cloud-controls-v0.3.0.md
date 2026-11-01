# Race Operations update v0.3.0

Adds an independent **Restart DVR cloud proxy** button to the existing v0.2.0 Windows cloud deployment. The working RaceBot + Commentator group is preserved. Tokens, probes, port-80 forwarding, firewall settings and task definitions are preserved.

## Install

Extract on the cloud PC. In Administrator PowerShell, from the directory containing Update-Cloud.ps1:

```
Unblock-File .\Update-Cloud.ps1
.\Update-Cloud.ps1
```

Only the management backend/agent restart during the update. No application restart occurs. The updater requires the verified root task `Race DVR Judge Proxy` and the enabled HTTP health profile at http://127.0.0.1:8767/health with requireOk=true. Pending recovery jobs block the update. Existing management files/configs and action database are backed up in the protected installation folder. Existing job history migrates to include target identity. Failed backend startup restores the prior management files/configs/database. Actual Windows update/rollback and proxy restart require live verification.

Refresh http://98.84.103.79/ with Ctrl+F5 and sign in again. /health should report version 0.3.0. The proxy control is disabled while proxy health is green. Its availability does not depend on RaceBot/Commentator health, but management permits only one pending restart at a time. Each target has a 120-second cooldown.

## Proxy recovery behavior

The confirmation explains remote judge sessions will temporarily disconnect. Operator must verify no critical judging transaction is in progress. There is no automated transaction-state check in this release. The cloud agent performs a fresh health check; Unknown, disabled or already healthy targets are not restarted. The action stops only the root Scheduled Task named `Race DVR Judge Proxy`, waits up to 15 seconds for its task state to leave Running, then starts that exact task. No process killing, shared-host reboot, or changes to RaceBot/Commentator occur.

Success requires HTTP health with ok=true within 60 seconds. It does not prove the DVR connector or all judges have reconnected. Inspect remote judge readiness separately after recovery. The UI names the action in its activity history.

Existing protections are retained: administrator session, CSRF token, explicit confirmation, fixed server/agent action allowlists, durable request IDs, no automatic replay, persistent audit database and retrying result reports. Uncertain dispatched actions deliberately block new recovery until investigated. HTTP transport remains as configured by the owner; this update does not alter remote network access or add encryption. Local DVR controls remain disabled.

## Controlled test

When no remote judging is active, on the cloud PC:

```
Stop-ScheduledTask -TaskName 'Race DVR Judge Proxy' -TaskPath '\'
```

Wait around 15 seconds for proxy red. Use the dashboard's independent proxy restart button and confirm. Expect succeeded / proxy_health_passed and green health. RaceBot/Commentator should remain green. If recovery fails, manual fallback:

```
Start-ScheduledTask -TaskName 'Race DVR Judge Proxy' -TaskPath '\'
```

Use Task Scheduler/logs for diagnostics. Do not stop a proxy needed by active judges solely to test. Automatic task recovery may restore health before you click; the agent correctly skips a restart if the target is already healthy.

## Validation

Portable tests exercise both action targets, migration of v0.2.0 audit history, authentication/CSRF, freshness/Unknown guards, independent eligibility, duplicate handling, agent crash behavior, fixed task command selection and mocked recovery. Python tests and JavaScript syntax checks run before packaging. PowerShell and Windows task execution cannot be validated in the Linux build environment.
