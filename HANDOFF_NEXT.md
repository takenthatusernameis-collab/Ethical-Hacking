# Handoff
Date: Mon Nov 09 2026 (session 19)

## What changed
Continued typing hygiene on small test files (test-side only; runtime behavior unchanged).

- `tests/test_cache_content_sweep.py`: added `assert user.cli_args is not None` before `runner.invoke(cli.cli, list(user.cli_args))` (narrows `tuple[str, ...] | None` → `Iterable[str]`).
- `tests/test_config_value_sweep.py`: widened `_required_args(..., skip: str | None)` to match call sites passing `None`-typed names in general usage.
- `tests/test_cli_trace_brute_unreachable_sweep.py`: used `setattr()` on `types.ModuleType("paramiko")` stubs (`SSHClient`, `AutoAddPolicy`) to satisfy mypy `[attr-defined]`. Note: `ruff B010` flags `setattr` with constant attribute names; this typing-hygiene pass prioritized `mypy` cleanliness. Do not “fix” back to direct attribute assignment without also resolving the mypy constraint.

## What was verified
- `python -m mypy tests/test_cache_content_sweep.py tests/test_config_value_sweep.py tests/test_cli_trace_brute_unreachable_sweep.py` → Success (0 issues).
- `python -m pytest tests/test_cli_trace_brute_unreachable_sweep.py tests/test_cache_content_sweep.py tests/test_config_value_sweep.py -q` → 80 passed, 3 skipped.
- `python -m pytest -q --ignore=tests/test_ping.py` → 5878 passed, 50 skipped, 0 failed (baseline unchanged).

## Unresolved
- `tests/test_ping.py` runtime failures — pre-existing Python 3.14 `socket.timeout` read-only descriptor blocker; left untouched.
- Repo-wide typing debt remains across many test files. Do not assume counts are current; reproduce per file with `python -m mypy tests/<file>`.

## Approaches that have already failed / to avoid
- Do not retry identical operations with unchanged assumptions.
- Do not weaken safety controls or skip verification.
- Do not “fix” `test_cli_trace_brute_unreachable_sweep.py` `setattr` to direct assignment without addressing mypy `[attr-defined]` (ruff B010 ↔ mypy tension).
- Do not fix `test_ping.py` without addressing the Python 3.14 `socket.timeout` descriptor constraint.

## Next task
Continue per-file typing hygiene on remaining test files with mypy errors. Reproduce each target with `python -m mypy tests/<file>` before editing. Prefer small, test-side annotations/casts; widen source signatures only where indexing dynamic `dict[str, object]`/result shapes is the root cause and the change is minimal/safe. Skip `tests/test_ping.py`. Verify per file: `mypy <file>` clean, `ruff check <file>` clean (resolve conflicts case-by-case), targeted pytest for that file, then `pytest -q --ignore=tests/test_ping.py` for baseline.

Candidate files (reproduce counts first): `test_cli.py` (12), `test_ldap.py` (6), `test_service.py` (5), `test_passwords.py` (5), `test_snmp.py` (9), `test_ssh.py` (9), `test_fuzz.py` (9), `test_subtake.py` (10), `test_geo.py` (11), `test_brute.py` (11), `test_tls.py` (16), `test_subdomains.py` (17), `test_dnssec.py` (18), `test_s3.py` (19), `test_jwt.py` (21), `test_osdetect.py` (23), `test_web.py` (27), `test_cve.py` (32), plus hostile-sweep variants as listed in prior handoffs (many follow `cast(Any, ...)` pattern). Start with lowest-error non-hostile files for quick wins.
