# Task
Date: Thu Nov 05 2026

## Current state
- HEAD (committed): `c9f228c`. Working tree has uncommitted local changes across sessions (including this session).
- Tests: 5869 passed, 53 skipped, 0 failed. (Previously 5868; +1 new `test_an_out_of_range_workers_option_does_not_start_a_probe` this session.)
- Formatter hostile-shape sweep is complete across all modules in scope: `ping`, `osdetect`, `trace`, `subdomains`, `stale`, `radix`, `completion`, `config`, `cidr`, `dnsbrute`, `passwords`, `validate`, `report`, plus earlier sessions `service`, `scanner`, `recon`, `resolve`, `s3`, `wifi`, `brute`, `cert`, `cve`, `dns`, `dnssec`, `ftp`, `fuzz`, `geo`, `hash`, `headers`, `http`, `jwt`, `ldap`, `mac`, `memcached`, `mongodb`, `mssql`, `mysql`, `netbios`, `nmap`, `ntp`, `oracle`, `postgresql`, `redis`, `smb`, `smtp`, `snmp`, `ssh`, `ssl`, `subtake`, `tls`, `urlcheck`, `vuln`, `web`, `whois`. ruff clean; mypy ethscan clean (59 source files).

## This session
- Found a permanent-test gap in the int-option range sweep: the 17 `--workers` options of the CLI are declared as `click.IntRange(1, None)` but were not named in `INT_OPTION_RANGES`, so `test_every_int_option_of_the_cli_is_range_checked` did not cover them. No source change was needed — the options already refuse out-of-range values (verified: `--workers 0` exits 2 with a clean single-line usage error on all 17 commands, and never starts a probe).
- Added the 17 `--workers` entries to `INT_OPTION_RANGES` in `tests/test_cli.py` so the coverage assertion names them.
- Added `test_an_out_of_range_workers_option_does_not_start_a_probe` (parametrized over the 17 entries) asserting that a value below the minimum is refused as a usage error before any network access happens (socket.connect/connect_ex/sendto/getaddrinfo are tripwires).
- Verified: `python3 -m pytest -q` → 5869 passed, 53 skipped, 0 failed (was 5868); `python3 -m ruff check .` → all checks passed; `python3 -m mypy ethscan` → Success, 59 source files.

## Blockers
- None.

## Next task
- None — every int option of the CLI is now range-checked and covered by a permanent test.
- Run: `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

(End of file - total 21 lines)