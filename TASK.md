# Task
Date: 2026-10-19T01:00:00Z
Status: stable-green
Branch: main (clean)

Completed
- Verified baseline: 3902 passed, 1 skipped; 53 CLI commands register; `python -m ethscan --help` OK; py_compile clean.
- Narrowed 3 BLE001 blind-except errors in tests/test_cli.py to json.JSONDecodeError (committed in 0f8424c). The previous agent's claim that all 46 ruff errors were unsafe was incorrect for these 3 — they wrap `json.loads(result.output)` in tests that assert the default output is JSON, and no test mocks `json.loads` itself, so narrowing to JSONDecodeError is behavior-preserving.
- Confirmed the remaining 43 ruff errors (30 BLE001, 12 TRY002, 1 PLR0402) are genuinely unsafe to fix:
  - 30 BLE001 in ethscan/ source: tests mock generic `Exception` (e.g. `side_effect=Exception("Network error")` in test_cert.py, test_geo.py, test_mac.py, test_trace.py, test_web.py; `side_effect=Exception("boom")` in test_cidr.py:606). Narrowing breaks those tests.
  - 12 TRY002 in tests/: tests deliberately raise plain `Exception` to exercise source `except Exception` paths (test_brute.py:59,79,127,150; test_oracle.py:1156,1196; test_resolve.py:471,572,667,731; test_web.py:679,855).
  - 1 PLR0402 in tests/test_brute.py:504: reload semantics depend on the `import ethscan.brute as brute` form.

Current state
- Working tree: clean.
- Lint: 43 errors (down from 46).
- Mypy: not targeted (historically large).
- Coverage: 70 missing lines documented as unreachable/environment-dependent.

Notes
- Next: await a genuine new issue/requirement. No safe bounded task remains.