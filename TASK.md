## Status: COMPLETE

Added CLI-level test coverage for the `config` command's warning output:
warnings for unknown commands and unknown options now have tests asserting they
appear in the JSON, Markdown, and CSV output of `ethscan config`.

### What changed
- tests/test_cli.py: added four tests
  (`test_config_unknown_command_warns_in_json_output`,
  `test_config_unknown_command_warns_in_markdown_output`,
  `test_config_unknown_command_warns_in_csv_output`,
  `test_config_unknown_option_warns_in_json_output`).

### What was actually verified
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped, 0 warnings.
- `python -m ruff check ethscan/ tests/` → All checks passed.

### What remains unresolved
None.

### One precise next task
None — repository complete. If new work arrives, implement the smallest change
solving a demonstrated problem and verify with `python -m pytest tests/ -q` +
`python -m ruff check ethscan/ tests/`.
