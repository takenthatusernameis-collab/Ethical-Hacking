# Next Task

## Status
Session complete (Sat Nov 14 2026): executed the `test_all_formatters_hostile_contract.py` task.
- Found and fixed a real defect in that test: `@pytest.mark.parametrize("value",
  HOSTILE_MATRIX, ids=...)` bound each `(id, value)` tuple itself to `value`, so
  the intended hostile values were never exercised. Parametrization now passes
  `[value for _id, value in HOSTILE_MATRIX]` with the same explicit ids.
- Added `test_formatter_is_pure_and_deterministic`: each single-argument
  formatter must not mutate its input and must render it identically twice.
- Probed all 157 single-argument formatters with extra hostile values (NaN,
  ±inf, deep nesting, list of dicts, every common field hostile): no crashes.

## Baseline (verified this session)
- `python -m pytest tests/test_all_formatters_hostile_contract.py -q` → 1258 passed.
- `python -m pytest -q` → 14500 passed, 146 skipped, 1 warning, 0 failed
  (baseline 14343; +157 purity/determinism tests). Warning: pre-existing
  `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- `python -m ruff check tests/test_all_formatters_hostile_contract.py` → All checks passed.
- `python -m mypy tests/test_all_formatters_hostile_contract.py --follow-imports=skip` → Success.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Approaches already tried / ruled out
- A JSON top-level-object assertion is too strict: hostile non-mapping input is
  rendered as a parseable JSON string, which is the documented contract.
- The same `(id, value)` parametrization mistake was not found elsewhere; the
  per-module hostile sweeps use flat `HOSTILE_TOP_LEVEL` tuples.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope
  per documented contract (exit 0, in-band error).
- `passwords` formatters keep their explicit allowlist; `config` is single-arg
  and is covered by the sweep.

## Next task (bounded, verifiable)
Expand the corrected repo-wide formatter contract test's hostile matrix with
additional realistic hostile values.

Steps:
1. Extend `HOSTILE_MATRIX` in `tests/test_all_formatters_hostile_contract.py`
   with: `float("nan")`, `float("inf")`, `float("-inf")`, a deeply nested list
   (e.g. `[[[[{"a": [1, {"b": [None]}]}]]]]`), a list of hostile dicts
   (e.g. `[{"rtt_avg_ms": "x"}, None]`), and a dict whose every common report
   field (`target`, `port`, `hops`, `notes`, `recursive_traces`, `cves`,
   `certificates`, `results`, `findings`, `services`, `records`, `entries`,
   `items`, `data`, `error`) holds a hostile value.
2. Re-run the focused test. These values were already probed against all 157
   formatters with no crashes, so the expected result is all-pass; if a
   formatter fails, make the smallest defensive fix + targeted regression
   (mirror `_fmt_rtt` in `ethscan/trace.py`).
3. Verify: focused test, `ruff`/`mypy` on the touched file, full
   `python -m pytest -q` (baseline to beat: 14500 passed, 146 skipped, 1
   warning), `python3 check_readme.py`.

Constraints/evidence:
- Do not speculate or weaken safety controls. The additional values were
  already verified against all single-argument formatters this session.
- Extreme Python edge cases (circular refs, unstringifiable objects, non-str
  dict keys) are out of scope (not realistic parser outputs).
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope
  per documented contract (exit 0, in-band error).
- Baseline to match/beat: `python -m pytest -q` → 14500 passed, 146 skipped,
  1 warning.