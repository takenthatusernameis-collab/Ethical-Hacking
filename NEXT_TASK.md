# Next Task

## Status: OPEN

Continue per-file typing hygiene on remaining test files with mypy errors.

## Scope
- Work on **one or a small batch** of test files per session. Reproduce errors first: `python -m mypy tests/<file>`.
- Use established patterns: test-side annotations/casts for `dict[str, object]` indexing/`.get()` returning `object`; `cast(Any, ...)` for hostile-sweep formatters where runtime accepts `object`; widen source return/type signatures only when minimal, safe, and clearly the root cause.
- Skip `tests/test_ping.py` (pre-existing Python 3.14 `socket.timeout` read-only descriptor blocker).
- Do not weaken safety controls or make speculative changes.
- Note: `tests/test_cli_trace_brute_unreachable_sweep.py` uses `setattr` on `ModuleType` stubs to satisfy mypy `[attr-defined]` (conflicts with ruff B010) — preserve unless you can satisfy both.

## Verification (required per batch)
1. `python -m mypy tests/<file>` → 0 issues for touched files.
2. `python -m ruff check tests/<file>` → clean (resolve conflicts case-by-case; document if mypy/ruff tension is unavoidable).
3. Targeted `python -m pytest <touched-test-files> -q` → pass.
4. `python -m pytest -q --ignore=tests/test_ping.py` → baseline unchanged (5878 passed, 50 skipped at handoff; re-verify).

## Suggested starting points (reproduce counts first)
Low-error non-hostile files: `test_ldap.py`, `test_service.py`, `test_passwords.py`, `test_fuzz.py`, `test_snmp.py`, `test_ssh.py`, `test_subtake.py`, `test_geo.py`, `test_brute.py`, `test_cli.py`. Then larger: `test_tls.py`, `test_subdomains.py`, `test_dnssec.py`, `test_s3.py`, `test_jwt.py`, `test_osdetect.py`, `test_web.py`, `test_cve.py`. Hostile-sweep files generally follow the `cast(Any, ...)` pattern.

## Handoff
Update `HANDOFF_NEXT.md` and this file with: files fixed, exact verification evidence, remaining counts (reproduced), and any new constraints/failures.
