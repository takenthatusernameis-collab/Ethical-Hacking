# Next task

None pending. Repository is fully green.

## Last completed session (Sat Nov 28 2026)

Extended independent-oracle verification to the `ethscan.cidr` pure helpers:
- New file `oracle_verify_cidr.py`: stdlib-only (`ipaddress`) oracles for
  `normalize_cidr`, `_contains_ip`, `_subtract_networks`, and `run_cidr` over a
  hostile input matrix (valid/invalid IPv4/IPv6 CIDRs, bare IPs, empty/control/
  non-ASCII inputs, host-bit / prefix-boundary cases, ~3700+ run_cidr cases
  including randomized).
- New file `tests/test_oracle_verify_cidr.py`: 4 pytest regression tests
  wrapping the oracle verification.
- No `ethscan/` source changed; test-only addition.

## Full gate (all green)

- `python -m pytest -q` → 50101 passed, 147 skipped, 0 failed (baseline 50097;
  +4 new oracle tests).
- `python -m mypy ethscan/ tests/` → Success: no issues in 290 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` → All checks passed.
- `python check_readme.py` → 54 CLI commands, 0 drift both directions.
- `python oracle_verify_cidr.py` → ALL VERIFICATIONS PASSED, 0 mismatches,
  exit 0.

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is
  intentional — out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known
  limitation — do not change to game coverage.
- Do not modify `.github/workflows/**`.
- Do NOT fabricate work, repeat verification-only sessions as progress, or
  make empty/control-marker commits.

## Environment / critical notes

- **Test deps are NOT preinstalled in this environment.** Run:
  `pip install --quiet pytest mypy ruff coverage dnspython` (installs to
  `~/.local/bin`, not on PATH; use `python -m <tool>`). `click`/`pyyaml` are
  preinstalled; `dnspython` is not.
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
  `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full pytest gate takes ~3.2 min (50101 tests). Full coverage gate ~2.9 min.
- Do not commit manually; the workflow controller stages and commits.
- ALWAYS re-verify HEAD first-hand (install deps, run the gate) rather than
  trusting the "green" claim — prior handoffs were repeatedly stale.

## Next task

None pending. If future work is needed, pick a single bounded, high-value,
verifiable improvement and reproduce it first — do not speculate or weaken
safety controls. A natural candidate following the established convention would
be extending independent-oracle verification to another pure-helper module
(e.g. `ethscan.urlcheck` or `ethscan.validate`) via a new
`oracle_verify_<mod>.py` + `tests/test_oracle_verify_<mod>.py`, but only if a
genuine defect-hunting gap is identified first.
