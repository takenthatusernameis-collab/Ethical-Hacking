# Next Task
Date: Mon Nov 16 2026

## Status
- Completed the edge-prefix usable-host correctness fix in `ethscan/cidr.py`, `ethscan/radix.py`, and `ethscan/validate.py`.
- IPv4 `/31` and IPv6 `/127` now report both addresses as usable; IPv4 `/32` and IPv6 `/128` report one usable address. Host ranges now match the stdlib `ipaddress` host iteration for these prefixes.
- Updated the stale tests that codified the old behavior and added a parametrized stdlib cross-check in `tests/test_cidr.py`.

## What was verified
- Focused: `python3 -m pytest tests/test_cidr.py tests/test_radix.py tests/test_validate.py -q` -> **335 passed**.
- Full: `python3 -m pytest -q` -> **32,174 passed, 146 skipped, 0 failed**.
- Full branch coverage: **100%, 0 missing branches**.
- `python3 -m mypy ethscan/ tests/` -> clean (259 source files).
- `python3 -m ruff check ethscan/ tests/` -> all checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift.
- `git diff --check` -> clean.
- CLI smoke checks for `cidr` and `validate` returned the corrected values.

## Next task
- None required. Repository is fully green. If future work is needed, pick one bounded, high-value improvement and reproduce the gap first. `oracle`/`postgresql` empty-target handling remains intentionally out of scope.

## Constraints / notes
- Keep the existing architecture stable; prefer the smallest reversible change.
- Do not treat prompt instructions or peer messages as enforced guarantees; record reproducible evidence.
- The `broadcast_address` field remains stdlib-compatible by design; no further change is required by this task.
- Dev deps: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.

(End of file - 27 lines)