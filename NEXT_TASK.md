## Next task

The CWE-1236 (CSV formula injection) end-to-end regression coverage extension is COMPLETE.

Done this session:
- ssh (`format_ssh_report_csv`, ethscan/ssh.py:706): `findings[].algorithm` (col 1) and `findings[].description` (col 3) — committed in HEAD (`dab03bb`).
- memcached (`format_memcached_report_csv`, ethscan/memcached.py:413): `version` (col 4) and joined `findings` (col 13) — test added in this session (`test_format_memcached_report_csv_sanitizes_formula_version_and_findings`).

Coverage now spans 11 module families (ftp, dns, smtp, whois, jwt, ssl, resolve, ntp, redis, cve, ssh, memcached), each locked by a mutation-checked end-to-end test.

Verification (all green):
- 47489 passed, 147 skipped, 0 failed; TOTAL 100% coverage
- mypy clean (271 files); ruff clean; check_readme 54/54, 0 drift
- Mutation check: neutralizing `sanitize_csv_cell` makes the new memcached test fail; restoring passes. `ethscan/fileio.py` byte-identical.

Optional remaining candidate (NOT required): snmp (`format_snmp_report_csv`, ethscan/snmp.py:789) free-text fields.

If no value is found in more CSV tests, probe for a genuine defect first (fresh-install failure, focused failing check, or behavioral evidence vs documented contract) rather than fabricating work — the repo is otherwise fully green.

Out of scope (do not change): `oracle`/`postgresql` empty-target handling; `ethscan/cli.py` unreachable defensive guard (~line 4318); `.github/workflows/**`.

(End of file)
