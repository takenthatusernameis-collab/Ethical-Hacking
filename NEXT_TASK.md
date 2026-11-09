# Next Task

## Status: OPEN

Continue per-file typing hygiene on remaining test files with mypy errors.

## Scope
- Work on **one or a small batch** of test files per session. Reproduce errors first: `python -m mypy tests/<file>`.
- Use established patterns: test-side `cast(...)` annotations for `dict[str, object]` indexing/`.get()` returning `object`; `cast(Any, ...)` for hostile-sweep formatters where runtime accepts `object`; widen source return/type signatures only when minimal, safe, and clearly the root cause.
- Skip `tests/test_ping.py` (pre-existing Python 3.14 `socket.timeout` read-only descriptor blocker).
- Do not weaken safety controls or make speculative changes.
- Note: `tests/test_cli_trace_brute_unreachable_sweep.py` uses `setattr` on `ModuleType` stubs to satisfy mypy `[attr-defined]` (conflicts with ruff B010) — preserve unless you can satisfy both.

## Verification (required per batch)
1. `python -m mypy tests/<file>` → 0 issues for touched files.
2. `python -m ruff check tests/<file>` → clean (resolve conflicts case-by-case; document if mypy/ruff tension is unavoidable).
3. Targeted `python -m pytest <touched-test-files> -q` → pass.
4. `python -m pytest -q --ignore=tests/test_ping.py` → baseline unchanged (5878 passed, 50 skipped at session 23; re-verify).

## Suggested starting points (reproduce counts first)
- Already clean (0 mypy errors, verified sessions 22-23): `test_cli.py`, `test_ssh.py`, `test_tls.py`, `test_subdomains.py`, `test_dnssec.py` (fixed session 22), `test_s3.py` (fixed session 23), `test_ldap.py`, `test_service.py`, `test_passwords.py`, `test_fuzz.py`, `test_snmp.py`, `test_geo.py`, `test_brute.py`, `test_main.py`, `test_web_hostile_sweep.py`.
- Remaining with errors (reproduced session 23): `test_jwt.py` (21), `test_osdetect.py` (23), `test_web.py` (27), `test_cve.py` (32). Then larger/hostile-sweep files per repo-wide counts, reproduce per file first.

## Handoff
Update `HANDOFF_NEXT.md` and this file with: files fixed, exact verification evidence, remaining counts (reproduced), and any new constraints/failures.
