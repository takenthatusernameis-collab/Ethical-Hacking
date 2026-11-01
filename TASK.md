## Status: COMPLETE (this session)

### What changed
- **`ethscan/config.py`** (`validate_config`): global `defaults` option names are now validated against the union of every command's accepted option dests, and unknown keys are reported as warnings. Previously only `commands.<cmd>.<opt>` typos were checked; a typo in `defaults` (e.g. `timeot`) was merged into every command's default map and silently ignored by Click.
- **`tests/test_config.py`**: added `test_validate_config_unknown_default_option`, `test_validate_config_known_default_option_clean`, `test_validate_config_format_key_in_defaults_is_known`.
- **`tests/test_cli.py`**: added `test_config_unknown_default_option_warning` and `test_config_known_default_option_no_warning`.

### What was actually verified
- `python -m pytest -q` -> 5458 passed, 53 skipped (full suite green).
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success, no issues found in 59 source files.
- Reproduced the defect before fixing: `defaults: {timeot: 5.0}` produced no warning, while `commands: {scan: {timeot: ...}}` did. After the fix the defaults typo is warned identically.
- End-to-end stderr assertion passes.

### What remains unresolved
- Nothing in-repo. `.github/workflows/test.yml` is maintainer-managed and excluded by the kilo controller.

### Which approaches failed and why
- None. The defect was found by behavioral audit, not by trusting prior "complete" claims.

### One precise next task
- None. Repository is in a verified complete state with one real defect fixed.