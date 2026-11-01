## Status: COMPLETE (this session)

### What changed
- **`ethscan/config.py`** (`validate_config`): global `defaults` option names are now validated against the union of every command's accepted option dests, and unknown keys are reported as warnings. Previously only `commands.<cmd>.<opt>` typos were checked; a typo in `defaults` (e.g. `timeot`) was merged into every command's default map and silently ignored by Click. The docstring already claimed typos were caught, so this was a real gap between contract and behavior.
- **`tests/test_config.py`**: added `test_validate_config_unknown_default_option`, `test_validate_config_known_default_option_clean`, `test_validate_config_format_key_in_defaults_is_known`; the pre-existing `test_validate_config_defaults_are_not_option_checked` (empty `known_options` sentinel) still passes because defaults are only checked when the caller supplies real command information.
- **`tests/test_cli.py`**: added `test_config_unknown_default_option_warning` and `test_config_known_default_option_no_warning` (end-to-end stderr assertions).

### What was actually verified (this session)
- `python -m pytest -q` -> **5458 passed, 53 skipped** (was 5453; +5 new tests). Full suite green.
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success, no issues found in 59 source files.
- Reproduced the defect before fixing: `defaults: {timeot: 5.0}` produced **no** warning, while `commands: {scan: {timeot: ...}}` did. After the fix the defaults typo is warned identically.
- End-to-end: `ethscan --config <yaml with defaults typo> scan --target 127.0.0.1 --ports 80` prints `Warning: Unknown option 'timeot' in global defaults (no such option for any command)` on stderr and still runs.
- Re-verified all README-documented behavioral contracts still hold (usage errors exit 2, validate/mysql/s3 exit 0, config --init/--out mutual exclusion, config --init writes sample, config report format precedence, hash --check match/mismatch/unknown-length, hash --iterations requires --salt, audit stdin, config `format` remap + CLI override).
- `git status --short` -> clean except the 3 intended files.

### What remains unresolved
- Nothing in-repo. The maintainer-managed `.github/workflows/test.yml` situation is unchanged and out of scope for in-repo agents (the kilo controller restores tracked workflow files and excludes `.github/workflows/**` from checkpoint commits).

### Which approaches failed and why
- None. The defect was found by behavioral audit, not by trusting prior "complete" claims. No speculative changes.

### One precise next task
- None. Repository is in a verified complete state with one real defect fixed. If a maintainer adds `.github/workflows/test.yml`, verify the Actions run passes across ubuntu/macos/windows.