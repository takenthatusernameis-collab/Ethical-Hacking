# Handoff
Date: Sun Nov 08 2026 (session 9)

## What changed
- `ethscan/resolve.py`:
  - Added `ResolveResult(TypedDict)` with precise fields (`target: str`, `normalized: str`, `is_ip: bool`, `record_types_queried: list[str]`, `records: dict[str, list[str]]`, `dnspython_available: bool`, `server: str | None`). Changed `run_resolve` and `resolve` return types from `dict[str, object]` to `ResolveResult`; the dict literal was replaced by an explicit constructor call (identical field values, no behavior change).
  - Widened `format_resolve_report_json`, `format_resolve_report_markdown`, `format_resolve_report_csv` signatures from `dict[str, object]` to `Mapping[str, object]` (formatters only read from `data`; mypy-recommended covariant type). Added `Mapping` to the typing import.
- `tests/test_resolve.py` (typing hygiene only, no behavior change, 48 mypy errors fixed):
  - Added `from typing import Any, cast` and a top-level `import sys`; removed a redundant inner `import sys`.
  - Changed 3 `created: list[object] = []` locals to `created: list[Any] = []` (the fakes expose `.nameservers`, which `object` lacks).
  - Replaced 10 `resolve.dns = FakeDns()` assignments with `resolve.dns = cast(Any, FakeDns())`.
  - Replaced `sys.modules["dns"] = None` with `sys.modules["dns"] = cast(Any, None)`.

## Root cause
- `run_resolve`/`resolve` returned `dict[str, object]`, so `result["records"]`, `result["target"]`, etc. were inferred as `object`, failing indexing, `in`, `.get()`, and `.nameservers` access across ~30 sites.
- `dict` is invariant, so `dict[str, Collection[str]]` literals were not assignable to formatter params typed `dict[str, object]`. `Mapping[str, object]` is covariant and the formatters only read from `data`.
- A `TypedDict` is the correct shape for `run_resolve`'s return: it is a plain `dict` at runtime (so `isinstance(results, dict)` and JSON serialization still work), but gives each field a precise type so downstream code can index safely.
- Test fakes assigned to module attributes (`resolve.dns`, `sys.modules["dns"]`) typed by the real import; `cast(Any, ...)` bridges the duck-typed fakes without weakening the real type.

## What was verified
- `python -m mypy tests/test_resolve.py` → Success: no issues found.
- `python -m mypy ethscan/resolve.py` → Success: no issues found.
- `python -m mypy ethscan/ tests/test_resolve.py` → Success: no issues found in 60 source files (whole project clean).
- `python -m ruff check tests/test_resolve.py ethscan/resolve.py` → All checks passed.
- `python -m pytest tests/test_resolve.py -q` → 76 passed.
- `python -m pytest tests/test_cli.py -q -k resolve` → 101 passed (CLI resolve path still works with the new return type).
- `python -m pytest -q --ignore=tests/test_ping.py` → 5878 passed, 50 skipped, 0 failed.

## Unresolved
- Pre-existing environment failures in `tests/test_ping.py` (6 tests): `_FakeRawSocket.__init__` sets `self.timeout: float | None = None`, but Python 3.14 made `socket.timeout` a read-only descriptor on `_socket.socket` subclasses. Unrelated to typing hygiene. The 6 failing tests are: `test_probe_icmp_raw_socket_echo_reply`, `test_probe_icmp_raw_socket_timeout`, `test_probe_icmp_raw_socket_oserror`, `test_probe_icmp_raw_socket_wrong_id`, `test_probe_icmp_raw_send_socket_creation_fails_falls_back`, `test_probe_icmp_raw_sendto_oserror`.

## Next task
- Continue typing hygiene in remaining test files with mypy errors: `test_ping.py` (36), `test_radix.py` (68), `test_cidr.py` (74). Reproduce with `python -m mypy tests/<file>` first, then fix per file. Note the `test_ping.py` Python 3.14 `socket.timeout` blocker above — fix only the typing errors that are independent of that failure.