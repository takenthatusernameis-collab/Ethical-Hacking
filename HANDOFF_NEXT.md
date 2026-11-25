# Handoff

## Status
Repository is fully green, installs cleanly, and matches its documented contract. No
source/test change was needed this session. The only edits made are these two handoff
files (NEXT_TASK.md, HANDOFF_NEXT.md); no source or test code was touched.

Note: the previous handoff said the memcached CSV test was "uncommitted"; it is in fact
committed in HEAD (`fa498b4`), so that note was stale.

## What was actually verified (this session)
- `python -m coverage run --branch --source=ethscan -m pytest -q`
  -> 47489 passed, 147 skipped, 0 failed (114.82s), EXIT 0.
- `python -m coverage report` -> TOTAL 100% (16250 stmts, 6140 branches, 0 missing).
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 271 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 CLI commands; 0 drift both directions; exit 0.
- Fresh install: `python -m venv venv_fresh && pip install <repo>` -> exit 0. The
  installed `ethscan` console script, `version`, and offline `cidr` all work from
  site-packages (verified `ethscan.__file__` resolves under site-packages, not the tree).
- README behavioral contracts exercised live, all matched EXACTLY (exit codes + text):
  - `scan --target 127.0.0.1 --ports abc` -> exit 2, "Invalid port number 'abc'".
  - `cidr --cidr bogus` -> exit 2, "'bogus/128' does not appear to be an IPv4 or IPv6 network".
  - `radix --cidrs 192.168.1.0/24,2001:db8::/32` -> exit 2, "Cannot mix IPv4 and IPv6 ...".
  - `redis|trace|s3 --target ""` -> exit 2, "Could not parse host from target ''".
  - `web --target host:notaport` -> exit 2, "Port could not be cast to integer ...".
  - `web --target "host name"` -> exit 2, "Target host contains a space or control character".
  - `web --target "https://example.com/a b"` -> exit 2, "Target path contains a space ...".
  - `redis --target example.com:99999` -> exit 2, "Port out of range 0-65535".
  - `s3 --target "[::1]:443"` -> exit 0, documented 77-candidate JSON (same error text).
  - `audit --file <non-utf8>` -> exit 2, "the file is not valid UTF-8".
- Cache robustness (geo) end-to-end: seeded `~/.cache/ethscan/geo_cache.json` with
  (a) invalid JSON, (b) non-object, (c) non-mapping entry, (d) non-finite timestamp,
  (e) stale entry -> every case exit 0; malformed -> empty cache -> live refetch; stale
  -> refetch. Top-level `offline_fallback` only echoes the option, not usage.

## Genuine-defect probe (result: none found)
- Import + CLI smoke: `import ethscan` ok; `--help`/`version` ok (source and installed).
- MD4/NTLM: verified CORRECT via clean-room RFC 1320 implementation (see below).
- Cache leniency + non-finite guard (geo/cert/mac/cve): matches README.
- `fileio.load_json` depth guard (string-aware) + `sanitize_csv_cell`/`csv_writer`
  (prefix `= + - @ TAB CR`, numeric exempt): unchanged, sound.

## False alarm (do not chase)
- MD4("password") = `8a9d093f14f8701df17732b2bb182c74` is CORRECT (clean-room MD4,
  validated vs canonical vectors; NTLM("password")=8846f7eaee8fb117ad06bdd830b7586c
  confirms the MD4 core). The `8a9d...95c9` value sometimes cited from memory is WRONG.

## Approaches already tried / ruled out (do not repeat)
- CSV formula-injection sweep: DONE (all 54 modules route through `csv_writer`; 11
  end-to-end mutation-checked tests). snmp is the only optional remaining candidate.
- Leading-whitespace formula cells, purely numeric cells: NOT gaps (documented).
- Parser/adversarial STRING fuzz, formatter/assessor hostile contracts, CLI
  target/option hostile sweeps, nested-field & per-key hostile sweeps: clean prior sessions.
- Fresh install, cache contract, MD4 vector: all verified this session (no defect).

## Out of scope (per documented contract, do not change)
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error).
- `ethscan/cli.py` unreachable defensive guard (documented known limitation, ~line 4318).
- `.github/workflows/**` (reverted by the controller).

## Next task
- No code change required. Re-run the gate above to confirm the baseline, then probe for a
  GENUINE defect (focused failing check or behavioral evidence vs the documented contract).
  Do not fabricate work.
- If a bounded task is wanted: the CSV formula-injection coverage is complete except the
  OPTIONAL snmp candidate (`format_snmp_report_csv`, ethscan/snmp.py:789) — only pursue it
  if you first find a genuinely attacker-controlled free-text CSV field with evidence of
  risk; otherwise leave it.

(End of file)