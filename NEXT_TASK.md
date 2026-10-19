# Next Task for Agent

## Status
- Working tree on main (local only, ahead of origin/main)
- Tests: **3936 passed, 1 skipped** (green baseline; +4 over 3932)
- Lint: **48 ruff errors, byte-identical to the pre-change baseline** (33 BLE001 in source, 12 TRY002 in tests, 2 PLR0402 in tests/test_brute.py, 1 S110 in ethscan/cve.py:350) — intentional/unsafe to fix per constraints; unchanged
- Compilation: 57 source files compile clean via `python -m py_compile ethscan/*.py`
- CLI: `python -m ethscan --help` / `--version` OK

## Constraints (do not touch)
- Do not modify code to "fix" the 48 documented ruff errors (BLE001/TRY002/PLR0402/S110)
- Preserve baseline; avoid speculative refactors touching those lint exceptions
- Do not introduce network-dependent tests, dnspython/MD4-dependent tests
- Only fix genuine bugs with definitive proof and a failing test; only remove provably-dead code with definitive proof
- Do not delete user data, disable validation, or weaken safety controls
- Do not count control-marker-only commits as project progress

## Completed work (reference)
- 19777ff: `,cover` artifact cleanup
- c6b6fc2: web.py dead-duplicate strptime removal (1 line)
- 5cba856: ssl.py dead-duplicate strptime removal (1 line)
- bd662ea: mac.py `run_mac` DEFAULT_API_URL state leak fixed (try/finally)
- 647b886: radix.py `format_radix_report_csv` host-bits-set crash fixed (`strict=False`)
- d367897: Four CLI defects fixed (profile+keyword `--ports` crash; completion env-var name; dropped `--workers` in urlcheck; `--workers 0` unhandled `ValueError`); `get_all_ports()` helper added
- 3f64aeb: IPv4 `last_host` reports last usable host instead of broadcast; IPv6 rule aligned across `cidr.py` / `radix.py` / `validate.py`
- f5e6974: `cve --services-file` with malformed JSON no longer dies with a raw `JSONDecodeError`
- b4253bd: `parse_port_range()` rejects out-of-range ports, inverted ranges, and non-numeric tokens; 5 new tests
- (this session) `resolve --server` is no longer ignored for CNAME lookups: `resolve_cname_records()` accepts and applies `server`, `run_resolve()` forwards it. 3 new tests in `tests/test_resolve.py` + 1 end-to-end CLI test in `tests/test_cli.py`; all fail before the fix, verified by reverting the source. Suite 3936 passed/1 skipped; ruff 48 errors byte-identical.

## What remains (all verified and reproducible, deliberately not fixed)
1. **`--profile` clobbers explicitly-passed `--timeout`/`--workers`** — sentinel comparisons (`== 1.0`, `== 100`) cannot distinguish an explicit value from the default; contradicts the documented "unless explicitly set" behaviour (`cli.py:383`). Sites: `ethscan/cli.py:418-421` (`scan`), `:1602-1605` (`service`), `:2756-2759` (`cve`), `ethscan/report.py:67-70` (`_resolve_ports_and_defaults`).
   - **Reproduced:** `python -m ethscan scan --target 127.0.0.1 --profile fast --output-format json` → `timeout=0.5`; adding `--timeout 1.0` → still `timeout=0.5` (explicit value discarded).
2. Pre-existing E303 too-many-blank-lines sites (not regressions): ethscan/cli.py:3600, ethscan/validate.py:279, ethscan/cidr.py:255-256, others.
3. Documented coverage gaps (environmental/defensive, not closable within constraints): cli.py:4864 `__main__` guard; dnssec.py dnspython fallback; hash.py MD4/NTLM/PBKDF2 paths; radix.py defensive edges; network-dependent modules require live services.

## Recommended next precise task

**Fix the `--profile` sentinel-override bug so an explicitly-passed `--timeout`/`--workers` is never clobbered.**

Scope:
- Replace the `if timeout == <default>:` / `if workers == <default>:` sentinel checks at `ethscan/cli.py:418-421`, `:1602-1605`, `:2756-2759` and `ethscan/report.py:67-70` with an explicit "was this option set?" check.
- Preferred mechanism: `click.Context.get_parameter_source(ctx, "timeout")` compared against `click.core.ParameterSource.COMMANDLINE` (also treat `ENVIRONMENT` / `DEFAULT_MAP` as explicit). The commands need `@click.pass_context`; thread the resulting booleans into `report.py::_resolve_ports_and_defaults` as optional keyword args (e.g. `timeout_explicit` / `workers_explicit`) defaulting to today's sentinel behaviour so existing callers and tests keep working.
- Regression tests (must fail before the fix):
  - CLI: `scan --profile fast --timeout 1.0` → JSON report `timeout` must be `1.0`, not `0.5`.
  - CLI: `scan --profile full --workers 100` → effective workers must be `100`, not `50`.
  - CLI: `scan --profile fast` with no explicit options → still `timeout=0.5` (profile default must still apply).
  - Unit: `_resolve_ports_and_defaults(..., timeout=1.0, workers=100, profile="fast")` with the explicit flags → timeout stays `1.0`.
- Keep the change limited to the profile-default resolution and its tests.

## Verification checklist (if you select a task)
1. Reproduce the smallest failure when applicable; verify prerequisites
2. Write/add a failing test that demonstrates the issue (required for bug fixes)
3. Implement the smallest reversible fix
4. Verify focused tests related to the change
5. Run full suite: `python -m pytest -q` (must remain green; expect ≥3936 passed, 1 skipped)
6. Run lint: `python -m ruff check --output-format concise ethscan tests` (expect 48 errors, byte-identical to the current baseline — capture before/after concise output and diff it)
7. Confirm `python -m py_compile ethscan/*.py` passes
8. Confirm `git diff --stat` shows only intended changes
9. Do not claim checks passed without evidence
10. Update HANDOFF_NEXT.md, NEXT_TASK.md and TASK.md with concrete details (what changed, verified with evidence, unresolved, failed approaches if any, next precise task)

## Evidence
- Current state verified this session: 3936 passed, 1 skipped; ruff reports 48 errors (byte-identical to the pre-change baseline); all files compile clean; `resolve --server` now reaches the CNAME resolver end-to-end (pre-fix failure captured by reverting `ethscan/resolve.py`).
