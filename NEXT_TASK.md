# Next Task
Pick one module with coverage gaps (scan with `pytest --cov=ethscan.<mod> --cov-report=term-missing`, use a larger shell timeout for smtp/ssh/snmp as prior scans exceeded 120s), close reachable gaps with tests or mark unreachable defensives with `# pragma: no cover - defensive`. Verify with full pytest/ruff/mypy. Do not commit unless explicitly asked.

Remaining candidate gaps:
- ethscan/smtp.py: 305, 463-478, 488
- ethscan/ssh.py: 168, 632-633
- ethscan/snmp.py: 586-587

Recently closed (this session): memcached.py 202-203, postgresql.py 355-356, web.py 74-75/368-372 — all now 100%.
