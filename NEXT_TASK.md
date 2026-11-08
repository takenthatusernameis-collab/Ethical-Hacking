# Next Task

## Status: CLOSED (this session)
Baseline is GREEN except for 6 pre-existing `test_ping.py` failures caused by Python 3.14 making `socket.timeout` read-only (see HANDOFF_NEXT.md Blockers). Excluding that file: `pytest -q --ignore=tests/test_ping.py` → 5878 passed, 50 skipped, 0 failed.

## Completed (Sun Nov 08 2026, session 9)
- Fixed 48 mypy errors in `tests/test_resolve.py` (typing hygiene; no behavior change):
  - Root cause: `run_resolve`/`resolve` returned `dict[str, object]`, so every `result[...]` access was `object` (broke indexing, `in`, `.get()`, `.nameservers`). Also `dict` is invariant, so `dict[str, Collection[str]]` literals could not be passed to formatters typed `dict[str, object]`.
  - `ethscan/resolve.py`:
    - Added `ResolveResult(TypedDict)` with precise fields and changed `run_resolve`/`resolve` return types to it; constructed via the constructor.
    - Widened `format_resolve_report_json/markdown/csv` signatures from `dict[str, object]` to `Mapping[str, object]` (formatters only read from `data`; mypy-recommended covariant type). Added `Mapping` import.
  - `tests/test_resolve.py`:
    - Added `from typing import Any, cast` and a top-level `import sys`; removed a redundant inner `import sys`.
    - Changed 3 `created: list[object] = []` locals to `created: list[Any] = []` (fakes expose `.nameservers`).
    - Replaced 10 `resolve.dns = FakeDns()` assignments with `resolve.dns = cast(Any, FakeDns())`.
    - Replaced `sys.modules["dns"] = None` with `sys.modules["dns"] = cast(Any, None)`.
- `ethscan/resolve.py` and `tests/test_resolve.py` changes verified clean; whole project (`mypy ethscan/ tests/test_resolve.py`) reports no issues in 60 source files.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.

## Suggested next task
- Continue typing hygiene in remaining test files with mypy errors: `test_ping.py` (36), `test_radix.py` (68), `test_cidr.py` (74). Reproduce with `python -m mypy tests/<file>` first, then fix per file. Note: `test_ping.py` also carries the Python 3.14 `socket.timeout` blocker — fix only the typing errors that are independent of that failure.