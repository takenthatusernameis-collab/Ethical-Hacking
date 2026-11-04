# Next Task
Pick next module with coverage gaps (scan with `pytest --cov=ethscan.<mod> --cov-report=term-missing`), close reachable gaps with tests or mark unreachable defensives with `# pragma: no cover - defensive`. Verify with full pytest/ruff/mypy. Do not commit unless explicitly asked.
