# TASK.md

Date: 2026-10-19T23:40:00Z
Status: a `--target` whose **port is not a number** is now a clean click usage
error (exit code 2) in the thirteen commands that used to dump a traceback,
the translation still lives in exactly one place, the library modules stay
free of click, and the five commands that report a failed probe keep their
contract and their exact error wording.

## What changed (this session)
- **`ethscan/target.py`**: new public helper `url_port(parsed)`. It returns
  the port of a parsed URL and re-raises the bare `ValueError` that
  `urllib.parse` raises for a non-numeric or out-of-range port as a
  `TargetSpecError`, **with the original message text unchanged**
  (`"Port could not be cast to integer value as 'notaport'"`). The module
  stays click-free.
- **14 protocol modules** (`redis`, `memcached`, `ntp`, `snmp`, `ftp`,
  `ldap`, `netbios`, `smb`, `smtp`, `mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`): the single `port = parsed.port` access in each
  `_normalize_target` now calls `url_port(parsed)`. **Nothing else changed** -
  the duplicated parsers were deliberately not consolidated, and the
  `host:` / bracketed-IPv6 edge cases keep their current behaviour.
- **`ethscan/web.py`**: `_parse_url` uses `url_port(parsed)` for both the
  https (443) and http (80) default. The empty-host -> `localhost` mapping
  and the scheme handling are unchanged.
- **`ethscan/ssh.py`**: `_extract_port` uses `url_port(parsed)`. The
  lower-casing of the host in `_normalize_host` is unchanged.
- **`ethscan/cli.py`**: the existing `_target_usage_errors` decorator (and
  its `_invalid_target` helper) is now also attached to the four commands
  that read the target as a URL: `web`, `headers`, `urlcheck`, `ssh`. The
  nine protocol commands already carried it, so they needed **no CLI
  change**.
- **`README.md`**: the Usage section documents the new usage error and
  names the thirteen commands it applies to.
- **`tests/test_target.py`** (+40 tests): `url_port` returns the port, returns
  `None` for a URL without a port, raises `TargetSpecError` for a
  non-numeric port and for an out-of-range port, and the error is still a
  `ValueError`; all 14 protocol modules raise it for a URL with a bad port
  and still parse a valid port; the five probe-failure modules still report
  the **unchanged** error string; `web._parse_url` and `ssh._extract_port`
  raise it and still parse valid ports.
- **`tests/test_cli.py`** (+9 tests): exit code 2, an
  `Error: Invalid value for '--target': ...` message and the absence of a
  traceback for each of the thirteen commands and each of the bad-port
  targets; a single-line error; no transport helper is reached for a
  rejected target; the five probe-failure commands still exit 0 and still
  report the error in their JSON output; `s3` is unaffected; valid targets
  are still accepted and still report the requested port. The existing
  `test_library_modules_stay_free_of_click` guard now also covers `web.py`
  and `ssh.py`.

## Verification
- **Behavioural equivalence**: a 289-invocation harness (19 commands x 11
  target values, plus 3 output formats and `--help` per command) was
  captured twice from a pristine `git archive HEAD` tree in `/tmp` and once
  from the working tree, and compared byte for byte. **234 are
  byte-identical**; **43 are exactly the intended conversions** (13
  commands x 3 scheme-qualified bad-port targets, plus the 4 URL commands
  x a bare `host:notaport` target: stdout byte-identical, exit code 1 ->
  2, stderr changed from a raw traceback to a one-line usage error).
  **0 unexpected differences.** 12 invocations (all `s3`, which makes real
  AWS requests) are not reproducible even between the two baseline runs and
  were excluded; `s3.py` itself is untouched by this change.
- **Full suite**: **4129 passed, 1 skipped** (baseline 4080 -> 4129, 49
  new). No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports the same 48 pre-existing errors as the baseline; the rule set is
  identical once line numbers are normalised.
- **Manual**: all thirteen previously-crashing invocations now print
  `Error: Invalid value for '--target': Port could not be cast to integer
  value as 'notaport'` and exit 2 instead of dumping a traceback and
  exiting 1.

## Unresolved / deliberate non-changes
- The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`) still report an unusable target inside their JSON
  output with exit code 0, with the **unchanged** error string. That is
  their documented contract, so it was left alone.
- `s3` never reads the port of the target, so it is unaffected by a
  non-numeric port and keeps exiting 0.
- `fuzz` is **not** fixed: it does not go through `urllib.parse`'s port
  property, it hands the URL to `http.client`, which raises its own
  `InvalidURL`. That is a separate variant, see `NEXT_TASK.md`.
- The 14 `_normalize_target` copies are still not consolidated; only the
  port access changed. The copies differ in how they detect a bracketed
  IPv6 literal, so a consolidation would change behaviour and is a separate
  task.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.

## Next
See `HANDOFF_NEXT.md` / `NEXT_TASK.md` for the remaining follow-up task.
