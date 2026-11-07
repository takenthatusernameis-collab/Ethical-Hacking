# Handoff
Date: Sat Nov 07 2026

## What changed
- `ethscan/cli.py`: `osdetect`, `vuln`, and `cve` now call `_validate_enum_target(target)` before reading `--banners-file`/`--services-file`/`--tls-file`/`--ssl-file`. Invalid/malformed targets are rejected as click usage errors (exit code 2) before any file I/O; previously the file was read first and (with a bad file) the file error won over the target error.
- `tests/test_cli.py`: Added 5 tests proving an unusable target is rejected before the file is read (bad file + unparseable URL target → target usage error, not file error) for vuln services/tls/ssl, osdetect banners, and cve services.

## Verified
- `python3 -m ruff check .` → all checks passed.
- `python3 -m mypy ethscan` → Success, 59 source files.
- `tests/test_cli.py tests/test_vuln.py tests/test_cve.py tests/test_osdetect.py` → 1333 passed.
- Full suite → 5907 passed, 50 skipped (1 unrelated flaky brute unreachable-sweep failure, passes in isolation).

## Unresolved
- None for this sweep. One pre-existing, unrelated flaky test (`test_brute_cli_reports_a_failed_login`) fails only under full-suite timing and passes in isolation; not caused by this change.

## Next task
- None demonstrated; baseline is green. Do not commit unless asked.
