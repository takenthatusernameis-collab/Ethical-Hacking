## Status: COMPLETE

### What changed
- Fixed 5 ruff `B904` errors (raise inside `except` without `from err` / `from None`):
  - `ethscan/cli.py:3617`: `raise SystemExit(1)` -> `raise SystemExit(1) from None` (OSError handler)
  - `ethscan/cli.py:3725`: `raise SystemExit(1)` -> `raise SystemExit(1) from None` ((OSError, ValueError) handler)
  - `ethscan/cli.py:3849`: `raise SystemExit(1)` -> `raise SystemExit(1) from None` (ValueError handler)
  - `ethscan/scanner.py:107-110`: bound `except ValueError as err` and chained `raise PortSpecError(...) from err`
  - `ethscan/scanner.py:123-124`: bound `except ValueError as err` and chained `raise PortSpecError(...) from err`

### What was actually verified
- `python -m ruff check ethscan tests` -> All checks passed (exit 0). Previously failed with 5 B904 errors.
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest -q` -> 5228 passed, 48 skipped (exit 0).

### What remains unresolved
- No project CI workflow enforces ruff/mypy/pytest on push or pull requests (only the Kilo controller workflow exists in `.github/workflows/main.yml`).

### Which approaches failed and why
- None.

### One precise next task
- Add a GitHub Actions CI workflow (`.github/workflows/ci.yml`) that runs `python -m ruff check ethscan tests`, `python -m mypy ethscan`, and `python -m pytest -q` on `push` and `pull_request` to `main`. Constraints: `ubuntu-latest`, install deps from `requirements.txt` plus dev tools, keep it small and reversible, do not modify `.github/workflows/main.yml` (Kilo controller). Verify with `python -m ruff check ethscan tests`, `python -m mypy ethscan`, `python -m pytest -q` locally before completing.
