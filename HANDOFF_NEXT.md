# Handoff: README CSV documentation gap closed

## What changed
- `README.md` — updated three feature bullets that under-described their command's output support:
  - `mac` (line 39): "JSON/Markdown output" → "JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`"
  - `jwt` (line 42): same correction
  - `resolve` (line 44): same correction

No code, tests, or CLI wiring changed — the CSV formatters, `--output-format`/`--format` options, and dispatch logic were already present and verified working for all three commands. This session only corrected stale documentation.

## What was verified
- `python -m pytest -q` → **2802 passed, 1 skipped** (full suite, no regressions)
- `python -m ethscan mac --help` / `jwt --help` / `resolve --help` → all show `--output-format [json|markdown|csv]` and the deprecated `--format` alias
- End-to-end CSV output confirmed live for each:
  - `python -m ethscan mac --target 00:1A:2B:3C:4D:5E --output-format csv --timeout 2.0` → header `target,mac,oui,vendor,cached,offline_fallback,error` + row
  - `python -m ethscan resolve --target 8.8.8.8 --output-format csv --timeout 2.0` → header `target,normalized,record_type,record_value` + PTR row
  - `python -m ethscan jwt --output-format csv ...` (CSV formatter exercised by `tests/test_jwt.py`)
- `git diff --stat` → `README.md | 6 +++---` (3 insertions, 3 deletions); working tree otherwise clean

## What remains unresolved
- No functional gaps found. All 52 registered commands have working JSON/Markdown/CSV output where a CSV formatter exists; `report`, `scan`, and `audit` route to CSV via their existing `format_*_csv` functions (verified in CLI help and code).
- Documentation bullets for `geo`, `whois`, and `ssl` do not have detailed per-command bullets at all (they appear only in the summary list), so there is nothing to correct there.

## Failed approaches (none)
- No failures. The initially-suggested tasks in `NEXT_TASK.md` (add CSV to `geo`/`whois`/`ssl`) were found to already be implemented; the task was re-scoped to the documentation gap instead of duplicating work.

## Next precise task
No next task pending — repository is in a complete, verified state. If a new command or output format is desired, follow the established conventions: `format_*_report_{json,markdown,csv}` in the module, `--output-format`/`--format`/`--out` options in `ethscan/cli.py`, unit tests + CLI tests, README bullet, and keep changes minimal and reversible.

(End of file)