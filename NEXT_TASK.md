## Next task

No code change was required this session. The repository is fully green, installs
cleanly, and matches its documented contract; a genuine-defect probe found nothing to
fix. Do NOT fabricate work — evidence below.

### Verification performed this session (all green)
- Full gate: `python -m pytest -q` -> 47489 passed, 147 skipped, 0 failed (~124s).
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> TOTAL 100%
  (16250 stmts, 6140 branches, 0 missing).
- `python -m mypy ethscan/ tests/` -> Success: no issues in 271 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 CLI commands, 0 drift; exit 0.
- Fresh install (network available): `python -m venv` + `pip install <repo>` -> exit 0;
  installed `ethscan` entry point, `version`, and offline `cidr` all work from
  site-packages (outside the source tree). (Offline install only fails because PEP 517
  build isolation cannot fetch setuptools>=61 — environment, not a project defect.)

### Genuine-defect probe (result: none found)
- `sanitize_csv_cell`/`csv_writer` complete (every cell sanitized, `= + - @ TAB CR`
  prefixes, numerics exempt, no bypass path). `report.py` hostile nested fields: 0 crashes.
- `audit --file` hostile content: exit 0 safe. IPv6 TCP scan: exit 0, correct output.
- MD4/NTLM correct via clean-room RFC 1320 implementation.

### Remaining / next
- Nothing blocking. Before any work, re-run the gate to confirm the baseline, then probe
  for a GENUINE defect (focused failing check or behavioral evidence vs the documented
  contract). Do not fabricate work.
- Out of scope (do not change): oracle/postgresql empty-target handling;
  ethscan/cli.py unreachable defensive guard (~line 4318); .github/workflows/**.
