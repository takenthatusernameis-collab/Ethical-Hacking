# NEXT_TASK

## Status: PENDING

Add an end-to-end CLI-level test in `tests/test_cli.py` for config option validation.

### What to do

Invoke `ethscan --config <file> <command>` through the Click runner and assert:
- (a) a config containing a bogus option for a command (e.g. `cidr: { bogus: 1 }`) prints a warning like `Unknown option 'bogus' for command 'cidr'` on stderr.
- (b) a config containing the documented `format` key (e.g. `cidr: { format: json }`) prints no such warning.

This complements the unit tests already in `tests/test_config.py` and locks in the end-to-end behavior.

### Verification commands

- `python -m ruff check ethscan/ tests/`
- `python -m pytest tests/test_config.py tests/test_cli.py -q`
- `python -m pytest tests/ -q`

### Constraints

- Smallest reversible change
- No behavior changes
- Ruff-clean
- Full test suite passes
- Do not commit unless explicitly asked

### Evidence / references

- `ethscan/config.py:234` `validate_config` now accepts `known_options` and warns on unknown options.
- `ethscan/config.py:_option_is_known` treats documented `format` as the `fmt` dest.
- `ethscan/cli.py:410` passes `known_options` built from `cli.commands`.
- `tests/test_config.py` already covers `validate_config` at unit level.
