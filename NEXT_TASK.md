# Next Task
Date: Mon Nov 16 2026

## Status
- Repository is green: full suite `python3 -m pytest -q` -> **32159 passed, 146 skipped, 0 failed** (previously 10 failed).
- The 10 failures inherited from the prior session are resolved:
  - `tests/test_cli.py::test_fuzz_output_format_markdown` (stale label)
  - 6x `tests/test_fuzz_hostile_sweep.py::test_markdown_non_list_findings_never_raises[...]` (stale label)
  - `tests/test_fuzz_hostile_sweep.py::test_csv_hostile_all_results_entries_never_raise` (wrong `is_finding` on hostile handoff)
  - `tests/test_fuzz_formatter_hostile_sweep.py::...[data15-format_fuzz_report_csv]` (unhashable `path` TypeError)
  - `tests/test_target.py::test_fetch_headers_drops_the_userinfo_of_the_target` (fake double missing `.status`)

## What changed this session
- `ethscan/fuzz.py`: module-level `_is_finding_status(status_code)` helper (non-int -> `False`; else not a finding for `404`/`5xx`/`429`); used by `run_fuzz` and `format_fuzz_report_csv`; removed the `finding_keys` membership set that crashed on an unhashable `path`.
- `tests/test_cli.py`, `tests/test_fuzz_hostile_sweep.py`: updated stale `**Findings (non-404):**` assertions to `**Findings:**`.
- `tests/test_target.py`: `FakeResponse` now sets `status = 200`.

## What was verified
- Focused previously-failing set -> 38 passed.
- `pytest tests/test_cli.py tests/test_fuzz.py tests/test_fuzz_hostile_sweep.py tests/test_fuzz_formatter_hostile_sweep.py tests/test_target.py -q` -> 1503 passed.
- `mypy` + `ruff` on touched files -> clean.
- `python3 check_readme.py` -> 54 commands, 0 drift.
- Full suite -> 32159 passed, 146 skipped, 0 failed.

## What remains unresolved
- 18 statically unreachable partial branches across `ethscan/` (prior handoff); no known functional defect.
- `ethscan/headers.py` does not surface `fetched.status` (unlike `ethscan/web.py`).

## Approaches already tried / ruled out
- Label-only test edits: rejected as insufficient; CSV formatter had a real source defect.
- Reverting label to `(non-404)`: rejected; `Findings` is accurate (excludes 5xx/429 too).
- Loosening `fetch_headers` to `getattr(..., "status", None)`: rejected as masking a test-double deficiency.

## Next task
- Surface the HTTP status in `ethscan/headers.py` `run_headers_check`, mirroring
  `ethscan/web.py:373-375`: read `getattr(fetched, "status", None)` and set
  `results["status"]` when not `None`; render `- **Status:** <code>` in
  `format_headers_report_markdown` and a `status,<code>` row in
  `format_headers_report_csv` when present (JSON is automatic). Add regression
  tests in `tests/test_headers.py` (success / HTTPError / transport failure;
  Markdown/CSV render and omit-when-None).
  Verify with `pytest tests/test_headers.py tests/test_web.py tests/test_cli.py -q`,
  `python3 check_readme.py`, `mypy`/`ruff` on touched files, and a full `pytest -q`.
  Do not modify `ethscan/web.py`.

## Environment/notes
- Dev deps: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Caches gitignored; controller stages/commits source/test/handoff files.