# Next Task

## Status: COMPLETE (Sat Nov 07 2026)
All four regression-test scenarios from the prior handoff were added to `tests/test_fileio.py` and pass. No product-code change. Full suite: 5929 passed, 50 skipped. Lint clean.

## Candidate (bounded, verify before coding)
None pending. The `write_text`/`write_json` error-handling regression tests are complete.

## Constraints
- Do not re-audit `--out`/`--init` routing (already covered).
- Do not weaken safety controls or turn this into an infrastructure project.