## What changed this session

Added a `[project.scripts]` entry point to `pyproject.toml`:

```
[project.scripts]
ethscan = "ethscan.cli:cli"
```

Previously `pip install .` installed the `ethscan` package but created no console
script, so the only way to run the CLI was `python -m ethscan`. Now `pip install .`
produces an `ethscan` executable bound to `ethscan.cli:cli`.

## What was actually verified

- `git status --porcelain` → only `pyproject.toml` modified; working tree otherwise clean
- `python -m ruff check ethscan/ tests/` → All checks passed
- `python -m pytest tests/test_main.py -q` → 14 passed (entry-point tests unchanged)
- Installed into a fresh temp venv (`pip install .`) and ran:
  - `ethscan --help` → exit 0, usage printed
  - `ethscan --version` → `ethscan, version 0.1.0`
  - `ethscan scan --target 127.0.0.1 --ports 80 --output-format json` → valid JSON, exit 0

## What remains unresolved

None. The change is small, reversible, and fully verified.

## Which approaches have already failed and why

None. No speculative or failed approach was taken.

## One precise next task

None — repository complete and in sync with origin/main, plus the new console-script
entry point is installed and verified. If new work arrives, implement the smallest
reversible change solving a demonstrated problem and verify with
`python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`, then update
`HANDOFF_NEXT.md` with evidence.
