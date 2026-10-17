# Next Task for Agent

## Status
- `ethscan/__main__.py` coverage → **100%** (3/3), added `test_python_m_ethscan_dunder_main_help_runs` to `tests/test_main.py` using `runpy.run_module("ethscan.__main__", run_name="__main__")` with `ethscan.cli.cli` patched. `tests/test_main.py`: 10 passed. ruff on `tests/test_main.py` clean.
- `ethscan/main.py` remains 100% (3/3).
- Full suite: **3873 passed, 1 skipped**. `ethscan/__main__.py` → 100%.
- Remaining sub-100% `ethscan/` modules (missing lines): `snmp.py` 5 (247, 319, 324, 357, 406), `mssql.py` 8 (389-391, 404, 432-433, 455-456), `radix.py` 9 (149-150, 153-154, 158-161, 219-220), `netbios.py` 10 (275, 342, 383, 390, 410-416, 615, 645), `cli.py` 21 (607-635, 4639).

## Provably dead code (intentionally left uncovered — do not retest; no `ethscan/` source changes)
- `ethscan/ntp.py:387` — `if mon_resp.get("error"):` inside `else` of same check; `mon_resp` never mutated between checks → always False.
- `ethscan/postgresql.py:201` — `if not msg_type: break` where `msg_type = data[pos:pos + 1]` and loop condition is `pos < n`; 1-byte slice always truthy.
- `ethscan/smtp.py:222` — `sock.close()` in outer `except`; unreachable on the success path.
- `ethscan/resolve.py:188` — all A/AAAA/CNAME/PTR types handled by earlier branches; `elif rtype_upper in all_supported: continue` never fires.
- `ethscan/vuln.py` (37, 57-62, 555-556, 904, 1047) — defensive branches confirmed unreachable.
- `ethscan/mongodb.py:205-206` — `except: pass` around `bytes.decode("utf-8", errors="replace")`, which never raises for bytes input.
- `ethscan/oracle.py:304-305` — same `decode(errors="replace")` pattern, never raises.
- `ethscan/redis.py:55-56` — `elif host.endswith("]")` inside bracketed-IPv6 branch; `host.startswith("[") and "]:" in host` guarantees `bracket_end > 0`, so the `elif` never fires.
- `ethscan/hash.py:226` — PBKDF2+`pepper` path, but `_compute_pbkdf2_hash` raises for any algorithm without a hashlib name (e.g. `ntlm`) before the HMAC `name is None` check runs.
- `ethscan/hash.py:34-35/60/83` — md4 block; environment-dependent (md4 unavailable in this build).
- `ethscan/mysql.py:107`/`111`/`150` — `if not payload:` impossible after `len(data) >= 5` guard; `pos >= len(payload)` impossible with `pos=0`; `salt1_len < 0` always false.
- `ethscan/brute.py:13` — `paramiko` import; environment-dependent.
- `ethscan/dns.py:155` — dnspython path; environment-dependent.
- `ethscan/dnssec.py:11-16` — dnspython imports; environment-dependent.

## Next precise task
Assess `snmp.py` (5 missing lines: 247, 319, 324, 357, 406) — the smallest remaining sub-100% module not yet characterized as dead-code or environment-dependent. Read the surrounding control flow at each missing line, cover any achievable gap with a minimal targeted unit test in `tests/test_snmp.py` (without modifying `ethscan/`), and document any provably-unreachable branches above.

Verification: targeted module tests pass; ruff on modified test files passes; full suite remains ≥3873 passed, 1 skipped.
