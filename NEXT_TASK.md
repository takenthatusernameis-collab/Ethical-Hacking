# Next Task

## Status
Session 132 handoff's stated next item (`geo` `geolocation` non-dict crash) was already fixed in
HEAD (f15760b, `_normalize_geo` + hostile-sweep coverage). Baseline at session 133 start: fully
green (`python -m pytest -q` → 6839 passed, 146 skipped; mypy clean 196 files; ruff clean;
`check_readme.py` → 54/54).

Session 133 closed a reproduced `whois` per-key formatter crash:
- Reproduced: `format_whois_report_markdown` crashed on top-level `raw` non-string
  (`123`/`True`/`1.5` etc.) with `AttributeError: 'X' object has no attribute 'strip'`.
- Fixed `ethscan/whois.py` markdown raw rendering to coerce `None`/non-str safely.
- Added hostile-sweep formatter cases in `tests/test_whois_hostile_sweep.py`.
- Verified: focused `pytest tests/test_whois.py tests/test_whois_hostile_sweep.py -q` → 81 passed;
  full suite → 6847 passed, 146 skipped, 0 failed; mypy/ruff clean on touched files;
  `check_readme.py` → 54/54. Valid-input string `raw` behavior preserved.

Session 134 (this session) continued the per-key formatter hostile-sweep campaign:
- Probed `ldap.raw_preview`/`root_dse` and `smb.smb2` per prior notes: no crashes reproduced (formatters already hardened via `_normalize_root_dse`, `_normalize_security_flags`, dict guards).
- Discovered and fixed two new crash families via evidence-first reproduction:
  1. **NetBIOS `names` field**: Both markdown and CSV formatters crashed on non-list/tuple `names` (int, str, dict, list with non-dicts). Fixed via `_normalize_names` helper in `ethscan/netbios.py`.
  2. **DNS `records` field (markdown)**: Markdown formatter crashed on non-iterable `records` dict values. Fixed via inline normalization in `ethscan/dns.py`.
- Added comprehensive parametrized hostile-sweep tests:
  - `tests/test_netbios_formatter_hostile_sweep.py` (16 tests)
  - `tests/test_dns_formatter_hostile_sweep.py` (19 tests)
- Fixed pre-existing `tests/test_smb_hostile_sweep.py` missing `import pytest`.
- Verified: full suite 6915 passed, 146 skipped, 0 failed; mypy/ruff clean; `check_readme.py` 54/54.

## One precise next task
- Continue the per-key formatter hostile-sweep campaign with evidence-first reproduction:
  probe remaining modules for unguarded `.get`/iteration/string ops on untrusted keys in formatters.
  Prior candidates from earlier fuzzer notes: `ftp`, `snmp`, `smtp`, `ldap` (other fields), `smb` (other fields),
  `redis`, `memcached`, `mongodb`, `mssql`, `mysql`, `postgresql`, `oracle`, `ntp`, `ssh`, `cert`, `geo`,
  `mac`, `cve`, `vuln`, `scan`, `web`, `headers`, `fuzz`, `subdomains`, `dnsbrute`, `whois`, `ssl`, `tls`,
  `brute`, `service`, `osdetect`, `ping`, `cidr`, `radix`, `stale`, `urlcheck`, `subtake`, `s3`, `recon`,
  `nmap`, `resolve`, `validate`, `jwt`, `wifi`, `hash`, `passwords`, `report`, `config`.
  Pick one module, probe its formatter with hostile shapes (non-dict containers, non-iterable list fields,
  non-string elements), and if a crash reproduces, apply the minimal `_normalize_*`/coercion pattern, add
  parametrized hostile-sweep tests, and verify.
- Constraints: do not change valid-input output; keep changes minimal and reversible; do not commit unless
  explicitly asked. `oracle`/`postgresql` empty-target contract remains out of scope.