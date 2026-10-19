# Next Task for Agent

## Status
- Working tree: clean (after commit of 3 BLE001 narrowings).
- Tests: 3902 passed, 1 skipped (green baseline).
- Repository complete: 53 CLI commands register on import; `python -m ethscan --help` OK.
- Lint: 43 ruff errors (30 BLE001, 12 TRY002, 1 PLR0402) — all proven unsafe to fix without breaking tests. Do not touch.
- Coverage: 99%; remaining source gaps are unreachable defensive code. Not worth targeting.

## Current issues (do not touch unless new requirement explicitly requires changing behavior)
- ruff BLE001 (30) — many tests mock plain-raise Exception paths; narrowing breaks behavior.
- ruff TRY002 (12) — tests expect raising plain Exception in certain mocked paths.
- ruff PLR0402 (1) — in tests/test_brute.py; reload semantics depend on import form.

## Completed this session
- Verified full baseline: git clean, stash empty, 3902 passed/1 skipped, 53 CLI commands register, `python -m ethscan --help` OK, py_compile clean.
- Disproved the prior claim that all 46 ruff errors are unsafe. Narrowed 3 BLE001 blind-except in tests/test_cli.py to json.JSONDecodeError (committed in 0f8424c):
  - tests/test_cli.py:19161 (test_redis_default_is_json)
  - tests/test_cli.py:19300 (test_smb_default_is_json)
  - tests/test_cli.py:19493 (test_ldap_default_is_json)
  These wrap `json.loads(result.output)` in tests asserting the default output is JSON; no test mocks json.loads, so narrowing is behavior-preserving. Verified the 3 tests still pass.
- Re-verified the remaining 43 errors are genuinely unsafe: source BLE001 (30) are all in try/except blocks where tests mock generic Exception (test_cert.py:186, test_geo.py:199, test_mac.py:163, test_trace.py:278, test_cidr.py:606, etc.); TRY002 (12) are tests deliberately raising plain Exception; PLR0402 (1) depends on reload semantics.

## Next precise task
- None remaining. Await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan).
- If a new issue arrives, implement the smallest verifiable change, run focused tests + `python -m pytest -q` + relevant lint checks, and preserve baseline.