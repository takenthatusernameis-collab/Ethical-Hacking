# NEXT_TASK

## Status: COMPLETE

### Task performed this session: narrow transport guard for SMTP seams

**Problem:** `ethscan/smtp.py` had `except (socket.timeout, OSError)` in `_read_response`, banner read, EHLO, VRFY, and relay probe paths. Transport failures of unnamed types (e.g. `ValueError`) could escape and crash the command instead of being reported through the error field.

**Fix:** Broadened those seams to `except Exception as exc:  # noqa: BLE001 - transport can raise any type` (and ensured errors are reported via `results["error"]` / user entry errors / `open_relay`).

**Test:** Added ValueError regression tests:
- `test_run_smtp_transport_failure_on_connect_unnamed_type_is_reported`
- `test_run_smtp_transport_failure_on_banner_unnamed_type_is_reported`
- `test_run_smtp_transport_failure_on_ehlo_unnamed_type_is_reported`
- `test_run_smtp_transport_failure_on_vrfy_unnamed_type_is_reported`
- `test_run_smtp_transport_failure_on_relay_unnamed_type_is_reported`

### What was actually verified

- Crashes reproduced before fix; after fix all report via module error fields, no traceback.
- `tests/test_smtp.py` → **65 passed** (includes 5 new regression tests).
- `python -m pytest tests/` → **5172 passed, 49 skipped, 0 failed** (3 pre-existing `test_main.py` runpy warnings). No regressions.
- `git diff --check` → clean. Nothing committed (commit only if explicitly asked).

### What remains unresolved

- **None on this task.** All SMTP transport seams with demonstrated escape paths are fixed.
- Other narrow transport tuples remain (service, ssh, ftp, geo, mac, cert, dnsbrute) but lack demonstrated crashes; see HANDOFF_NEXT.md for candidates.

### Constraints

- Smallest reversible change; crashes become reported via error fields.
- Do not commit unless explicitly asked.
- `ruff` not installed in this environment.
- Reproduce before fixing any further tuple.

### One precise next task

Scan remaining narrow transport `except` tuples (start with `ethscan/service.py`), reproduce any crash with an unnamed exception type, broaden to `except Exception` (# noqa: BLE001), add a `ValueError` regression test next to the module's own tests, and re-run `python -m pytest tests/`. Do not broaden without a demonstrated crash.
