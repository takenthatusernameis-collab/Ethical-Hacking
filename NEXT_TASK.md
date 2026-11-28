# Next task

None pending. Repository fully green with 100% coverage (49999 passed, 147 skipped, 0 failed; mypy/ruff clean; README 54/54, 0 drift). Do NOT fabricate work, repeat verification-only sessions as progress, or make empty/control-marker commits.

## Last change (this session)

- Added durable property-test hardening for the security-critical `scanner.parse_port_range` (decides which TCP/UDP ports a scan touches), which previously had only fixed example tests. A fresh-angle differential fuzz against an independent "construct-from-known-set" oracle first confirmed the implementation is CORRECT (0 mismatches / 20,000 valid specs; all 19 invalid specs raised `PortSpecError`) — not a defect. New `tests/test_scanner_port_range_property.py` (21 cases, seed 20261128). No production code changed.

## Verified this session (evidence)

- Mutation check: `range(start, end + 1)` -> `range(start, end)` made 2 tests FAIL; source restored, all 21 pass.
- `python -m pytest -q` (under coverage) -> 49999 passed, 147 skipped, 0 failed
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 280 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions; exit 0
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> TOTAL 100% (16295 stmts, 6178 branches, 0 missing)
- `git status` -> only new `tests/test_scanner_port_range_property.py` (untracked); `git diff --check` clean

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation.
- Do not modify `.github/workflows/**`.
- `scanner.parse_port_range` is now property-tested and was fuzz-verified correct — do not re-probe unchanged or "fix" it.
- All previously probed leads (`cert._extract_subdomains`, `snmp._decode_varbind_value`/`_assign_varbind`, version matching, password helpers, checksum/netbios/nmap/cidr-validate property tests, etc.) were confirmed correct — do not re-probe unchanged.

## If future work is genuinely needed

FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), then apply the smallest safe fix, rerun the focused check, then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.

Evidence-based lead NOT yet done (fresh angle): property-check `wifi._parse_proc_net_wireless` (pure `/proc/net/wireless` parser, only example tests) vs an independent line-format oracle, or `mac._normalize_mac_for_api`/`_is_mac_address` vs a stdlib `re`/`ipaddress` oracle. Prior sessions report wifi/mac clean, so only revisit with a NEW angle.

## Environment/notes

- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Do not commit manually; the workflow controller stages and commits.