# Next Task

## Status
Sun Nov 15 2026: Prior handoff said "no task remains". Re-verified baseline and found a real gap: **branch coverage is 99% (91 partial branches), not 100%** (statement coverage is 100%). Closed all 8 partial branches in `ethscan/dnssec.py` this session. Repository green.

## Baseline / verification this session (re-verified from scratch)
- `python -m pytest -q` → 32040 passed, 146 skipped, 0 failed (1 preexisting warning).
- `python -m mypy ethscan/ tests/` → Success: no issues found in 237 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.
- `python -m pytest --cov=ethscan.dnssec --cov-branch --cov-report=term-missing -q` → `dnssec.py` 482 stmts, 0 miss, 214 branch, 0 BrPart, **100%**.
- Full branch sweep: partial branches **91 → 83**; statement miss still 0.

## What changed
- Added `tests/test_dnssec_branch_gaps.py` (8 tests). No source changes. Only file changed in the tree.

## Key pitfall (read before adding tests near `test_dnssec.py`)
`tests/test_dnssec.py::test_dnssec_import_error` pops `ethscan.dnssec` from `sys.modules`
without re-import, and several tests there use `importlib.reload`/`sys.modules`. This leaves
a stale duplicate module. Tests that run after it must bind the module object once
(`import ethscan.dnssec as dnssec_mod`) and patch/call through that object, never by string
(`monkeypatch.setattr("ethscan.dnssec.X", ...)`), or they silently patch a different object.

## Blockers
- None.

## Approaches already tried / ruled out
- Statement coverage: 100%, nothing to add.
- Formatter hostile-shape sweep, empty-target normalization, README/CLI sync, CLI wiring,
  formatter hardening, service.py branch gaps (prior commit): complete. Do not re-speculate.
- Do not add speculative runtime guards or untested code to manufacture progress.

## Next task
- Close the **7 partial branches in `ethscan/smtp.py`** (98%, branches
  `61->74, 63->74, 68->74, 330->318, 380->388, 384->388, 395->398`).
  - Create `tests/test_smtp_branch_gaps.py` with focused tests:
    - host:port / bracketed-host parsing edge cases (lines 61-74) via the public target
      parsing path (mirror existing `test_smtp.py` helpers).
    - EHLO capability loop continue branch (`330->318`).
    - relay-check exception branches (`380->388`, `384->388`, `395->398`) using injected
      fake sockets/queries.
  - Bind to the module object consistently (`import ethscan.smtp as smtp_mod`). Note:
    `tests/test_smtp.py` does not use reload/sys.modules, so the dnssec pitfall does not
    apply here, but keep the object-binding pattern.
  - Verify: `python -m pytest tests/test_smtp.py tests/test_smtp_branch_gaps.py -q`, then
    `python -m pytest --cov=ethscan.smtp --cov-branch --cov-report=term-missing -q` shows
    `smtp.py ... 0 BrPart 100%`, then re-run the four gates (pytest/mypy/ruff/check_readme).
- If smtp is completed, continue one module per session (next: smb or ntp). Do not attempt
  all 83 at once; one module is the bounded unit.

(End of file - total 46 lines)