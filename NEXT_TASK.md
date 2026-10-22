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
- About 10 of the 53 commands still have no CLI-level failure-field check (see the counts in
  `HANDOFF_NEXT.md`).
- `python ethscan/cli.py` cannot work in this layout (pre-existing); use `python -m ethscan.cli`.

## Constraints
- Smallest reversible change; do not weaken an existing guard; turn the crash into the module's
  documented error signal.
- Keep the permanent sweeps in the repository, and prove every new check by reverting the guard of its
  own module.
- Do not commit unless explicitly asked.

## One precise next task
Extend the permanent CLI failure-field coverage to the commands still lacking it (about 10 of 53, not
covered by `test_cli_unreachable_sweep.py`, `test_cli_http_unreachable_sweep.py`,
`test_cli_trace_brute_unreachable_sweep.py`, `tests/test_cli_aggregator_unreachable_sweep.py`). For each
command: run via `CliRunner` under `no_external_network`, assert exit 0, no traceback, and the
command's own failure signal; add to the appropriate sweep file; prove by reverting the relevant guard.
