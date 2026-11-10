# Next Task

## Task
- None pending. Repository is fully green.

## Evidence
- Baseline (this session): started green on tests (5962 passed, 50 skipped), ruff clean, mypy clean (187 source files).
- Fixed `ethscan/stale.py`: narrowed blind `except Exception` handlers (BLE001) to specific exception types:
  - Resolver functions (`resolve_a_records`, `resolve_aaaa_records`, `resolve_cname`): `except (OSError, ValueError)` — covers `socket.gaierror`, `socket.timeout`, `UnicodeEncodeError`.
  - `check_tcp_connect`: `except (OSError, ValueError, OverflowError)` — covers socket errors and port overflow.
  - `resolve_domain_all`: removed redundant try/except blocks (resolvers handle exceptions internally).
  - `run_stale`: kept safety-net `except Exception` with explanatory `# noqa: BLE001` comment.
- Updated `tests/test_stale.py`: replaced 3 exception-branch tests (mocked `RuntimeError`) with 2 behavior-focused tests. Net -1 test.
- Verification: `ruff check` → clean; `mypy ethscan/ tests/` → clean; `pytest -q` → 5961 passed, 50 skipped, 0 failed; CLI smoke tests pass.

## Next task after that
- If future work is needed, pick a single high-value, verifiable improvement and reproduce it first. Do not speculate or weaken safety controls.

(End of file - total 22 lines)