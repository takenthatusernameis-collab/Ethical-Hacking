# Next Task

## Status: INVESTIGATED (Sun Nov 08 2026, dnspython installed)
- `dnspython` IS installed here (2.9.2), unlike the prior environment.
- Full suite run #1: 5932 passed, 50 skipped, 0 failed (85.85s).
- Full suite run #2: 5932 passed, 50 skipped, 0 failed (85.34s).
- Reverse order run: 5932 passed, 50 skipped, 0 failed.
- Targeted DNS/reload + radix/stale: 572 passed.
- `ethscan/cli.py:3611` uses `ethscan.fileio.read_lines` and `cli.py:4631` uses `ethscan.stale.load_domains_from_file` via module-attribute lookup at call time — patch targets stable.
- No reload of `ethscan.fileio`/`ethscan.stale` in tests; reloads are limited to `ethscan.brute`/`ethscan.ssh` (paramiko-gated) and `ethscan.subtake`.
- Flakiness still does not reproduce; no reproducible defect. No product change made.

## Candidate
None pending. No speculative changes (per policy).

## Constraints
- Do not re-audit `--out`/`--init` routing.
- Do not weaken safety controls or turn this into an infrastructure project.
- Do not make speculative changes without a reproducible failure.
" filePath="/home/runner/work/Ethical-Hacking/Ethical-Hacking/NEXT_TASK.md