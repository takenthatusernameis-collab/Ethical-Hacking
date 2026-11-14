# Handoff
Date: Sat Nov 14 2026 (session 163)

## This session
- Executed the handoff task: the repo-wide formatter contract test
  (`tests/test_all_formatters_hostile_contract.py`, added by the prior session).
- Found and fixed a real defect in that new test: its hostile-value
  parametrization passed the whole `(id, value)` tuple as the single `value`
  argument. Because `HOSTILE_MATRIX` is a list of `(id, value)` tuples and the
  test used `@pytest.mark.parametrize("value", HOSTILE_MATRIX, ids=...)`,
  pytest bound each tuple itself to `value`. The intended hostile values
  (`None`, `1`, `"x"`, `[]`, `b"bytes"`, `{}`, the hostile field dict) were
  therefore never exercised; formatters received 2-element lists instead.
  The old test passed (1101) while testing the wrong inputs.
- Fix: parametrize over `[value for _id, value in HOSTILE_MATRIX]` with the
  same explicit ids, so each real hostile value is passed. This is the
  smallest change; no production code changed.
- Added `test_formatter_is_pure_and_deterministic`: for every discovered
  single-argument formatter, a hostile field dict is deep-copied, rendered,
  and the formatter must neither mutate the input nor return a different
  string on a second call.
- Also probed all 157 single-argument formatters directly with additional
  hostile values (NaN, +inf, -inf, a deeply nested list, a list of hostile
  dicts, a dict with hostile values under every common report field): no
  crashes and no non-`str` returns.

## Verification
- Focused: `python -m pytest tests/test_all_formatters_hostile_contract.py -q`
  → 1258 passed (1101 hostile-matrix + 157 purity/determinism).
- Full: `python -m pytest -q` → 14500 passed, 146 skipped, 1 warning, 0 failed
  (baseline 14343; +157 purity tests).
- `python -m ruff check tests/test_all_formatters_hostile_contract.py` → All checks passed.
- `python -m mypy tests/test_all_formatters_hostile_contract.py --follow-imports=skip`
  → Success: no issues found.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Campaign status
- Discovery now covers 53 formatter modules and 157 single-argument formatters;
  3 `ethscan.passwords.format_audit_report_*` remain in the documented
  non-standard allowlist (their richer signatures are not drop-in).
- With the parametrization fixed, every discovered single-argument formatter
  survives the real hostile matrix (including non-mapping scalars/containers),
  returns `str`, and emits parseable JSON for `*_report_json` variants.

## Approaches already tried / ruled out
- Asserting that every `*_report_json` output is a top-level JSON object is too
  strict: for hostile non-mapping input (e.g. `b"bytes"`, `1`, `"x"`, `[]`),
  formatters render a JSON string (e.g. `"b'bytes'"`). That is parseable JSON,
  which is the documented contract, so the assertion was removed rather than
  changing production formatters.
- `passwords` formatters keep their explicit allowlist; `config` is a
  single-argument formatter and is covered by the sweep.
- The same `(id, value)` parametrization mistake was not found elsewhere: the
  per-module hostile sweeps use flat `HOSTILE_TOP_LEVEL` tuples.

## Next task
Expand the corrected repo-wide formatter contract test's hostile matrix with
additional realistic hostile values, then verify.

Steps:
1. Extend `HOSTILE_MATRIX` in `tests/test_all_formatters_hostile_contract.py`
   with: `float("nan")`, `float("inf")`, `float("-inf")`, a deeply nested list
   (e.g. `[[[[{"a": [1, {"b": [None]}]}]]]]`), a list of hostile dicts
   (e.g. `[{"rtt_avg_ms": "x"}, None]`), and a dict whose every common report
   field (`target`, `port`, `hops`, `notes`, `recursive_traces`, `cves`,
   `certificates`, `results`, `findings`, `services`, `records`, `entries`,
   `items`, `data`, `error`) holds a hostile value.
2. Re-run the focused test. All 157 formatters were already probed against
   these values with no crashes, so the expected result is all-pass; if any
   formatter now fails, make the smallest defensive fix plus a targeted
   regression (mirror the `_fmt_rtt` guard in `ethscan/trace.py`).
3. Verify: focused test, `ruff`/`mypy` on the touched file, full
   `python -m pytest -q` (baseline to beat: 14500 passed, 146 skipped, 1
   warning), `python3 check_readme.py`.

Constraints/evidence:
- Do not speculate or weaken safety controls. The additional values were
  already verified against all single-argument formatters this session.
- Extreme Python edge cases (circular refs, unstringifiable objects, non-str
  dict keys) remain out of scope (not realistic parser outputs).
- `oracle`/`postgresql` empty-target handling remains intentionally out of
  scope per documented contract (exit 0, in-band error).
- Baseline to match/beat: `python -m pytest -q` → 14500 passed, 146 skipped,
  1 warning.