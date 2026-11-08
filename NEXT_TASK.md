# Next Task

## Status: CLOSED (this session)
Baseline is GREEN: `pytest -q` → 5936 passed, 50 skipped, 0 failed.

## Completed (Sun Nov 08 2026, session 7)
- Fixed 6 mypy errors in `tests/test_netbios.py`:
  - 2 × `var-annotated`: annotated `captured: dict[str, object] = {}` in `test_send_recv_connector_receives_arguments` and `test_run_netbios_url_target`.
  - 4 × `operator`: added `assert err is not None` after `assert data is None` in the four transport-failure tests, narrowing `str | None` to `str` before the `in` check.
- No behavior change; `ethscan/` source untouched.
- Verified: mypy clean, ruff clean, 84 netbios tests pass, full suite unchanged.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.

## Suggested next task
- Continue typing hygiene in remaining test files with mypy errors. Reproduce with `python -m mypy tests/<file>` first, then fix the smallest set of errors per file. Files with the most remaining errors: `test_radix.py` (110), `test_cidr.py` (106), `test_recon.py` (74), `test_resolve.py` (52), `test_ping.py` (49).