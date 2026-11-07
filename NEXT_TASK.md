# Next Task
Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection, or a silent-accept validation gap, then add the smallest permanent guard/test.

## Baseline (verified)
- Full suite: `5903 passed, 50 skipped` (Python 3.14/OpenSSL 3.5.5).
- `python3 -m ruff check .` → all checks passed. `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## This session (fixed, verified)
- Prevented wordlist file I/O before target validation in `subdomains`, `subtake`, `dnsbrute`, `s3`, `recon` (`--subdomains-wordlist`). Added CLI `_validate_enum_target()` (via `parse_url`) called before `load_subdomain_wordlist`; invalid/malformed targets now rejected as usage errors before file reads. Targeted enum/CLI tests all passed (`1344 passed`). Normal flows unchanged.

## Candidate work (only if demonstrated)
- Find/reproduce another case where option validation/File I/O/network setup happens before rejecting unusable option values. Stop at first reproduced gap; smallest guard/test only. Do not treat intentional contracts as gaps.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then relevant broader suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
