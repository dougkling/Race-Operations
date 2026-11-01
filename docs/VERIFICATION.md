# Verification record — 2026-11-01

## Current checks

- Stable source extracted from the published Race Operations subtree through UI 0.9.2. All 148 unique blobs across 14 historical source revisions verified against their original Git SHA-1 blob hashes.
- Python portable suite: **166 tests passed**, `python3 -m unittest discover -s tests -v`, 47.781 seconds, Linux. Synthetic credentials/local mocks only.
- `node --check cloud/web/app.js`: passed.
- `node tests/test_connector_ui.js`: connector evidence, disk display, health-report display and Pilot Review display checks passed.
- Historical UI 0.9.2 Chromium test run passed at 1440, 768, 390 and 320px: all 15 links/status mappings, keyboard activation, collapse persistence, phone PC selectors, mute/recording/stale states, scroll/focus persistence, recovery confirmation and session expiry. UI source bytes were unchanged for this standalone import.
- A fresh browser rerun initially could not launch because the runtime's Chromium executable was missing; the normal browser download failed. This is a test-environment limitation, not a recorded test pass. Any subsequent successful rerun must be recorded explicitly below.

## Not certified by these checks

No production host was accessed. Native Windows Task Scheduler, PowerShell execution, ACLs, DPAPI, OBS desktop recovery, fresh installation, real SES/network behavior and rollback are not certified by Linux mocks. The GitHub CI definition includes a Windows PowerShell parse job; a checked-in workflow is not proof it ran. Installed-code parity requires actual host hashes.

The DVR first installer was corrected to accept backend v0.9.0 and take an explicit server origin, preserving the one historical HTTP exception behind an explicit switch. This change still requires Windows acceptance. Stable backend/agent/UI runtime behavior is otherwise unchanged.

See OPEN_ITEMS.md for publication, native validation and product gaps. Do not mark AI-only reconnect as verified: it is incomplete development-branch work.

## Standalone preparation checks

- Local documentation links, Git whitespace checks, UI manifest hashes, identical action catalogs and tracked-source credential patterns passed.
- A fallback headless Chromium package also could not initialize in this environment (`EINVAL` during font extraction). Fresh browser validation remains pending; this does not supersede the historical UI test result.
- Package ZIP integrity and repeat-build hashes are checked during handoff packaging; BUILD.json records the exact source commit and whether tracked changes were present.
