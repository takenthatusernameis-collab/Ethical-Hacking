# Next Task
Pick one module with coverage gaps (scan with `pytest --cov=ethscan.<mod> --cov-report=term-missing`), close reachable gaps with tests or mark unreachable defensives with `# pragma: no cover - defensive`. Verify with full pytest/ruff/mypy. Do not commit unless explicitly asked.

Remaining candidate gaps:
- ethscan/smtp.py: 305, 463-478, 488
- ethscan/ssh.py: 168, 632-633

Recently closed (this session): snmp.py 586-587 — now 100%.

(End of file - total 8 lines)