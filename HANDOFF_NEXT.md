# HANDOFF: state for the next agent

## What changed this session

**Nothing.** The working tree is clean (`git status` empty, `git diff --stat` empty). No source or test file was modified. The task handed off from the previous session was inspected end-to-end and found already complete.

## What was actually verified

- Reproduced all six crash sites named in the previous handoff, patching the transport seam to raise a `RuntimeError` (an unnamed type) and calling the public `run_*`:
  - `ping.run_ping("127.0.0.1", count=1)` -> reported, probe error `hostile transport`.
  - `osdetect.run_osdetect("127.0.0.1", ports=[80])` -> reported, probe error `hostile transport`.
  - `resolve.run_resolve("example.com", record_types=["A"])` -> reported, `records["A"] == []`.
  - `dns.run_dns("example.com")` -> reported, `records["A"] == []`.
  - `stale.run_stale(["example.com"])` -> reported, entry `A == []`, `stale is True`.
  - `subdomains.run_subdomains("example.com", subdomains=["www"])` -> reported, `resolved == []`.
  None of them raised. The guards are in place at every site the handoff named.
- The six commands are in the permanent sweep `tests/test_protocol_hostile_sweep.py` (`test_ping_transport_failure_is_reported_not_raised`, `test_osdetect_...`, `test_resolve_...`, `test_dns_...`, `test_stale_...`, `test_subdomains_...` at lines 537-625).
- Each module carries its own regression test next to its tests: `tests/test_ping.py:1101`, `tests/test_osdetect.py:829`, `tests/test_resolve.py:948`, `tests/test_dns.py:648`, `tests/test_stale.py:379`, `tests/test_subdomains.py:775`.
- `tests/test_cli_sweep_coverage.py` -> 57 passed. Every CLI command is named in a CLI-level sweep, so no command can be silently dropped.
- `python -m pytest tests/` -> **5158 passed, 49 skipped, 3 warnings** (the 3 warnings are the pre-existing `test_main.py` runpy ones). Identical to the baseline the previous handoff recorded. No regressions.

## What remains unresolved

**None on the handed-off task.** The crash-guard domain is complete across all 53 CLI commands: module-level hostile sweeps, CLI-level unreachable/offline sweeps, and offline-input sweeps.

A survey of the remaining narrow `except` tuples in the rest of the codebase (`ethscan/cert.py`, `geo.py`, `mac.py`, `s3.py`, `service.py`, `smb.py`, `ssh.py`, `tls.py`, `ssl.py`, `dnssec.py`, `dnsbrute.py`, `ftp.py`, `scanner.py`, `mongodb.py`, `mssql.py`, `mysql.py`, `netbios.py`, `oracle.py`, `postgresql.py`, `resolve.py`) found no demonstrable escape: patching the named transport seam to raise a `RuntimeError` in each case is reported through the module's own failure field, never raised. They are left untouched because there is no evidence of a crash to fix and the project convention is smallest-reversible-change.

## Approaches that failed and why

- **None.** No approach was repeated blindly. The previous handoff's evidence was stale: it described crash sites that had already been guarded in an earlier session. The correct action was to verify rather than to re-apply the fix.

## One precise next task

- **No outstanding task.** If a new assignment exists, inspect `git status`/`git diff` first. Do not re-add guards that already exist, and do not broaden `except` tuples that have no demonstrated escape path.

(End of file - total 52 lines)