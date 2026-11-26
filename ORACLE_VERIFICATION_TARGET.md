# Oracle Verification Results: ethscan.target Pure Helpers

**Date:** 2026-11-26
**Python:** 3.14.4
**Status:** ✅ ALL PASSED - 0 mismatches

## Summary

Extended independent-oracle verification to the `ethscan.target` pure helper functions using stdlib-only oracles (`ipaddress`, `urllib.parse`, `re`) over a hostile input matrix. All 7 functions verified with **0 mismatches**.

## Functions Verified

| Function | Test Cases | Result |
|----------|------------|--------|
| `normalize_host` | ~15,000+ | ✅ PASS |
| `parse_url` | ~15,000+ | ✅ PASS |
| `check_port` | ~65,500+ | ✅ PASS |
| `url_port` | ~15,000+ | ✅ PASS |
| `check_target_host` | ~2,000+ | ✅ PASS |
| `check_target_path` | ~2,000+ | ✅ PASS |
| `strip_userinfo` | ~50+ | ✅ PASS |
| `format_host_header` | ~30+ | ✅ PASS |

**Total cases:** ~115,000+ hostile inputs

## Hostile Input Matrix Coverage

### normalize_host / parse_url
- Empty/whitespace-only targets
- Schemes without hosts (`http://`, `redis://`, `://`)
- Hosts with spaces, tabs, newlines, control chars (C0 + DEL)
- Percent-encoded control chars (`%00`, `%09`, `%0a`, `%0d`, `%20`, `%7f`)
- IPv6 literals (bracketed/unbracketed, with/without ports, zone IDs)
- IPv6 literals ending in `:<digits>` (port ambiguity)
- IPv4 literals
- DNS names (valid, IDN, malformed `....`, `example..com`)
- Userinfo in authority (`user:pass@host`, `user@host`)
- Very long inputs (10K+ chars)
- Non-ASCII / Unicode hosts
- Mixed case schemes/hosts
- Unparseable URLs (unmatched brackets)

### check_port / url_port
- Full range -10 to 65545 (boundaries 0, 65535, 65536)
- String forms of all numeric ports
- Non-numeric strings (`notaport`, `1.5`, empty, whitespace)
- Unicode digits (fullwidth, Arabic-Indic, Devanagari) - accepted by `int()`
- Very large numbers (10^10, 10^20)
- Negative strings

### check_target_host
- Empty/whitespace
- Hosts with spaces and all C0 control chars + DEL
- Percent-encoded control chars (raw and decoded)
- Valid hosts (DNS, IPv4, IPv6, with schemes)
- Very long hosts (10K chars)

### check_target_path
- Valid paths (with/without query, fragment, percent-encoding)
- Paths with spaces, tabs, newlines, control chars
- Query strings with spaces/control chars
- Fragments with spaces/control chars (should be accepted - not sent to server)
- Percent-encoded paths (raw check only)
- Very long paths (10K chars)

### strip_userinfo
- Standard userinfo cases (`user:pass@`, `user@`, `:@`)
- Multiple `@` in path (only authority stripped)
- With/without schemes
- IPv6 hosts with userinfo
- Edge cases (empty user, empty pass, both empty)

### format_host_header
- IPv6 literals (bracketed by oracle)
- Already bracketed IPv6 (unchanged)
- IPv6 with zone IDs (zone stripped, then bracketed)
- IPv4 literals (unchanged)
- DNS names (unchanged)
- Empty/whitespace
- Invalid inputs (graceful handling)

## Verification Methodology

Each function was verified against a **stdlib-only oracle** that implements the same specification using only:
- `ipaddress` for IP parsing/validation
- `urllib.parse` for URL parsing
- `re` for character class matching

The oracle is independent of the implementation - it re-implements the spec from scratch using only stdlib. A mismatch indicates a genuine defect in either the implementation or the oracle.

## Baseline Re-verification

All project quality gates remain green:
- `pytest -q` → **49,799 passed, 147 skipped, 0 failed** (150s)
- `mypy ethscan/ tests/` → **Success: no issues found in 271 files**
- `ruff check ethscan/ tests/ check_readme.py` → **All checks passed**
- `check_readme.py` → **54 CLI commands, 0 drift both directions, exit 0**
- `coverage` → **TOTAL 100% (16,271 stmts, 6,160 branches, 0 missing)** on Python 3.14.4

## Conclusion

No defects found in `ethscan.target` pure helpers. The implementation correctly handles all hostile inputs per specification. The oracle verification script (`oracle_verify_target.py`) is retained for future regression testing.