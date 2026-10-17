What changed:
- Coverage: `ethscan/__main__.py` 67% → **100%** (0 missing; line 6 `cli()` guard now covered) via 1 new test in `tests/test_main.py`:
  - `test_python_m_ethscan_dunder_main_help_runs` — runs `runpy.run_module("ethscan.__main__", run_name="__main__")` with `ethscan.cli.cli` patched to a counting stub that raises `SystemExit(0)`, asserting `cli()` is invoked exactly once by the `__main__` guard.
- `tests/test_main.py`: added `check=False` to the two pre-existing `subprocess.run` calls (lines 51, 61) so the modified file is `ruff`-clean (behavior-identical; `check=False` is the default).
- No files under `ethscan/` were modified.

What was verified:
- `tests/test_main.py`: 10 passed (9 pre-existing + 1 new).
- `python -m ruff check tests/test_main.py` → all checks passed.
- Full suite: **3873 passed, 1 skipped** (was 3872; +1 new test; no regressions).
- `ethscan/__main__.py` → 100%; `ethscan/main.py` → 100%.

Characterized remaining sub-100% gaps (all provably unreachable or environment-dependent; no `ethscan/` source changes):
- Dead/unreachable defensive branches:
  - `ntp.py:387`, `postgresql.py:201`, `smtp.py:222`, `resolve.py:188`, `vuln.py` (37, 57-62, 555-556, 904, 1047) — previously documented.
  - `mongodb.py:205-206` — `except: pass` around `bytes.decode("utf-8", errors="replace")`, which never raises for bytes input.
  - `oracle.py:304-305` — same `decode(errors="replace")` pattern, never raises.
  - `redis.py:55-56` — `elif host.endswith("]")` inside the bracketed-IPv6 branch; `host.startswith("[") and "]:" in host` guarantees `host.find("]:") >= 1`, so `bracket_end > 0` is always true and the `elif` never fires.
  - `hash.py:226` — reached only via PBKDF2 + pepper, but `_compute_pbkdf2_hash` raises for any algorithm without a hashlib name (e.g. `ntlm`) before the HMAC `name is None` check can run.
  - `mysql.py:107` / `111` / `150` — `if not payload:` impossible after `len(data) >= 5` guard; `pos >= len(payload)` impossible with `pos=0` and non-empty payload; `salt1_len < 0` impossible (`null1 - salt1_start >= 0` or default 8).
- Environment-dependent (optional deps not installed): `brute.py:13` (`paramiko`), `dns.py:155` (dnspython), `hash.py:34-35/60/83` (md4 unavailable), `dnssec.py:11-16` (dnspython imports).

What remains unresolved (achievability not yet determined):
- `snmp.py` (5 missing: 247, 319, 324, 357, 406) — smallest remaining candidate gap.
- `mssql.py` (8 missing: 389-391, 404, 432-433, 455-456).
- `radix.py` (9 missing: 149-150, 153-154, 158-161, 219-220).
- `netbios.py` (10 missing: 275, 342, 383, 390, 410-416, 615, 645).
- `cli.py` (21 missing: 607-635, 4639).

Which approaches failed and why:
- `mongodb.py:205-206`, `oracle.py:304-305`, `redis.py:55-56`, `hash.py:226`, `mysql.py:107/111/150`: provably unreachable (confirmed by control-flow inspection and `decode(errors="replace")` empirical test) — skip, document as dead code; do not modify `ethscan/` to force coverage.
- `brute.py:13` / `dns.py:155` / `hash.py:34-35/60/83` / `dnssec.py:11-16`: environment-dependent (optional deps not installed) — skip unless deps are installed.

Next task:
- Assess `snmp.py` (5 missing lines: 247, 319, 324, 357, 406) — the smallest remaining sub-100% module not yet characterized as dead/env-dep. Read the surrounding control flow at each missing line, cover any achievable gap with a minimal targeted unit test in `tests/test_snmp.py` (without modifying `ethscan/`), and document any provably-unreachable branches above.
- Verify: full suite ≥3873 passed, 1 skipped; `ruff` clean on any modified test files.
