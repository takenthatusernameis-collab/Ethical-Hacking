# Next task

None pending. Repository fully green with 100% coverage (49966 passed, 147 skipped, 0
failed; mypy/ruff clean; README 54/54, 0 drift). Do NOT fabricate work, repeat
verification-only sessions as progress, or make empty/control-marker commits.

## Last change (this session)
- Added durable property-test hardening for the NetBIOS first-level name encoding
  (`ethscan/netbios.py::_encode_name_chars` / `_decode_name_chars`), a security-relevant
  pure helper that previously had only 3 fixed-input round-trip tests.
- `tests/test_netbios.py` (+44 lines, test-only, no production change):
  - `_rfc1001_first_level_oracle` — independent RFC 1001 first-level encoder.
  - `test_encode_name_chars_matches_rfc1001_oracle` — 4000 seeded cases vs the oracle.
  - `test_encode_decode_roundtrip_random_names` — 4000 seeded round-trip cases.
  - Seed `20261127`; added `import random`.

## Verified this session (evidence)
- Oracle probe before writing tests: 20,000 cases, 0 encode mismatches; round-trip
  failures only for trailing-space names (lossy by design) -> helper correct, not a defect.
- Mutation check: swapping nibble order in `_encode_name_chars` fails BOTH new tests;
  source restored clean; tests pass.
- Full gate under coverage: 49966 passed, 147 skipped, 0 failed (baseline 49964; +2);
  TOTAL 100% (16295 stmts, 6178 branches, 0 missing).
- `python -m mypy ethscan/ tests/` -> Success (278 files).
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions.

## Constraints / do-not-touch
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation.
- Do not modify `.github/workflows/**`.
- `snmp._parse_oid`, `service._parse_banner_*`, `headers.*`, netbios encode/decode are now
  verified clean / property-tested — do not re-probe unchanged.

## If future work is genuinely needed
FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral
evidence vs documented contract), then apply the smallest safe fix, rerun the focused check,
then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.
Fresh-angle lead not yet done: property-check `geo` cache/format helpers or `urlcheck` URL
classification vs a stdlib `urllib.parse` oracle, or strengthen another security-relevant
pure helper that only has `isinstance`/range assertions (checksum/netbios precedent).

Env note: `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
Do not commit manually; the workflow controller stages and commits.