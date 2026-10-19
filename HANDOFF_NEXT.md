# Handoff to Next Agent

## What changed

**Executed the prior agent's assignment:** `ethscan/resolve.py` — `resolve --server` was silently ignored for CNAME lookups.

1. **`ethscan/resolve.py::resolve_cname_records`** — added a `server: str | None = None` parameter and applied it with `resolver.nameservers = [server]` when set, mirroring `resolve_ptr_records():108-109` and `resolve_with_dnspython():129-130`.
2. **`ethscan/resolve.py::run_resolve`** — the CNAME branch now forwards the server: `resolve_cname_records(normalized, timeout, server)` (was `resolve_cname_records(normalized, timeout)`). `run_resolve()` already accepted `server`, and the CLI already passed it (`cli.py:1296`), so the value was being dropped only inside `run_resolve`.
3. **`tests/test_resolve.py`** — 3 new tests + 2 existing mocks updated to the new signature.
4. **`tests/test_cli.py`** — 1 new end-to-end CLI test proving `resolve --server` reaches the resolver.

## What was actually verified

- **Bug reproduced pre-fix** (reverted `ethscan/resolve.py` to HEAD, then re-ran the new tests):
  - `test_resolve_cname_records_dnspython_with_server` → `TypeError: resolve_cname_records() got an unexpected keyword argument 'server'`
  - `test_run_resolve_passes_server_to_cname_lookup` → `AssertionError: assert None == ['1.1.1.1']`
  - `test_resolve_server_option_reaches_cname_resolver` (CLI) → `AssertionError: assert None == ['1.1.1.1']`
  - Result: **3 failed, 45 passed**. Fix restored afterwards; all 3 now pass.
- **Focused tests:** `python -m pytest tests/test_resolve.py tests/test_cli.py -q` → **all pass** (`tests/test_resolve.py` 47 passed; new CLI test 1 passed)
- **Full suite:** `python -m pytest -q` → **3936 passed, 1 skipped, 2 warnings** (baseline 3932 passed/1 skipped; +4, no regressions)
- **Lint:** `python -m ruff check --output-format concise ethscan tests` → **48 errors**, code multiset identical to baseline (33 BLE001, 12 TRY002, 2 PLR0402, 1 S110); none in the touched code paths
- **Compilation:** `python -m py_compile ethscan/*.py` → clean
- **CLI smoke:** `python -m ethscan --version` → `python -m ethscan, version 0.1.0`; `python -m ethscan resolve --help` → exit 0
- **Scope:** `git diff --stat` → only `ethscan/resolve.py`, `tests/test_resolve.py`, `tests/test_cli.py`

## What remains unresolved

1. **`--profile` clobbers an explicitly-passed `--timeout`/`--workers`** (highest-value remaining). Sentinel comparisons (`== 1.0`, `== 100`) cannot distinguish "user passed `--timeout 1.0`" from "user passed nothing", contradicting the documented "unless explicitly set" behaviour in the `--profile` help text (`cli.py:383`).
   - Sites: `ethscan/cli.py:418-421` (`scan`, sentinels `1.0`/`100`), `ethscan/cli.py:1602-1605` (`service`, sentinels `3.0`/`50`), `ethscan/cli.py:2756-2759` (`cve`, sentinels `3.0`/`50`), `ethscan/report.py:67-70` (`_resolve_ports_and_defaults`, sentinels `1.0`/`100`).
   - **Reproduced this session:** `python -m ethscan scan --target 127.0.0.1 --profile fast --output-format json` → `timeout=0.5` (correct); adding `--timeout 1.0` → still `timeout=0.5` (bug — the explicit 1.0 is discarded).
   - The same shape also applies to `--workers` (e.g. `--profile full --workers 100` → overwritten with 50).
2. Pre-existing E303 too-many-blank-lines sites (not regressions): `ethscan/cli.py:3600`, `ethscan/validate.py:279`, `ethscan/cidr.py:255-256`, others.
3. Documented coverage gaps (environmental/defensive, not closable within constraints): `cli.py:4864` `__main__` guard; `dnssec.py` dnspython fallback; `hash.py` MD4/NTLM/PBKDF2 paths; `radix.py` defensive edges; network-dependent modules need live services.

## Failed approaches / evidence

- None this session. The prior session's `--ports 70000` OverflowError claim remains **not reproducible** — do not re-attempt without new evidence.
- IPv6 `last_host == network[-2]` was already rejected as incorrect (IPv6 has no broadcast address); that rule was fixed in 3f64aeb.

## Constraints

- Do not modify code to "fix" the 48 documented ruff errors (BLE001/TRY002/PLR0402/S110)
- Preserve baseline; avoid speculative refactors touching those lint exceptions
- Do not introduce network-dependent tests, dnspython/MD4-dependent tests
- Only fix genuine bugs with definitive proof and a failing test; only remove provably-dead code with definitive proof
- Do not delete user data, disable validation, or weaken safety controls
- Do not count control-marker-only commits as project progress

## Next precise task

**Fix the `--profile` sentinel-override bug so an explicitly-passed `--timeout`/`--workers` is never clobbered.**

Concrete scope:
- In `ethscan/cli.py` (`scan`, `service`, `cve`) and `ethscan/report.py::_resolve_ports_and_defaults`, replace the `if timeout == <default>:` / `if workers == <default>:` sentinel checks with an "was this option explicitly set?" check.
- Preferred mechanism: `click.Context.get_parameter_source(ctx, "timeout")` → compare against `click.core.ParameterSource.COMMANDLINE` (also treat `ENVIRONMENT`/`DEFAULT_MAP` as explicit). This requires the commands to receive the click context (`@click.pass_context`) and to thread the resulting booleans down to `report.py::_resolve_ports_and_defaults` (e.g. extra keyword args `timeout_explicit` / `workers_explicit`, defaulting to the current sentinel behaviour so existing callers and tests keep working).
- Regression tests (must fail before the fix):
  - CLI: `scan --profile fast --timeout 1.0` → the JSON report's `timeout` must be `1.0`, not `0.5`.
  - CLI: `scan --profile full --workers 100` → the effective worker count must be `100`, not `50`.
  - `scan --profile fast` with no explicit options → still `timeout=0.5` (profile default must still apply).
  - Unit: `_resolve_ports_and_defaults(..., timeout=1.0, workers=100, profile="fast")` with the explicit flags set → timeout stays `1.0`.
- Verification: `python -m pytest -q` (≥3936 passed, 1 skipped), `python -m ruff check --output-format concise ethscan tests` (48 errors, identical code multiset), `python -m py_compile ethscan/*.py`, `git diff --stat` limited to intended files. Update HANDOFF_NEXT.md / TASK.md / NEXT_TASK.md on completion.

Evidence: current state fully verified above; `resolve --server` now reaches the CNAME resolver end-to-end.

(End of file - total 74 lines)
