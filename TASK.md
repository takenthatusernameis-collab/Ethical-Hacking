# TASK.md

Date: 2026-10-20T19:54:00Z
Status: the **`--services-file` of the `cve` command** is now read leniently,
the way the CLI already reads it, and is kept that way with a test. A services
file with a byte that is not UTF-8 used to leak a `UnicodeDecodeError`
traceback (exit 1); it now exits 0 with no traceback.

## What changed

### 1. Read the services file leniently
- **Root cause:** the services file was read with a strict
  `open(services_file, "r", encoding="utf-8")` and `json.load`. The `except`
  clause caught `json.JSONDecodeError` and `OSError`, but not a
  `UnicodeDecodeError` (a `ValueError`), so a services file with a stray byte
  leaked a traceback. The CLI pre-reads the file leniently, so the check
  passed and the module then read it strictly.
- **`ethscan/cve.py:271-277`**: the services file is now read with
  `ethscan.fileio.load_json`, which decodes leniently (the same contract the
  CLI already used). The existing `except (json.JSONDecodeError, OSError)`
  clause is kept, so a file that is not JSON is still reported in the `notes`
  of the result (the module's library contract) and a file that cannot be
  decoded is read as far as it can be read.

### 2. Regression test
- **`tests/test_cve.py`: `test_run_cve_services_file_not_utf8`** — a services
  file with a non-UTF-8 byte is read without leaking a traceback and its
  decoded content is used.

## Verification

- Reproduction now exits 0 with no traceback (before: `UnicodeDecodeError` at
  `ethscan/cve.py:274`, exit 1).
- Full suite: **4558 passed, 48 skipped, 2 warnings** (before: 4557 passed;
  the new test adds 1 case).
- Ruff: `ruff check ethscan/ tests/` → **All checks passed**.
- `git diff --check`: clean.
- No remaining `open(...encoding="utf-8")` + `json.load` strict reads in
  `ethscan/`.

## Remaining

- The **`cve` library** still reports an unreadable services file as a `notes`
  entry ("Failed to read services file"); the CLI reports it as a usage error
  (exit 2). Left alone on purpose: module contract.
- A config file whose `defaults` or `commands` section is not a mapping is
  still a warning, not a usage error (`ethscan/config.py`: `validate_config`).
  Left alone: existing contract.
- One precise next task for the next agent: add a subprocess-level CLI
  regression test proving `cve --services-file <non-utf8-file>` exits 0 with
  no traceback (see `HANDOFF_NEXT.md` / `NEXT_TASK.md`).
