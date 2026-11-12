# Next Task

## Status
Session 109 fixed a reproducible README documentation regression in the "Usage" error-handling examples (malformed/misordered CLI examples). Verified: `python -m ethscan scan --target 127.0.0.1 --ports "abc"` → exit 2 with `Invalid port number 'abc'`; `python -m ethscan cidr --cidr bogus` → exit 2 with expected CIDR error; `python -m ruff check ethscan/ tests/` clean; `python -m mypy ethscan/ tests/` clean (188 source files). Full pytest suite not rerun this session (README-only change).

## One precise next task
Run full baseline verification and record results: `python -m pytest -q`, `python -m ruff check ethscan/ tests/`, `python -m mypy ethscan/ tests/`. If all green, audit remaining README CLI error/output examples against live command behavior and correct any evidenced mismatches with minimal edits (do not speculate).

## Notes
- Keep oracle/postgresql empty-target in-band contract (exit 0) distinct from commands that reject with usage error exit 2.
- Do not weaken safety/validation checks or tests to force green.