# Next task for the next agent

## Current state (verified this session)
- All ~54 ethscan commands are implemented, registered in `ethscan/cli.py`, and wired with `--format`/`--output-format [json|markdown|csv]` and `--out`.
- Every command module (`ethscan/*.py`) has a corresponding `tests/test_*.py` with healthy test-to-module line ratios (all >= ~0.7, most >1.0).
- Every command has CLI integration tests in `tests/test_cli.py`.
- `python -m pytest -q` → **3477 passed, 1 skipped** (full suite, green).
- Offline CLI end-to-end verified: `cidr`, `hash`, `validate`.

## This session's change
- Closed two CLI test gaps: added `test_web_help`, `test_cli_help_lists_web`, `test_jwt_help`, `test_cli_help_lists_jwt` to `tests/test_cli.py` (+4 tests). Prior to this, the `web` and `jwt` commands lacked `--help` verification tests.

## Next task
There is no required next task — the codebase is complete and green. If continuing, the smallest bounded task is adding the remaining `web`/`jwt` CLI output tests (offline JSON/Markdown, `--out`, `--output-format` precedence) to match every other command's coverage. Use `monkeypatch` mocks; no live network; confirm with `python -m pytest -q`.
