# NEXT TASK

## Status: COMPLETE (smtp: a hostile server answer no longer crashes the command)

1. **`ethscan/smtp.py`** no longer crashes on a hostile answer:
   - a status line whose code is written with Unicode superscript digits
     is reported as code `0` (the code is only read when the text is
     ASCII digits);
   - an EHLO capability line that holds no word after the separator is
     skipped instead of being read at a fixed index into an empty list;
   - the probe block of `run_smtp()` reports an unexpected failure
     through the `error` field instead of letting it escape.
2. **Regression tests added** in `tests/test_smtp.py`: 6 tests, 5 of
   which fail with the `IndexError` / `ValueError` on the unfixed module.

## Verification

- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/test_smtp.py -q` → **59 passed** (was 53).
- `python -m pytest -q` → **4572 passed, 48 skipped, 2 warnings**
  (was 4566).
- `git diff --check` → clean.

## Next agent

One bounded task is described in `HANDOFF_NEXT.md`: sweep the
**text-protocol and HTTP answer parsers** for the same class of bug. The
binary protocol parsers of the previous candidate list are now verified
clean, and the two bugs that were found lived in a *text* protocol, so
that is where the remaining surface is.
