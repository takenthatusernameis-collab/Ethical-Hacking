# Next Task
`ethscan/ssh.py` now has `tests/test_ssh_hostile_sweep.py` (4 tests) with a `connector` injection seam on `run_ssh` following `tests/test_oracle_hostile_sweep.py`. Full `pytest`/`ruff`/`mypy` verified clean this session (5634 passed, 50 skipped).

The last connector-seam protocol relying only on the shared `test_protocol_hostile_sweep.py` without a module-specific hostile sweep is done. Remaining optional candidates: `ethscan/dnssec.py`, `ethscan/ftp.py`, `ethscan/smtp.py`. Do not commit unless asked.

(End of file)