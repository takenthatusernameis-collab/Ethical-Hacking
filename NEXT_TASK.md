# Next Task

## Status: CLOSED (Sun Nov 08 2026)
The handoff task (investigate order-dependent CLI file-error test failures under full-suite ordering) is closed:
- `ethscan/cli.py` already uses stable module-attribute lookups (`ethscan.fileio.read_lines`, `ethscan.stale.load_domains_from_file`) matching the tests' patch targets.
- The environment gap is resolved: `dnspython` 2.9.2 is installed (`import dns` works).
- Full suite passes twice with dnspython: 5932 passed, 50 skipped, 0 failed; twice without: 5929 passed, 53 skipped, 0 failed. `ruff check .` clean; `mypy ethscan/` clean.
- Flakiness does not reproduce in either environment.

## Candidate
None pending. Baseline is green.

## Constraints
- Do not re-audit `--out`/`--init` routing (already covered).
- Do not weaken safety controls or turn this into an infrastructure project.
- Do not make speculative changes without a reproducible failure.
- If flakiness reappears: reproduce here (dnspython installed) and find the earlier test that rebinds `ethscan.fileio`/`ethscan.stale` or reloads modules so a `patch.object` target stops being the object `cli.py` reads at call time.

(End of file - total 22 lines)
