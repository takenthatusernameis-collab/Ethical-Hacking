# Next Task

## Candidate (bounded, verify before coding)
Add regression tests to `tests/test_fileio.py` for `write_text`/`write_json` error handling, capturing the repro evidence from this session:
- (a) unwritable parent directory → `OSError` (e.g. `PermissionError`)
- (b) target path that is an existing directory → `OSError` (e.g. `IsADirectoryError`)
- (c) parent path that is a file → `OSError` (e.g. `FileExistsError`)
- (d) atomicity on failure: a failed mid-write leaves existing destination content intact and removes the temp file

Assert `OSError` is raised (matching the `_write_output` → `click.BadParameter` usage-error contract, exit 2). No product-code change. Verify with `python -m pytest tests/test_fileio.py -q` and `ruff check`. Do not commit unless asked.

## Constraints
- Do not re-audit `--out`/`--init` routing (already covered: all `--out` sites route through `_write_output` → `write_text`; `--init` routes through `write_text`).
- Do not weaken safety controls or turn this into an infrastructure project.
