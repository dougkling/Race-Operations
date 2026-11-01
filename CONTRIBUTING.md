# Development and release policy

GitHub is the intended authoritative source after the standalone import is published. Owner: Doug Kling. The owner authorized temporary public publication and plans to make it private later. Use feature branches and PRs; merge only after relevant tests and review. Protect `main` against force pushes/deletion and require the `portable` and `powershell` checks once those checks have run. Configure this in GitHub settings; a policy document alone does not enforce protection.

Keep complete source, installers, configuration contracts, architecture, operations, validation, rollback and open items together. No production credentials, databases, logs or private backups. Do not copy the managed products' entire source into this repository.

Run `python tools/validate.py`, the Playwright suite for UI changes, and parse changed PowerShell on Windows. Tests must use mocks/synthetic credentials and never control production machines. Native Windows install/recovery/reboot and live email validation remain separate operator evidence.

Build packages with `python tools/build_packages.py --output dist` from the reviewed commit. Record source commit and SHA256 values. Version backend, cloud agent, DVR agent and UI separately where appropriate. Tag accepted releases immutably; do not overwrite tags/releases or fabricate historical versions. The `source-revision/*` tags are authenticated historical subtree snapshots, not newly certified deployed releases.

Keep incomplete work on a development branch and clearly mark deployment blockers. The existing AI-only reconnect draft must not be merged until its cross-project API, tests, rollback and installation path are complete. Existing `main` is the stable UI 0.9.2/backend 0.9.0 baseline with the documented installer correction.
