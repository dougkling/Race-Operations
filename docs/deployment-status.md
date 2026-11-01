# Deployment status

## Verified by the operator

- Cloud backend/agent installed; cloud UI login and UTF-8 fix verified.
- RaceBot and Commentator HTTP checks verified green.
- Cloud DVR proxy task identified: root task `Race DVR Judge Proxy`; health http://127.0.0.1:8767/health, version 1.0.2 at discovery.
- Shared RaceBot + Commentator manager stop/restart/recovery tested end to end.
- Independent cloud proxy stop/restart/recovery tested end to end.
- Windows port-80 forwarding and external dashboard access verified.
- Cloud management SYSTEM boot triggers and recovery settings applied; external availability after reboot without RDP login verified.
- DVR agent 0.3.1 installed; first three health checks reported green.
- OBS process/listener identified; Judge Cues reports OBS connected, but integration.recording is absent.
- Local OBS settings identified at unification.obs.{enabled,url,password} in Judge Cues config.

## Fix delivered, live verification pending

DVR 0.3.2 deliberately closed its OBS session after every poll, causing repeated connect/disconnect notifications. DVR 0.3.3 replaces that with a persistent authenticated connection and dedicated poll worker with reconnect backoff. Automated persistence tests passed. Operator has not yet supplied the v0.3.3 installation and stability result. Do not describe this fix as verified on the live host yet.

## Uploader monitoring source 0.4.0

Operator observed task Running and UTC heartbeats approximately 6–10 minutes apart in uploader-2026-10-27.log, still actively written October 29. Source now reads exact task state, picks the most recently modified uploader log and applies a 900-second warning threshold. Automated checks passed; live 0.4.0 deployment is pending. No uploader control action exists.

## Pending

- Verify stable OBS connection and Idle/Recording/Unknown behavior after v0.3.3 update.
- Verify DVR agent startup after reboot without interfering with recording operations.
- Deploy and verify uploader task/heartbeat/recent-operation checks; then add backlog/object/manifest-lag verification and guarded recovery.
- Add Cloud Connector, disk/network, Pilot Review, scoring and health-monitor checks.
- Reconcile OBS state with authoritative Judge Cues recording ownership before enabling Judge Cues restart.
- Add safe DVR component actions, per-operator identities/roles and audit retention.
- Improve HTTP reachability checks to component/integration health.
- Resolve cloud disk capacity (2.1 GB free was reported during initial discovery; no later reading is available).
- Replace current HTTP transport when ready.

## Fixed restart targets

RaceBot + Commentator use C:\Program Files\PitWall\manager\PitWall.ps1 -Command restart, grouped by operator approval. Cloud proxy uses only its exact scheduled task. No host reboot action or generic shell endpoint exists. DVR agent currently supports no actions; no OBS/recording control requests exist in its monitoring client.

## Connector source 0.4.1

Operator verified proxy 1.0.2 reports dvrConnected=true and remoteJudges=0. Cloud deployment was last observed at 0.3.2. Cloud-only 0.4.1 source adds proxy-observed connector state using the existing health poll; no heartbeat-age claim or connector restart action. Windows rollout pending.

## Live rollout and uploader time correction

Operator installed cloud 0.4.1 and DVR 0.4.0 successfully; heartbeat accepted. Screenshot confirms connector Healthy with zero judges, OBS connected/idle, and other enabled HTTP checks Healthy. Uploader showed 243 minutes despite a recent local log write. Local/UTC comparison confirms local wall time mislabeled Z. DVR 0.4.2 source corrects parsing; live fix verification pending.

## Disk monitoring v0.5.0

Operator verified uploader v0.4.2 now green. Cloud C: expanded to 99 GiB / 72.4 free (73.2%); DVR C: 231.8 GiB / 67.9 free (29.3%). Recording path confirmed C:/DVR. Disk capacity source added for both hosts; Windows deployment pending. Network monitoring remains pending separately.

## Health-check observation v0.6.0

Disk monitoring v0.5.0 verified by operator. Existing health checker and wrapper succeeded interactively; SYSTEM task rerun returned 0 with fresh log. Source now observes task/report without altering schedule or executing checks. Expected current result: warnings, not application outage. Live v0.6.0 rollout pending.

## Pilot Review v0.7.0

Operator verified page and BOM-prefixed manifest HTTP 200; schema fields version/generatedAt/races. Current and archived sample HEAD responses are video/mp4 and exactly match manifest sizes. Source now monitors these from DVR background worker. Live v0.7.0 rollout pending. Health report v0.6.0 verified fresh with 24 passes, 2 warnings; installed checker version default manually changed to 1.7.14 by operator (not part of management-agent source).

## DVR controls v0.8.0

Operator confirmed the health report refreshed and cleared the arm warning after a scheduled run; the task previously had only a boot trigger. Operator added a five-minute repeat successfully. v0.8.0 codifies that schedule, marks reports stale after 15 minutes and adds DVR recovery controls. Prior monitoring-only statements describe earlier releases. Scoring PC unavailable: monitoring/control deferred. New Windows control execution is not yet live-verified; see `dvr-controls-v0.8.0.md` for rollout and limits.
