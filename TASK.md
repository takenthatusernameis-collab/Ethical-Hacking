# TASK.md

Date: 2026-10-19T23:55:00Z
Status: a `--target` whose **host contains a space or a control character** is
now a clean click usage error (exit code 2) in the five commands that turn a
target into a host, the rule lives in exactly one place, the library modules
stay free of click, and every valid target form keeps its previous
behaviour byte for byte.

## What changed (this session)
- **`ethscan/target.py`**: new public helper `check_target_host(target)`. It
  reads the **authority** of the raw target (the part between the scheme and
  the path, the query or the fragment) and raises `TargetSpecError` with the
  message `"Target host contains a space or control character"` when that
  part contains a character matched by `[\x00-\x20\x7f]` - the C0 control
  characters, the space and DEL, which is exactly what `http.client`
  refuses. The module still imports no click.
  The authority is read from the **raw target text** and not from
  `urllib.parse`, because `urlsplit` silently removes tab, carriage return
  and newline characters: `urlparse("https://host\tname").hostname` is
  `"hostname"`, while the host that is actually sent over the network is
  `"host\tname"`. A private `_host_of(target)` does the extraction.
- **`ethscan/web.py`** (`_parse_url`), **`ethscan/fuzz.py`**
  (`_normalize_base_url`) and **`ethscan/s3.py`** (`_normalize_target`): the
  three places that turn a target into a host now call
  `check_target_host`. The empty-host -> `localhost` mapping of
  `web._parse_url`, the lower-casing of `s3._normalize_target` and the
  `scheme://netloc` construction of `fuzz._normalize_base_url` are unchanged.
- **`ethscan/fuzz.py`**: `_normalize_base_url` now also calls the existing
  `url_port(parsed)`, so `fuzz` rejects a target whose port is not a number
  with the same message and the same exit code as the other fourteen
  commands. This was the "adjacent variant" of the previous session's task
  and it was **included** on purpose (see the design notes below).
- **`ethscan/cli.py`**: the existing `_target_usage_errors` decorator is now
  also attached to `fuzz` and `s3`. `web`, `headers` and `urlcheck` already
  carried it, so they needed **no CLI change**.
- **`README.md`**: the Usage section documents the new usage error and names
  the five commands it applies to.
- **`tests/test_target.py`** (+29 tests) and **`tests/test_cli.py`**
  (+16 tests, plus `fuzz` added to the two existing non-numeric-port
  command tuples).

## Design choice (the task asked for it to be stated)
The **stable message** was chosen over preserving `str(exc)` of the
`http.client.InvalidURL`:
`"Target host contains a space or control character"`.
The raw `InvalidURL` text quotes the host that is actually sent, and for
`s3` that host is a *derived* bucket name
(`'host name-cdn.s3.amazonaws.com'`), so the message would differ per
command and would name a value the user never typed. One stable message
gives the same one-line error for all five commands; a test asserts that.
The port variant keeps the `urllib.parse` wording
(`"Port could not be cast to integer value as 'notaport'"`), because that
is the message the other fourteen commands already report.

The **fuzz port variant was included**. `fuzz` hands the whole URL to
`http.client` instead of reading `urllib.parse`'s port property, so it
raised its own `InvalidURL: nonnumeric port: 'notaport'`. Validating the
parsed netloc in `fuzz._normalize_base_url` (host **and** port) covers both
fuzz variants in one place and makes `fuzz` behave like `web`, `headers`
and `urlcheck`, which already rejected a non-numeric port.

## Verification
- **Behavioural equivalence**: a 320-invocation harness (19 commands x 11
  target values, 5 commands x 3 hostile-host targets, a bare
  `host:notaport` target for the five URL-based commands, 3 output formats
  and `--help` per command) was captured **twice** from a pristine
  `git archive HEAD` tree in `/tmp/ethscan_before` and once from the
  working tree, and compared byte for byte.
  **288 are byte-identical**; **16 are exactly the intended conversions**
  (14 traceback -> usage error, plus 2 report -> usage error, see below);
  **0 differences that this change caused**. 14 invocations (all `s3`,
  which makes real AWS requests) are not reproducible even between the two
  baseline runs and were excluded from the comparison.
  Two further `s3` invocations (`--target "[::1]:443"` and
  `--target "[::1]:6379"`) differ only in *which* bucket candidate raised
  first. That is **pre-existing non-determinism**: eight runs of the
  **unchanged** tree produce four different tracebacks for the same
  command, because `run_s3` probes the candidates concurrently and
  re-raises whichever exception finishes first. The exit code (1) and the
  stdout are identical before and after.
- **Full suite**: **4159 passed, 1 skipped** (baseline 4129 -> 4159, 30
  new). No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports the same 48 pre-existing errors as the baseline; the rule set is
  identical once line numbers are normalised (`diff` of the normalised
  output is empty).
- **Manual**: all fifteen previously-crashing invocations now print
  `Error: Invalid value for '--target': Target host contains a space or
  control character` and exit 2.

## Unresolved / deliberate non-changes
- Two `fuzz` invocations changed from *exit 0 with a report* to *exit 2
  with a usage error*, and this is intended:
  - `fuzz --target "host<TAB>name"`: before, `urlsplit` dropped the tab, so
    the fuzzer silently scanned a **different** host (`hostname`) and
    reported DNS errors for it. It is now rejected.
  - `fuzz --target "redis://host:notaport"`: before, the unknown URL scheme
    was reported per path and the command exited 0. It is now the same
    usage error the other fourteen commands give.
- The **path and query** of a target are still not validated. A target
  whose path contains a space (`https://example.com/a b`) still dies with
  a raw `http.client.InvalidURL: URL can't contain control characters.
  '/a b'` traceback in `web`, `headers` and `urlcheck`. That is the same
  family of defect but a different component, and the task deliberately
  scoped this change to the host. See `NEXT_TASK.md`.
- `s3` still crashes with a raw traceback for a bracketed IPv6 target
  (`[::1]:443`): the derived bucket names contain `:`, which makes the
  bucket URL malformed. Pre-existing, not touched here, and it is the
  second entry in `NEXT_TASK.md`.
- `trace --target ''` still dies with `ValueError: Invalid target`
  (`ethscan/trace.py:79`): `trace` has no `--target` usage-error handling
  at all yet. Third entry in `NEXT_TASK.md`.
- The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`) are untouched; they never reach a host, so the
  hostile-host rule does not apply to them.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.

## Next
See `HANDOFF_NEXT.md` / `NEXT_TASK.md` for the remaining follow-up task.
