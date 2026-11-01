# Authentic source history

Fourteen original Race Operations subtree revisions were retrieved from `dougkling/DroneRaceTools` and imported in chronological order. Every source blob matched its original Git SHA-1 hash. Each import commit records the original SHA, author timestamp and message; import timestamps are current, not backdated.

The immutable `source-revision/*` tags identify authentic recovered source snapshots. They are not newly certified deployed releases. Original product versions are preserved in source/changelog; patches and UI-only changes remain distinct from full software packages. Earlier 0.1–0.3.1 artifacts are mentioned by the original changelog but are not fabricated as missing source commits.

| Original source commit | Original timestamp (UTC) | Change | Snapshot tag |
| --- | --- | --- | --- |
| [7bf5b8b2edc1](https://github.com/dougkling/DroneRaceTools/commit/7bf5b8b2edc1d9f6185a9c3349f1d73a66763fc8) | 2026-10-29T06:08:44Z | Add Race Operations cloud management and persistent DVR OBS monitoring | `source-revision/7bf5b8b2edc1` |
| [9a48024ae160](https://github.com/dougkling/DroneRaceTools/commit/9a48024ae160247d0393d898253bfb083777c565) | 2026-10-29T06:13:31Z | Monitor uploader task heartbeat and recent operations | `source-revision/9a48024ae160` |
| [e3052d437a41](https://github.com/dougkling/DroneRaceTools/commit/e3052d437a4116ac1f5ddfa8961de7599286f1d3) | 2026-10-29T06:27:21Z | Monitor cloud-observed DVR connector state in Race Operations v0.4.1 | `source-revision/e3052d437a41` |
| [abf6838e9605](https://github.com/dougkling/DroneRaceTools/commit/abf6838e96052c5eefa970e09d58fb5507c907ed) | 2026-10-29T16:28:40Z | Fix uploader local-time heartbeat age in DVR agent v0.4.2 | `source-revision/abf6838e9605` |
| [f282ca039726](https://github.com/dougkling/DroneRaceTools/commit/f282ca03972648557f70af0604e01b1e2525e7b2) | 2026-10-29T18:19:19Z | Add cloud and DVR disk capacity monitoring v0.5.0 | `source-revision/f282ca039726` |
| [26340547c0e5](https://github.com/dougkling/DroneRaceTools/commit/26340547c0e5c3740486980347c52970be166d41) | 2026-10-29T19:48:01Z | Observe DVR scheduled health reports in v0.6.0 | `source-revision/26340547c0e5` |
| [5ed501232183](https://github.com/dougkling/DroneRaceTools/commit/5ed501232183cbe8c4a909d4d0f0501ef9694da0) | 2026-10-29T20:54:19Z | Monitor public Pilot Review page manifest and video samples v0.7.0 | `source-revision/5ed501232183` |
| [2f71b6c3f267](https://github.com/dougkling/DroneRaceTools/commit/2f71b6c3f267e8445a71ad26c64b2c34048e2332) | 2026-10-30T01:45:01Z | Add guarded DVR recovery controls and recurring health reports | `source-revision/2f71b6c3f267` |
| [ad372881986d](https://github.com/dougkling/DroneRaceTools/commit/ad372881986dcab44a1b08e2ab077a73e2be8a93) | 2026-10-30T05:33:17Z | Restyle dashboard to match Commentator Desk and fix mobile layout | `source-revision/ad372881986d` |
| [c91e7bf7955f](https://github.com/dougkling/DroneRaceTools/commit/c91e7bf7955f27a5634feea7165032bafab06537) | 2026-10-30T05:37:13Z | Use explicit File.Replace backup path for Windows PowerShell | `source-revision/c91e7bf7955f` |
| [7189e66fd1f4](https://github.com/dougkling/DroneRaceTools/commit/7189e66fd1f461e3989bb6c5d07d139b78030869) | 2026-10-30T12:26:10Z | Add persistent monitor mutes and SES red incident notifications | `source-revision/7189e66fd1f4` |
| [80a26a336648](https://github.com/dougkling/DroneRaceTools/commit/80a26a336648efcd3e6f209190b6085d29c0db7a) | 2026-10-31T01:31:26Z | Restyle dashboard as host-scoped NOC service racks with inline mute switches | `source-revision/80a26a336648` |
| [079cb01b7515](https://github.com/dougkling/DroneRaceTools/commit/079cb01b7515dbb35aaef9bb63fcbfb0e3356d41) | 2026-10-31T01:31:53Z | Reserve separate greyed scoring PC integration section | `source-revision/079cb01b7515` |
| [bceae031a842](https://github.com/dougkling/DroneRaceTools/commit/bceae031a8428c77b5c4d045b932ab643df25065) | 2026-10-31T01:48:48Z | Add live topology map with monitor navigation and saved collapse (UI 0.9.2) | `source-revision/bceae031a842` |

`SOURCE_HISTORY.json` records the original-to-import commit mapping. Main continues from the final recovered revision with standalone documentation and the explicitly listed installer correction. Source provenance does not establish current production file parity; no live-host export was supplied during this import.

## Remote import mapping

The JSON record maps original commits to both local bundle commits and new GitHub import commits. Parent history and import timestamps differ, while the source file blobs are identical. Annotated source-revision tags now exist in GitHub, created by the successful source-tags workflow. The earlier handoff bundle retains its original local import tags.
