# NEXT_TASK

## Status: COMPLETE

### Task performed this session: narrow transport guard for dnsbrute.py and mac.py seams

**Problem:** Two remaining narrow transport `except` tuples from the previous sweep let
unnamed exception types escape and crash the public command instead of being reported.

- `ethscan/dnsbrute.py:267` (`query_axfr_raw`): `except (socket.timeout, socket.gaierror,
  OSError, ValueError, RuntimeError)` around `socket.create_connection` / `recv`.
- `ethscan/mac.py:48` (`_resolve_host`): `except (socket.timeout, socket.gaierror,
  socket.herror, OSError, ValueError, RuntimeError)` around `socket.gethostbyname`.

**Fix:** Broadened both to `except Exception` with `# noqa: BLE001`.

**Tests:** Added `test_query_axfr_raw_transport_failure_unnamed_type_on_connect_reported`
(next to `tests/test_dnsbrute.py`) and `test_resolver_failure_of_an_unnamed_type_is_reported`
(next to `tests/test_mac.py`).

### What was actually verified

- Crash reproduced before fix; after fix no traceback, error reported / lookup returns None.
- `tests/test_dnsbrute.py` -> 162 passed, 1 skipped (includes the new regression test).
- `tests/test_mac.py` -> all pass (includes the new regression test).
- `python3 -m pytest tests/` -> **5183 passed, 49 skipped, 0 failed** (3 pre-existing
  `test_main.py` runpy warnings). No regressions.
- `git diff --check` -> clean. Nothing committed (commit only if explicitly asked).
- `ruff` not installed in this environment. `pytest` was not installed either and was
  installed locally with `pip install pytest` for this session.

### What remains unresolved

- `ethscan/dnsbrute.py:_resolve_label` (lines 384, 394) still uses a narrow tuple that
  excludes `TypeError`, but it is only reachable when a `resolver` is given AND dnspython
  is installed. dnspython is **not** installed here, so the branch is unreachable and no
  crash could be demonstrated. Left untouched per the "reproduce before fixing" rule.
- `ethscan/geo.py` and `ethscan/cert.py` were inspected: their `_resolve_host` already
  uses `except Exception`; their other narrow tuples are cache/JSON seams, not
  transport seams, so they are out of scope.
- See HANDOFF_NEXT.md for the remaining candidate list and the precise next task.

### Constraints

- Smallest reversible change; crashes become swallowed/reported, never tracebacks.
- Do not commit unless explicitly asked.
- Reproduce before fixing any further tuple.
- `ruff` and `pytest` may not be pre-installed; install `pytest` locally if needed.

### One precise next task

Continue the sweep of remaining narrow transport `except` tuples, starting with
`ethscan/dnsbrute.py:_resolve_label` once dnspython is available. For each candidate,
reproduce the crash with a hostile seam (patch the transport to raise `TypeError('hostile')`,
call the public `run_*`, confirm it raises), broaden the narrowest seam to
`except Exception` (# noqa: BLE001), add a focused regression test next to the module's
own tests, and re-run `python3 -m pytest tests/`. Do not broaden any tuple without first
demonstrating a crash.

(End of file - total 44 lines)
