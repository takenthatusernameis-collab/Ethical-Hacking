# NEXT_TASK

## Status: COMPLETE

### Task performed this session: reproduce-and-fix the remaining narrow resolver tuples

The previous handoff left the narrow resolver tuples in `subtake.py` and
`dnssec.py` untouched, claiming they were unreachable through the public
seam. This session re-ran that claim instead of trusting it: a reproduction
script (`/tmp/hostile_resolver.py`) was written that patches the resolver and
the dnspython transport to raise a custom `Hostile(Exception)` and calls each
helper and its public `run_*` with a `resolver=`/`server=` argument.

**Result: 5 of 12 seams crashed with the pre-fix source.** All 12 report with
the fix.

### What was actually verified

- `/tmp/hostile_resolver.py` -> pre-fix: 5 CRASH / 7 REPORTED; post-fix:
  12 REPORTED, 0 crashes.
- The 6 new regression tests fail against the pre-fix source (5 raise, 1
  passes only because `run_dnssec` already has an outer net) and pass with the
  fix: verified by stashing only the source changes.
- `python3 -m pytest tests/` -> **5190 passed, 48 skipped, 3 warnings**
  (baseline 5184; 6 new tests).
- `python3 -m pytest tests/test_protocol_hostile_sweep.py -q` -> **264 passed**.
- `python3 -m ruff check ethscan/ tests/` -> 40 errors, same codes as baseline
  (S110 +2 in subtake.py, matching the pre-existing style; no new codes, no
  unused-import regressions).
- `git diff --check` -> clean.
- The handoff's premise (dnspython 2.9.0 removed `dns.message`/`dns._features`,
  breaking 34 tests) was **verified false**: both attributes import in 2.9.0
  and the suite was already green. No dnspython repair was performed.

### What remains unresolved

Nothing demonstrated. The five crashing guards are fixed and locked in.

### Constraints

- Smallest reversible change; crashes become reported, never tracebacks.
- Do not commit unless explicitly asked.
- Reproduce before fixing any further tuple.

### One precise next task

None. The demonstrated crashes are fixed and covered by tests that fail
without the fix. The six commands from TASK.md (`ping`, `osdetect`, `resolve`,
`dns`, `stale`, `subdomains`) are already in
`tests/test_protocol_hostile_sweep.py` (lines 555-643), so that task is stale
too.

(End of file - total 47 lines)