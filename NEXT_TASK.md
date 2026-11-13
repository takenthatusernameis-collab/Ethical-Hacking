# Next Task

## Status
Session 132 handoff's stated next item (`geo` `geolocation` non-dict crash) was already fixed in
HEAD (f15760b, `_normalize_geo` + hostile-sweep coverage). Baseline at session 133 start: fully
green (`python -m pytest -q` → 6839 passed, 146 skipped; mypy clean 196 files; ruff clean;
`check_readme.py` → 54/54).

Session 133 (this session) closed a reproduced `whois` per-key formatter crash:
- Reproduced: `format_whois_report_markdown` crashed on top-level `raw` non-string
  (`123`/`True`/`1.5` etc.) with `AttributeError: 'X' object has no attribute 'strip'`.
- Fixed `ethscan/whois.py` markdown raw rendering to coerce `None`/non-str safely.
- Added hostile-sweep formatter cases in `tests/test_whois_hostile_sweep.py`.
- Verified: focused `pytest tests/test_whois.py tests/test_whois_hostile_sweep.py -q` → 81 passed;
  full suite → 6847 passed, 146 skipped, 0 failed; mypy/ruff clean on touched files;
  `check_readme.py` → 54/54. Valid-input string `raw` behavior preserved.
- Changes uncommitted (whois fix/tests + handoff docs). No commit requested.

## One precise next task
- Continue the per-key formatter hostile-sweep campaign with evidence-first reproduction:
  probe `ldap` and `smb` formatter paths called out in prior notes (`ldap.raw_preview` elements
  / unexpected container shapes, `smb.smb2` nested shapes) and other modules for unguarded
  `.get`/iteration/string ops on untrusted keys. If a crash reproduces, fix that single bounded
  family with the minimal `_as_dict`/`_normalize_*`/coercion pattern, add parametrized
  hostile-sweep tests, and verify. If probes show no crash, record the exact probed shapes as
  evidence and select the next module with a demonstrated formatter crash.
- Constraints: do not change valid-input output; keep changes minimal and reversible; do not
  commit unless explicitly asked. `oracle`/`postgresql` empty-target contract remains out of scope.

(End of file)
