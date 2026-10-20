# TASK.md

Date: 2026-10-20T10:40:00Z
Status: the **hostile option sweep** of the CLI is finished. A sweep over
every string option and every file option of all 42 commands used to leak
**110 tracebacks**; it now leaks **none**, and the six root causes behind
them are fixed with regression tests.

## What changed

### 1. A target whose URL `urllib.parse` refuses (`--target 'http://[::1'`)
- **Root cause:** `urllib.parse.urlparse` raises a bare `ValueError`
  (`Invalid IPv6 URL`) for a URL whose authority holds an unmatched bracket
  (`http://[::1`, `http://example.com]`). The error is a `ValueError` and not
  an `OSError`, so the narrow `except` clauses of the library did not catch
  it and it reached the user as a raw traceback in **36 of the 42** target
  commands.
- **`ethscan/target.py`**: new `parse_url(url)` helper that parses a URL and
  re-raises the `ValueError` of urllib as a `TargetSpecError` (the message is
  kept). The library stays free of click.
- **39 modules** (33 of them only for the URL parsing, plus `cert`, `geo`,
  `mac`, `dnsbrute` and `whois` for the other fixes): every target
  normalizer parses its URL with `parse_url` instead of `urlparse`.
- **`ethscan/cli.py`**: the per-command decorator `_target_usage_errors` was
  replaced by a group class `_TargetGroup` that translates a `TargetSpecError`
  into the same click usage error for **every** command. The guarantee is now
  structural: a command that is added later cannot leak the error either.
- The target is now either refused (**exit 2**, one line
  `Error: Invalid value for '--target': Invalid IPv6 URL`) or reported as a
  failed probe (**exit 0**) by the modules whose contract is to do so.

### 2. An API base URL that `urllib` refuses (`--api-url 'not a url'`)
- **Root cause:** `urllib.request.Request` raises a bare `ValueError`
  (`unknown url type`) for a URL whose scheme it does not know, and the
  request was built **outside** the `try` block of the fetch helpers.
- **`ethscan/{cert,geo,mac}.py`**: the request is built inside the `try`
  block, so an unusable API base URL is reported like any other failed
  fetch (inside the output, **exit 0**).

### 3. A file option that points at something unusable
- **Root cause:** the three file options that were plain strings (`audit
  --file`, `hash --file`, `report --audit-file`) opened the file without
  checking it, so a missing file ended in a `FileNotFoundError` traceback.
  The options that already existed (`click.Path(exists=True, readable=True)`)
  accepted a **directory**, which `open()` refuses with an
  `IsADirectoryError` traceback.
- **`ethscan/cli.py`**: the three options became
  `click.Path(exists=True, readable=True, dir_okay=False)` and the 17
  existing file options got the missing `dir_okay=False`. A missing file or
  a directory is now a usage error (**exit 2**).

### 4. A WHOIS server that cannot be reached (`--server 'not a host'`)
- **Root cause:** the primary query of `ethscan/whois.py` connected to the
  server without catching the `socket.gaierror` / `ConnectionRefusedError` of
  a host that cannot be resolved (the recursive hop already caught them).
- **`ethscan/whois.py`**: the lookup reports a failed query (an `error` key,
  an empty `raw`) inside the output (**exit 0**); the markdown and the CSV
  format show the error as well.

### 5. An output path that cannot be written (`--out /tmp`)
- **Root cause:** every command wrote its report with a bare `open()`, so a
  directory, a path whose directory does not exist or a name the file system
  refuses ended in an `OSError` traceback (in 53 commands).
- **`ethscan/cli.py`**: new `_write_output()` helper reports an unusable
  output path as a usage error (**exit 2**). The `config` command keeps its
  own contract (**exit 1** with `Error writing output: ...`).

### 6. A nameserver whose label is too long (`--ns <300 characters>`)
- **Root cause:** the resolver encodes a host name as IDNA and raises a
  `UnicodeError` for a label that is too long. A `UnicodeError` is a
  `ValueError` and not an `OSError`, so it escaped the `except OSError` of
  the raw AXFR query.
- **`ethscan/dnsbrute.py`**: the query catches `ValueError` as well.

## Verification
- Full suite: **4342 passed, 1 skipped** (4328 before + 14 new tests).
- Ruff: the same **48** pre-existing errors, **no new ones**
  (`ruff check ethscan/ tests/`).
- `git diff --check`: clean.
- Sweep over every **string** option of every command
  (973 invocations): **0 leaked tracebacks** (110 before).
- Sweep over every **file** option of every command
  (225 invocations): **0 leaked tracebacks** (132 before).
- The 16 timeouts of the sweeps are the commands that probe a real host
  (`brute`, `recon`, `snmp`, `ssh`, `trace`), with or without a change.

## Remaining
- The 48 pre-existing ruff errors are unrelated and left alone.
- The `--ports` option (the plural form) is validated in every command that
  has it - checked in an earlier session, no change needed.
- A target that is not a usable host is still reported as a failed probe
  (**exit 0**) by the modules whose contract is to do so (`ftp`, `ldap`,
  `mac`, `memcached`, `mongodb`, `mssql`, `mysql`, `netbios`, `ntp`,
  `oracle`, `postgresql`, `redis`, `service`, `smb`, `smtp`, `snmp`).
  That contract is unchanged; only the crash is gone.
