What changed:
- Coverage: `ethscan/s3.py` 98% → **100%** (0 missing; lines 136 and 145-146 now covered) via 2 new tests in `tests/test_s3.py`:
  - `test_resolve_s3_endpoint_hostname_falsy_returns_none` — monkeypatches `_build_s3_url` to return a hostless URL (`https:///`), exercising the `if not hostname: return None` branch.
  - `test_resolve_s3_endpoint_setdefaulttimeout_none_oserror` — injects a fake `socket` whose `setdefaulttimeout(None)` raises `OSError` in the `finally` block, exercising `except OSError: pass`.
- Coverage: `ethscan/fuzz.py` 99% → **100%** (0 missing; line 79 urlopen success path now covered) via 1 new test in `tests/test_fuzz.py`:
  - `test_fuzz_path_success` — monkeypatches `ethscan.fuzz.urllib.request.urlopen` to return a fake response with `status=200`, exercising the success return.
- `tests/test_fuzz.py`: removed 3 pre-existing unused imports (`pytest`, `ThreadPoolExecutor`, `MagicMock`) and re-sorted the import block (added `fuzz_path`) so `ruff` passes on the modified file.
- No files under `ethscan/` were modified.

What was verified:
- `tests/test_s3.py`: 49 passed; `tests/test_fuzz.py`: 25 passed.
- `python -m ruff check tests/test_fuzz.py tests/test_s3.py` → all checks passed.
- Full suite: **3872 passed, 1 skipped** (was 3869; +3 new tests; no regressions).
- `ethscan/s3.py` → 100%; `ethscan/fuzz.py` → 100%.

What remains unresolved:
- Remaining sub-100% modules are predominantly provably unreachable/dead-code or environment-dependent:
  - Dead/unreachable (documented in TASK.md): `ntp.py:387`, `postgresql.py:201`, `smtp.py:222`, `vuln.py` (37, 57-62, 555-556, 904, 1047), `resolve.py:188` (confirmed provably unreachable this session — all A/AAAA/CNAME/PTR types are handled by earlier branches, so `elif rtype_upper in all_supported: continue` never fires).
  - Environment-dependent (optional deps not installed here): `brute.py:13` (`paramiko` import), `dns.py:155` (dnspython path).
  - Small defensive/decode gaps to characterize: `cli.py` (607-635, 4639), `dnssec.py:11-16` (dnspython imports), `hash.py` (34-35, 60, 83, 226), `mssql.py` (389-391, 404, 432-433, 455-456), `mongodb.py:205-206`, `mysql.py:107/111/150`, `netbios.py` (10 lines), `oracle.py:304-305`, `radix.py` (9 lines), `redis.py:55-56`.
- Avoid modifying `ethscan/` source to force coverage of provably unreachable code.

Which approaches failed and why:
- `resolve.py:188`: provably unreachable (all supported record types handled above it) — skip, document as dead code.
- `brute.py:13` / `dns.py:155`: environment-dependent (optional deps not installed) — skip unless deps are installed.

Next task:
- Characterize each remaining sub-100% gap: read the surrounding control flow, confirm provably-unreachable branches and add them to the documented dead-code list in TASK.md, and cover any gap that proves achievable with a minimal targeted test (without modifying `ethscan/`).
- Verify: full suite ≥3872 passed, 1 skipped; `ruff` clean on any modified test files.
