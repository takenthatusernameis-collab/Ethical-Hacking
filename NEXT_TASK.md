## Next task

Lock in the completed CWE-1236 (CSV formula injection) mitigation with a few
representative end-to-end regression tests.

Context:
- The shared sanitizer `ethscan/fileio.py::sanitize_csv_cell` and the
  `csv_writer` / `SanitizingCSVWriter` wrapper are in place, and all 54 CSV-producing
  modules in `ethscan/` now route through `csv_writer` (verified: no `format_*_csv`
  module bypasses it; only `fileio.py` still imports `csv`).
- Only `tests/test_ftp.py::test_format_ftp_report_csv_sanitizes_formula_banner` currently
  proves the wiring end-to-end.

Remaining work:
- Add 2-3 end-to-end tests in the relevant `tests/test_*.py` files (suggested: `dns`
  record_value, `whois` registrar/error, `smtp` banner) that feed a hostile value
  beginning with `= + - @` and assert the emitted CSV cell is prefixed with `'`
  (parse with `csv.reader` and compare the exact cell).
- Do not weaken existing tests; assert exact sanitized values.
- Re-run the FULL gate (pytest/coverage/mypy/ruff/check_readme) to prove 100% coverage
  and no regressions.

Evidence:
- `python -c "from ethscan.fileio import sanitize_csv_cell as s; print(repr(s('=1+1')))"`
  -> `"'=1+1"`.
- `git diff --stat` -> 56 files changed (54 modules + fileio.py + test_ftp.py).

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py` unreachable defensive guard (documented known limitation)
- `.github/workflows/**` (reverted by the controller)
- Leading-whitespace formula cells (e.g. `" =1+1"`) are NOT a gap; do not chase.