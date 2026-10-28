## Status: READY

### One precise next task
- Add a GitHub Actions CI workflow (`.github/workflows/ci.yml`) that runs `python -m ruff check ethscan tests`, `python -m mypy ethscan`, and `python -m pytest -q` on `push` and `pull_request` to `main`. Constraints: `ubuntu-latest`, install deps from `requirements.txt` plus dev tools (ruff, mypy, pytest, dnspython), keep it small and reversible, do not modify `.github/workflows/main.yml` (Kilo controller). Verify locally with `python -m ruff check ethscan tests`, `python -m mypy ethscan`, `python -m pytest -q` before marking complete.
