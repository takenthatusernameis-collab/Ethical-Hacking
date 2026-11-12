# Next Task

## Status
Session 121 closed the `ftp` formatter `findings` hostile-shape gap (the handoff's `features`/`auth_types` field names did not match the code; the real field is `findings`, now hardened in both Markdown and CSV formatters).

## One precise next task
Harden one remaining module from the session 117 fuzzer list where both Markdown and CSV iterate a potentially wrong-typed list field. Candidate: `ntp` (also still open: `oracle`, `smtp`, `snmp`).

Steps:
1. Reproduce first: craft hostile shapes for the module's list field(s) (e.g. `None`, an `int`/`bool`, a bare `str`, a list with non-string elements `[None, 1]`) and confirm `format_*_report_markdown` / `format_*_report_csv` raise `TypeError`/`AttributeError`.
2. Fix: add a normalization helper (following the `_normalize_findings` / `_normalize_security_flags` / `_normalize_root_dse` pattern) that coerces non-list/tuple to `[]` and stringifies list/tuple elements; apply it in both formatters.
3. Add a focused hostile-sweep test (one file, e.g. `tests/test_<module>_formatter_hostile_sweep.py` or extend the existing hostile-sweep file).
4. Verify: module tests, full `pytest -q`, `mypy ethscan/ tests/`, `ruff check ethscan/ tests/`.

Constraints: one module per session (do not batch); preserve the oracle/postgresql in-band exit-0 contract; do not weaken CLI validation or tests; reproduce before fixing — no speculative changes.
