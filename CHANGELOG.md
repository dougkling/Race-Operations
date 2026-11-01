# Changelog

## Cloud/DVR 0.4.0

- Read-only uploader task-state, UTC heartbeat age and recent-operation evidence.
- Fifteen-minute heartbeat warning based on observed 6–10 minute cadence; no calendar-filename rollover assumption.
- Bounded log tails and allowlisted telemetry, without raw logs or credentials.
- Preserve persistent OBS monitor and existing cloud recovery actions.
- Uploader restart and S3 backlog/object verification remain pending.

## DVR 0.3.3

- Retain one authenticated OBS WebSocket session across status reads.
- Dedicated read-only poll worker; cloud heartbeat delays do not force connection churn.
- Reconnect backoff and stale sample protection.
- Failed updater restores monitoring files but leaves a faulty monitor disabled.

## Cloud/DVR OBS monitoring 0.3.2

- Direct GetRecordStatus monitoring with local credential lookup.
- Project explicit booleans/duration to dashboard; missing recording state remains Unknown.
- Maintain tested cloud controls and compatible heartbeat handling.

## DVR 0.3.1

- Outbound monitoring agent, protected enrollment and SYSTEM boot task.
- Judge Cues, Review Status and IIS checks.

## Cloud 0.3.0

- Independent scheduled-task restart for DVR cloud proxy.
- Target-specific activity, cooldown and audit migration.

## Cloud 0.2.0

- Shared RaceBot + Commentator restart with confirmation, CSRF, fixed command and recovery verification.
- Durable at-most-once dispatch and result/audit storage.

## Wireframe 0.1.0

- Cloud dashboard, token sign-in, host-scoped heartbeats and disabled component inventory.
- Explicit UTF-8 file reads fixed Windows script serving.

## 0.8.0

DVR recovery: Judge Cues, Review Status, IIS, uploader, discovered connector, and verified interactive OBS launch. Adds on-demand health-check execution, five-minute scheduling, 15-minute report freshness, per-host action routing, persistent deduplication, and recording guards. Windows rollout remains operator-verified.

## Dashboard UI 0.8.1

Commentator Desk charcoal/gold styling, responsive service cards, adjacent recovery controls, collapsible diagnostics, status overview and readable activity cards. Cloud web files only; backend and DVR agent remain 0.8.0.
