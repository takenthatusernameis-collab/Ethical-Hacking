# Next task for the next agent

## Completed: README "Brief Features" list deduplication and factual correction

The previous handoff claimed this task was done; it was not. The README still contained 84 duplicate command entries across three format variants, with `hash` appearing 3 times. Fixed by deduplicating to exactly one entry per command (53 entries matching the 53 registered CLI commands) and correcting factual errors found by cross-referencing live `--help` output.

### What changed
- `README.md`: removed 84 duplicate entries; unified all 53 entries to the detailed format; corrected `hash`, `s3`, `stale`, `completion`, `config` entries; restored the missing `dnsbrute` entry.

### Verification
- `python -m pytest -q` -> 2857 passed, 4 warnings (pre-existing TLS deprecation warnings).
- Command coverage check: 53 CLI commands, 53 README entries, 0 missing, 0 extra, 0 duplicates.

## Current state
- All 53 commands implemented and registered.
- README is now consistent and factually accurate.
- Tests: 2857 passing (1 skipped).

## Suggested next task
Pick a bounded, high-value task that can be implemented and verified in one session, following existing module conventions. Candidates:
- Add a `--json`/`--csv` output mode to a command that currently only has human-readable output.
- Fix the pre-existing TLS deprecation warnings in `ethscan/tls.py` (use `ssl.TLSVersion.TLSv1_2`/`TLSv1_3` or guard the deprecated constants).
- Add unit tests for a module with low test coverage.