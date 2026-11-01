# Public Pilot Review monitoring v0.7.0

Verified public base: https://race-dvr-public.s3.us-east-1.amazonaws.com/pilot-review/. Page and manifest returned 200. Manifest UTF-8 BOM EF BB BF is supported via utf-8-sig; schema version 1.7.1 is independent of Judge Cues version. 339 races observed, generatedAt 2026-10-29T06:25:31.1251720Z. Current sample HEAD: video/mp4, 93918 bytes; archived: video/mp4, 425849932 bytes; both match manifest.

DVR background worker probes immediately and then every five minutes. Agent heartbeats do not wait on the worker. HTTP timeout five seconds per request, page max 1 MiB, manifest max 4 MiB, max 20000 entries. Evidence older than ten minutes becomes Unknown. All requests use fixed public origin, no credentials/environment proxy, no redirects, and cache-busting query. Sample URLs must be relative MP4 paths under pilot-review/races and agree with the manifest object key. No video body is requested: HEAD only, matching Content-Type and Content-Length.

Checks page HTML, BOM-aware JSON/schema, one current and one archived entry when present. Empty categories display No entries. Old manifests are not unhealthy solely for age because publishing may be idle. Future timestamps warn. It does not prove playback, validate every video, confirm newest expected publication, or calculate upload backlog/manifest lag. Fields sent are booleans, counts, ages, safe reason enums and sample pass/fail only, not names/aliases/URLs.

## Deployment

Extract cloud v0.7.0 ZIP and run Administrator PowerShell Unblock-File .\Update-Cloud.ps1 then .\Update-Cloud.ps1. Then DVR v0.7.0 ZIP: Unblock-File .\Update-DVR-Agent.ps1 then .\Update-DVR-Agent.ps1. Refresh Ctrl+F5; allow about 30 seconds for the initial background check. Cloud compatibility and prior disk/OBS/uploader/health-report fixes retained. Only management tasks restart; no application changes. Live Windows rollout pending.
