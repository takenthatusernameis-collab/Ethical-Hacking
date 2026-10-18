# Task State

## Current state
- Working tree: clean. HEAD: aa2f1cb (plus uncommitted UP006/UP035 fixes below until committed).
- Tests: 3900 passed, 1 skipped (green baseline).
- Code compiles cleanly; ethscan imports successfully.
- Packaging: ethscan/py.typed present with package-data configured (PEP 561).

## Completed (this session)
- Fixed UP006 (non-pep585-annotation) + UP035 (deprecated-import) across tests/test_dnsbrute.py and tests/test_ssh.py: 18 errors.
  - test_dnsbrute.py: removed `from typing import List, Tuple`; `List[Tuple[str, int]]` -> `list[tuple[str, int]]`.
  - test_ssh.py: `from typing import Any, Dict, List` -> `from typing import Any`; `List[str]` -> `list[str]` (10 sites); `Dict[str, Any]` -> `dict[str, Any]` (2 sites).
- Safe on Python >= 3.9 (requires-python >= 3.9); no runtime annotation usage anywhere (get_type_hints/__annotations__/typing.get/cast/Annotated all absent), so builtin generics in annotations never break evaluation.

## Verified
- `python -m pytest -q` -> 3900 passed, 1 skipped, 2 warnings (3901 collected, all accounted for).
- `python -m ruff check tests/test_ssh.py tests/test_dnsbrute.py --select UP006,UP035` -> All checks passed.
- `python -m ruff check --statistics` -> 89 errors (down from 107): UP006 and UP035 fully cleared.
- `python -m py_compile ethscan/*.py` -> clean (unchanged source).
- CLI smoke test unaffected (no source changes).

## Unresolved (pre-existing, not targets unless revisited)
- ruff: 89 errors remain across 10 categories.
  - BLE001 (42 blind-except): Narrowing is PROVEN UNSAFE — tests mock plain `Exception` and assert the broad handler swallows it (brute/web/ssh/cert/cve/geo/mac/oracle + test_cli.py:16385/19232/19371/19564). Do NOT reopen.
  - TRY002 (12 raise-vanilla-class): in tests that deliberately raise plain `Exception` as mock side effects; changing breaks assertions.
  - RUF013 (10 implicit-optional), RUF059 (10 unused-unpacked-var), F811 (9 redefined-unused tests), C405 (2 unnecessary-list-literal -> set-literal in test_cli.py:4423/4784), SIM222 (1), ISC004 (1), PLR0402 (1), RUF012 (1).
- mypy: not targeted (~522 errors historically; mypy present but not run as part of baseline).
- Coverage: 70 missing lines (documented unreachable/environment-dependent).

## Next precise task
- C405 (2 errors) RESOLVED in tests/test_cli.py:4423 and :4784: rewrite `set([20, 21, ...])` as set literal `{20, 21, ...}`. Safe, bounded, mechanical; verify with `python -m ruff check --select C405 tests/test_cli.py` and `python -m pytest -q`.
- After C405, no remaining clearly-safe bounded lint task; await a genuine new issue/requirement before further speculative changes.

(End of file)
