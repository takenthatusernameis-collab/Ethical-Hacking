# HANDOFF_NEXT.md

## Summary
Executed the prior agent's assignment: a `--target` whose **port is not a
number** is now a clean click usage error (exit code 2, one-line message, no
traceback) in the thirteen commands that used to dump a traceback.

The prior session had already identified the defect and left a precise plan
in `NEXT_TASK.md`; the library side had not been touched, so every
`redis://host:notaport`-style invocation still dumped a
`ValueError: Port could not be cast to integer value as 'notaport'`
traceback and exited 1.

## Changes
- **`ethscan/target.py`**: new public helper `url_port(parsed)`. It returns
  the port of a parsed URL and re-raises the bare `ValueError` that
  `urllib.parse` raises for a non-numeric or out-of-range port as a
  `TargetSpecError`, **with the original message text unchanged**. The
  module still imports no click.
- **14 protocol modules** (`redis`, `memcached`, `ntp`, `snmp`, `ftp`,
  `ldap`, `netbios`, `smb`, `smtp`, `mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`): the single `port = parsed.port` access in each
  `_normalize_target` now calls `url_port(parsed)`. **Nothing else changed** -
  the parsers were not consolidated, as instructed, and the `host:` /
  bracketed-IPv6 edge cases keep their current behaviour.
- **`ethscan/web.py`** (`_parse_url`) and **`ethscan/ssh.py`**
  (`_extract_port`): the same one-line swap. The empty-host ->
  `localhost` mapping, the scheme handling and the lower-casing of the host
  are unchanged.
- **`ethscan/cli.py`**: the existing `_target_usage_errors` decorator is now
  also attached to `web`, `headers`, `urlcheck` and `ssh`. The nine
  protocol commands already carried it, so they needed **no CLI change**.
- **`README.md`**: the Usage section documents the new usage error.
- **`tests/test_target.py`** (+40 tests) and **`tests/test_cli.py`**
  (+9 tests).

### Design choice (the prior task asked for it to be stated)
The port access was **not** wrapped in a `try/except ValueError` at each of
the 16 call sites. Instead a single shared helper `url_port(parsed)` was
added to `ethscan/target.py`, next to the existing `TargetSpecError`.
Reasons: it keeps the "a bad port is an unusable target" rule in one place
instead of 16 copies of it; it keeps the *original* `ValueError` message
(the helper re-raises `str(exc)` verbatim), so the five modules that report
a failed probe keep the exact wording they report today; and the CLI still
has exactly one `except` clause, because `TargetSpecError` is a
`ValueError` subclass and is caught by the existing
`except ValueError` handlers in those five modules with no change at all.

The translation itself still lives in one place: `_target_usage_errors` in
`ethscan/cli.py`. No library module imports click - the existing
`test_library_modules_stay_free_of_click` guard was extended to cover
`web.py` and `ssh.py` so this cannot regress.

## Verification
- **Behavioural equivalence**: a 289-invocation harness (19 commands x 11
  target values, plus 3 output formats and `--help` per command) was
  captured **twice** from a pristine `git archive HEAD` tree in `/tmp` and
  once from the working tree, then compared byte for byte.
  **234 of 289 are byte-identical**; **43 are exactly the intended
  conversions** (13 commands x 3 scheme-qualified bad-port targets, plus
  the 4 URL commands x a bare `host:notaport` target: stdout byte-identical,
  exit code 1 -> 2, stderr changed from a raw traceback to a one-line usage
  error). **0 unexpected differences.** 12 invocations (all `s3`, which
  makes real AWS requests) are not reproducible even between the two
  baseline runs and were excluded from the comparison; `s3.py` is untouched
  by this change.
- **Full suite**: 4129 passed, 1 skipped (baseline 4080 -> 4129, 49 new).
  No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports the same 48 pre-existing errors as the baseline; the rule set is
  identical once line numbers are normalised.
- **Manual**: all thirteen previously-crashing invocations now print
  `Error: Invalid value for '--target': Port could not be cast to integer
  value as 'notaport'` and exit 2.

## Unresolved
- The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`) still report an unusable target inside their JSON
  output with exit code 0, with the **unchanged** error string. Intentional
  - their contract is "the probe failed", not "the option is invalid".
- `fuzz` still dies with `http.client.InvalidURL` for a bad port or a
  space in the target: it never touches `urllib.parse`'s port property, it
  hands the URL to `http.client`. Left alone deliberately - see
  `NEXT_TASK.md`.
- `s3` is unaffected: it never reads the port of the target.
- The 14 `_normalize_target` copies are still duplicated. They are not
  identical (some use `host.find("]:")`, some `host.endswith("]")`), so
  consolidating them is a separate refactor that would change behaviour for
  the `host:` and bracketed-IPv6 edge cases.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.
- The remaining raw-traceback clusters listed in `NEXT_TASK.md` were
  re-verified on this commit and still reproduce; they were deliberately not
  bundled into this change.

## Next agent task
Implement the "host contains a space or a control character" cluster
described in `NEXT_TASK.md`: `headers`, `web`, `fuzz`, `urlcheck` and `s3`
die with a raw
`http.client.InvalidURL: URL can't contain control characters. 'host name'`
traceback (exit 1) when the `--target` contains a space. Turn it into a
click usage error at the CLI boundary, mirroring the `_check_cidr` /
`CidrSpecError`, `url_port` / `TargetSpecError` and `_target_usage_errors`
patterns already established.
