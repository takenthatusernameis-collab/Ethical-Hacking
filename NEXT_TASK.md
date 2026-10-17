# Next Task for Agent

## Status (current)
- Working tree: **7 staged deletions** (`.cover` junk files), not yet committed.
- Full suite: **3891 passed, 1 skipped**. No regressions.
- `ruff check`: **2010 pre-existing errors**, unchanged. No `[tool.ruff]` config in `pyproject.toml`.
- Coverage: ~99%; all remaining gaps provably dead or optional-dep-dependent. No reachable coverage gap remains.

## Provably dead / unreachable-in-tests (do not retest)
- Same as prior HANDOFF_NEXT.md: `ntp.py:387`, `mysql.py`, `postgresql.py`, `resolve.py`, `smtp.py`, `redis.py`, `mongodb.py`, `oracle.py`, `mssql.py`, `radix.py`, `vuln.py` gaps — all unreachable or environment-dependent.

## Next precise task
1. Commit the 7 staged `.cover` deletions and push to `origin/main`; verify remote HEAD == local HEAD.
2. Then select a **bounded feature or bug fix with evidence** — coverage-hunting is exhausted and should not be resumed.

## Evidence / constraints
- Staged deletions: `git status --short` shows `D ethscan/cli.py,cover ... tests/test_trace_cli.py,cover`.
- `git ls-files | grep -i cover` returns empty.
- Do not commit unless explicitly asked (this session); preserve the staged changes for the next session/controller.