# Next Task
Date: Mon Nov 16 2026

## Status
- Repository green (fuzz audit applied): `python3 -m pytest tests/test_fuzz.py -q` -> **31 passed** (baseline 30). `python3 -m mypy ethscan/fuzz.py tests/test_fuzz.py` -> success. `python3 -m ruff check ethscan/fuzz.py tests/test_fuzz.py` -> all checks passed. `python3 check_readme.py` -> 54 CLI commands, 0 drift.
- Full-suite/whole-repo mypy/ruff not rerun this session (focused change only); prior baseline was 32147 passed, 0 warnings, mypy/ruff clean across `ethscan/ tests/`.

## What changed this session
- Focused functional audit of `ethscan/fuzz.py` finding classification with concrete reproducer (fake `urlopen`/`HTTPError` returning 200/401/403/404/429/500/502 + transport error).
- **Reproduced defect:** every non-404 response with a status (including 5xx server errors and 429 rate limits) was reported as a `finding` / `is_finding=true` in JSON/MD/CSV, inflating results with server-failure/rate-limit artifacts rather than present/protected paths. 401/403 correctly indicate presence/protection and remain findings.
- Fix (small, reversible): `run_fuzz` now classifies a response as a finding only when status is not `None`, not `404`, not `429`, and not `5xx`. `all_results` still records every probe unchanged. CSV `is_finding` and findings section derive from the same `findings` list. Markdown label changed from `Findings (non-404)` to `Findings`.
- `ethscan/fuzz.py`: finding classifier + consistent CSV/MD rendering.
- `tests/test_fuzz.py`: added `test_run_fuzz_classifies_server_errors_and_rate_limits_not_findings` (covers 200/401/403/404/429/500/502/transport-error across JSON/MD/CSV/all_results); updated existing finding-count assertions.
- `README.md`: fuzz feature text documents that 404/5xx/429 are not findings (still listed in all results).

## What remains unresolved
- 18 partial branches remain across `ethscan/`; all statically unreachable per prior handoff evidence (`ftp.py` 46->59/216->220, `netbios.py` 131->144, `ntp.py` 61->74/245->243/393->400, `hash.py` 589->596, `memcached.py` 144->133/151->133, `nmap.py` 315->313, `smtp.py` 61->74/330->318/380->388/384->388/395->398, `snmp.py` 133->146/577->576, `vuln.py` 1036->1029). No known functional defect reproduced.

## Approaches already tried / ruled out
- Treating all non-404 as findings: ruled out (false positives on 5xx/429); replaced with presence/protection-oriented classification.
- Chasing remaining BrParts: unreachable; do not add speculative tests or weaken code.
- Blanket `-W error` suite gate: pre-existing unrelated unraisable-exception warnings elsewhere; standard gate is plain `pytest -q`.

## Next task
- Perform one focused functional audit with a concrete reproducer. Candidate (from prior handoff): `ethscan/web.py` header/status handling (`fetch_headers`/`run_web_checks`, ~`ethscan/web.py:172-188+` / `:323+`). Reproduce with a fake `urlopen`/`HTTPError` exercising non-200/redirect/error cases and inspect how status/headers/errors surface in JSON/MD/CSV (e.g. does `fetch_headers` preserve status context on HTTPError, are 3xx/4xx/5xx distinguished from transport failures). If a defect: smallest fix + regression test + README. Constraints: concrete scenario, no speculation, no weakened safety controls, reversible change.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Caches gitignored; controller stages/commits source/test/handoff files automatically.