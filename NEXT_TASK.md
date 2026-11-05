# Next Task
Pick the remaining protocol module without a module-specific hostile sweep (`ethscan/ssh.py`), add focused tests for hostile transport / hostile input edge cases following `tests/test_oracle_hostile_sweep.py`, re-run full `pytest`/`ruff`/`mypy`. Do not commit unless asked.

`ethscan/netbios.py` now has `tests/test_netbios_hostile_sweep.py` (restored this session: 4 tests, all passing). SSH is the last connector-seam protocol relying only on the shared `test_protocol_hostile_sweep.py` without a module-specific hostile sweep.

Coverage is complete across all 59 modules (verified this session). The remaining candidate work is the hostile-transport / hostile-input edge-case sweep for ssh.

(End of file)