## Next task

No code change was required this session. The repository is fully green, installs
cleanly, and matches its documented contract; a genuine-defect probe found nothing to
fix. Do NOT fabricate work — evidence below.

### Verification performed this session (all green)
- Full gate: `python -m coverage run --branch --source=ethscan -m pytest -q`
  -> 47489 passed, 147 skipped, 0 failed (~115s).
- `python -m coverage report` -> TOTAL 100% (16250 stmts, 6140 branches, 0 missing).
- `python -m mypy ethscan/ tests/` -> Success: no issues in 271 files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 CLI commands, 0 drift; exit 0.
- Fresh install (network available): `python -m venv` + `pip install <repo>` -> exit 0;
  installed `ethscan` entry point, `version`, and offline `cidr` all work from
  site-packages (outside the source tree). (Offline install only fails because PEP 517
  build isolation cannot fetch setuptools>=61 — environment, not a project defect.)
- README behavioral contracts exercised LIVE, matched EXACTLY (exit codes + text):
  usage errors (scan --ports abc; cidr bogus; radix mixed families; redis/trace/s3
  empty target; web host:notaport / "host name" / path-with-space; redis port 99999)
  all exit 2 with documented messages; `s3 --target [::1]:443` emits the documented
  77-candidate JSON; `audit --file <non-utf8>` exits 2 "the file is not valid UTF-8".
- Cache robustness (geo) end-to-end: seeded `~/.cache/ethscan/geo_cache.json` with
  invalid JSON / non-object / non-mapping entry / non-finite timestamp / stale entry —
  every case exits 0 (never an error), malformed -> empty cache -> live refetch, stale
  -> refetch (offline_fallback only echoes the option).

### False alarm resolved (do not chase)
- `ethscan hash --algorithm md4 --password password` = `8a9d093f14f8701df17732b2bb182c74`
  is CORRECT. A clean-room RFC 1320 MD4 (validated vs MD4("")=31d6cfe0...,
  MD4("abc")=a448017a...) reproduces it; NTLM("password")=8846f7eaee8fb117ad06bdd830b7586c
  (well-known) depends on the same MD4 core. The `8a9d...95c9` value from memory is WRONG.

### Remaining / next
- Nothing blocking. Before any work, re-run the gate to confirm the baseline, then probe
  for a GENUINE defect (focused failing check or behavioral evidence vs the documented
  contract). CSV formula-injection coverage remains COMPLETE (11 families, mutation-checked).
- Out of scope (do not change): oracle/postgresql empty-target handling;
  ethscan/cli.py unreachable defensive guard (~line 4318); .github/workflows/**.