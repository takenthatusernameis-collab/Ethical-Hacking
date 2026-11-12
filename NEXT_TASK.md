# Next Task

## Status
Session 113 completed the bounded test-coverage task: added 9 missing `test_<cmd>_invalid_target_is_usage_error` CLI tests for `ftp`, `smtp`, `ntp`, `snmp`, `ldap`, `netbios`, `smb`, `redis`, `memcached`. All 9 commands already rejected empty/unusable targets as usage errors (exit 2) but lacked the corresponding test that exists for every other target-taking command. `pytest` 6117 passed (+9), `mypy` clean, `ruff` clean.

## One precise next task
No further task identified this session. If a new task is needed, inspect `TASK.md`, the README, and recent git history for the next bounded, high-value improvement.

## Notes
- Keep README examples evidence-based; do not invent outputs.
- Do not weaken CLI validation or tests. Preserve oracle/postgresql in-band exit-0 contract vs usage-error exits elsewhere.

(End of file - total 13 lines)