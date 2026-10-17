What changed:
- Added targeted unit tests to improve coverage without modifying `ethscan/`:
  - `tests/test_ssl.py`: added `test_wrap_socket()` to exercise `_wrap_socket()` success path (mocked network), bringing `ethscan/ssl.py` from 98% (4 missing) to **100%**.
  - `tests/test_redis.py`: added `test_normalize_target_ipv6_non_numeric_port_suffix()` and `test_normalize_target_ipv6_malformed_port_with_trailing_bracket()` to cover IPv6 target normalization edge cases.
  - `tests/test_s3.py`: added `test_check_bucket_public_403_direct_response()` to cover the 403 branch in the urlopen success path (not HTTPError), reducing `ethscan/s3.py` missing from 6 to 3 (136, 145-146 remain; hard-to-trigger defensive/finally cases).
  - `tests/test_mongodb.py`: added `test_parse_buildinfo_handles_decode_edge_case()` with minimal inputs; cleaned up a stray test name/import issue.
- Fixed minor ruff issues in modified test files (`tests/test_redis.py`, `tests/test_s3.py`, `tests/test_ssl.py`, `tests/test_mongodb.py`) — all modified test files pass ruff checks after fixes.

What was verified:
- Full suite: **3869 passed, 1 skipped** (was 3860 passed, 1 skipped in prior main.py coverage completion; +9 tests total across added cases; no regressions).
- Targeted module coverage after changes: `ethscan/ssl.py` → 100% (0 missing). `ethscan/s3.py` → 98% (3 missing: 136, 145-146). `ethscan/redis.py` behavior unchanged (remains at 99% with 2 unreachable-like lines 55-56). `ethscan/mongodb.py` remains at 99% (2 missing: 205-206). `ethscan/mysql.py` remains at 99% (3 missing: 107, 111, 150). `ethscan/oracle.py` remains at 99% (2 missing: 304-305). `ethscan/resolve.py` remains at 99% (1 missing: 188). `ethscan/hash.py` remains at 98% (5 missing: 34-35, 60, 83, 226; environment/flow-dependent). `ethscan/dnssec.py` remains at 98% (6 missing: 11-16; dnspython-dependent imports).
- `python -m ruff check` on modified test files: all pass.

What remains unresolved:
- Unreachable/defensive branches and environment-dependent lines persist in several modules (as listed above). These are not easily coverable without changing environment or making brittle test harnesses. Avoid modifying `ethscan/` source to "cover" provably unreachable code.
- Remaining achievable small gaps from the prior list: `ftp.py` is already 100%; others with small gaps mostly have defensive branches (e.g. mysql/oracle/mongodb have try-except decode paths that are effectively unreachable with `errors='replace'`, redis has a nested IPv6 normalization branch that is hard to trigger given the guard conditions).

Which approaches failed and why:
- Attempting to hit some "hard" branches in redis normalization revealed they are structurally unreachable given the outer condition checks (bracket_end <= 0 case cannot occur when both startswith('[') and ']:' in host hold in the specific form). Chose to add practical IPv6 cases that do execute real logic instead of contorting inputs.
- Coverage of subprocess-executed `__main__` was already handled via `runpy.run_module` in-process (prior task). Did not regress that.

Next task:
- Continue coverage improvements by tackling modules with the smallest remaining achievable gaps. Strong candidates: `s3.py` (lines 136, 145-146 — test hostname falsy case in `_resolve_s3_hostname` and the `setdefaulttimeout(None)` OSError path if feasible with mocking), then `resolve.py` (line 188 — unreachable given current control flow; skip unless a clean way emerges), or look to other modules not yet at 100%. Prefer adding minimal targeted unit tests in corresponding test files without modifying `ethscan/`. Verify: targeted tests pass, ruff on modified test files passes, full suite remains ≥3869 passed, 1 skipped.
