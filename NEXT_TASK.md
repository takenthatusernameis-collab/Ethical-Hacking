# Next Task
Date: Mon Nov 16 2026

## Status
- Repository is green: full suite `python3 -m pytest -q` -> **32168 passed, 146 skipped, 0 failed**
  (previously 32159 passed; +9 new tests, no failures).
- The assigned task (surface HTTP status in `ethscan/headers.py`) is complete.

## What changed this session
- `ethscan/headers.py`:
  - `run_headers` sets `results["status"]` from `getattr(fetched, "status", None)`
    when not `None` (mirrors `ethscan/web.py:373-375`).
  - `format_headers_report_markdown` renders `- **Status:** <code>` when present.
  - `format_headers_report_csv` renders a `status,<code>` row when present
    (JSON is automatic).
- `tests/test_headers.py`: 9 new regression tests (success / HTTPError / transport
  failure / plain-dict; Markdown/CSV/JSON render and omit-when-None).

## What was verified
- `pytest tests/test_headers.py tests/test_web.py tests/test_cli.py -q` -> 1247 passed.
- `python3 check_readme.py` -> 54 commands, 0 drift.
- `mypy` + `ruff` on touched files -> clean.
- End-to-end render check -> status 200 in dict, Markdown, and CSV.
- Full suite -> 32168 passed, 146 skipped, 0 failed.

## What remains unresolved
- 18 statically unreachable partial branches across `ethscan/` (prior handoff); no
  known functional defect.
- `ethscan/headers.py` now matches `ethscan/web.py` for status surfacing.

## Approaches already tried / ruled out
- Test-only edits: rejected; status was genuinely absent from source output.
- Importing `run_web_checks`/web formatters into `headers.py`: rejected; `run_headers`
  already receives the `FetchedHeaders` object (with `.status`) from `fetch_headers`,
  so the change stays local and minimal.

## Next task
- Enumerate and triage the 18 statically unreachable partial branches across `ethscan/`.
  Run `python3 -m coverage report --show-missing` (or read `coverage.json`) against
  the full suite to list uncovered lines, group by root cause, and for each decide
  whether it is genuinely unreachable (targeted `# pragma: no cover` only where truly
  unreachable) or a missing test. Do not mask reachable paths.
  Verify with `pytest -q` (green), `mypy`/`ruff` on touched files, and
  `python3 check_readme.py`. Keep changes minimal and reversible.

## Environment/notes
- Dev deps: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Caches gitignored; controller stages/commits source/test/handoff files.