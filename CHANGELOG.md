# Publication compatibility correction — 2026-11-01

- Normalize .NET seven-digit manifest timestamps to microseconds before parsing, fixing Pilot Review on the documented Python 3.10 minimum. Existing sample/age tests cover the production timestamp format.

# Changelog

## Standalone repository preparation — 2026-11-01

- Preserved 14 authentic source revisions with original hashes and provenance.
- Added complete installation, configuration, architecture, operations, upgrade/rollback, AI handoff, verification and open-item guides.
- Added development validation, CI definition and deterministic package builder.
- DVR first installer now accepts backend 0.9.0 and requires an explicit server origin; the exact legacy HTTP exception requires opt-in.
- AI-only reconnect remains isolated unfinished development work. No production deployment is claimed.

## Dashboard UI 0.9.2

Live topology with 15 monitored nodes, exact monitor links, saved collapse, recording/disk/mute evidence and mobile PC navigation.

## Dashboard UI 0.9.1

Distinct NOC host sections, inline mute switches, DVR Control Server display name and separate grey Scoring PC section.

## Cloud alerts 0.9.0

Persistent per-monitor mute preferences and SES red-incident notifications.

## Monitoring 0.4.1–0.7.0

0.4.1 cloud proxy-observed connector evidence; 0.4.2 uploader local-time correction; 0.5.0 cloud/DVR capacity; 0.6.0 health-report observation; 0.7.0 public Pilot Review page/manifest/sample checks. Exact source revisions are in docs/SOURCE_HISTORY.md.


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


## 0.10.0 — 2026-11-02

Added independent RaceBot AI monitoring, real request failures, five-minute active probes, failure-only AI reconnect, AI-aware shared restart, existing SES alert integration, a clickable AI map/row, and a transactional cross-project updater with rollback. API credentials remain inside RaceBot. Automated tests do not establish native Windows/live provider/SES acceptance.
