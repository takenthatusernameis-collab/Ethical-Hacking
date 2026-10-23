# NEXT TASK

## Status: COMPLETE

### Previously assigned task: `cve` and `osdetect` bad-document crashes
**Done — already committed in the baseline (`8b4da94`, HEAD).**
- `cve --services-file` with `{"results": [{"port": 22, "banner": 5}]}` -> exit 0, notes name the problem,
  no traceback (`ethscan/cve.py:344-365`).
- `osdetect --banners-file` with `{"results": "abc"}` -> exit 0, note
  `Banners data holds no 'results' list` (`ethscan/cli.py:2310-2341`).
- Covered by 3 checks in `tests/test_cli_aggregator_unreachable_sweep.py`; verified at the command line
  and by the test suite (12 passed in that file).

### This session: `socket.setdefaulttimeout()` process-wide side effect
**Done in the worktree, not committed.** Every resolution helper that called `socket.setdefaulttimeout()`
now saves the previous default timeout and restores it in a `finally`, so the default timeout no longer
leaks to later tests: `ethscan/dns.py`, `ethscan/resolve.py`, `ethscan/stale.py`, `ethscan/subtake.py`,
`ethscan/s3.py`, `ethscan/subdomains.py`, `ethscan/dnssec.py` (7 modules, 13 call sites).

### What was actually verified
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **5125 passed, 48 skipped, 3 warnings** (pre-existing `test_main.py` runpy
  warnings).
- Each of the 7 new restoration tests was proved by mutation (revert guard -> check fails -> restore ->
  check passes); all guards restored, no mutation artifacts in the diff.
- Updated 2 existing tests that coupled to the old behavior: `tests/test_dnssec.py:806`,
  `tests/test_s3.py:961`.

## What remains unresolved

- **None.** The CLI failure-field coverage task is complete: all 53 CLI commands now have a
  permanent CLI-level failure-field check. The 10 commands that do not open a transport of their
  own are covered by `tests/test_cli_offline_sweep.py` and `tests/test_cli_offline_input_sweep.py`;
  the other 43 are covered by the four transport sweep files. A cross-reference of every
  `@cli.command()` against the sweep files confirms 53/53 covered.
- `python ethscan/cli.py` cannot work in this layout (pre-existing); use `python -m ethscan.cli`.

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash into the module's
  documented error signal.
- Keep the permanent sweeps in the repository, and prove every new check by reverting the guard of
  its own module.
- Do not commit unless explicitly asked.

## One precise next task

- **No outstanding task from this handoff.** The CLI failure-field coverage work is done and
  verified (`python -m pytest tests/` -> 5158 passed, 48 skipped; `python -m ruff check ethscan/
  tests/` -> all checks passed). Do not re-add checks that already exist.
