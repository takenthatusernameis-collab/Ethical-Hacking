# HANDOFF_NEXT.md

## Summary
The **`s3` bracketed-IPv6 crash is fixed**. `python -m ethscan s3
--target '[::1]:443'` used to die with a raw traceback
(`http.client.InvalidURL: nonnumeric port: '1.s3.amazonaws.com'`, exit
1). It now exits 0 and reports every candidate as a failed probe inside
the normal JSON/Markdown/CSV output.

The same change also fixed a **second crash of the same class** that the
handoff had not recorded: a hostile `--region` (`--region 'a b'`)
produced the identical `http.client.InvalidURL` traceback.

No `s3` usage error was introduced: for `s3` a malformed or unusable
target is a probe failure, not an invalid option, so the failure is
reported in the result (`error` field) and the command exits 0.

## What changed
### `ethscan/s3.py`
1. **`_bucket_name_problem(bucket_name) -> str | None`** (new helper).
   An S3 bucket name is a DNS-compliant label: 3-63 characters of
   lowercase letters, digits, dots and hyphens, starting and ending with
   a letter or a digit, without adjacent periods and not formatted as an
   IPv4 address. The helper returns a short description of the problem,
   or `None` when the name is valid.
2. **`check_bucket_public()`**:
   - a name that cannot be an S3 bucket name is reported as
     `error: "Invalid bucket name: <reason>"` and returns **before** the
     DNS lookup and the HTTP request (no network traffic at all);
   - `http.client.HTTPException` (e.g. `InvalidURL`, `UnknownProtocol`)
     is caught next to `HTTPError` / `URLError` / `OSError` and reported
     in `error`. `InvalidURL` derives from `HTTPException` and **not**
     from `OSError`, which is why it used to escape the `except` clause
     and reach the user as a traceback;
   - the `urllib.request.Request(...)` construction moved inside the
     `try` block.
3. **`run_s3()`**:
   - the worker wrapper catches any exception of a probe and turns it
     into a failed probe result (`error: "<Type>: <message>"`), so a
     single unusable candidate can no longer abort the report of all the
     other candidates;
   - a note is added when **no** derived candidate is a valid bucket
     name: `"None of the 77 derived bucket names is a valid S3 bucket
     name."`.

### Decisions that were made (the handoff asked for them explicitly)
1. **Which bucket names are usable.** Option (b) of the handoff was
   chosen: the candidates are **not** silently filtered out, every
   candidate keeps its place in the report and carries an explicit
   `error`. Dropping them would have (a) hidden the entries of an
   explicit `--wordlist`, (b) changed the meaning of
   `candidates_tested`, and (c) produced the misleading note "No bucket
   candidates could be derived from the target." for a target that did
   produce candidates. A summary note tells the user what happened.
2. **Where a failed probe is reported.** Inside the result dict, in the
   `error` field, exactly like `HTTPError` / `URLError` / `socket.
   timeout` / `OSError` already were. **Not** a click usage error: for
   `s3` a malformed or unresolvable target is a probe failure.

## Verification
- `python -m ethscan s3 --target '[::1]:443'` -> exit 0, no stderr, JSON
  with 77 results, every `error` = "Invalid bucket name: contains
  characters that are not allowed in a bucket name", `dns_resolved` is
  `null`, no request is sent.
- `python -m ethscan s3 --target '[::1]:443' --format markdown` and
  `--format csv` -> exit 0, same data, the note is rendered in the
  "Notes" section.
- `python -m ethscan s3 --target example.com --region 'a b'` -> exit 0
  (before the fix: exit 1 + `InvalidURL` traceback), every probe reports
  "URL can't contain control characters.".
- `python -m ethscan s3 --target example.com --timeout 2` -> exit 0, DNS
  still resolved, probe failures still reported in `error`: the normal
  path is unchanged.
- Full suite: **4215 passed, 1 skipped** (4207 before + 8 new tests).
- Ruff: **48 errors, the same pre-existing ones**, no new ones (the
  blind `except Exception` in the worker carries `# noqa: BLE001` so the
  baseline does not grow).
- Sweep of every `--target` command with `''`, `'host name'`,
  `'no-such-host.invalid'` and `'[::1]:443'`: **0 leaked tracebacks**
  (168 invocations).

## Next task (bounded, high-value): a port out of range in the bare `host:port` form

### Evidence
`--target example.com:99999` still dies with a raw traceback in seven
commands:

```
$ python -m ethscan redis --target 'example.com:99999'
  File ".../ethscan/redis.py", line 193, in _send_recv
    sock.connect((host, port))
OverflowError: connect(): port must be 0-65535.
EXIT=1
```

Affects: `redis`, `ldap`, `memcached`, `netbios`, `ntp`, `smb`, `snmp`
(7 commands, same traceback in each).

The **same** target with a scheme is already handled correctly:

```
$ python -m ethscan redis --target 'http://example.com:99999'
Error: Invalid value for '--target': Port out of range 0-65535
EXIT=2
```

### Root cause
The seven modules share one `_normalize_target` shape (e.g.
`ethscan/redis.py:33`):

- target **with** a scheme -> `url_port(parsed)` (`ethscan/target.py:52`)
  -> `urlparse` raises `ValueError("Port out of range 0-65535")` ->
  `url_port` re-raises it as `TargetSpecError` -> the CLI turns it into
  a usage error (exit 2). **Already correct.**
- target **without** a scheme -> the port is parsed by hand, e.g.
  `ethscan/redis.py:61-65`:

  ```python
  elif host and ":" in host and "]" not in host:
      base, _, rest = host.rpartition(":")
      if rest.isdigit():
          host = base
          port = port or int(rest)      # <-- no range check
  ```

  `int("99999")` is accepted, and the value reaches `socket.connect()` /
  `socket.sendto()`, which raise `OverflowError` (an `OSError`
  subclass, but raised at connect time, far from the parser).

The same shape is repeated in `ethscan/ldap.py:152-159`,
`ethscan/memcached.py:57-64`, `ethscan/netbios.py:135-142`,
`ethscan/ntp.py:48-55`, `ethscan/smb.py:188-195`,
`ethscan/snmp.py:136-143`.

### Suggested fix shape
Add one shared helper next to `url_port` in `ethscan/target.py`, e.g.

```python
def check_port(port: int) -> int:
    """Raise ``TargetSpecError`` when a port is outside 0-65535."""
```

and call it in the hand-written `host:port` branch of the seven
`_normalize_target` functions, so the bare form reports the same usage
error as the scheme form (exit 2, "Error: Invalid value for '--target':
Port out of range 0-65535") instead of an `OverflowError` traceback.

Verify with `python -m ethscan <cmd> --target 'example.com:99999'` ->
exit 2, no traceback, for all seven commands, and that
`--target 'example.com:65535'` and `--target 'host:port'` keep working.
Add a library test per module and one CLI test that loops over the seven
commands.

### Backlog found by the same sweep (not the next task)
Reproduce with the script in `NEXT_TASK.md` (15 hostile inputs x 42
commands). Two further classes of leaked traceback remain:

| input | commands | error |
|---|---|---|
| `--target '....'` | `cert`, `dnssec`, `ftp`, `geo`, `mac`, `osdetect`, `ping`, `report`, `scan`, `service`, `smtp`, `ssh`, `vuln` (13) | `UnicodeError: label empty or too long` (the idna encoding of a host made only of dots) |
| `--target '%00'` | `fuzz`, `headers`, `urlcheck`, `web` (4) | `InvalidURL: URL can't contain control characters. '\x00'` (the percent-encoded NUL is decoded after `check_target_path` has inspected the raw path) |
| `--target 'http://user:pass@example.com'` | `fuzz`, `headers`, `urlcheck`, `web` (4) | `InvalidURL: nonnumeric port: 'pass@example.com'` (the userinfo is not stripped before the host is used) |

Both are the same shape as the tasks above: the target is accepted by
the parser and refused later by the network layer. The established
convention applies - report it as a usage error (exit 2) when the target
is unusable, otherwise as a probe failure inside the output.

## Unchanged / deliberate non-changes
- `_build_bucket_candidates` still derives the same candidates in the
  same order; only the probe decides that a name is unusable. The
  documented "original case kept" behaviour of the wordlist entries is
  unchanged.
- `s3._normalize_target` still lower-cases the target and keeps the
  IPv6 form (`_normalize_target("https://[::1]/path") == "::1"`).
- `s3` keeps its `_target_usage_errors` decorator, but an unusable
  bucket name is still **not** a usage error.
- The 48 pre-existing ruff errors are unrelated and left alone.
- The 14 `_normalize_target` copies remain duplicated (separate refactor;
  they differ on `host:` / bracketed-IPv6 edge cases).
