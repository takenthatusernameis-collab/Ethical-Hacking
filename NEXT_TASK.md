# NEXT_TASK

## Status: READY

### Suggested task: audit for remaining unguarded transport seams

All known crash paths are fixed. The codebase follows the pattern of catching broad exceptions and reporting them as structured errors. A good bounded task is to do a quick audit for any public `run_*` functions that might have unguarded transport calls.

### What to verify

- For each command module, check if `run_*` can propagate exceptions from transport/resolve calls
- Pay special attention to paths using `socket.*`, `connect`, raw sockets, subprocess, etc.
- If any crash is found, reproduce with hostile transport raising `RuntimeError`, fix with smallest change, add regression test

### Verification commands

- `python3 -m pytest tests/test_protocol_hostile_sweep.py -q`
- `python3 -m pytest tests/ -q`
- `python3 -m ruff check ethscan/ tests/`

### Constraints

- Smallest reversible change; exceptions become reported errors, never tracebacks
- Add regression test next to module's tests if fixing
- Do not commit unless explicitly asked
- Reproduce before fixing

### Evidence of completion

All tests pass, no unguarded seams found or fixed with tests.
