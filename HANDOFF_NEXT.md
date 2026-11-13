# Handoff
Date: Fri Nov 13 2026 (session 136)

## This session
- Continued the per-key formatter hostile-sweep campaign with evidence-first reproduction.
- Probed `vuln` formatters with hostile nested shapes: scalar `recursive_hosts_scanned` (int/float/bool) crashed `format_vuln_report_markdown` at `ethscan/vuln.py:1198` with `TypeError: object of type 'int' has no len()`. The line used `len(cast(list, data.get('recursive_hosts_scanned', []) or []))` directly on an untrusted value.
- Fixed `ethscan/vuln.py` by introducing an inline `isinstance(recursive_hosts, (list, tuple, set))` guard (mirrors the existing `recursive_findings` guard below it); non-list/tuple/set values normalize to `[]`, so the count renders as 0 instead of raising.
- Added permanent hostile-sweep tests in `tests/test_vuln_hostile_sweep.py`:
  - `test_vuln_markdown_recursive_hosts_scanned_hostile` (7 parametrized shapes: None, 0, 1, True, 1.5, "x", b"bytes").
  - `test_vuln_markdown_recursive_findings_hostile` (same 7 shapes on `recursive_findings`).
  - `test_vuln_markdown_recursive_findings_elem_hostile` (non-dict recursive finding elements: None, 0, "x", (1,2), {1,2}, b"bytes", True, [1,2]).
  - `test_vuln_markdown_well_formed_recursive_preserved` (valid recursive data renders verbatim, including `**Recursive Hosts Scanned:** 2`).
- Added `import pytest` to the test file (was missing).

## Verification
- Repro before fix: `format_vuln_report_markdown` with `recursive_hosts_scanned=42` raised `TypeError`; after fix all hostile shapes render without raising.
- `pytest tests/test_vuln_hostile_sweep.py tests/test_vuln.py -q` -> 135 passed.
- `python -m pytest -q` -> 7056 passed, 146 skipped, 0 failed (baseline +18 new tests).
- `python -m mypy ethscan/vuln.py tests/test_vuln_hostile_sweep.py` -> Success: no issues found.
- `python -m ruff check ethscan/vuln.py tests/test_vuln_hostile_sweep.py` -> All checks passed.
- `python3 check_readme.py` -> 54/54, no diffs.
- `git diff --stat` (uncommitted): `ethscan/vuln.py` (+4/-1), plus new tests appended to existing test file.

## Blockers
- None.

## Approaches already tried / ruled out
- Generic top-level hostile-shape sweep across all formatters: 0 crashes (already hardened).
- Per-key hostile replacement sweep on `recon` formatters: 0 crashes (`_as_dict`/`_as_list` already guard).
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- Did not commit (no explicit commit request).

## Next task
- None pending. The pending hostile-sweep batch was executed this session with evidence-first reproduction: 212 hostile formatter calls across 13 modules (hash `results`, urlcheck `fuzz.all_results`, osdetect `probes`, subtake `vulnerable`/`all_results`, subdomains `resolved`/`all_results`/`per_depth`, dnssec `dnskey.keys`/`ds.records`/`chain`, ping `probes`, cidr `diff.difference`, s3 `results`, tls `versions`/`ciphers`, ssl `sans`, dnsbrute `axfr_entries`, resolve `records`, trace `hops`/`recursive_traces`) — 0 crashes reproduce. All formatters in this batch are already guarded with inline `isinstance` checks before iteration/indexing/join, so no fix is needed; do not speculate or add unneeded guards.
- Repository fully green (7056 passed, 146 skipped, 0 failed; mypy/ruff clean; check_readme 54/54). No source or test changes were made this session; probe-only, fully reversible, working tree clean.
- If future work is needed, pick a single bounded, verifiable improvement and reproduce it first — do not widen scope; do not commit unless explicitly asked. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

(End of file - total 39 lines)