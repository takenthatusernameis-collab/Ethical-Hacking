# Next Task for Agent

## Status (current)
- `tests/test_vuln.py` modified (+1 test: `test_run_vuln_recursive_negative_max_depth_guards_immediately`), **not committed**.
- Full suite: **3890 passed, 1 skipped** (confirmed). No regressions.
- `ethscan/vuln.py`: 98% coverage; line 904 now covered. Remaining misses (`37, 57-62, 555-556`) are provably unreachable or tooling-quirk/functionally covered.
- `ruff check tests/test_vuln.py`: clean.

## Provably dead / unreachable-in-tests (do not retest; avoid `ethscan/` source changes)
As previously documented across `cli.py`, `mssql.py`, `radix.py`, `hash.py`, `vuln.py`, plus environment-dependent optional-dep branches (`paramiko`, `dnspython`).

## Next precise task
**Cover `ethscan/ntp.py:387`** — the monlist-error line `lines.append(f"- **Error:** {mon_resp['error']}")` inside `if mon_resp.get("error"):` in `format_ntp_report_markdown`.

Evidence:
- `ethscan/ntp.py:386-387`: `if mon_resp.get("error"): lines.append(f"- **Error:** {mon_resp['error']}")`.
- Reachable via `format_ntp_report_markdown({"monlist_response": {"error": "<err>"}})` — no network, no optional deps.
- `format_ntp_report_markdown` is imported in `tests/test_ntp.py` but never invoked with an error-bearing `monlist_response`, so line 387 is uncovered.

Constraints:
- Add a unit test in `tests/test_ntp.py`, bound to <30 lines.
- Verify with focused test, `ruff check tests/test_ntp.py`, and full suite.
- Do not modify `ethscan/` source; do not commit unless explicitly asked.
