# Next Task
Date: Tue Nov 17 2026

## Status
- Repository baseline green at start and end: `pytest -q` -> 32220 passed, 146 skipped, 0 failed; `mypy ethscan/ tests/` clean (259 files); `ruff` clean; `check_readme.py` 54/54, 0 drift; 100% statement/branch coverage; `git diff --check` clean.
- This session fixed all 6 `--check-untyped-defs` mypy errors in `tests/test_mongodb.py` (test-only; `cast(Any, ...)` for hostile inputs, `dict[str, Any]` annotation for formatter dict, `assert err is not None` before `in` on `str | None`). No production code changed.

## Evidence the gap was real and is fixed
- Before: `python -m mypy --check-untyped-defs tests/test_mongodb.py` -> 6 errors (`arg-type` on hostile `None` arg, `operator` on `str | None` x2, `var-annotated` missing annotation for `data`, `arg-type` on non-dict formatter args x2).
- After: `python -m mypy --check-untyped-defs tests/test_mongodb.py` -> Success.
- `python -m pytest tests/test_mongodb.py -q` -> 41 passed; full suite unchanged at 32220 passed / 146 skipped.
- Coverage remains 100% statement/branch (15661/15661).

## Next task
- Continue per-file `--check-untyped-defs` typing hygiene on the next-largest file, `tests/test_s3.py` (5) or `tests/test_postgresql.py` (5). Reproduce with `python -m mypy --check-untyped-defs tests/test_s3.py`, then fix with the established pattern: annotate locals holding `dict[str, object]` results as `dict[str, Any]`; use `cast(Any, ...)` for hostile/monkeypatch inputs; add `assert err is not None` before `in` on `str | None`. Do NOT weaken production source annotations.
- Remaining files with `--check-untyped-defs` errors (for later sessions): test_s3.py 5, test_postgresql.py 5, test_oracle.py 4, test_trace.py 2, test_dns.py 2, test_resolve.py 3, test_subtake.py 4, test_smtp.py 2, test_ntp.py 1, test_cli.py 1. `test_nmap.py`, `test_dnssec.py`, `test_mysql.py`, `test_mssql.py`, `test_dnsbrute.py`, `test_redis.py`, and `test_mongodb.py` are now 0.

## Constraints / notes
- Keep the existing architecture stable; prefer the smallest reversible change. Do not commit unless explicitly asked. `oracle`/`postgresql` empty-target handling is intentionally out of scope (exit 0, in-band error) per their documented contract.
- Dev deps installed: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, Python 3.14.4. No pytest-cov plugin — use `python -m coverage run --branch --source=ethscan -m pytest` for coverage. Always run the full gate after a change and record results in TASK.md/HANDOFF_NEXT.md.
