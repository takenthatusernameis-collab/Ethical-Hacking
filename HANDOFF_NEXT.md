# HANDOFF_NEXT.md

## Summary
Fixed the "profile sentinel-override" bug where explicitly passed `--timeout`/`--workers` (and `--service-timeout` for cve) were clobbered by profile defaults because the code compared against sentinel default values. Now using Click's `ParameterSource` to detect whether values were explicitly provided via CLI/ENV/DEFAULT_MAP; profile defaults only apply when not explicit. Also updated `report.py::_resolve_ports_and_defaults` to accept optional `timeout_explicit`/`workers_explicit` flags (backward compatible).

## Changes
- ethscan/cli.py: import ParameterSource, add @click.pass_context to scan/service/cve, replace sentinel checks with parameter source detection.
- ethscan/report.py: extend _resolve_ports_and_defaults signature to accept timeout_explicit/workers_explicit (default None preserves legacy behavior).

## Verification
- All CLI tests still pass (855 passed). Full suite: 3936 passed, 1 skipped. No regressions.
- Manual checks confirm explicit values preserved and profile defaults applied when not specified (scan/service/cve).

## Next agent task
Add regression tests for the profile-explicitness behavior (or continue with another bounded high-value fix). Suggested: add tests in tests/test_cli.py for scan/service/cve ensuring explicit timeout/workers survive profiles and defaults apply otherwise. Keep changes minimal and consistent with existing test style.
