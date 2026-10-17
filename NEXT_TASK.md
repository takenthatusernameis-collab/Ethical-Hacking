# Next Task for Agent

## Status
- `ethscan/__main__.py` → 100% (3/3); `ethscan/main.py` → 100% (3/3).
- `ethscan/snmp.py` → **100%** (0 missing): the 5 previously-missing lines (247, 319, 324, 357, 406) are covered by existing tests; no source changes.
- `ethscan/netbios.py` → **100%** (0 missing): the 10 previously-missing lines (275, 342, 383, 390, 410-416, 615, 645) are all reachable and now covered by 8 new targeted tests in `tests/test_netbios.py`; no source changes.
- `ethscan/mssql.py` → **98%** (7 missing, all provably unreachable); line 404 covered by 1 new test in `tests/test_mssql.py`.
- `ethscan/radix.py` → **97%** (9 missing, all provably unreachable); not coverable without modifying `ethscan/`.
- `ethscan/cli.py` → **99%** (21 missing, all unreachable-in-tests): 607-635 is the body of the orphaned/superseded `hash` function at line 605 (the active `hash` command is `hash_cmd` at line 2906; `cli.commands["hash"].callback` is `hash_cmd`); 4639 is the `if __name__ == "__main__": cli()` guard, never triggered because tests invoke via `__main__.py` / `CliRunner`.
- Full suite: **3887 passed, 1 skipped** (baseline 3873; +14 net new tests across mssql/netbios).
- Total `ethscan/` missing lines: **72** (was 83) — every remaining missing line is documented below as provably unreachable or unreachable-in-tests.

## Provably dead / unreachable-in-tests code (intentionally left uncovered — do not retest; no `ethscan/` source changes)
Previously documented: `ntp.py:387`, `postgresql.py:201`, `smtp.py:222`, `resolve.py:188`, `vuln.py` (37, 57-62, 555-556, 904, 1047), `mongodb.py:205-206`, `oracle.py:304-305`, `redis.py:55-56`, `hash.py:226`, `mysql.py:107/111/150`; env-dep `brute.py:13`, `dns.py:155`, `hash.py:34-35/60/83`, `dnssec.py:11-16`.

Newly characterized this session:
- `ethscan/mssql.py`:
  - `389-391` `except struct.error` — `struct.unpack("!BBHHBH", data[:9])` always gets exactly 9 bytes (guard `len(data) < 9` at line 379) → never raises.
  - `432-433` / `455-456` `except Exception` around `decode("utf-8", errors="replace")` → never raises for bytes input.
- `ethscan/radix.py`:
  - `149-150` `if net.version != last.version` — mixed versions crash at `sorted()` (line 141) before the loop; same-version makes `!=` always False.
  - `153-154` `except Exception: collapsed = None` — `collapse_addresses` never raises for same-version networks.
  - `158-161` `elif last.overlaps(net):` — overlapping CIDR blocks always contain one another → `collapse_addresses` returns 1 → branch never fires.
  - `219-220` `except ValueError` around `ip_network(f"{start}/{range_prefix}", strict=False)` — `range_prefix` always in `[0, max_bits]`, `start` valid → never raises.
- `ethscan/cli.py`:
  - `607-635` body of the line-605 `hash` function — superseded duplicate; the registered `hash` command is `hash_cmd` (verified `cli.commands["hash"].callback` is `hash_cmd`; `python -m ethscan hash --help` shows `hash_cmd`'s options). Body never executed by any test.
  - `4639` `cli()` under `if __name__ == "__main__":` — only reached by running `ethscan/cli.py` directly as `__main__`, which tests never do (entry point is `ethscan.__main__`).

## Coverage effort: COMPLETE
Every `ethscan/` module is now at 100% coverage or has all remaining missing lines characterized as provably unreachable / unreachable-in-tests and documented above. No coverable gaps remain.

## Next precise task
None — coverage characterization is complete. If resuming, the only remaining work would be committing the test additions (`tests/test_mssql.py`, `tests/test_netbios.py`) and updating `README.md`/changelog if desired; no further `ethscan/` source or test gaps exist.

Verification (already done): full suite 3887 passed, 1 skipped; `python -m ruff check tests/test_mssql.py tests/test_netbios.py` adds no new violations (all 7 netbios + mssql import-sort findings are pre-existing in untouched code).
