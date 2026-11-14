# Next Task

## Status
Session complete (Sat Nov 14 2026): executed the `ethscan.trace` formatter hostile sweep.
- Probe found a real crash: `format_trace_report_markdown` raised on hostile hop RTT values because `_fmt_rtt` (ethscan/trace.py:38) applied `:.2f` to raw `rtt_avg_ms`/`rtt_ms` values. `ValueError` for strings, `TypeError` for dict/list.
- Fixed `_fmt_rtt` to return `"N/A"` for non-numeric values (bools, containers, non-numeric strings), format ints/floats as before, and accept numeric strings via `float()`. Single helper covers both markdown call sites.
- Added `tests/test_trace_formatter_hostile_sweep.py` (525 tests): non-mapping top-level, hostile top-level fields, hostile `hops`/`recursive_traces` entries (incl. RTT values), hostile notes/list shapes, combined hostile shape, well-formed + minimal regressions across json/markdown/csv, and a direct `_fmt_rtt` unit regression.

## Baseline (verified this session)
- `python -m pytest -q` → 13242 passed, 146 skipped, 1 warning, 0 failed (baseline was 12707; +535 new tests). Pre-existing warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- `python -m pytest tests/test_trace_formatter_hostile_sweep.py -q` → 535 passed.
- `python -m ruff check ethscan/trace.py tests/test_trace_formatter_hostile_sweep.py` → All checks passed.
- `python -m mypy ethscan/trace.py tests/test_trace_formatter_hostile_sweep.py --follow-imports=skip` → Success.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Approaches already tried / ruled out
- `_fmt_rtt` fix is the smallest change (private helper used only by two markdown call sites). CSV is safe via `csv.writer` str-coercion; JSON is safe via `default=str`.
- All 50 `ethscan.*` formatter modules already have hostile-sweep tests; the previous "remaining: trace, completion, headers, ftp" list was stale.
- Scanned for the same unguarded-numeric-format bug class: `ethscan/wifi.py` frequency formatting is already `isinstance`-guarded; no formatter-body `int()`/`float()` conversions; `round()` uses are guarded.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for the single-arg Mapping pattern.

## Next task (bounded, verifiable)
Add a repo-wide, introspection-based cross-module formatter contract test so future formatter regressions are caught automatically.

Steps:
1. Create `tests/test_all_formatters_hostile_contract.py`.
2. Discover every `format_*_report_json` / `format_*_report_markdown` / `format_*_report_csv` callable in `ethscan.*` (e.g. `pkgutil`/`importlib` + `inspect.signature`), filtering to single-argument formatters.
3. Assert each returns `str` and never raises for a hostile top-level matrix: `None`, `1`, `"x"`, `[]`, `b"bytes"`, `{}`, and a hostile field dict (e.g. `{"target": [], "port": "x", "hops": [None, {"rtt_avg_ms": "x"}], "notes": [None, {}], "recursive_traces": [None, {"hops": "x"}]}`). JSON output must be parseable.
4. Use an explicit allowlist for formatters with non-standard signatures (`passwords`, `config`) rather than a blanket skip; assert the allowlist stays accurate.
5. Reproduce first: if any formatter crashes, make the smallest defensive fix + targeted regression (mirror the `_fmt_rtt` fix), then re-run.
6. Verify: focused test, `ruff`/`mypy` on touched files, full `python -m pytest -q`, `python3 check_readme.py`.

Constraints/evidence:
- Do not speculate or weaken safety controls. Reproduce before writing guards.
- Extreme Python edge cases (circular refs, unstringifiable objects, non-str dict keys) are out of scope (not realistic parser outputs).
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- Baseline to match/beat: `python -m pytest -q` → 13242 passed, 146 skipped, 1 warning.
