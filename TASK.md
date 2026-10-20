# TASK

Status: COMPLETE (smtp: a hostile server answer no longer crashes the command)

## What was done

The previous handoff asked for a sweep of the server-answer parsers for
the class of bug that the `netbios` fix removed: a fixed index into a
decoded buffer, or an exception type that the module's guard does not
catch. The sweep found **two** remotely triggerable tracebacks, both in
`ethscan/smtp.py`, which was not on the previous candidate list.

- **`ethscan/smtp.py:79-92` (new `_reply_code`) and `:102`**: the reply
  code of an SMTP status line is now only read when the text is ASCII
  digits. Before the fix the code was read with
  `int(first[:3]) if first[:3].isdigit() else 0`, and `str.isdigit()`
  accepts the Unicode superscript digits that `int()` refuses. A server
  that answers `"²²² 5.7.1 blocked"` therefore raised
  `ValueError: invalid literal for int() with base 10: '²²²'`. A status
  line that is not a valid reply code is now reported as code `0`, like
  any other non-numeric line.
- **`ethscan/smtp.py:253-262`**: an EHLO capability line that holds no
  word after the separator (`"250-   "`) is now skipped. Before the fix
  the capability was read with `line[4:].split()[0]`, a fixed index into
  a list that is empty for such a line, so the server raised
  `IndexError: list index out of range`.
- **`ethscan/smtp.py:316-319`**: the probe block of `run_smtp()` had a
  `finally` but no `except`, so neither exception was caught and both
  reached the command line as a raw traceback. The block now reports an
  unexpected failure through the `error` field, the way `run_mysql()`,
  `run_mssql()`, `run_postgresql()`, `run_mongodb()` and `run_oracle()`
  already do.
- **`tests/test_smtp.py`**: 6 regression tests (see below). The fake
  SMTP server learned two optional config keys (`ehlo_response` and
  `mail_response`) so a hostile answer can be served over a real socket.

## Verification

- Reproduction before the fix: a server that answers EHLO with
  `250-   \r\n250 OK\r\n` made `ethscan smtp --target <host>` exit 1
  with `IndexError: list index out of range` and no output; a server
  that answers `MAIL FROM` with `²²² 5.7.1 blocked` made it exit 1 with
  `ValueError: invalid literal for int() with base 10: '²²²'`. Both are
  reachable with the default options (`check_relay` is on by default), so
  no option is needed to trigger them. After the fix the same answers are
  parsed (`capabilities` is empty, `open_relay` is `False`) and the
  command exits 0.
- The 5 new hostile-answer tests were run against the unfixed module
  (`git stash push -- ethscan/smtp.py`): all 5 failed with the
  `IndexError` / `ValueError`. With the fix they pass. The 6th test
  (`test_parse_smtp_response_plain_code_is_unchanged`) is a control that
  passes in both cases and pins that an ordinary reply code is still
  read as a number.
- The two parser fixes are each necessary: with only the new
  `except Exception` net and the old parsers, 4 of the new tests still
  fail (the result then carries `smtp probe failed: ...` in `error`).
- `python -m ruff check ethscan/ tests/` → **All checks passed**.
- `python -m pytest tests/test_smtp.py -q` → **59 passed** (was 53).
- `python -m pytest -q` → **4572 passed, 48 skipped, 2 warnings**
  (was 4566).
- `git diff --check` → clean.

## Handoff

See `HANDOFF_NEXT.md` and `NEXT_TASK.md`. The baseline is clean: the fix
and its tests are committed, nothing else is modified.
