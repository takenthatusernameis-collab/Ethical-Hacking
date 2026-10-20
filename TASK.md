# TASK.md

Date: 2026-10-20T19:15:40Z
Status: the **values that the config file holds** are hardened and are now
covered by a permanent sweep. A config value of the wrong type used to leak
**5 different tracebacks** in the commands that read one; it now leaks
**none** and is reported as a usage error that names the option and the
config file.

The path of a file option was covered before (`tests/test_file_option_sweep.py`)
and the content of a file was covered before that
(`tests/test_file_content_sweep.py`). The values of the config file were not:
nothing kept them from being of a type that click cannot convert.

## What changed

### 1. A config value that click cannot convert
- **Root cause:** a config value reaches an option through click's
  `default_map`, and click's converters only ever expect the text that a
  command line delivers. A value that is a mapping (or a sequence) made click
  raise an unhandled `TypeError` (or `AttributeError`) instead of reporting a
  usage error. Five different tracebacks were reachable:
  `int()` (an integer option), `float()` (a float option), the `in` test of a
  `Choice` (an unhashable mapping), `os.stat()` (a file option) and
  `value.strip()` (a boolean option).
- **`ethscan/cli.py`**: the default map of a command is now a
  `_CheckedDefaultMap` (a `dict` subclass). It hands a value out only after
  the value has been checked against the option it belongs to, so a value of
  the wrong type is a usage error (**exit 2**) that names the option and the
  config file:
  `Invalid value for '--workers' in the config file /home/u/ethscan.yaml: expected a text value, got {'a': 1}.`
- The check is **lazy on purpose**: click looks a default up only for the
  options that the command line did not fill, so a config value is checked
  exactly when it is used. A value that the command line overrides is none of
  the command's business, which keeps the documented rule true ("CLI
  arguments always take precedence over config values").

### 2. A config value that is of the wrong type for its option
- **Root cause:** a value of the right *kind* but the wrong *type* was
  converted by click itself, which accepts a few types that the command line
  cannot deliver: `workers: 5.5` became `5` (the command line refuses
  `--workers 5.5`), and `salt: 5` stayed the integer `5` instead of the text
  `"5"`.
- **`ethscan/cli.py`**: a config value is turned into the text that click
  would read from the command line before it is checked, so the two ways of
  passing a value behave the same.

### 3. A permanent sweep
- **`tests/test_config_value_sweep.py`** (new): walks every option of every
  command and writes a config file that holds a value of the wrong type for
  it, once in the section of the command itself and once in the global
  `defaults` that every command inherits. The command must report a usage
  error (exit code 2) that names the option, and must never leak a
  traceback. It also keeps the three rules that surround the check: a valid
  value is used, a broken value of another command is not this command's
  business, and a command line argument still wins over a broken config
  value.

## Verification

- Full suite: **4538 passed, 48 skipped** (before: 4484 passed, 45 skipped;
  the new sweep adds 54 cases and skips the 3 commands that need a network
  round trip).
- Ruff: `ruff check ethscan/ tests/` → **All checks passed**.
- `git diff --check`: clean.
- The new permanent sweep `tests/test_config_value_sweep.py` is a real
  regression test: with the production code reverted (`git stash push --
  ethscan/`) **50 of its 54 cases fail**, 68 of them with a leaked
  traceback.
- The command line still wins over the config file: `ethscan --config
  ethscan.yaml redis --port 22` runs with the port 22 even when the config
  file holds a `port: 99999`.

## Remaining

- The cache files of the `geo`, `cert` and `mac` commands
  (`~/.cache/ethscan/*.json`) are still read without a guard: a cache file
  that is not valid UTF-8, a cache entry that is not a mapping, or a
  timestamp that is not a number still leaks a traceback. See
  `HANDOFF_NEXT.md` for the reproduction and the task.
- The `cve` command still reports a services file it cannot read inside its
  own output when it is used as a library (`ethscan/cve.py`: the `notes`
  entry "Failed to read services file"). The CLI reports it as a usage error
  before the module runs, so the note is only reachable for a direct API
  user.
- A config file whose `defaults` or `commands` section is not a mapping is
  still a warning, not a usage error (the existing contract of
  `ethscan/config.py`: `validate_config`).
