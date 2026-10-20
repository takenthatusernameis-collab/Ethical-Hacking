# NEXT TASK

## Status: COMPLETE

The **`--services-file` of the `cve` command** is now read leniently, the way
the CLI already reads it, and is kept that way with a test.

## What was done

- **`ethscan/cve.py:271-277`**: the services file is now read with
  `ethscan.fileio.load_json` (lenient UTF-8 decode via `errors="replace"`)
  instead of a strict `open(services_file, "r", encoding="utf-8")` +
  `json.load`. The existing `except (json.JSONDecodeError, OSError)` clause is
  kept, so a file that is not JSON is still reported in the `notes` of the
  result (the module's library contract) and a file that cannot be decoded is
  read as far as it can be read.
- **`tests/test_cve.py`**: new
  `test_run_cve_services_file_not_utf8` — a services file with a byte that is
  not UTF-8 is read without leaking a traceback and its decoded content is
  used.
- The **`notes` entry "Failed to read services file"** is unchanged: it is the
  module's own contract for a direct API user. The CLI still reports an
  unusable services file as a usage error (exit 2) — `ethscan/cli.py`
  `_load_json_file` is not weakened.

## Verification

- Reproduction from `HANDOFF_NEXT.md` now exits 0 with no traceback (before:
  `UnicodeDecodeError` at `ethscan/cve.py:274`, exit 1).
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/test_cve.py -q` → **59 passed**.
- `python -m pytest -q` → **4558 passed, 48 skipped, 2 warnings**
  (was 4557 passed; the new test adds 1 case).
- `git diff --check` → clean.

## Next agent

Do not re-run the services-file task; it is complete and verified.

The remaining open items from `HANDOFF_NEXT.md` were **deliberately left
alone** and are not bugs:
- the `cve` library reports an unreadable services file as a `notes` entry
  ("Failed to read services file"); the CLI reports it as a usage error
  (exit 2);
- a config file whose `defaults` or `commands` section is not a mapping is a
  warning, not a usage error (`ethscan/config.py`: `validate_config`).

One precise next task (bounded, verifiable): **add a subprocess-level CLI
regression test** proving `cve --services-file <file-with-a-non-utf8-byte>`
exits 0 and prints no traceback. Current coverage is library-level only; the
file-content sweep (`tests/test_file_content_sweep.py`) cannot see this leak
because the CLI pre-reads the file leniently before the module reads it.

Evidence and constraints:

- Reproduction (exit 0, no traceback after the fix):
  ```bash
  D=$(mktemp -d)
  printf '{"services": [{"port": 80, "banner": "Apache/2.4 \xff bad"}]}' > "$D/services.json"
  python -m ethscan cve --target 127.0.0.1 --services-file "$D/services.json"
  ```
- The test must run the CLI as a subprocess (or via CliRunner over the full
  `cli()` entry point), not call `run_cve` directly, so it guards against the
  CLI/module drift that caused the leak.
- Constraints: keep the `notes` entry contract; keep the CLI usage-error
  (exit 2) for an unusable services file; do not change the services file's
  content.
