# Next Task
Date: Mon Nov 16 2026

## Status
- Repository green for `ethscan/web.py` audit: `tests/test_web.py` -> **100 passed**; `mypy ethscan/web.py tests/test_web.py` -> success; `ruff check ethscan/web.py tests/test_web.py` -> all checks passed; `check_readme.py` -> 54 CLI commands, 0 drift.
- Full suite `pytest -q` -> 32149 passed, 146 skipped, **10 failed**, all verified pre-existing on the clean tree (`git stash`), none caused by this change:
  - `tests/test_cli.py::test_fuzz_output_format_markdown`
  - 7x `tests/test_fuzz_hostile_sweep.py::test_markdown_non_list_findings_never_raises[...]`
  - `tests/test_fuzz_formatter_hostile_sweep.py::test_fuzz_formatters_tolerate_hostile_nested_shapes[data15-format_fuzz_report_csv]`
  - `tests/test_target.py::test_fetch_headers_drops_the_userinfo_of_the_target`

## What changed this session
- Focused functional audit of `ethscan/web.py` header/status handling (per prior handoff).
- **Reproduced defect:** `fetch_headers` returned `HTTPError` headers with `error=None` and discarded `exc.code`, so 4xx/5xx responses were indistinguishable from successes and transport failures in JSON/Markdown/CSV.
- Fix: `FetchedHeaders` gains a `status` attribute; `fetch_headers` records `response.status`/`exc.code`; `run_web_checks` surfaces `results["status"]`; Markdown/CSV render status; JSON includes it automatically. Follows the `fuzz_path` precedent (`ethscan/fuzz.py:96-97`).
- +13 regression tests in `tests/test_web.py`; README `web` feature bullet documents status reporting.

## What remains unresolved
- 10 pre-existing test failures listed above (fuzz `Findings (non-404)` label gone stale, hostile-sweep TypeError, test_target userinfo assertion). Unrelated to `web.py`; reproduce-verified on clean tree.
- 18 statically unreachable partial branches across `ethscan/` (prior handoff); no known functional defect.
- `ethscan/headers.py` could also surface `fetched.status`; left unchanged (bounded scope).

## Approaches already tried / ruled out
- Making HTTPError a transport error: ruled out; `error=None` + recorded `status` matches `fuzz_path` precedent and preserves headers.
- Chasing BrParts / blanket `-W error`: ruled out (prior handoff).

## Next task
- Reconcile the 10 pre-existing test failures: update stale `**Findings (non-404):**` label assertions to `**Findings:**` in `tests/test_cli.py` and `tests/test_fuzz_hostile_sweep.py`; inspect the TypeError in `tests/test_fuzz_formatter_hostile_sweep.py` data15 CSV case and the `{'server': 'test'}` vs `{}` assertion in `tests/test_target.py::test_fetch_headers_drops_the_userinfo_of_the_target`. Smallest change; tests must match current intended behavior. Verify with `pytest tests/test_cli.py tests/test_fuzz*.py tests/test_target.py -q` and `python3 check_readme.py`. Do not modify `ethscan/` source unless a functional defect is reproduced.

## Environment/notes
- Dev deps: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Caches gitignored; controller stages/commits source/test/handoff files automatically.
