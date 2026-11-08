# Next Task

## Status: INVESTIGATED (Sun Nov 08 2026)
The handoff task was to investigate why two CLI file-error tests fail only under full-suite ordering (`patch.object` target stability). Investigation found no reproducible defect in this checkout:
- `ethscan/cli.py` already uses stable module-attribute lookups (`ethscan.fileio.read_lines`, `ethscan.stale.load_domains_from_file`) matching the tests' patch targets.
- Full suite passes twice: 5929 passed, 53 skipped, 0 failed. `ruff check .` clean.
- Flakiness does not reproduce here; this environment lacks `dnspython`, which may be a factor.

## Candidate
None pending. If flakiness reappears, see HANDOFF_NEXT.md for the reproduction plan (dnspython-installed environment).

## Constraints
- Do not re-audit `--out`/`--init` routing (already covered).
- Do not weaken safety controls or turn this into an infrastructure project.
- Do not make speculative changes without a reproducible failure.
