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
