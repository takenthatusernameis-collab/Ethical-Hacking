## Next task

Repository is green (independently re-verified this session, FULL gate):
- `coverage run --branch --source=ethscan -m pytest -q` -> 47475 passed, 147 skipped, 0 failed
- `coverage report` -> TOTAL 100% (16245 stmts, 6136 branches, 0 missing)
- `mypy ethscan/ tests/` -> clean (271 source files)
- `ruff check ethscan/ tests/ check_readme.py` -> all checks passed
- `check_readme.py` -> 54 commands, 0 drift both directions
- `git status` -> only ethscan/fileio.py + tests/test_fileio.py modified (uncommitted; controller commits)

This session fixed a reproduced bug: `ethscan/fileio.py::load_json` falsely rejected valid JSON
whose string contained >1000 brackets (the depth guard counted brackets inside string literals).
Now string-aware; genuine deep nesting still rejected. +2 tests.

High-value gap reproduced but NOT fixed (needs a bounded follow-up): CSV formula injection
(CWE-1236). 54 ethscan modules write attacker-influenced values (banners, headers, findings,
DNS records) via `csv.writer` with no sanitization, so a hostile value like `=cmd|...` or
`=HYPERLINK(...)` is emitted verbatim and can execute when the CSV is opened in a spreadsheet.
Reproduce: `python -c "from ethscan.ftp import format_ftp_report_csv;
print(format_ftp_report_csv({'target':'t','host':'h','port':21,'banner':\"=cmd|' /C calc'!A0\"}))"`.
Fix approach: ONE shared sanitizer (prefix `'` to string cells starting with `= + - @`/TAB/CR,
but not purely numeric cells) applied across all `csv.writer` modules + a focused test; re-run
the FULL gate to confirm no exact-output test regresses. If too broad to land safely, document
as a known limitation instead.

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py` unreachable defensive guard (documented known limitation)
- `.github/workflows/**` (reverted by the controller)

If future work is needed: reproduce a concrete gap first (focused failing check or behavioral
evidence vs documented contract), apply the smallest safe fix, rerun focused then broader gates
(pytest/coverage/mypy/ruff/check_readme), preserve safety/validation. Do not delete tests to go
green. Do not repeat verification-only sessions as progress.

(End of file)