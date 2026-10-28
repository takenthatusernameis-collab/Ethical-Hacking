## Status: COMPLETE

### What changed
- Added a `[tool.ruff]` lint configuration to `pyproject.toml` (`line-length = 88`, rules `F`, `BLE001`, `S110`) — the project previously had no linter configured.
- Fixed 5 lint errors surfaced by ruff:
  - `ethscan/resolve.py:8`: removed unused `from typing import Any` (F401).
  - `ethscan/ssl.py:151-152`: removed dead `pem_data = f.read()` block (F841).
  - `ethscan/ssl.py:155`: annotated the intentional defensive `except Exception` with `# noqa: BLE001` (private C API fallback).
  - `ethscan/validate.py:242`: narrowed `except Exception` to `except (ValueError, TypeError)` (BLE001/S110).

### What was actually verified
- `python -m ruff check ethscan tests` -> All checks passed.
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest -q` -> 5225 passed, 51 skipped.

### What remains unresolved
- ruff is configured but not declared as a project/dev dependency, so it is not installed by `pip install -r requirements.txt` and not enforced anywhere yet.

### Which approaches failed and why
- None.

### One precise next task
- Declare ruff as a dev dependency (add `dev = ["ruff>=0.17"]` to `[project.optional-dependencies]` in `pyproject.toml`) and verify `python -m ruff check ethscan tests` still passes after install.
