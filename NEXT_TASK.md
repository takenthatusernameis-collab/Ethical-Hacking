# NEXT TASK

## Status: COMPLETE

### Task performed this session: `whois` narrow transport guard

**Problem:** `ethscan/whois.py` `run_whois` was the only module not following the codebase's transport-seam convention (`except Exception` because "transport can raise any type"). Its two `except` clauses used a narrow tuple `(socket.gaierror, socket.timeout, ConnectionRefusedError, OSError, RuntimeError)`, and `socket.socket()` creation at `ethscan/whois.py:43` is outside the try block. A transport failure of an unnamed type (e.g. `ValueError` from socket creation) crashed the command instead of being reported through its `error` field. Reproduced before the fix: patching `socket.socket` to raise `ValueError` made `whois.run_whois("example.com")` crash.

**Fix:** Broadened both `except` clauses in `run_whois` to `except Exception` (with `noqa: BLE001`), matching every other transport module (`ethscan/whois.py`).

**Test:** Added `test_run_whois_transport_failure_unnamed_type_reported` in `tests/test_whois.py` — patches `ethscan.whois.socket.socket` to raise `ValueError` and asserts `run_whois` reports the error and never raises.

### What was actually verified

- Crash reproduced before the fix; after the fix the same probe returns a result with `error` set, `raw == ""`, no traceback.
- `tests/test_whois.py` -> **42 passed** (includes the new regression test).
- `python -m pytest tests/` -> **5158 passed, 49 skipped, 3 warnings** (baseline 5157 passed; the 3 warnings are the pre-existing `test_main.py` runpy ones). No regressions.
- `git diff` contains only `ethscan/whois.py` and `tests/test_whois.py`. Nothing committed (commit only if explicitly asked).

### What remains unresolved

- **None.** All 53 CLI commands are covered by CLI-level unreachable/offline sweeps, and every transport-opening module has a module-level hostile-sweep check. `whois` is now consistent with the rest.

### Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash into the module's documented error signal.
- Keep the permanent sweeps in the repository.
- Do not commit unless explicitly asked.

### One precise next task

- **No outstanding task from this handoff.** If no new assignment exists, inspect `git status`/`git diff` only.
