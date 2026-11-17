# Next Task
Date: Tue Nov 17 2026

## Status
- Repository baseline green: `pytest -q` -> 32220 passed, 146 skipped, 0 failed; `mypy ethscan/ tests/` clean (259 files); `ruff` clean; `check_readme.py` 54/54, 0 drift; 100% statement/branch coverage (15661/15661); `git diff --check` clean.
- This session fixed all 5 `--check-untyped-defs` errors in `tests/test_oracle.py` (test-only, reversible): `cast(Any, None)` for hostile input, `assert err is not None` before `in` on `str | None`, and targeted `type: ignore[assignment]` for intentional monkeypatch. No production code changed.

## Evidence the gap was real and is fixed
- Before: `python -m mypy --check-untyped-defs tests/test_oracle.py` -> 5 errors.
- After: `python -m mypy --check-untyped-defs tests/test_oracle.py` -> Success.
- `python -m pytest tests/test_oracle.py -q` -> 119 passed; full suite 32220 passed / 146 skipped.
- Coverage remains 100% statement/branch (15661/15661).

## Next task
- Continue per-file `--check-untyped-defs` typing hygiene on `tests/test_dns.py` (2 errors). Reproduce with `python -m mypy --check-untyped-defs tests/test_dns.py`, then fix with the established pattern: annotate locals holding `dict[str, object]` results as `dict[str, Any]`; use `cast(Any, ...)` for hostile/monkeypatch inputs; add `assert ... is not None` before operations on `Optional` values; use targeted `type: ignore[...]` only when required for intentional monkeypatch/overload cases. Do NOT weaken production source annotations.
- Remaining files with `--check-untyped-defs` errors (for later sessions, reproduce before fixing): `tests/test_dns.py` 2, `tests/test_resolve.py` 3, `tests/test_subtake.py` 4, `tests/test_smtp.py` 2, `tests/test_ntp.py` 1, `tests/test_cli.py` 1. `test_s3.py`, `test_postgresql.py`, `test_mongodb.py`, `test_redis.py`, `test_dnsbrute.py`, `test_mssql.py`, `test_mysql.py`, `test_dnssec.py`, `test_nmap.py`, `test_oracle.py`, `test_trace.py` are now 0.

## Constraints / notes
- Keep the existing architecture stable; prefer the smallest reversible change. Do not commit unless explicitly asked. `oracle`/`postgresql` empty-target handling is intentionally out of scope (exit 0, in-band error) per documented contract.
- Dev deps: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, Python 3.14.4. No pytest-cov plugin — use `python -m coverage run --branch --source=ethscan -m pytest` for coverage. Always run the full gate after a change and record results in HANDOFF_NEXT.md/NEXT_TASK.md.
