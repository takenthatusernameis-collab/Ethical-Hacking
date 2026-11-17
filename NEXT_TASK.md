# Next Task
Date: Tue Nov 17 2026

## Status
- Repository fully green; no pending task. This session independently re-verified the baseline and investigated for a reproducible gap before selecting work; none was found, each ruled out with evidence.

## Baseline (independently re-verified this session)
- `python -m pytest -q` -> 32217 passed, 146 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` -> Success, no issues in 259 source files.
- `python -m ruff check ethscan/ tests/` -> All checks passed.
- `python check_readme.py` -> 54/54, 0 drift.
- Working tree clean at commit `6c5f342`; nothing committed.

## Investigated and ruled out this session (evidence recorded)
- Formatter hostile gaps: all 157 single-arg `format_*_report_*` callables probed with a full hostile matrix + all-fields-hostile dict -> 0 crashes. Covered by `tests/test_all_formatters_hostile_contract.py`; the 3 non-standard `ethscan.passwords.format_audit_report_*` formatters are hostile-tested in `tests/test_passwords_hostile_sweep.py`.
- Empty-target consistency: all 43 `--target` commands run with `--target ""` exit 2 (usage error), matching the README; only `oracle`/`postgresql` exit 0 with an in-band error (documented, intentionally out of scope).
- Coverage: 100% statement/branch of `ethscan/` (unchanged, no code modified).
- No `FIXME`/`TODO`/`XXX`/`HACK` markers in `ethscan/` or `tests/`.

## Next task
- None pending. Repository is fully green. If future work is needed, pick a single bounded, high-value, verifiable improvement and reproduce the gap first — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

## Constraints / notes
- Keep the existing architecture stable; prefer the smallest reversible change. Do not commit unless explicitly asked.
- Dev deps installed: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, Python 3.14.4. No pytest-cov plugin — use `python -m coverage run --branch --source=ethscan -m pytest` for coverage.
