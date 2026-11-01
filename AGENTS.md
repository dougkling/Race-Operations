# Maintainer instructions

- Read README, docs/AI_HANDOFF.md, docs/OPEN_ITEMS.md and CONTRIBUTING.md before edits.
- Preserve independent Cloud, DVR and Scoring host identities. Never turn unknown evidence into green.
- Fixed action catalog only; retain CSRF, exact confirmation, host scoping, capability checks, recording guards, cooldown, persistent at-most-once execution and audit evidence.
- Do not alter production settings or invoke recovery while testing. No real secrets or emails in tests.
- Do not confuse HTTP reachability with AI, chat, WebSocket or end-to-end integration readiness.
- Preserve tokens, OBS/scoring authority, recordings and private databases during upgrades. Keep sensitive state outside Git.
- Use feature branches, relevant validation and reviewed PRs. Update installation, verification, rollback and open-items docs when behavior changes.
- Preserve authentic history and immutable tags; do not invent past releases or claim unrun Windows/live tests.
