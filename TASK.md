# Task

Date: 2026-10-19T15:10:00Z
Status: Prior agent's assignment executed and verified (`resolve --server` ignored for CNAME lookups). New bounded task selected and documented in HANDOFF_NEXT.md / NEXT_TASK.md.
Branch: main (local, up to date with origin/main; working tree has the changes for this session)

## Prior work completed (reference)

- 19777ff: `,cover` artifact cleanup (113 files + .gitignore update)
- c6b6fc2: Removed provably-dead duplicate strptime in `ethscan/web.py` (1 line)
- 5cba856: Removed provably-dead duplicate strptime in `ethscan/ssl.py` (1 line)
- bd662ea: Fixed `ethscan/mac.py::run_mac` DEFAULT_API_URL state leak on early-return path
- 647b886: Fixed `ethscan/radix.py::format_radix_report_csv` crash on CIDRs with host bits set (`strict=False`)
- (previous session) Four CLI defects fixed: profile+keyword `--ports` crash; completion env-var name for hyphenated/dotted program names; dropped `--workers` in urlcheck; `--workers 0` unhandled `ValueError`; `get_all_ports()` helper. 16 tests added. Suite 3924 passed/1 skipped; ruff 48 errors byte-identical.
- 3f64aeb: IPv4 `last_host` reports last usable host instead of broadcast; IPv6 rule aligned across `cidr.py` / `radix.py` / `validate.py`. 3 new tests, existing assertions corrected. 3927 passed/1 skipped.
- f5e6974: `cve --services-file` with malformed JSON no longer dies with a raw `JSONDecodeError`; emits the graceful note and returns exit 0.
- b4253bd: `parse_port_range()` now rejects out-of-range ports, inverted ranges, and non-numeric tokens, matching `ethscan/validate.py::_validate_port_spec`. 5 new tests. 3932 passed/1 skipped.

## What changed (this session)

**Fixed the prior agent's assigned task: `resolve --server` was silently ignored for CNAME lookups.**

1. **`ethscan/resolve.py::resolve_cname_records`** — added `server: str | None = None` and applied it via `resolver.nameservers = [server]` when set, mirroring `resolve_ptr_records():108-109` and `resolve_with_dnspython():129-130`. Previously the user-supplied `--server` never reached the CNAME query, so the lookup always used the system resolvers.

2. **`ethscan/resolve.py::run_resolve`** — the CNAME branch now forwards the server: `resolve_cname_records(normalized, timeout, server)` (was `resolve_cname_records(normalized, timeout)`). `run_resolve()` already accepted `server` and the CLI already passed it (`cli.py:1296`), so the value was dropped only inside `run_resolve`.

3. **`tests/test_resolve.py`** — 3 new tests:
   - `test_resolve_cname_records_dnspython_with_server` — the configured `nameservers` are applied to the CNAME resolver.
   - `test_resolve_cname_records_dnspython_without_server_keeps_default` — without a custom server the resolver keeps the system resolvers (guards against unconditional assignment).
   - `test_run_resolve_passes_server_to_cname_lookup` — `run_resolve()` forwards the server to the CNAME resolver.
   Plus 2 existing mocks updated to the new `resolve_cname_records(domain, timeout, server)` signature.

4. **`tests/test_cli.py`** — `test_resolve_server_option_reaches_cname_resolver`: end-to-end proof through the CLI that `resolve --types CNAME --server 1.1.1.1` configures the resolver's `nameservers`.

## What was actually verified (this session)

- **Pre-fix failure captured:** reverted `ethscan/resolve.py` to HEAD and re-ran the new tests → 3 failed / 45 passed:
  - `test_resolve_cname_records_dnspython_with_server` → `TypeError: resolve_cname_records() got an unexpected keyword argument 'server'`
  - `test_run_resolve_passes_server_to_cname_lookup` → `AssertionError: assert None == ['1.1.1.1']`
  - `test_resolve_server_option_reaches_cname_resolver` → `AssertionError: assert None == ['1.1.1.1']`
  Fix restored afterwards; all 3 pass.
- **Focused tests:** `python -m pytest tests/test_resolve.py -q` → 47 passed; new CLI test → 1 passed
- **Full suite:** `python -m pytest -q` → **3936 passed, 1 skipped, 2 warnings** (baseline 3932 passed/1 skipped; +4, no regressions)
- **Lint:** `python -m ruff check --output-format concise ethscan tests` → **48 errors**, code multiset identical to baseline (33 BLE001, 12 TRY002, 2 PLR0402, 1 S110); none in the touched code paths
- **Compilation:** `python -m py_compile ethscan/*.py` → clean
- **CLI smoke:** `python -m ethscan --version` → `version 0.1.0`; `python -m ethscan resolve --help` → exit 0
- **Scope:** `git diff --stat` → only `ethscan/resolve.py`, `tests/test_resolve.py`, `tests/test_cli.py` (plus the handoff docs)

## Current state

- Tests: 3936 passed, 1 skipped (green)
- Lint baseline: 48 documented intentional errors — unchanged in kind/count
- Next task selected and documented in HANDOFF_NEXT.md and NEXT_TASK.md

## Constraints

- Do not modify code to "fix" the 48 documented ruff errors (BLE001/TRY002/PLR0402/S110)
- Preserve baseline; avoid speculative refactors touching those lint exceptions
- Do not introduce network-dependent tests, dnspython/MD4-dependent tests
- Only fix genuine bugs with definitive proof and a failing test; only remove provably-dead code with definitive proof
- Do not delete user data, disable validation, or weaken safety controls
- Do not count control-marker-only commits as project progress

## Failed approaches / evidence

- None this session. The prior session's `--ports 70000` OverflowError claim remains **not reproducible** — do not re-attempt without new evidence.
- IPv6 `last_host == network[-2]` was already rejected (IPv6 has no broadcast address) and fixed in 3f64aeb.

## Next precise task (for next agent)

**Fix the `--profile` sentinel-override bug: an explicitly-passed `--timeout`/`--workers` is clobbered by the profile defaults.**

Evidence reproduced this session:
- `python -m ethscan scan --target 127.0.0.1 --profile fast --output-format json` → `timeout=0.5` (correct, profile default)
- `python -m ethscan scan --target 127.0.0.1 --profile fast --timeout 1.0 --output-format json` → still `timeout=0.5` (**bug** — the explicit 1.0 is discarded)

Sites: `ethscan/cli.py:418-421` (`scan`, sentinels `1.0`/`100`), `ethscan/cli.py:1602-1605` (`service`, sentinels `3.0`/`50`), `ethscan/cli.py:2756-2759` (`cve`, sentinels `3.0`/`50`), `ethscan/report.py:67-70` (`_resolve_ports_and_defaults`, sentinels `1.0`/`100`). Contradicts the `--profile` help text at `cli.py:383` ("Overrides --ports, --timeout, --workers unless explicitly set").

Scope: replace the sentinel comparisons with a `click.Context.get_parameter_source(ctx, "timeout") == ParameterSource.COMMANDLINE` style check (also treating `ENVIRONMENT`/`DEFAULT_MAP` as explicit); thread the resulting booleans into `report.py::_resolve_ports_and_defaults` as optional keyword args defaulting to today's behaviour. Add regression tests that fail before the fix (CLI `--timeout 1.0` must survive `--profile fast`; `--workers 100` must survive `--profile full`; profile defaults must still apply when nothing is passed).

Verification: `python -m pytest -q` (≥3936 passed, 1 skipped); `python -m ruff check --output-format concise ethscan tests` (48 errors, identical code multiset); `python -m py_compile ethscan/*.py`; `git diff --stat` limited to intended files. Update HANDOFF_NEXT.md / NEXT_TASK.md / TASK.md on completion.

Also still open (deferred): pre-existing E303 sites; documented coverage gaps.

(End of file - total 66 lines)
