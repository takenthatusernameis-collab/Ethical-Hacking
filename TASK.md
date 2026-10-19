# TASK.md

Date: 2026-10-19T23:09:00Z
Status: the **trace** command validates its `--target` (clean click usage
error, exit 2) and **`ping` no longer leaks `socket.gaierror`** for an
unresolvable host (exit 0, failure reported inside output). Both are
committed at HEAD (`9a86aa0` includes the `ping` fix). The only remaining
`--target` leak is the `s3` bracketed-IPv6 crash (`http.client.InvalidURL`),
prepared as the next task in `HANDOFF_NEXT.md` / `NEXT_TASK.md`.

## What changed
- **`ethscan/trace.py`**: `_trace_single` raises `TargetSpecError("Invalid
  target")` instead of a bare `ValueError`; `trace` carries the
  `_target_usage_errors` decorator (click usage error, exit 2).
- **`ethscan/ping.py`**: `probe_icmp` catches `socket.gaierror` around
  `connect_ex` and returns a `NO-RESPONSE` probe with the resolver error in
  `error`; `run_ping` keeps its "Could not resolve host ..." note. Raw ICMP
  path unchanged.
- Tests added for `trace` (library + CLI) and `ping` (library + CLI).

## Verification
- Manual: `trace --target ''`, `--target '   '`, `--target 'http://'` exit 2
  with `Error: Invalid value for '--target': Invalid target`, no traceback;
  `trace --target example.com` exits 0.
- `ping --target no-such-host.invalid` and `--target 'host name'` exit 0
  with structured JSON (`response_type: NO-RESPONSE`, resolver error in
  `error`, "Could not resolve host ..." note); `ping --target example.com`
  exits 0.
- Full suite: **4207 passed, 1 skipped**. Ruff: same 48 pre-existing errors,
  no new ones.
- Sweep: all 42 `--target` commands with `--target ''`, `--target 'host
  name'`, `--target 'no-such-host.invalid'`; no tracebacks remain except
  `s3 --target '[::1]:443'`.

## Remaining
- `s3 --target '[::1]:443'` crashes with `http.client.InvalidURL:
  nonnumeric port: '1.s3.amazonaws.com'` (exit 1, non-deterministic). See
  `HANDOFF_NEXT.md` for root cause, the two pre-code decisions, and the
  suggested minimal fix.
- The 48 pre-existing ruff errors are unrelated and left alone.
