# Next Task

## Task
All previously identified offline-testable coverage gaps are now closed:
- `ethscan/tls.py:145` — already covered by existing test `test_validate_ciphers_skips_empty_strings`
- `ethscan/service.py:262` — covered by new test `test_format_service_report_markdown_non_list_results`
- `ethscan/fuzz.py:186` — already at 100% coverage
- `ethscan/validate.py:334` — covered by new test `test_format_validate_report_csv_valid_true_empty_ports_list` and non-dict guards

## Evidence / constraints
- Baseline is green: `python -m pytest -q` → 6016 passed, 53 skipped, 0 failed; `mypy ethscan/ tests/` → clean; `ruff check ethscan/ tests/` → all checks passed.
- Coverage for target modules: `ethscan/service.py`, `ethscan/tls.py`, `ethscan/validate.py`, `ethscan/fuzz.py` all at 100%.
- Remaining offline-testable gaps (if any): inspect `python -m coverage report --include="ethscan/*" -m` for modules with <100% coverage that don't require network access. Candidates include formatters with non-dict guards (similar to validate.py lines 317/361 now covered).

## Session environment
- Python 3.14.4, pytest 9.2.0, ruff 0.17.4, mypy 2.4.1, Click 8.1.8.