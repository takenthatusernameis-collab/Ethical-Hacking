## Next task

Extend the completed CWE-1236 (CSV formula injection) end-to-end regression coverage to
2-3 more modules that carry attacker-controlled free text into CSV but are not yet covered.

Context:
- The shared sanitizer `ethscan/fileio.py::sanitize_csv_cell` and the
  `csv_writer` / `SanitizingCSVWriter` wrapper are in place, and all 54 CSV-producing
  modules route through `csv_writer` (verified: no `format_*_csv` module bypasses it; no
  `writerows`/`DictWriter`/manual CSV building; only `fileio.py` imports `csv`).
- 7 end-to-end regression tests now lock the wiring across 7 field shapes:
  `ftp` (banner/message), `dns` (record_value), `smtp` (error/findings),
  `whois` (registrar/registrant_org/error), `jwt` (other_claims value),
  `ssl` (cert subject/issuer/sans), `resolve` (record_value).
- A mutation check (neutralize `sanitize_csv_cell`) makes all 7 fail; restoring makes all
  7 pass — the tests genuinely guard the shared wrapper.

Remaining work:
- Add 2-3 end-to-end tests in the relevant `tests/test_*.py` files (suggested: `ntp`
  `findings`, `redis` `dangerous_findings`, `cve` `title`/`description`) that feed a
  hostile value beginning with `= + - @` and assert the emitted CSV cell is prefixed with
  `'` (parse with `csv.reader` and compare the exact cell).
- Do not weaken existing tests; assert exact sanitized values; keep changes test-only.
- Re-run the FULL gate (pytest/coverage/mypy/ruff/check_readme) to prove 100% coverage
  and no regressions.

Evidence:
- `python -c "from ethscan.fileio import sanitize_csv_cell as s; print(repr(s('=1+1')))"`
  -> `"'=1+1"`.
- 7 existing sanitization tests across ftp/dns/smtp/whois/jwt/ssl/resolve; mutation check
  (neutralized sanitizer) -> 7 failed; restored -> 7 passed.

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py` unreachable defensive guard (documented known limitation)
- `.github/workflows/**` (reverted by the controller)
- Leading-whitespace formula cells (e.g. `" =1+1"`) are NOT a gap; do not chase.
- Purely numeric cells (`+1`, `-1`, `3.14`) are intentionally not sanitized; not a gap.

If no value is found in more CSV tests, probe for a genuine defect first (fresh-install
failure, focused failing check, or behavioral evidence vs documented contract) rather than
fabricating work — the repo is otherwise fully green.