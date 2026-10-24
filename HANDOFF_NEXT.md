# HANDOFF: state for the next agent

## What changed this session

No source changes. This session was a verification sweep, not a fix sweep.

- Re-derived the full public `run_*` surface from `ethscan/*.py` (46 `run_*`
  functions) and identified every network seam.
- Ran a hostile-seam reproduction script (`/tmp/hostile_repro.py`) that patches
  each seam to raise `TypeError('hostile')` and calls the public function.
  **Result: 0 crashes out of 30 seam-bearing commands.** The remaining narrow
  `except` tuples (`subtake.py:302,333,361,425`, `dnssec.py:408,440`,
  `dnsbrute.py:_resolve_label` at 384/394) are behind a `resolver` argument and
  were exercised through their public paths; no crash was demonstrated, so per
  the handoff rule no tuple was broadened.

## What was actually verified

- `python3 /tmp/hostile_repro.py` -> 24 REPORTED, 6 skip (no seam), 0 crashes.
- `python3 -m pytest tests/test_protocol_hostile_sweep.py -q` -> **264 passed**.
- `python3 -m pytest tests/test_mac.py -q` -> **60 passed**.
- `git status` / `git diff --check` -> clean. Nothing committed.
- The 17 failures in `tests/test_dnsbrute.py` and the 16+1 in
  `tests/test_subtake.py` / `tests/test_subdomains.py` are **pre-existing on the
  committed tree** (verified by running them on a clean checkout): dnspython
  2.9.0 removed `dns.message` and `dns._features`. Not regressions.

## What remains unresolved

- **dnspython 2.9.0 incompatibility is the dominant open item.** It breaks 34
  tests across `test_dnsbrute.py`, `test_subtake.py` and `test_subdomains.py`.
  The affected code paths are guarded behind `DNS_AVAILABLE` / a custom
  `resolver`, so normal CLI use does not crash, but the suite is red. This is a
  library API change, not a missing `except`, and is out of scope for the
  transport-seam sweep.
- The dnspython resolver tuples in `dnsbrute._resolve_label`,
  `subtake.resolve_*` and `dnssec._query_*_dnspython` still exclude unnamed
  types; they were left untouched because no crash could be demonstrated with
  the installed dnspython.

## Which approaches have already failed and why

- Trusting the previous handoff's candidate list at face value would have wasted
  effort: re-deriving the surface from the source showed the remaining tuples
  are unreachable through the public seam, so broadening them would have been an
  unforced change with no demonstrated benefit.

## One precise next task

Repair the dnspython 2.9.0 incompatibility so the suite is green: replace the
removed `dns.message` / `dns._features` usages in `ethscan/dnsbrute.py`,
`ethscan/dns.py`, `ethscan/subtake.py`, `ethscan/dnssec.py` and
`ethscan/subdomains.py` with their 2.9.0 equivalents, then re-run
`python3 -m pytest tests/` and confirm the 34 failures are gone with no
regressions. After that, re-run `/tmp/hostile_repro.py` to confirm the
dnspython resolver seams still report instead of raise.

Do not broaden any tuple without first demonstrating a crash. Do not commit
unless explicitly asked.

(End of file - total 64 lines)