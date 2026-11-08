# Handoff
Date: Sun Nov 08 2026

## What changed
- Removed temporary debug/probe artifacts: `tests/test_debug_probe.py`, `repro.py`, `repro2.py`.

## What was verified
- `ruff check .` clean.
- Full suite: 5927 passed, 53 skipped, 2 failed (order-dependent): `tests/test_radix.py::...unreadable_runtime...` and `tests/test_stale.py::...unreadable_runtime...`. Both pass individually and in small subsets.

## Unresolved
- Two CLI file-error tests fail only under full-suite ordering, likely module rebind/import caching. Needs investigation of patch target stability.

## Next task
- Investigate why `patch.object(ethscan.cli, "read_lines"/"load_domains_from_file")` does not apply in full-suite order; make patch robust or adjust command to use a stable lookup. Reproduce with `pytest -q` (full).
