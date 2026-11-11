# Next Task

## Task
Close another offline-testable coverage gap: `ethscan/tls.py:145` (the `continue` branch that skips an empty cipher string in `_validate_ciphers`).

## Evidence / constraints
- Baseline is green: `python -m pytest -q` → 6003 passed, 53 skipped, 0 failed; `mypy ethscan/ tests/` → clean; `ruff check ethscan/ tests/` → all checks passed.
- Coverage report (`python -m coverage report --include="ethscan/*" -m`) lists `ethscan/tls.py 235 1 99% 145` as the only uncovered line in tls.py.
- Reproduce first: confirm `_validate_ciphers(["", "TLS_AES_128_GCM_SHA256"])` returns `["TLS_AES_128_GCM_SHA256"]` without raising, then add a focused test asserting the empty string is skipped.
- Keep the change bounded: one test, no source change unless required; preserve mypy/ruff clean and full suite green.
- Related offline-testable gaps if tls.py:145 is already covered by context: `ethscan/service.py:262`, `ethscan/fuzz.py:186`, `ethscan/validate.py:334`.

## Session environment
- Python 3.14.4, pytest 9.2.0, ruff 0.17.4, mypy 2.4.1, Click 8.1.8.
