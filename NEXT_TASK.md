# NEXT_TASK.md

## Status (2026-10-19T15:20:00Z)
- Task from prior agent: fix `resolve --server` ignored for CNAME lookups — completed and verified (previous session + this context)
- Current: fixed profile sentinel-override bug (explicit CLI `--timeout`/`--workers` clobbered by profile defaults) in CLI (scan/service/cve) using Click parameter source detection; also updated report.py to accept explicit flags while preserving backward compatibility. All existing tests still pass (3936 passed, 1 skipped). No regressions.
- Lint baseline unchanged (48 intentional errors). No new lint errors introduced in touched files.

## What changed
- `ethscan/cli.py`: added `ParameterSource` import, `@click.pass_context` on scan/service/cve, detect if timeout/workers/service_timeout were explicitly passed via CLI/ENV/DEFAULT_MAP; only apply profile defaults when not explicit.
- `ethscan/report.py`: `_resolve_ports_and_defaults` now accepts optional `timeout_explicit`/`workers_explicit` booleans (defaulting to legacy behavior) so callers can signal explicitness.

## Verification
- CLI tests: 855 passed
- Full suite: 3936 passed, 1 skipped
- Targeted verification:
  - `scan --profile fast` → timeout 0.5, workers 200 (profile defaults)
  - `scan --profile fast --timeout 1.0` → timeout 1.0 preserved
  - `scan --profile full --workers 100` → workers 100 preserved
  - `scan --profile full` → timeout 2.0, workers 50
  - `service --profile fast --timeout 1.0` → timeout 1.0 preserved
  - `service --profile full --workers 30` → workers 30 preserved
  - `cve --profile fast --service-timeout 1.0` → service_timeout 1.0 preserved
  - `cve --profile fast --workers 100` → workers 100 preserved

## Next task (bounded, high-value)
Investigate and fix `scan --ports all` with profile interaction semantics if any; or add tests for `service/cve --ports all` with profiles? Or alternatively look at a small remaining issue: in CLI scan, when profile is set, if user passes `--ports all`, we correctly take all ports (not profile ports). Also in report.py when explicit flags not given, it falls back to sentinel logic - consistent. Another potential issue: when ports are explicitly specified (not 'common'), does profile override timeout/workers regardless? Yes per current logic. But maybe add explicit regression tests for the report module's new explicit flags if called that way.

But looking at the test suite more - there might be a useful small fix. Let us look for another issue: in CLI scan, when profile is given and ports is not 'common' and not 'all', we parse ports as given - correct. Also the profile's help text says "Overrides --ports, --timeout, --workers unless explicitly set." So ports behavior is: if ports is 'common' (default when using profile?), or if not explicitly changed? The logic: if profile and ports_spec=='common', use profile ports. If user explicitly gives other ports, we use those ports - so ports can be overridden by explicit specification. That matches. The fix is correct.

Another small thing - the handoff said "thread the resulting booleans into `report.py::_resolve_ports_and_defaults` as optional keyword args defaulting to today's behaviour" - done. Also maybe the `run_report` in report.py could accept/forward? Let us check - does run_report need updating? Looking at how it's called. The current signature takes timeout/workers as values; if someone wants to signal explicitness from outside, they can't with current signature. But the handoff only mentioned threading booleans into _resolve_ports_and_defaults. That matches what we did.

A good bounded next task: add regression tests for the report module with explicit flags? Or fix any remaining sentinel logic. Let us look around - also in cve, when services_file is provided, profile logic is skipped - correct. Also in CLI, for scan/service/cve we handle correctly.

Another task: there might be an issue where if user sets timeout via env var or default_map, we correctly treat as explicit. That matches the handoff's requirement.

Alternatively, let us add the regression tests that the handoff mentioned? The handoff said "Add regression tests that fail before the fix..." but didn't specify exact test locations. Maybe add to test_cli.py? Let us look up test patterns - maybe add tests like test_scan_profile_preserves_explicit_timeout etc. Let us add a couple of focused regression tests. Let us look at how other profile tests are named.
