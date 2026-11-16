# Handoff
Date: Mon Nov 16 2026

## This session
- No queued assignment existed; the prior handoff recorded a green baseline. I independently reproduced the baseline before selecting work: 32,169 passed, 146 skipped; mypy/ruff/README checks clean.
- Fixed a real network-calculation bug in the three network-info calculators: IPv4 `/31` and IPv6 `/127` now report both addresses as usable hosts (first address through last address), while IPv4 `/32` and IPv6 `/128` report their single address as usable.
- Changed `ethscan/cidr.py`, `ethscan/radix.py`, and `ethscan/validate.py` consistently. The previous formulas always subtracted the IPv4 network/broadcast pair (or the IPv6 network address), which produced zero or partial host counts for these edge prefixes.
- Updated stale assertions in `tests/test_cidr.py`, `tests/test_radix.py`, and `tests/test_validate.py` that had codified the incorrect behavior. Added a parametrized CIDR regression test that compares usable count and host range with the stdlib `ipaddress.ip_network(...).hosts()` result.

## What was actually verified
- Reproduction before fix: `/31`, `/32`, `/127`, and `/128` all reported zero or partial usable hosts in `cidr`, `radix`, and `validate`.
- Post-fix CLI smoke tests: `cidr --cidr 192.0.2.0/31`, `validate --cidr 192.0.2.0/31`, `cidr --cidr 2001:db8::/127`, and `validate --cidr 2001:db8::1/128` all exited 0 with the corrected values.
- Focused suite: `python3 -m pytest tests/test_cidr.py tests/test_radix.py tests/test_validate.py -q` -> **335 passed**.
- Full suite: `python3 -m pytest -q` -> **32,174 passed, 146 skipped, 0 failed** (baseline 32,169; +5 net new tests).
- Full branch coverage: `python3 -m coverage run --branch --source=ethscan -m pytest -q` plus `coverage json` -> **100%, 0 missing branches**.
- `python3 -m mypy ethscan/ tests/` -> clean (259 source files).
- `python3 -m ruff check ethscan/ tests/` -> all checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift.
- `git diff --check` -> clean.

## What remains unresolved
- None for this task. The existing `broadcast_address` field was intentionally left unchanged: it still follows the stdlib property (including its value for `/31`/`/32`). This task was limited to the demonstrated usable-host and host-range defect.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented exit-0/in-band-error contract.

## Approaches already tried / ruled out
- A direct shared-helper refactor was rejected to keep the change minimal and preserve the existing module architecture.
- The first focused test run exposed two stale `/31` and `/127` assertions that asserted `first_host == last_host`; those assertions were the bug, not the implementation, and were updated to compare against stdlib host semantics.
- An intermediate edit dropped the `netmask`/`broadcast`/`wildcard` locals in `ethscan/cidr.py`; a smoke test caught the resulting `NameError`, and the locals were restored before any test gate passed. No evidence supports further refactoring.

## Next task
- None required. Repository is fully green with 100% branch coverage. If future work is needed, pick one bounded improvement and reproduce the gap first; do not change code speculatively or weaken safety controls.
- Relevant follow-up evidence, only if a future task explicitly requests it: the three calculators still duplicate network-info formatting (`ethscan/cidr.py`, `ethscan/radix.py`, `ethscan/validate.py`), but consolidation is a refactor, not a demonstrated correctness fix.

## Environment/notes
- Dev deps used: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- No commit was created; changes are left in the working tree for review.

(End of file - 47 lines)