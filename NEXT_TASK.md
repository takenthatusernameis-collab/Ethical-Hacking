# Next Task

## Status: CLOSED (this session)
Baseline is NOT green in this environment: `pytest -q` → 7 failed, 5929 passed, 50 skipped. The 7 failures are Click 8.5.1 / OpenSSL 3.5.5 version drift (see TASK.md), not regressions from this session's change.

## Completed (Sun Nov 08 2026)
- Reproduced a real hostile-shape gap via a sweep of all 320 report formatters: `ethscan/ssh.py` `format_ssh_report_markdown` raised `KeyError`/`TypeError` on hostile shapes.
- Fixed with the smallest reversible change (`.get` + isinstance guards + safe coercion), added `tests/test_ssh_hostile_sweep_formatter.py`, verified 92 ssh tests pass, full suite unchanged except +2 new passing tests, ruff/mypy clean on changed files.

## Candidate (only if reproduced/justified)
- The 7 version-drift failures above are reproduced and deterministic. Fixing them is a separate concern from hostile-shape robustness: either pin Click/OpenSSL in `pyproject.toml`/CI, or adapt the affected tests to Click 8.5's merged streams and `NoArgsIsHelpError` behavior. Do not conflate with the formatter-robustness work.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls or turn maintenance into infrastructure projects.
- Verify with evidence (focused tests + `pytest -q`, ruff, mypy as appropriate).

(End of file - total 18 lines)