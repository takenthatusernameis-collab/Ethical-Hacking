# Handoff
Date: Sat Nov 07 2026

## What changed
- `ethscan/cli.py`: Added `_validate_enum_target(target)` before wordlist/file I/O in `fuzz` (before `load_wordlist`) and `brute` (before `_require_utf8`/`load_cred_wordlist`). Invalid/malformed targets now rejected as usage errors before file reads.

## Verified
- `python3 -m ruff check .` → all checks passed.
- `python3 -m mypy ethscan` → Success, 59 source files.
- `python3 -m pytest tests/test_fuzz.py tests/test_brute.py tests/test_cli.py -q` → 1102 passed.

## Unresolved
- Other commands may still read files before target validation; not audited exhaustively.

## Next task
- Audit remaining file-reading commands (e.g., osdetect banners, vuln services, cve services) for side-effect-before-validation gaps; reproduce first, then smallest guard.
