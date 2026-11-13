# Next Task

## Status
Session 131 (Fri Nov 13 2026) closed a bounded formatter-robustness gap: the protocol-recon
formatters assumed a nested response container was a dict. Baseline was fully green at start:
- `python -m pytest -q` → 6621 passed, 50 skipped, 0 failed
- `python -m mypy ethscan/ tests/` → clean (195 source files)
- `python -m ruff check ethscan/ tests/` → all checks passed
- `python3 check_readme.py` → 54/54, no diffs

After the fix: `pytest -q` → 6838 passed, 146 skipped, 0 failed (+217 new tests); mypy clean
(196 files); ruff clean; readme clean. Valid-input output verified byte-identical (git stash A/B).

## One precise next task
- Close the remaining per-key formatter crash families surfaced by the same hostile fuzzer, one
  module at a time (reproduce first, then apply the `_as_dict` / `_normalize_*` pattern and add
  parametrized hostile-sweep tests):
  - `dnsbrute`: `axfr`, `nameservers`, `resolved`, `all_results`, `recursive_axfr` as
    non-iterable scalars → `TypeError: 'int' object is not iterable` in both Markdown and CSV.
  - `geo`: `geolocation` non-dict → `AttributeError: 'int' object has no attribute 'get'`.
  - `whois`: `raw` non-string → `AttributeError: 'int' object has no attribute 'strip'`.
  - `ldap`: `raw_preview` with non-string elements → `TypeError: sequence item N: expected str`.
  - `smb`: `smb2` non-dict → `AttributeError: 'int' object has no attribute 'get'`.
- Constraints: do not change valid-input output; keep changes minimal and reversible; do not
  commit unless explicitly asked. `oracle`/`postgresql` empty-target handling remains
  intentionally out of scope per their documented contract (exit 0, in-band error).

(End of file - total 24 lines)