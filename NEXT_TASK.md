# Next Task
Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection, or a silent-accept validation gap, then add the smallest permanent guard/test.

## Baseline (verified this session)
- `python3 -m pytest -q --tb=no` → `5893 passed, 50 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`

## This session
- Fixed demonstrated gap: `recon --dns-types` silently accepted unknown DNS record types (proceeded to `run_recon`/network side effects, no CLI rejection). `ethscan/cli.py` now validates `--dns-types` against the same valid set as `dns`/`resolve` (`A`, `AAAA`, `MX`, `NS`, `TXT`, `CNAME`, `SOA`, case-insensitive) and rejects with `click.UsageError` (exit 2) before `run_recon`. Libraries unchanged.
- Added CLI test: `test_recon_unknown_dns_types_rejected` (exit 2, error text, valid types, `run_recon` not called).

## Candidate work (only if demonstrated)
- Find/reproduce a validation or side-effect-before-reject gap in a **materially different** area (CLI edge sweep, `--probes`, `recon --modules`, `recon --dns-types` now fixed). Stop at first reproduced gap; smallest guard/test only.
- Do not duplicate existing sweeps or treat intentional in-output reporting/contracts as gaps.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then full suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
