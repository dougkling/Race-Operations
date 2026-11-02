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

## GitHub publication checks

- The full imported historical source tree matches local Git tree `38741f50c2f604518e5a09f58a16d6b985f3873f`. The initial documentation/source PR tree matches `9b6cf45689b473f971dd67041983110ead854fb2`.
- Windows PowerShell parsing passed in GitHub Actions run 41332218697 on the initial import PR head. This validates syntax only, not deployment or recovery execution.
- Source-tag automation passed an isolated local Git-remote test: creation, repeat-run idempotence, and refusal to overwrite an existing tag.
- The portable/browser GitHub job is still pending at this documentation revision; consult the PR checks for its final result.

- Initial GitHub Python 3.10 validation exposed six Pilot Review failures caused by seven-digit .NET fractional timestamps. The parser now normalizes to six microsecond digits; the existing manifest/sample tests are rerun in CI. This is a compatibility fix, not a new live deployment.

## Final published-code validation

- [GitHub Actions run 41332357323](https://github.com/dougkling/Race-Operations/actions/runs/41332357323) passed both portable and powershell jobs on `507c81fd00f6847c2a50dc995ac945d61eea68c8`: 166 Python tests on Python 3.10, JS helpers/syntax, Chromium dashboard regression tests, package builds, and Windows PowerShell syntax parsing. This successful browser run supersedes the earlier local-environment limitation.
- PR #1 merged the tested source to main at `b8ce1b6104789bfd99b77b349519ae540c5f2e85`.
- Source snapshot tag creation succeeded in run 41332498951. Repository administration/branch protection could not be verified or changed with this integration (GitHub returned 403); enforcement remains an open item.
- These checks do not certify installation or live Windows recovery. No production service was changed.


## AI health and recovery v0.10.0

See [the AI monitor contract, installation, validation and rollback](ai-monitor-v0.10.0.md). This supersedes earlier statements that AI monitoring is absent. Actual Windows deployment and live email acceptance remain separate from automated source tests.

AI update verification in this change: RaceBot 242 offline unit tests passed; the Race Operations regression suite includes AI alert and scoped recovery tests. Chromium Headless Shell 134 passed desktop/mobile dashboard tests at 1440, 768, 390 and 320 pixels, including the AI map node and failure-only reconnect confirmation. Installer planning/apply/idempotency/rollback/concurrent-edit tests passed. PowerShell native execution and live Windows acceptance remain unrun locally.
