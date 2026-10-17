What changed:
- Coverage: `ethscan/netbios.py` 97% → **100%** (0 missing) via 8 new targeted tests in `tests/test_netbios.py` covering the previously-missing lines:
  - `test_parse_dns_name_empty_name_returns_empty` (line 275: `return "", next_offset` when raw name is empty)
  - `test_parse_nbns_response_truncated_rr_header` (line 383: truncated resource record header)
  - `test_parse_nbns_response_truncated_rr_rdata` (line 390: truncated RR RDATA)
  - `test_parse_nbns_response_nb_record` (lines 410-414: NB record branch)
  - `test_parse_nbns_response_unknown_rr_type` (lines 415-416: unknown RR type branch)
  - `test_skip_question_truncated_question_record` (line 342: truncated question record)
  - `test_format_netbios_report_markdown_empty_name` (line 615: "(empty)" name fallback)
  - `test_format_netbios_report_markdown_domain_member` (line 645: is_domain_member YES line)
- Coverage: `ethscan/mssql.py` 98% → covered line 404 (was 8 missing → 7) via 1 new test `test_parse_prelogin_response_trailing_byte_breaks_loop` in `tests/test_mssql.py`.
- `ethscan/snmp.py` confirmed at **100%** (0 missing) — the 5 lines flagged in the prior snapshot (247, 319, 324, 357, 406) are covered by existing tests; no source change needed.
- No files under `ethscan/` were modified.

What was verified:
- `tests/test_netbios.py`: 73 passed (was 65; +8 new).
- `tests/test_mssql.py`: 78 passed (was 77; +1 new).
- `python -m ruff check tests/test_mssql.py tests/test_netbios.py` → no NEW violations (remaining import-sort/unused-import findings are pre-existing in untouched code).
- Full suite: **3887 passed, 1 skipped** (was 3873; +14 net new tests).
- `ethscan/netbios.py` → 100%; `ethscan/snmp.py` → 100%; `ethscan/mssql.py` → 98% (7 dead); `ethscan/radix.py` → 97% (9 dead); `ethscan/cli.py` → 99% (21 unreachable-in-tests).
- Total `ethscan/` missing lines: 83 → 72, all documented as dead/unreachable.

What remains unresolved:
- Nothing coverable remains. Every remaining missing line is documented as provably unreachable or unreachable-in-tests in NEXT_TASK.md:
  - mssql.py: 389-391, 432-433, 455-456 (dead)
  - radix.py: 149-150, 153-154, 158-161, 219-220 (dead)
  - cli.py: 607-635 (superseded hash function body; active command is hash_cmd), 4639 (__main__ guard not triggered by tests)

Which approaches failed and why:
- `mssql.py:389-391`, `radix.py:149-150/153-154/158-161/219-220`, `cli.py:607-635`: provably unreachable/dead code confirmed by control-flow inspection and empirical tracing; not coverable without modifying `ethscan/` (which is out of scope per the coverage-convention).
- `cli.py:4639`: `__main__` guard; only reachable by running `ethscan/cli.py` directly, which tests never do.

Next task:
- None — coverage characterization is complete. Optional follow-up: commit the two test files (`tests/test_mssql.py`, `tests/test_netbios.py`) if a commit is desired; no further `ethscan/` source or test gaps exist.
