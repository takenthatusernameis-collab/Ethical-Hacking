# Next Task
Pick the remaining protocol module without a module-specific hostile sweep (`ethscan/netbios.py`), add focused tests for hostile transport / hostile input edge cases following `tests/test_oracle_hostile_sweep.py`, re-run full `pytest`/`ruff`/`mypy`. Do not commit unless asked.

`ethscan/ntp.py` now has `tests/test_ntp_hostile_sweep.py` (added this session: 4 tests, all passing). NetBIOS is the last module relying only on the shared `test_protocol_hostile_sweep.py` without a module-specific hostile sweep.

Coverage is complete across all 59 modules (verified this session). The remaining candidate work is the hostile-transport / hostile-input edge-case sweep for netbios.

(End of file)
