# Next task for the next agent

## Current state (verified this session)
- All ~54 ethscan commands are implemented, registered in `ethscan/cli.py`, and wired with `--format`/`--output-format [json|markdown|csv]` and `--out`.
- Every command module (`ethscan/*.py`) has a corresponding `tests/test_*.py` with healthy test-to-module line ratios (all >= ~0.7, most >1.0).
- Every command has CLI integration tests in `tests/test_cli.py`.
- `python -m pytest -q` → **3488 passed, 1 skipped** (full suite, green).
- Offline CLI end-to-end verified: `cidr`, `hash`, `validate`, `web`, `jwt`.

## This session's change
- Closed the remaining `web`/`jwt` CLI output-test gaps in `tests/test_cli.py` (+11 tests):
  - web: offline target JSON/Markdown, `--out` JSON/Markdown, `--output-format` precedence over `--format`, default-format-is-JSON.
  - jwt: offline JSON/Markdown, `--out` JSON, `--output-format` precedence over `--format`, default-format-is-JSON.
- Follows existing conventions: `CliRunner`, `monkeypatch.setattr("ethscan.cli.run_web_checks", ...)` / `run_jwt` mocks, no live network.

## Next task
There is no required next task — the codebase is complete and green.
If continuing, the smallest bounded task is a coverage audit: confirm every `ethscan` command module has CLI output-format tests covering json/markdown/csv and that test-to-module ratios remain >= ~0.7, then run `python -m pytest -q` to confirm green. Constraints: no live network; use `monkeypatch` mocks for network-dependent commands.
