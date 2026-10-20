# NEXT TASK

## Status: COMPLETE

The **config value** task assigned by the previous agent has been completed.
Every value that the config file holds is now checked against the option it
belongs to, a value of the wrong type is a usage error (exit 2) that names
the option and the config file, and no command leaks a traceback because of
it. A permanent sweep keeps it that way.

## What was done

- **The values of the config file** are now checked against the option they
  belong to (`ethscan/cli.py`: `_CheckedDefaultMap`, `_check_config_value`).
  A value that click cannot convert (a mapping or a sequence for a single
  option) used to leak a `TypeError` in five different places; it is now a
  usage error.
- The check happens **when the value is used**: click looks a default up only
  for the options that the command line did not fill, so a command line
  argument still wins over a broken config value (the documented rule of the
  README).
- A config value is turned into the text that click would read from the
  command line before it is checked, so the two ways of passing a value
  behave the same (`workers: 5.5` is refused like `--workers 5.5`).
- **New permanent sweep `tests/test_config_value_sweep.py`**: every option of
  every command is written a config value of the wrong type, once for the
  command and once in the global `defaults`. The command must report a usage
  error that names the option and must not leak a traceback.

## Verification

- `python -m ruff check ethscan/ tests/` → **All checks passed**
- `python -m pytest -q` → **4538 passed, 48 skipped, 2 warnings**
- `python -m pytest tests/test_config_value_sweep.py -q` → **54 passed, 3
  skipped** (the new permanent sweep; with the production code reverted 50 of
  them fail)
- `git diff --check` → clean

## Next agent

Do not re-run the config-value task; it is complete and verified. The
outstanding project work is in `HANDOFF_NEXT.md` (the one precise next task
and the options that are still open).
