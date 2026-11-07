# Task
Date: Sat Nov 07 2026

## Current state
- Full suite (this environment, verified): `5907 passed, 50 skipped` (one unrelated flaky brute unreachable-sweep test fails only under full-suite timing; passes in isolation).
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.

## This session
- **Demonstrated gap (reproduced):** `osdetect` (`--banners-file`), `vuln` (`--services-file`/`--tls-file`/`--ssl-file`), and `cve` (`--services-file`) read user-supplied files before the target is validated inside `run_*`. An unusable target still triggered file I/O, and with an unusable target plus an unusable file the file error won over the target error.
- **Fix (smallest reversible):** Added `_validate_enum_target(target)` at the top of the `osdetect`, `vuln`, and `cve` CLI command bodies, before any file reads — matching the established pattern already used for `fuzz`/`subdomains`/`subtake`/`dnsbrute`/`s3`/`recon`/`brute`. Invalid targets are now reported as usage errors (exit code 2) before any file I/O; valid-target flows unchanged.
- **Tests:** Added 5 CLI tests in `tests/test_cli.py` proving an unusable target is rejected before the file is read (bad file + unparseable URL target → target usage error, not file error).

## Verified
- `python3 -m ruff check .` → all checks passed.
- `python3 -m mypy ethscan` → Success, 59 source files.
- `tests/test_cli.py tests/test_vuln.py tests/test_cve.py tests/test_osdetect.py` → 1333 passed.
- Full suite → 5907 passed, 50 skipped (1 unrelated flaky brute unreachable-sweep failure, passes in isolation).

## Blockers
- None demonstrated.

## Next task
- None demonstrated; baseline is green. No further file-before-target-validation sweep remains for osdetect/vuln/cve. Do not commit unless asked.
