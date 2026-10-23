# NEXT_TASK

## Status: COMPLETE

### Task performed this session: narrow transport guard for service.py seams

**Problem:** `ethscan/service.py` had `except (socket.timeout, ConnectionRefusedError, OSError, ValueError, RuntimeError)`
around `socket.create_connection` in `grab_banner`. Transport failures of unnamed types (e.g. `TypeError`)
could escape and crash `run_service` instead of being swallowed.

**Fix:** Broadened that seam to `except Exception as exc:  # noqa: BLE001 - transport can raise any type`.

**Test:** Added `test_run_service_transport_failure_unnamed_type_on_connect_reported` (TypeError from
`create_connection` is caught, `run_service` returns empty results, no traceback).

### What was actually verified

- Crash reproduced before fix; after fix no traceback, empty results returned.
- `tests/test_service.py` → **26 passed** (includes the new regression test).
- `python -m pytest tests/` → **5174 passed, 49 skipped, 0 failed** (3 pre-existing `test_main.py` runpy
  warnings). No regressions.
- `git diff --check` → clean. Nothing committed (commit only if explicitly asked).
- `ruff` not installed in this environment.

### What remains unresolved

- None on this task. The `service.py` transport seam with a demonstrated escape path is fixed.
- Other narrow transport tuples remain without demonstrated crashes (ssh.py, ftp.py, geo.py, mac.py,
  cert.py, dnsbrute.py) — see HANDOFF_NEXT.md.

### Constraints

- Smallest reversible change; crashes become swallowed/reported, never tracebacks.
- Do not commit unless explicitly asked.
- Reproduce before fixing any further tuple.
- `ruff` not installed in this environment.

### One precise next task

Scan remaining narrow transport `except` tuples (start with `ethscan/ssh.py`), reproduce any crash
with an unnamed exception type (patch seam to raise `ValueError`/`TypeError`, call public `run_*`,
confirm it raises), broaden to `except Exception` (# noqa: BLE001), add a regression test next to
the module's own tests, and re-run `python -m pytest tests/`. Do not broaden any tuple without first
demonstrating a crash.
