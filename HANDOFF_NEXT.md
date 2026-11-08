# Handoff
Date: Sun Nov 08 2026

## What changed
- Investigated the reported flaky CLI file-error tests:
  - `tests/test_radix.py::TestRadixCliFileErrors::test_radix_cidr_file_unreadable_runtime_reports_bad_parameter`
  - `tests/test_stale.py::TestStaleCliFileErrors::test_stale_file_unreadable_runtime_reports_bad_parameter`
- No product-code change: `ethscan/cli.py` already reads via `ethscan.fileio.read_lines` (cli.py:3611) and `ethscan.stale.load_domains_from_file` (cli.py:4631), i.e. module-attribute lookups resolved at call time. These are exactly the attributes the tests patch (`patch.object(ethscan.fileio, "read_lines")` / `patch.object(ethscan.stale, "load_domains_from_file")`), so the lookup target is already stable.

## What was verified
- Full `python -m pytest -q` run #1: 5929 passed, 53 skipped, 0 failed.
- Full `python -m pytest -q` run #2: 5929 passed, 53 skipped, 0 failed. The reported 2 failures do NOT reproduce in this environment.
- `python -m ruff check .` → All checks passed.
- `pytest tests/test_radix.py tests/test_stale.py tests/test_fileio.py` → 211 passed.

## Unresolved
- Flakiness not reproducible here. This environment lacks `dnspython` (`import dns` fails), while several DNS/reload-heavy test modules (test_dns, test_dnsbrute, test_dnssec, test_subdomains, test_subtake) inject/reload modules; that difference may explain why the HANDOFF author saw order-dependent failures and this session does not.

## Approaches that failed
- None: no reproducible defect exists in this checkout, so no speculative change was made (per the rule against speculative changes).

## Next task
- None pending; baseline is green.
- If the flakiness reappears, reproduce in an environment with `dnspython` installed and identify which earlier test rebinds `ethscan.fileio`/`ethscan.stale` on the package or reloads modules such that a `patch.object` target stops being the object `cli.py` reads at call time.
