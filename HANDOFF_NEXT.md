# Handoff
Date: Sun Nov 22 2026

## State
- HEAD: `384c651` (main). The single commit between the prior HANDOFF's `a10e18d` and `384c651` is control-marker-only (touches `HANDOFF_NEXT.md`/`NEXT_TASK.md` only, no source/test changes) — not counted as progress.
- Working tree: clean.
- Repo fully green; no pending task. This session was inspection + gap-probing (no source/test changes).

## What changed this session
- Nothing. No source or test changes made.

## What was actually verified this session (fresh evidence)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python -m mypy ethscan/ tests/` -> Success: no issues in 268 source files.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions; `git diff --check` clean.
- `python -m pytest -q` -> **46771 passed, 147 skipped, 0 failed** (matches baseline).
- `python -m pytest tests/test_readme_sync.py -q` -> 5 passed (bidirectional command + option sync).
- `python -m pytest tests/test_all_formatters_hostile_contract.py tests/test_all_assessors_hostile_contract.py -q` -> all pass.

## Gap-probing performed (no genuine gap found — do not repeat)
Probed and confirmed correct, so these are NOT candidates for new work:
- Empty-target rejection across all 22 target-taking commands (`redis`, `memcached`, `ntp`, `snmp`, `ftp`, `ldap`, `netbios`, `smb`, `smtp`, `service`, `dnssec`, `ssl`, `tls`, `web`, `fuzz`, `trace`, `s3`, `mysql`, `mongodb`, `mssql`, `recon`, `geo`) — all exit 2 usage error.
- IPv6 transport: every `socket.socket(...)` call uses a `family` resolved via `socket.getaddrinfo`; no hardcoded `AF_INET` sockets remain (the `AF_INET` hits in `resolve.py`/`dns.py`/`stale.py`/`subtake.py` are `getaddrinfo` name-resolution hints, not sockets).
- `hash --check` with non-hex digest -> `algorithm: null` + "Could not infer algorithm ..." error (correct).
- `mac --target "https://00:1A:2B:3C:4D:5E/"` -> `mac: "00:1a:2b:3c:4d:5e"` (correct).
- `radix --cidrs 192.168.1.0/24,2001:db8::/32` -> exit 2 "Cannot mix IPv4 and IPv6" (correct).
- All documented README console examples covered by `tests/test_readme_examples.py`.

## What remains unresolved
- Nothing functional. Known limitations unchanged (documented, intentional):
  - `ethscan/cli.py:4318` unreachable defensive guard (leave it; do not game coverage or remove validation).
  - `oracle`/`postgresql` empty-target exit-0 in-band contract (intentional, out of scope).
  - PBKDF2+NTLM intentionally unsupported.

## Approaches already failed / why
- None this session. No line of work was started; no gap was reproduced, so no fix was attempted.

## Next task
- None pending. Repository is fully green.
- Next session: run fast gates first (`ruff`, `mypy ethscan/ tests/`, `check_readme.py`); if green run `python -m pytest -q` once; if green, proceed. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work; do not repeat verification-only sessions. If probing turns up nothing, leave the baseline intact and record the findings.

## Environment/notes
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.4 via `python -m coverage`.
- Do not commit manually unless explicitly asked; the workflow controller stages and commits.
