# Handoff
Date: Fri Nov 06 2026

## What changed
- `ethscan/cli.py` (`recon`): validate `--modules` against allowed modules (`subdomains`, `dns`, `whois`, `geo`, `trace`). Unknown names now raise `click.UsageError` (exit 2) with `Unknown modules: ... Valid modules: ...` before any recon work runs. Whitespace-only/empty items after split remain ignored (existing behavior); no library changes.
- `tests/test_cli.py`: added `test_recon_modules_unknown_rejected` and `test_recon_modules_mixed_unknown_rejected` asserting exit 2, error text, and `run_recon` not invoked.

## Demonstrated gap (reproduced, now fixed)
- Before: `python3 -m ethscan recon --target example.com --modules bogus` → exit 0, `modules_run=[]`. `--modules dns,bogus,whois` → exit 0, `modules_run=["dns","whois"]` and DNS executed (unknown silently ignored). Contrast: `dns --types BOGUS` rejects at CLI (exit 2).

## Verified (evidence)
- `python3 -m pytest tests/test_recon.py tests/test_recon_hostile_sweep.py -q --tb=no` → `38 passed`.
- `python3 -m pytest tests/test_cli.py -q -k recon --tb=no` → `23 passed, 1002 deselected`.
- `python3 -m pytest -q --tb=no` → `5880 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Unresolved
- None demonstrated by this change.

## Approaches already tried / not to repeat blindly
- Broad CLI edge-case sweeps (ports/timeout/workers/iterations/CIDR/target/host/offline/file/JSON/XML/`--out`/`--config`, intentional `--contains`/`hash --check`/`validate` reporting) — exhausted across sessions; do not repeat unchanged.
- Treating intentional in-output reporting / documented contracts as usage-error gaps — not actionable without a demonstrated mismatch.

## Next task
- Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection or a silent-accept validation gap in an area **different** from the exhausted CLI edge sweep and fixed `recon --modules`. Materially different scan surface only; stop at first reproduced gap; add smallest permanent guard/test. Keep baseline green; do not commit unless asked.
