# Next Task

## Status
Sun Nov 15 2026 (session 2): removed duplicated README validation block (file-options/nmap-XML text repeated after S3 port-range example). Baseline remains green per prior full run; targeted checks passed this session.

## Baseline / verification this session
- `python3 check_readme.py` → 54/54, README and CLI in sync.
- `python3 -m ruff check ethscan/ tests/` → All checks passed.
- `python3 -m mypy ethscan/` → Success: no issues found in 59 source files.
- `python3 -m pytest tests/test_trace.py -q` → 44 passed.
- Prior full baseline (session 1 handoff): `python3 -m pytest -q` → 32026 passed, 146 skipped, 1 warning, 0 failed.

## Blockers
- None.

## Approaches already tried / ruled out
- `ethscan/hash.py` arc `589->596`: requires a list/tuple subclass whose `__bool__` is True when empty; not a valid public-contract input. Do not retry.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

## Next task
- Bounded: audit `README.md` "Usage" error-example section for remaining duplication/staleness versus actual CLI behavior (focus on target/file validation examples). For any mismatch, prefer the smallest doc fix; reproduce each claimed example with the current CLI (`python3 -m ethscan ...; echo $?`) before editing and re-run `python3 check_readme.py`. Avoid speculative rewrites and do not change command contracts.
