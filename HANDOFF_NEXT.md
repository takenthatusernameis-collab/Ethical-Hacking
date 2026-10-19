# HANDOFF_NEXT.md

## Summary
Executed the prior agent's assignment: the **trace** command now reports a
`--target` without a usable host as a clean click usage error (exit code 2,
one-line message, no traceback), instead of dying with a raw
`ValueError: Invalid target` (`ethscan/trace.py:79`).

The prior session had identified the defect and left a precise plan in
`NEXT_TASK.md`; the shared machinery already existed
(`ethscan/target.py` with `TargetSpecError`, and the `_target_usage_errors`
decorator in `ethscan/cli.py`), but `trace` used a bare `ValueError` and
carried no decorator. This session closed that gap and re-verified the
behaviour end to end, including the two internal callers of the traceroute.

## Changes
- **`ethscan/trace.py`**: `_trace_single` raises
  `TargetSpecError("Invalid target")` instead of a bare `ValueError`.
  `TargetSpecError` subclasses `ValueError`, so every existing
  `except ValueError` handler keeps working - including the ones in
  `ethscan/recon.py` and `ethscan/geo.py`, which run the traceroute as a
  module and already reported the failure as a note. The module docstring
  documents the contract; `TargetSpecError` was added to `__all__`.
- **`ethscan/cli.py`**: the `trace` command now carries the
  `@_target_usage_errors` decorator (one line).
- **`README.md`**: the Usage section documents the new usage error, names
  `trace` as an affected command and `recon` / `geo` as unaffected.
- **`tests/test_trace.py`** (+4), **`tests/test_trace_cli.py`** (+9),
  **`tests/test_target.py`** (+3).

### Design choice (the prior task asked for it to be stated)
The **existing message** `"Invalid target"` was kept. It is the wording the
module already used, it is stable across every unusable target form (empty
string, whitespace, scheme without a host), and the two commands that report
the failure inside their own output (`recon`, `geo`) already print it - so
the CLI and the library now say the same thing.

`trace` was **not** given the hostile-host rule. The five commands that
hand the target to `http.client` (`web`, `headers`, `urlcheck`, `fuzz`,
`s3`) need it because `http.client.InvalidURL` is not a `ValueError`. The
traceroute resolves the host with `socket.gethostbyname`, which already
fails with a `socket.gaierror` that the module catches and reports inside
its own output.

## Verification
- **Manual**: `trace --target ''`, `--target '   '` and `--target 'http://'`
  print `Error: Invalid value for '--target': Invalid target` and exit 2,
  with no traceback.
- **Still working**: `trace --target example.com` exits 0 and produces the
  usual JSON report.
- **Unchanged callers**: `geo --target '' --recursive` and
  `recon --target ''` still exit 0 and report the same notes as before
  ("recursive hop geolocation failed: Invalid target",
  "trace module failed: Invalid target").
- **Full suite**: **4204 passed, 1 skipped** (baseline 4159 -> 4189 -> 4204,
  15 new). No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports exactly the same 48 pre-existing errors as the baseline (compared
  rule-by-rule, ignoring line numbers); no new ones.
- **Sweep**: all 42 CLI commands that take a `--target` were invoked with
  `--target ''`, `--target 'host name'` and
  `--target 'no-such-host.invalid'`. After this change **no command leaks a
  traceback for an empty target**; the only remaining leaker for an
  unresolvable host is `ping`.

## Unresolved
- `ping` still crashes with a raw `socket.gaierror` traceback
  (`ethscan/ping.py:249`) when the host cannot be resolved. This is the top
  entry in `NEXT_TASK.md`, with a full reproduction and a root-cause
  analysis.
- `s3` still crashes with a raw traceback for a bracketed IPv6 target
  (`[::1]:443`): the derived bucket names keep the `:`, so the bucket URL is
  malformed, and `http.client.InvalidURL` escapes the thread pool. The
  crash message is **non-deterministic** (six runs of the unchanged tree
  produced three different messages). Second entry in `NEXT_TASK.md`.
- The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`) are untouched; they never reach a host, so the
  hostile-host rule does not apply to them.
- The 14 `_normalize_target` copies are still duplicated. They are not
  identical (some use `host.find("]:")`, some `host.endswith("]")`), so
  consolidating them is a separate refactor that would change behaviour for
  the `host:` and bracketed-IPv6 edge cases.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.

## Next agent task
Take the **first** entry in `NEXT_TASK.md`: `ping` leaks a raw
`socket.gaierror` for a target that cannot be resolved. It is small,
deterministic and self-contained, and the sweep in `NEXT_TASK.md` proves it
is the only remaining command in that class.

The `s3` bracketed-IPv6 cluster (second entry) needs two decisions that
should be made explicitly before any code is written: which bucket names
are usable, and whether a failed probe should be reported inside the result
instead of escaping the thread pool.
