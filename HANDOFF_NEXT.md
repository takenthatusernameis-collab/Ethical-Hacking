# Handoff
Date: Sat Nov 07 2026

## What changed
- `ethscan/cli.py` (`stale`): validate each explicit `--target` with `_validate_enum_target()` before reading `--file` (`load_domains_from_file`). Smallest reversible fix for file-read side effect when an explicit target is unusable.
- `tests/test_cli.py`: added `test_stale_rejects_bad_target_before_reading_file`.

## Verified
- `python3 -m pytest tests/test_cli.py -q -k "stale_rejects_bad_target_before_reading_file or stale_help or stale_offline"` → 5 passed.
- `python3 -m pytest tests/test_stale.py tests/test_cli.py -q -k stale` → 66 passed.
- `python3 -m ruff check ethscan/cli.py tests/test_cli.py` → all checks passed.
- `python3 -m mypy ethscan/cli.py` → Success.

## Unresolved
- Full suite not rerun this session (focused change; prior baseline 5909 passed, 50 skipped per previous handoff). Re-run if integrating multiple changes or if broader regressions are suspected.

## Failed approaches / evidence
- None. Reproduced gap before fix: `stale --file <existing> --target 'http://]bad['` returned target usage error (exit 2) but the CLI read the file before `run_stale` normalized targets; fix moves explicit-target validation before file read.

## Next task
- Audit for a *demonstrated* file/side-effect-before-validation gap in a different command. Reproduce with an unusable input that should be rejected (usage error) plus a file/side effect that would be triggered first; fix only with evidence. Avoid re-sweeping already-fixed patterns (`report`/`brute` target-before-credential-file order already correct in code).
