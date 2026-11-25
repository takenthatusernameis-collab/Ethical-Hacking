## Next task

CSV formula injection (CWE-1236) mitigation is partially scaffolded:

- Shared sanitizer `ethscan/fileio.py::sanitize_csv_cell` added (prefixes `'` to string
  cells beginning with `= + - @` TAB/CR, except purely numeric cells). Focused tests in
  `tests/test_fileio.py` pass; mypy/ruff clean.
- Remaining work: route every `csv.writer` module (58 modules in ethscan/) through the
  sanitizer. Because 144 test files assert exact CSV output, this is a broad change that
  risks regressions; apply module-by-module with the FULL gate after each batch and
  update expected outputs only where the sanitizer changes them (never weaken tests).
- If the sweep proves unsafe to land in one session, document as a known limitation.

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py` unreachable defensive guard (documented known limitation)
- `.github/workflows/**` (reverted by the controller)
