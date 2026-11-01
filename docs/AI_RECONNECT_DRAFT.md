# Unfinished RaceBot AI reconnect draft

This development branch preserves interrupted work. Do not deploy it. Stable main contains none of these runtime changes.

The cloud adapter, backend action and RaceBot patch helper are incomplete as a product: dashboard controls, tests, supported installer, rollback and coordinated RaceBot publication are still required. Existing portable tests have not been certified against this branch. Python compilation only checks syntax.

The RaceBot app itself belongs in its own repository. `racebot/patch_racebot.py` describes the proposed narrow app integration; it must be reviewed against the exact deployed source before use. See AI_HANDOFF.md and OPEN_ITEMS.md.
