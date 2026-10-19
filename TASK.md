# TASK.md

Date: 2026-10-19T19:35:00Z
Status: the **path and query** of a `--target` are now validated the same way
the host is: a target whose path or query contains a space or a control
character is a clean click usage error (exit code 2) in the three commands
that send the raw target to the server (`web`, `headers`, `urlcheck`). The
rule lives in exactly one place (`ethscan/target.py`), the library modules
stay free of click, and every valid target form keeps its previous behaviour
byte for byte.

## What changed (this session)
- **`ethscan/target.py`**: two new public helpers, `check_target_path` and
  its private extraction helper `_path_of`. `check_target_path` reads the
  **path+query** of the raw target and raises `TargetSpecError` with the
  message `"Target path contains a space or control character"` when that
  part contains a character matched by `[\x00-\x20\x7f]` - the C0 control
  characters, the space and DEL, which is exactly what `http.client`
  refuses. The fragment (`#...`) is never sent to the server and is
  therefore not validated; the userinfo and the port belong to the
  authority and are already covered by `check_target_host` and `url_port`.
  The path is read from the **raw target text** and not from
  `urllib.parse`, for the same reason the host is: `urlsplit` silently
  removes tab, carriage return and newline characters.
- **`ethscan/web.py`** (`_parse_url`): now calls `check_target_path` after
  `check_target_host`. `web`, `headers` and `urlcheck` all reach this code
  (`headers.run_headers` calls `_parse_url`; `urlcheck.run_urlcheck`
  normalizes the target then calls `run_web_checks`). The empty-host ->
  `localhost` mapping and the port handling are unchanged.
- **`ethscan/cli.py`**: no change needed. `web`, `headers` and `urlcheck`
  already carried the `_target_usage_errors` decorator, which translates a
  `TargetSpecError` into a click usage error at the CLI boundary.
- **`README.md`**: the Usage section documents the new usage error and
  names the three commands it applies to.
- **`tests/test_target.py`** (+19 tests) and **`tests/test_cli.py`**
  (+8 tests).

## Design choice (the task asked for it to be stated)
The **stable message** was chosen over preserving `str(exc)` of the
`http.client.InvalidURL`:
`"Target path contains a space or control character"`.
The raw `InvalidURL` text quotes the derived request target that is
actually sent (`'/a b'`), so the message would differ per command and
would name a value the user never typed. One stable message gives the
same one-line error for all three commands; a test asserts that.

The **extraction helper is a second private function** (`_path_of`) rather
than one combined helper that checks the whole URL, because the host and
the path are two distinct parts of the target with two distinct messages
and two distinct reachability sets: the host rule applies to five
commands (`web`, `headers`, `urlcheck`, `fuzz`, `s3`) while the path rule
applies to the three that send the raw target to the server. Keeping the
two helpers separate lets each command call exactly the rules that apply
to it.

## Verification
- **Manual**: `web`, `headers` and `urlcheck` with `--target
  "https://example.com/a b"`, `--target "https://example.com/a\tb"`,
  `--target "https://example.com/?q=a b"`, `--target "https://example.com/a\x7fb"`
  all print `Error: Invalid value for '--target': Target path contains a
  space or control character` and exit 2, with no traceback.
- **Valid forms**: `https://example.com/path`, `https://example.com/a%20b`,
  `https://example.com/?q=1`, `https://example.com/path#frag` are still
  accepted (exit 0) by all three commands, and a fragment containing a
  space or tab is not rejected.
- **Full suite**: **4189 passed, 1 skipped** (baseline 4159 -> 4189, 30
  new). No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports the same 48 pre-existing errors as the baseline; no new ones.

## Unresolved / deliberate non-changes
- The `s3` and `fuzz` commands are unaffected by the path rule: `fuzz`
  keeps only `scheme://netloc` in `_normalize_base_url`, and `s3` derives a
  bucket name from the host alone. A percent-encoded path still works for
  both.
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