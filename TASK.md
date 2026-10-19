# TASK.md

Date: 2026-10-19T19:41:00Z
Status: the **trace** command now validates its `--target` like the other
target-consuming commands: a target without a usable host is a clean click
usage error (exit code 2) instead of a raw `ValueError` traceback. The rule
lives in exactly one place (`ethscan/target.py`), the library module stays
free of click, and every valid target form keeps its previous behaviour.

## What changed (this session)
- **`ethscan/trace.py`**: `_trace_single` now raises
  `TargetSpecError("Invalid target")` instead of a bare
  `ValueError("Invalid target")`. `TargetSpecError` subclasses `ValueError`,
  so every existing `except ValueError` handler keeps working unchanged -
  including the ones in `ethscan/recon.py` and `ethscan/geo.py`, which run
  the traceroute as one of their modules and already reported the failure
  as a note ("trace module failed: Invalid target"). The module docstring
  documents the new contract, and `TargetSpecError` was added to `__all__`.
- **`ethscan/cli.py`**: the `trace` command now carries the
  `_target_usage_errors` decorator, which is the single place where a
  `TargetSpecError` becomes a click usage error (exit code 2).
- **`README.md`**: the Usage section documents the new usage error and names
  the commands that are affected (`trace`) and the ones that are not
  (`recon`, `geo`).
- **`tests/test_trace.py`** (+4 tests): the unusable targets (`""`, `"   "`,
  `"http://"`, `"https://"`, `"/"`) raise `TargetSpecError`; the error is
  still a `ValueError`; no name lookup and no probe happen for an unusable
  target; the valid target forms (`example.com`, `example.com:80`,
  `http://example.com/`) keep working.
- **`tests/test_trace_cli.py`** (+9 tests): exit code 2, one-line
  `Error: Invalid value for '--target': Invalid target`, no traceback, no
  probe started, and the valid target forms still reach the traceroute.
- **`tests/test_target.py`** (+3 tests): the traceroute rejects a target
  without a usable host, the error is still a `ValueError`, and the working
  target forms are unchanged.

## Design choice
The **existing message** `"Invalid target"` was kept rather than inventing a
new one. It is the wording the module already used, it is stable for every
unusable target form (empty string, whitespace, scheme without a host), and
the two callers that report the failure inside their own output
(`recon`, `geo`) already print it - so the CLI and the library now say the
same thing.

The check stayed where it was (`_trace_single`, right after
`_normalize_host`), so no new validation path was introduced. The recursive
tracing path calls `_trace_single` with hop IPs that are never empty, so it
cannot turn a partial result into a hard failure.

`trace` was **not** given a hostile-host rule. Unlike the five commands
that hand the target to `http.client` (`web`, `headers`, `urlcheck`, `fuzz`,
`s3`), the traceroute resolves the host with `socket.gethostbyname`, which
already fails cleanly with a `socket.gaierror` that the module catches and
reports inside its own output.

## Verification
- **Manual**: `python -m ethscan trace --target ''`, `--target '   '` and
  `--target 'http://'` all print
  `Error: Invalid value for '--target': Invalid target` and exit 2, with no
  traceback.
- **Still working**: `python -m ethscan trace --target example.com` exits 0
  and produces the usual JSON report.
- **Unchanged callers**: `python -m ethscan geo --target '' --recursive`
  and `python -m ethscan recon --target ''` still exit 0 and report
  "recursive hop geolocation failed: Invalid target" /
  "trace module failed: Invalid target" - byte for byte the same as before
  the change.
- **Full suite**: **4204 passed, 1 skipped** (baseline 4189 -> 4204, 15
  new). No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports exactly the same 48 pre-existing errors as the baseline (compared
  rule-by-rule, ignoring line numbers); no new ones.
- **Sweep**: all 42 CLI commands that take a `--target` were invoked with
  `--target ''`, `--target 'host name'` and `--target 'no-such-host.invalid'`.
  After this change **no command leaks a traceback for an empty target**, and
  the only remaining leaker for an unresolvable host is `ping` (see
  `NEXT_TASK.md`).

## Unresolved / deliberate non-changes
- `ping` still crashes with a raw `socket.gaierror` traceback
  (`ethscan/ping.py:249`) when the host cannot be resolved. This is now the
  top entry in `NEXT_TASK.md`.
- `s3` still crashes with a raw traceback for a bracketed IPv6 target
  (`[::1]:443`): the derived bucket names keep the `:`, so the bucket URL is
  malformed, and `http.client.InvalidURL` escapes the thread pool. The
  crash message is **non-deterministic**. Second entry in `NEXT_TASK.md`.
- The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`) are untouched; they never reach a host, so the
  hostile-host rule does not apply to them.
- The 14 `_normalize_target` copies are still duplicated. They are not
  identical (some use `host.find("]:")`, some `host.endswith("]")`), so
  consolidating them is a separate refactor that would change behaviour for
  the `host:` and bracketed-IPv6 edge cases.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.

## Next
See `HANDOFF_NEXT.md` / `NEXT_TASK.md` for the remaining follow-up task.
