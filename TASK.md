# TASK

Status: COMPLETE (netbios: a short first-level name no longer crashes the command)

## What was done

- **`ethscan/netbios.py:177-193`**: `_decode_name_chars` now rejects a name
  that is shorter than 32 chars (16 decoded bytes) with a `ValueError`,
  like every other malformed name. Before the fix it only checked that the
  length was even, so a name of 2 to 30 even chars was decoded into fewer
  than 16 bytes and the suffix byte was then read out of range
  (`suffix = raw[15]`).
- The `IndexError` that this produced escaped **every** guard around the
  NBNS parser: `_parse_dns_name` catches `ValueError`, `_parse_nbns_response`
  documents `ValueError`, and `run_netbios` catches `ValueError` only. A
  host that answers the NBNS query with such a name crashed the `netbios`
  command with a traceback.
- The short name is now reported as the text it is, the same way every
  other name that is not first-level encoded is reported.
- **`tests/test_netbios.py`**: 5 regression tests
  (`test_decode_name_chars_too_short_raises`,
  `test_parse_dns_name_short_name_is_reported_as_text`,
  `test_parse_nbns_response_short_question_name_does_not_raise`,
  `test_run_netbios_hostile_short_name_does_not_leak_a_traceback`,
  `test_netbios_command_hostile_short_name_does_not_leak_a_traceback`).

## Verification

- Reproduction before the fix: an NBNS response whose question name is the
  2-byte label `AB` raised `IndexError: bytearray index out of range` in
  `run_netbios`, in `_parse_nbns_response`, in `_parse_dns_name` and on the
  command line (`ethscan netbios --target 127.0.0.1`). After the fix the
  same packet is parsed (the name is reported as the text `AB`) and the
  command exits 0.
- The 5 new tests were run against the unfixed module (`git stash push --
  ethscan/netbios.py`): all 5 failed with the `IndexError`. With the fix
  they pass.
- `python -m ruff check ethscan/ tests/` → **All checks passed**.
- `python -m pytest tests/test_netbios.py -q` → **78 passed** (was 73).
- `python -m pytest -q` → **4566 passed, 48 skipped, 2 warnings** (was 4561).
- `git diff --check` → clean.

## Handoff

See `HANDOFF_NEXT.md` and `NEXT_TASK.md`. The baseline is clean: the fix and
its tests are committed, nothing else is modified.
