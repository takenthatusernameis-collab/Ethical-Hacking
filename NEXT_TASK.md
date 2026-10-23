# NEXT TASK

## Status: COMPLETE

### Task performed this session: narrow transport guard for database/NBNS `_send_recv` seams

**Problem:** `ethscan/mongodb.py`, `ethscan/mysql.py`, `ethscan/mssql.py`, `ethscan/postgresql.py`, `ethscan/oracle.py` `_send_recv` and `ethscan/netbios.py` `_send_recv` each had `except (OSError, RuntimeError)` around `socket.create_connection`/`socket.socket`+`sendto`/`recvfrom`. A transport failure of an unnamed type (e.g. `ValueError`) escaped and crashed the command instead of being reported through the error field. Reproduced before the fix for all six.

**Fix:** Broadened all six `except (OSError, RuntimeError) as exc:` clauses to `except Exception as exc:  # noqa: BLE001 - transport can raise any type`, matching the codebase transport-seam convention.

**Test:** Added a `ValueError` sibling to each module's existing `RuntimeError` transport-failure test:
- `test_run_mongodb_transport_failure_of_unnamed_type_is_reported`
- `test_run_mysql_transport_failure_of_unnamed_type_is_reported`
- `test_run_mssql_transport_failure_of_unnamed_type_is_reported`
- `test_run_postgresql_transport_failure_of_unnamed_type_is_reported`
- `test_run_oracle_transport_failure_of_unnamed_type_is_reported`
- `test_send_recv_socket_creation_failure_of_unnamed_type_is_reported` (netbios)

### What was actually verified

- Crash reproduced before the fix; after the fix all six report via the error field, no traceback.
- Affected module test files → **453 passed** (includes 6 new regression tests).
- `python -m pytest tests/` → **5167 passed, 49 skipped, 0 failed** (3 pre-existing `test_main.py` runpy warnings). No regressions.
- `git diff --check` → clean. Nothing committed (commit only if explicitly asked).

### What remains unresolved

- **None on this task.** All six narrow transport seams with a demonstrated escape path are fixed.
- Other narrow transport tuples remain (smtp, service, ssh, ftp, geo, mac, cert, dnsbrute) but lack a demonstrated crash; see HANDOFF_NEXT.md "What remains unresolved" for the candidate list and the rule not to broaden without evidence.

### Constraints

- Smallest reversible change; the crash becomes the module's documented error signal; do not weaken an existing guard.
- Do not commit unless explicitly asked.
- `ruff` is not installed in this environment; lint check could not be run.
- Reproduce before fixing any further tuple.

### One precise next task

Scan the remaining narrow transport `except` tuples (smtp.py `except (socket.timeout, OSError)` seams first), reproduce any crash with an unnamed exception type, broaden to `except Exception` (# noqa: BLE001), add a `ValueError` regression test next to the module's own tests, and re-run `python -m pytest tests/`. Do not broaden without a demonstrated crash.
