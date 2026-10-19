# HANDOFF_NEXT.md

## Summary
Executed the prior agent's assignment: a `--target` whose **path or query**
contains a space or a control character is now a clean click usage error
(exit code 2, one-line message, no traceback) in the three commands that
send the raw target to the server (`web`, `headers`, `urlcheck`).

The prior session had identified the defect and left a precise plan in
`NEXT_TASK.md`; the library side already had the helpers (`_path_of` and
`check_target_path` in `ethscan/target.py`) and the wiring into
`web._parse_url`, but there were **no tests** for the path rule and the
**README did not document it**. This session closed those gaps and
re-verified the behaviour end to end.

## Changes
- **`ethscan/target.py`**: module docstring now documents
  `check_target_path` alongside `check_target_host` and `url_port`.
- **`ethscan/web.py`**: no change - `check_target_path` was already called
  inside `_parse_url`, which `run_web_checks` and (via `run_headers`) the
  `headers` command reach, and which `urlcheck` reaches after normalizing
  the target.
- **`ethscan/cli.py`**: no change - `web`, `headers` and `urlcheck` already
  carried the `_target_usage_errors` decorator.
- **`README.md`**: the Usage section now documents the path/query usage
  error and names the three commands it applies to.
- **`tests/test_target.py`** (+19 tests): rejects space/tab/newline/DEL in
  the path and query; accepts the valid forms including a percent-encoded
  path and a target with a fragment; asserts the fragment is not rejected
  even when it contains a space or a tab; asserts a bare host is a no-op.
- **`tests/test_cli.py`** (+8 tests): exit code 2, one-line
  `Error: Invalid value for '--target': Target path contains a space or
  control character`, no traceback, no probe started, valid path forms
  still accepted, identical message across all three commands.

### Design choice (the prior task asked for it to be stated)
The **stable message** was chosen over preserving `str(exc)` of the
`http.client.InvalidURL`:
`"Target path contains a space or control character"`.
The raw `InvalidURL` text quotes the derived request target that is
actually sent (`'/a b'`), so the message would differ per command and
would name a value the user never typed. One stable message gives the
same one-line error for all three commands; a test asserts that.

The **extraction helper is a second private function** (`_path_of`)
rather than one combined helper that checks the whole URL, because the
host and the path are two distinct parts of the target with two distinct
messages and two distinct reachability sets: the host rule applies to
five commands (`web`, `headers`, `urlcheck`, `fuzz`, `s3`) while the path
rule applies to the three that send the raw target to the server. Keeping
the two helpers separate lets each command call exactly the rules that
apply to it.

## Verification
- **Manual**: `web`, `headers` and `urlcheck` with `--target
  "https://example.com/a b"`, `--target "https://example.com/a\tb"`,
  `--target "https://example.com/?q=a b"` and
  `--target "https://example.com/a\x7fb"` all print
  `Error: Invalid value for '--target': Target path contains a space or
  control character` and exit 2, with no traceback.
- **Valid forms**: `https://example.com/path`,
  `https://example.com/a%20b`, `https://example.com/?q=1` and
  `https://example.com/path#frag` are still accepted (exit 0) by all three
  commands, and a fragment containing a space or a tab is not rejected.
- **Full suite**: **4189 passed, 1 skipped** (baseline 4159 -> 4189, 30
  new). No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports the same 48 pre-existing errors as the baseline; no new ones.

## Unresolved
- `s3` still crashes with a raw traceback for a bracketed IPv6 target
  (`[::1]:443`): the derived bucket names contain `:`, which makes the
  bucket URL malformed, and the crash message is non-deterministic
  (`run_s3` probes the candidates concurrently and re-raises whichever
  exception finishes first).
- `trace --target ''` still dies with `ValueError: Invalid target`
  (`ethscan/trace.py:79`): `trace` has no `--target` usage-error handling
  at all yet.
- The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`) are untouched; they never reach a host, so the
  hostile-host rule does not apply to them. Intentional - their contract is
  "the probe failed", not "the option is invalid".
- The 14 `_normalize_target` copies are still duplicated. They are not
  identical (some use `host.find("]:")`, some `host.endswith("]")`), so
  consolidating them is a separate refactor that would change behaviour for
  the `host:` and bracketed-IPv6 edge cases.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.

## Next agent task
Pick one of the remaining clusters in `NEXT_TASK.md`. The two that are
self-contained and deterministic are:
1. `trace --target ''` -> `ValueError: Invalid target`
   (`ethscan/trace.py:79`): `trace` has no `--target` usage-error handling
   at all yet. Small and self-contained.
2. `s3` with a bracketed IPv6 target (`--target "[::1]:443"`) ->
   `http.client.InvalidURL: nonnumeric port: '1.s3.amazonaws.com'`. The
   derived bucket names keep the `:`, so the bucket URL is malformed. The
   message is **non-deterministic**: `run_s3` probes the candidates
   concurrently and re-raises whichever exception finishes first, so eight
   runs of the unchanged tree produce four different tracebacks. Two
   things to decide: which bucket names are usable, and whether a failed
   probe should be reported inside the result instead of escaping the
   thread pool.

The network-dependent clusters (`ping`, `geo`, `dnssec`, `vuln`,
`osdetect`, `service`, `scan`, `smtp`, `ftp`, `ssh`, `s3` with an
unresolvable host -> `socket.gaierror` or `encoding with 'idna' codec
failed`) need a different decision: a failed DNS lookup is arguably a probe
result (exit 0 with an error field) rather than a usage error.