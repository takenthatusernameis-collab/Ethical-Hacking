# Task

Date: 2026-10-19T15:20:00Z
Status: Profile sentinel-override bug fixed; handoff prepared.

## What changed
- Fixed profile logic in CLI (scan/service/cve) to detect explicit parameters via Click ParameterSource instead of sentinel equality; profile defaults only apply when not explicitly set (CLI/ENV/DEFAULT_MAP treated as explicit per fix requirement).
- Updated report.py::_resolve_ports_and_defaults to accept optional timeout_explicit/workers_explicit flags while preserving backward compatibility.

## Verification
- CLI: 855 passed
- Full suite: 3936 passed, 1 skipped (no regressions)
- Confirmed explicit timeout/workers survive profiles; profile defaults apply when unspecified.

## Next
See HANDOFF_NEXT.md and NEXT_TASK.md for next bounded task and details.
