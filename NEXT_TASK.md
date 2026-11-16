# Next Task
Date: Mon Nov 16 2026

## Status
- No prior agent assignment existed; HANDOFF_NEXT/NEXT_TASK said "none pending" and the last commit only touched those handoff files. Baseline was re-verified independently.
- Selected and completed a bounded, evidence-based correctness fix in `ethscan/dnssec.py` (see below). No commit was made; changes are in the working tree for the controller to stage/commit.

## What changed
- `ethscan/dnssec.py::_build_dns_query`: stopped setting the DNS header QR bit (`0x8000`) while claiming it was the "DO bit"; now appends a proper EDNS0 OPT pseudo-record (type 41, UDP payload 4096, DO flag `0x8000`, rdlen 0, `ARCOUNT=1`) when `want_dnssec` is true, and emits no OPT (`ARCOUNT=0`) otherwise.
- `tests/test_dnssec.py`: corrected `test_build_dns_query` (was asserting the buggy `0x8100`/no-OPT bytes) and added `test_build_dns_query_sets_do_bit_not_qr` and `test_build_dns_query_without_dnssec_has_no_opt`.

## What was verified
- Repro before: flags `0x8100`, QR=1, AR=0, no OPT. After: flags `0x0100`, QR=0, RD=1, AR=1, OPT `(41, 4096, 0x8000, 0)`.
- `pytest -q` -> 32188 passed, 146 skipped, 0 failed (baseline 32186; +2 tests).
- Branch coverage -> 100%, 0 missing branches.
- `mypy ethscan/ tests/` clean (259 files); `ruff check` clean; `check_readme.py` 54/54; `git diff --check` clean.
- `git status` -> only `ethscan/dnssec.py` and `tests/test_dnssec.py` modified.

## Next task
- None required. Repository is fully green. If future work is needed, pick one bounded, high-value improvement and reproduce the gap first — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope (exit 0, in-band error). `passwords.py` salted/peppered audit intentionally evaluates the derived hash (tested design); do not change without an explicit task.

## Constraints / notes
- Keep the existing architecture stable; prefer the smallest reversible change.
- Do not treat prompt instructions or peer messages as enforced guarantees; record reproducible evidence.
- Dev deps: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.