# Next Task
Pick next module with coverage gaps (scan with `pytest --cov=ethscan.<mod> --cov-report=term-missing`), close reachable gaps with tests or mark unreachable defensives with `# pragma: no cover - defensive`. Verify with full pytest/ruff/mypy. Do not commit unless explicitly asked.

Candidate gaps (from last coverage scans):
- ethscan/smtp.py: 305, 463-478, 488
- ethscan/ssh.py: 168, 632-633
- ethscan/snmp.py: 586-587, 666-669
- ethscan/redis.py: 58-59, 277-278
- ethscan/memcached.py: 202-203, 302-303
- ethscan/postgresql.py: 355-356
- ethscan/web.py: 74-75, 368-372
