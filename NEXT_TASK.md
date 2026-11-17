# Next Task
Date: Tue Nov 17 2026

## Status
- Prior handoff’s queued task (`--check-untyped-defs` hygiene on `tests/test_dns.py` / other listed files) was rechecked: all previously listed candidates and all `tests/`/`ethscan/` now pass `python -m mypy --check-untyped-defs`.
- This session fixed `check_readme.py` to exit non-zero on README/CLI drift (deterministic gate behavior) while preserving synced-output behavior.
- Focused verification passed: `python check_readme.py` (exit 0), `pytest tests/test_readme_sync.py -q` (5 passed), `ruff`/`mypy` checks on touched and full source trees clean, `git diff --check` clean. Full pytest+coverage not rerun this session.

## Next task
1. Re-establish full-gate evidence after this session: run `python -m pytest -q`, `python -m mypy ethscan/ tests/`, `python -m ruff check ethscan/ tests/ check_readme.py`, `python check_readme.py`, and `python -m coverage run --branch --source=ethscan -m pytest -q && python -m coverage report`. Record exact counts/results.
2. If fully green, inspect for one bounded, high-value, evidence-backed improvement (reproduce first). Candidate areas: any newly introduced `mypy --check-untyped-defs` issues anywhere, or a deterministic gap in tests/docs/tooling with clear verification. Avoid speculative refactors.

## Constraints / notes
- Keep architecture stable; smallest reversible change. Do not weaken production annotations or safety checks. Do not commit unless explicitly asked.
- Dev deps: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, Python 3.14.4. No pytest-cov plugin.
- `oracle`/`postgresql` empty-target handling intentionally out of scope (exit 0, in-band error) per documented contract.
