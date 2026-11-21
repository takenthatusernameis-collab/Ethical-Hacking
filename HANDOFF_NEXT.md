# Handoff
Date: Sat Nov 21 2026 (verification-only session; fresh full-suite evidence captured this session)

## State
- HEAD: `b856e7f` (main). Working tree clean (no uncommitted changes).
- No prior agent assignment produced a functional task. This session was verification-only.
- Last substantive project change: `f9487f9` added the scanner **service-detection** feature (`scanner.grab_banner`, `scanner.scan_ports_with_service`, the CLI `--service-detect` path, and the markdown/CSV formatter `service_detect` branches) but shipped it with **no tests**; that gap was closed in a prior session and coverage is now 100%.

## What changed this session
- None — verification-only session. No source, test, or docs changes made. Working tree clean.

## What was verified this session (fresh evidence)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python check_readme.py` -> 54 commands; 0 drift both directions
- `python -m mypy ethscan/ tests/` -> Success: no issues in 268 source files
- `python -m pytest -q --no-header -p no:cacheprovider` -> **46758 passed, 146 skipped, 0 failed** (baseline unchanged)
- `python -m coverage report --fail-under=100` -> exit 0 (gate passes; coverage.json already at 100%)

## Test-pollution trap discovered and worked around (important for future tests)
- `tests/test_main.py` runs `sys.modules.pop("ethscan.cli", None)` + `runpy.run_module("ethscan.cli", run_name="__main__")` and does **not** restore the module. Any test file that (a) does `from ethscan.cli import cli` at module import time and (b) later runs after `test_main.py` (alphabetical order: `test_scanner_*` > `test_main`) will patch a **different** module object than the one its `cli` group uses if it uses a **string** monkeypatch target (e.g. `monkeypatch.setattr("ethscan.cli.scan_ports_with_service", ...)`). The string target re-imports `ethscan.cli`, patches the fresh copy, and the captured `cli` keeps calling the real function -> real network call.
- Fix used in `tests/test_scanner_service_detect.py`: `import ethscan.cli as cli_module` and patch the **object** (`monkeypatch.setattr(cli_module, "scan_ports_with_service", ...)`). Verified with an ordering repro (polluted then patched object -> mock hit, no network). `ethscan.scanner` is never popped, so string patches there are safe.
- Repro that first exposed this: running the new tests under the full suite made a **live** call to example.com (got a real banner in the markdown test). Fixed; suite is now hermetic.

## Known-intentional behavior (do NOT "fix" blindly)
- `hash --check` with a 32-char digest and no `--algorithm` prefers md5; ntlm/md4 32-char digests report `match:false` unless `--algorithm` is given. DOCUMENTED + TESTED design, not a bug.
- `oracle` / `postgresql` empty/unusable-target in-band "probe failed" (exit 0) per documented contract.
- `ethscan/cli.py` completion non-install path: unreachable `effective_shell is None` guard (`# pragma: no cover`). Leave unless a task explicitly asks to refactor.
- `ethscan/hash.py` `_normalize_passwords` strips whitespace and drops empty passwords (documented).

## What remains unresolved
- Nothing functional. Repo is independently verified green with fresh full-suite + 100% coverage evidence.

## Approaches that already failed / why
- Trusting the committed `coverage.json` as ground truth -> it was stale (initial import). Always regenerate with a fresh `coverage run` before trusting the number.
- String-form monkeypatch of `ethscan.cli` in a test file ordered after `test_main.py` -> patches the wrong module; real network call. Use object-form patch (`cli_module.attr`).

## Next task
- No genuine pending functional task remains; repo is independently verified green at the service-detection level with FRESH full-suite + 100% coverage evidence.
- If the orchestration invokes another session here: run the fast gates first (`ruff`, `mypy`, `check_readme.py`); only run the full `pytest` + `coverage` once if those pass. Do not re-run the whole suite repeatedly as the primary activity.
- Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work; do not count handoff-doc-only commits as progress.
- Candidate next investigations (only if reproduced): (a) the `ethscan/cli.py` completion `effective_shell is None` unreachable guard could be made reachable/removed if a task asks; (b) audit whether other test files ordered after `test_main.py` use string-form monkeypatch of `ethscan.cli` (they may be silently exercising real paths). These are optional, evidence-gated.

## Environment/notes
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage via `python -m coverage`.
- Do not commit manually unless explicitly asked; the workflow controller stages and commits.
- Do not introduce unrelated modifications; handoff docs are the designated communication channel.

(End of file)