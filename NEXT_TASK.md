# Next task

None strictly required. Repository fully green with 100% coverage (50063 passed, 147 skipped, 0 failed; mypy/ruff clean). Do NOT fabricate work, repeat verification-only sessions as progress, or make empty/control-marker commits.

## Last change (this session)

- Added 2 test fns to `tests/test_netbios.py` locking the security-critical `ethscan.netbios._parse_nbtstat_rdata` (NBSTAT RDATA -> names + MAC) against an INDEPENDENT from-scratch packet-builder oracle:
  - `_oracle_nbtstat_entry` / `_oracle_nbtstat_flags` / `_NBSTAT_SUFFIX_ORACLE` (complete independent suffix->service table, does not reuse ethscan or test `_entry`).
  - `test_parse_nbtstat_rdata_matches_independent_oracle_random`: 3000 random RDATA buffers assert names, suffixes, flags dict, and MAC match the oracle.
  - `test_parse_nbtstat_rdata_hostile_bytes_never_crash`: 3000 random hostile buffers assert only ValueError or a dict return (no hang/crash/other exception).
- No `ethscan/` source changed (verified correct, not a defect).

## Verified this session (evidence)

- `python -m pytest tests/test_netbios.py -q` -> 97 passed (95 baseline + 2 new), 0 failed.
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> 50063 passed, 147 skipped, 0 failed (baseline 50061; +2 new tests); TOTAL 100% (16292 stmts, 6178 branches, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 286 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `git status` -> only `tests/test_netbios.py` modified; `git diff --check` clean; nothing committed

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional — out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation — do not change to game coverage.
- `_parse_dns_name`/`_decode_name_chars`/`_encode_name_chars`, `netbios` encode/decode, `hash` MD4, and `_parse_nbtstat_rdata` are verified correct and now property-tested — do not re-probe unchanged or "fix" them.
- Do not modify `.github/workflows/**`.
- All documented leads are done or probed clean; do not re-probe unchanged.

## If future work is genuinely needed

FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), then apply the smallest safe fix, rerun the focused check, then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`.

- Evidence-based lead NOT yet done (revisit only with a NEW angle): randomized differential of `_parse_nbns_response` full-message assembly vs an INDEPENDENT packet builder (build random NBSTAT/NB answers with a from-scratch encoder incl. DNS compression pointers, assert parsed names/suffix/flags/mac/addresses match). Currently only example-based tests.

## Environment / critical notes

- **Test deps are NOT preinstalled.** Run `pip install --quiet pytest mypy ruff coverage dnspython` first (installs to `~/.local/bin`, not on PATH; use `python -m <tool>`). `click`/`pyyaml` preinstalled; `dnspython` is not.
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.8 min (50063 tests). Do not commit manually; the workflow controller stages and commits.
- Always re-verify HEAD first-hand rather than trusting the handoff's "green" claim — prior handoffs were stale.
