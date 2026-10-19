# Next Task for Agent

## Status
- Working tree on main (local only, ahead of origin/main)
- Tests: **3924 passed, 1 skipped** (green baseline; +16 over 3908)
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
- (this session) Four CLI defects fixed:
  - `ethscan/cli.py` `scan` + `ethscan/report.py` `_resolve_ports_and_defaults`: `--profile` combined with keyword `--ports` (`all`, or any case variant of `common`) raised `ValueError: invalid literal for int() with base 10: 'all'`
  - `ethscan/completion.py`: generated completion scripts embedded `_{PROG}_COMPLETE` while click's runtime reads `_{SANITIZED_PROG}_COMPLETE`, so completions for hyphenated/dotted program names were dead code
  - `ethscan/urlcheck.py`: `--workers` was dropped before `run_fuzz()`, so fuzzing always ran single-threaded while the report advertised the requested count
  - all 17 `--workers` CLI options: `--workers 0` escaped as an unhandled `ValueError`; now `click.IntRange(min=1)` → clean usage error (exit 2)
  - `ethscan/scanner.py`: added `get_all_ports()` helper (replaces a literal duplicated in three places)
  - 16 new test cases across `tests/test_report.py`, `tests/test_cli.py`, `tests/test_completion.py`, `tests/test_urlcheck.py`; all fail before the fix
  - Verified: 3924 passed/1 skipped, ruff byte-identical to the 48-error baseline, all files compile clean

## What remains (all verified and reproducible, deliberately not fixed)
1. `ethscan/cidr.py:52,66` — IPv4 `last_host` is the **broadcast address** (`network[-1]`), while `ethscan/radix.py:263` and `ethscan/validate.py:128` use `network[-2]`. `tests/test_cidr.py:76` asserts the current buggy value, so a fix means changing an existing green assertion. IPv6 semantics need an explicit decision (`radix.py:277` uses `[-2]`, dropping IPv6's genuine last address).
2. `ethscan/cli.py:414-417` (also `:1602-1605`, `:2756-2759`, `ethscan/report.py:66-69`) — profile defaults clobber explicitly-passed `--timeout`/`--workers` because sentinel comparisons (`== 1.0`, `== 100`) cannot tell an explicit value from the default; contradicts the documented "unless explicitly set" behaviour. Needs `click.Context.get_parameter_source` plumbing.
3. `ethscan/scanner.py:55-78` — `parse_port_range()` accepts out-of-range ports (`70000`) and inverted ranges (`100-50` → silently 0 ports); `ethscan/validate.py:64-79` already rejects both.
4. `ethscan/resolve.py:78-91` — `resolve --server` is ignored for CNAME lookups (no `server` parameter on `resolve_cname_records`).
5. `ethscan/cli.py:2743-2745` — `cve --services-file` with malformed JSON dies with a raw `JSONDecodeError` instead of the graceful note in `ethscan/cve.py:256-259`.
6. Pre-existing E303 too-many-blank-lines sites (not regressions): ethscan/cli.py:3600, ethscan/validate.py:279, ethscan/cidr.py:255-256, others.
7. Documented coverage gaps (environmental/defensive, not closable within constraints): cli.py:4864 `__main__` guard; dnssec.py dnspython fallback; hash.py MD4/NTLM/PBKDF2 paths; radix.py defensive edges; network-dependent modules require live services.

## Recommended next precise task
**Fix `ethscan/cidr.py`'s IPv4 `last_host` (broadcast → last usable host) and align the IPv6 rule across `ethscan/cidr.py` / `ethscan/radix.py` / `ethscan/validate.py`.**

Scope:
- `ethscan/cidr.py:52` — IPv4 `last_host` must be `network[-2]` (last usable host), matching `ethscan/validate.py:128` and `ethscan/radix.py:263`.
- Decide the IPv6 rule deliberately and apply it consistently (`ethscan/radix.py:277` and `ethscan/validate.py:128` currently use `[-2]`, which drops IPv6's genuine last address; IPv6 has no broadcast).
- Update the existing green assertion `tests/test_cidr.py:76` and add IPv4/IPv6 cases for `/24`, `/31`, `/32`, `/127`, `/128`.
- Keep `usable_host_count` (`ethscan/cidr.py:59`) consistent with whichever first/last host rule is chosen (it currently subtracts 2 for IPv6 too).
- Keep the change limited to the host-range computation and its tests.

## Verification checklist (if you select a task)
1. Reproduce the smallest failure when applicable; verify prerequisites
2. Write/add a failing test that demonstrates the issue (required for bug fixes)
3. Implement the smallest reversible fix
4. Verify focused tests related to the change
5. Run full suite: `python -m pytest -q` (must remain green; expect ≥3924 passed, 1 skipped)
6. Run lint: `python -m ruff check ethscan tests` (expect 48 errors, byte-identical to the current baseline — capture before/after concise output and diff it)
7. Confirm `python -m py_compile ethscan/*.py` passes
8. Confirm `git diff --stat` shows only intended changes; working tree clean
9. Do not claim checks passed without evidence
10. Update HANDOFF_NEXT.md and TASK.md with concrete details (what changed, verified with evidence, unresolved, failed approaches if any, next precise task)

## Evidence
- Current state verified: 3924 passed, 1 skipped; ruff reports 48 errors (byte-identical to the pre-change baseline); all files compile clean; working tree clean after commit.
- The four CLI fixes are each backed by a test that failed before the change, plus CLI end-to-end reproduction (e.g. `scan --profile fast --ports all` now reports `ports_scanned: 65535`; the completion script now produces a real completion list instead of dumping `--help`).
