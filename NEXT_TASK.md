# Next Task

## Status
Previous handoff task completed: added permanent formatter hostile-sweep tests for
`cert`, `cve`, and `mac` (`tests/test_cert_formatter_hostile_sweep.py`,
`tests/test_cve_formatter_hostile_sweep.py`,
`tests/test_mac_formatter_hostile_sweep.py`, +285 tests). Pre-probe found 0
crashes; coverage-only. Repo green: `pytest -q` -> 8023 passed, 149 skipped, 0
failed; `mypy ethscan/ tests/` clean (211 source files); `ruff check ethscan/ tests/`
clean; `python3 check_readme.py` 54/54.

## One precise next task
Add permanent formatter hostile-sweep tests for `geo` and `web`
(modules with `format_*_report_*` lacking dedicated `*_formatter_hostile_sweep.py`).

- Evidence: scan of `ethscan/*.py` modules defining `format_*_report_*` vs existing
  formatter hostile-sweep tests shows `geo` and `web` still missing formatter
  sweep coverage (many others also missing; there is no `ethscan/audit.py`).
- Reproduce first (do not assume a bug): for each, call `format_*_{json,markdown,csv}`
  with hostile shapes: non-dict top-level (None/int/str/list/bool/float) and key
  payload fields set to scalars, non-dict list elements, and hostile nested dicts
  (inspect `ethscan/geo.py` and `ethscan/web.py` for actual fields). Record any
  `TypeError`/`AttributeError`.
- If a crash reproduces, fix minimally in the formatter and add regression tests
  pinning the exact crash payloads; if none, deliver coverage-only tests.
- Create `tests/test_geo_formatter_hostile_sweep.py` and
  `tests/test_web_formatter_hostile_sweep.py` (follow
  `tests/test_cert_formatter_hostile_sweep.py` / `tests/test_ssh_formatter_hostile_sweep.py`):
  parametrize over formatters, assert `isinstance(output, str)` for every hostile
  shape, assert JSON returns `"{}"` for non-mapping top-level, plus a well-formed
  regression.
- Verify: `python -m pytest tests/test_geo_formatter_hostile_sweep.py tests/test_web_formatter_hostile_sweep.py -q`,
  then full `python -m pytest -q`, `python -m mypy ethscan/ tests/`,
  `python -m ruff check ethscan/ tests/`, `python3 check_readme.py`. Update
  `HANDOFF_NEXT.md` and `NEXT_TASK.md` with evidence.

## Approaches already tried / ruled out
- `cert`/`cve`/`mac` formatter hostile probes: 0 crashes on plausible shapes;
  regression coverage added this session (285 tests). Do not rework.
- Session-137 batch and `redis` formatter sweeps: already complete/guarded.
