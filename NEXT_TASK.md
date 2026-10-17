# Next Task for Agent

## Status (current)
- `ethscan/__main__.py` → 100%; `ethscan/main.py` → 100%.
- `ethscan/snmp.py` → 100%; `ethscan/netbios.py` → 100% (covered by tests added/committed).
- `ethscan/mssql.py` → 98% (7 missing, provably unreachable; line 404 covered).
- `ethscan/radix.py` → 97% (9 missing, provably unreachable).
- `ethscan/cli.py` → 99% (21 missing, unreachable-in-tests).
- Full suite: 3887 passed, 1 skipped (confirmed).
- Working tree: clean. Tests `tests/test_netbios.py`, `tests/test_mssql.py` committed (3eace12).

## Provably dead / unreachable-in-tests (do not retest; avoid `ethscan/` source changes)
As previously documented:
- `mssql.py`: 389-391, 432-433, 455-456
- `radix.py`: 149-150, 153-154, 158-161, 219-220
- `cli.py`: 607-635 (superseded hash function; active is `hash_cmd`), 4639 (`__main__` guard not triggered by tests)

## Coverage effort: COMPLETE
Every `ethscan/` module is at 100% or has remaining missing lines characterized as provably unreachable/unreachable-in-tests and documented. No coverable gaps remain.

## Next precise task
Select a bounded, high-value task not involving forcing coverage of unreachable lines. Candidates:
1. **CLI UX/edge cases** (coverable): audit `cli.py` for small, verifiable behavior improvements with new tests that don’t require executing unreachable code. For example, improve test coverage for argument parsing/validation paths that are actually reachable, or verify error messages. Bound to <100-200 lines change max.
2. **Module robustness**: identify a specific function in a well-covered module that could benefit from a small defensive test (e.g. error handling path that is reachable). Prefer modules with existing high coverage.
3. **Documentation/tests linting hygiene**: fix minor lint/style issues in tests if they are non-invasive and verifiable, without touching `ethscan/`.

**Recommended next task:** Audit `cli.py` for a single, concrete, reachable edge case not currently tested (e.g. a specific validation error or option combination) and add 1-3 targeted tests. Avoid the documented unreachable regions (607-635, 4639). Verify with focused tests and ensure no behavior change to `ethscan/`.

## Verification approach
- Run targeted tests for the chosen module/feature.
- Ensure no new ruff violations in modified files only.
- Do not modify `ethscan/` source unless strictly necessary and with justification.
- Full suite not required if change is localized and safe, but acceptable.

Constraints: Preserve working baseline. Smallest reversible change. No parallel redesign. Proportionate handling.
