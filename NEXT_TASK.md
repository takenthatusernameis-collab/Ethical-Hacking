# Next Task

## Status
The incoming handoff was stale: its task (`tests/test_redis_formatter_hostile_sweep.py`)
was already committed in `ae117d9` and is green (80 tests). This session instead
fixed a real crash in the SSH Markdown formatter and added its permanent
formatter hostile-sweep test (317 tests). Repo is fully green: `pytest -q` ->
7738 passed, 149 skipped, 0 failed; mypy/ruff clean; README 54/54.

## One precise next task
Add permanent formatter hostile-sweep tests for the three modules that still
have NO formatter-input coverage: `cert`, `cve`, `mac`.
- Their `tests/test_<mod>_hostile_sweep.py` only exercises `run_*` (the network
  entry point), never `format_*`; none has `tests/test_<mod>_formatter_hostile_sweep.py`.
- Reproduce first (do not assume a bug): call each `format_*_{json,markdown,csv}`
  with hostile shapes:
  - non-dict top-level (None, int, str, list, bool, float)
  - `subdomains`/`notes`/`cert_data`/`cert_data.entries`/`mac_data`/
    `vulnerabilities`/`cve_data` set to scalars, lists with non-dict elements,
    and dicts with hostile nested values
- A hostile-shape probe run this session on these three modules produced 0
  crashes, so the expectation is that the formatters are already guarded and the
  deliverable is regression coverage, not a fix. If a crash does reproduce, fix
  it minimally (see the ssh precedent: `_normalize_algo_list` in `ethscan/ssh.py`).
- Create `tests/test_cert_formatter_hostile_sweep.py` first (then cve, then mac),
  following `tests/test_ssh_formatter_hostile_sweep.py`: parametrized over all
  formatters, assert `isinstance(output, str)` for every hostile shape, plus a
  well-formed regression.
- Verify: `pytest tests/test_cert_formatter_hostile_sweep.py -q`, then full
  `pytest -q`, `mypy ethscan/ tests/`, `ruff check ethscan/ tests/`.

## Approaches already tried / ruled out
- `redis` formatter hostile-sweep: already complete (commit `ae117d9`); no work needed.
- Session-137 batch (hash/urlcheck/osdetect/subtake/subdomains/dnssec/ping/cidr/
  s3/tls/ssl/dnsbrute/resolve/trace): probed, already guarded; do not add guards.
- `cert`/`cve`/`mac` formatter hostile probe (plausible shapes): 0 crashes.