# TASK

## Status: COMPLETE

Repository verified. One bounded, demonstrated bug was found and fixed this session: `config --out` leaked a failure when the parent directory did not exist.

### What changed

- `ethscan/cli.py:3684-3693` — `config --out` wrote its report with a raw `open()` instead of delegating to `ethscan.fileio.write_text`, so a `--out` path whose parent directory did not exist failed with "Error writing output: [Errno 2] No such file or directory" and exited 1. Every other report command (and `config --init`) already used `write_text`, which creates the parent directory. The fix routes `config --out` through the same helper, matching the contract established in commit `d5c5926`.
- `tests/test_cli.py` — added `test_config_out_creates_missing_parent_dirs` and `test_config_out_refuses_a_directory` next to the existing `test_config_out_json` / `test_config_out_markdown`.

### What was actually verified

- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5215 passed, 51 skipped, 0 warnings (was 5213).
- `python -m ethscan config --out /tmp/cfg-missing/deep/config.json` → writes the report and creates the parent directories (exit 0), confirmed by hand after the fix.

### What remains unresolved

None.

### One precise next task

None — repository complete. If new work arrives, implement the smallest change solving a demonstrated problem and verify with `python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`.