# TASK.md

Date: 2026-10-20T08:20:00Z
Status: the **explicit `--port` option** is range-checked and, for the first
time, **covered by tests** (the fix itself was already in the code, but
untested and undocumented). The three classes of the wider sweep that were
left in the backlog - a **percent-encoded control character** in the host, a
**userinfo part** in the authority and a **host that is not a valid host
name** - are fixed as well, so the sweep over all 42 commands and 11
hostile targets no longer leaks a single traceback.

## What changed

### 1. The `--port` option (the task of the previous session)
- The 24 port options of the CLI (`--port`, `--tcp-port`, `--trace-port`,
  `--whois-port`) were already declared as `click.IntRange(0, 65535)`.
  This session **verified** that and added the missing regression tests:
  - `tests/test_cli.py`: every command with a port option refuses
    `65536`, `99999`, `-1` and `99999999999999999999` with **exit 2** and
    the single line
    `Error: Invalid value for '--port': 99999 is not in the range 0<=x<=65535.`
  - an invariant test that **every** port option of the CLI is an
    `IntRange(0, 65535)` that does not clamp, so a command added later
    cannot slip through without a range check;
  - a tripwire test that no connection is started for a rejected value
    (`socket.socket.connect`, `connect_ex`, `sendto` and
    `socket.getaddrinfo` are replaced);
  - the same check for a port that comes from the **config file**
    (`commands: {redis: {port: 99999}}`), which click validates as well;
  - a test that a valid port is still used for the probe (`0`, `1`, `65535`).
- No source change was needed for this part.

### 2. A percent-encoded control character in the host (`--target '%00'`)
- **Root cause:** `urllib.request` decodes the percent escapes of the host
  before it uses it (`urllib/request.py`: `self.host = unquote(self.host)`),
  so a host that looks harmless in its raw form carries a control character
  in the host that reaches `http.client`, which refuses it with an
  `InvalidURL` (not a `ValueError`, so it escaped the library).
- **`ethscan/target.py`**: `check_target_host()` now checks the host twice -
  as it is written and after its percent escapes are decoded. The message
  (`Target host contains a space or control character`) is unchanged.
- `web`, `headers`, `urlcheck` and `fuzz` now report the target as a usage
  error (**exit 2**).

### 3. A userinfo part in the authority (`--target 'http://user:pass@example.com'`)
- **Root cause:** `urllib.request` keeps the userinfo in the host it
  connects to, and `http.client` then reads the text after the last colon
  of that host as the port (`InvalidURL: nonnumeric port: 'pass@example.com'`).
- **`ethscan/target.py`**: new `strip_userinfo(url)` helper that drops the
  userinfo and keeps the scheme, the host, the port, the path, the query and
  the fragment exactly as they are.
- **`ethscan/web.py`** (`fetch_headers`) and **`ethscan/fuzz.py`**
  (`_normalize_base_url`) use it, the way the whois, mongodb and ssh modules
  already used the host without the userinfo.
- The target is now scanned as `example.com` instead of crashing.

### 4. A host that is not a valid host name (`--target '....'`)
- **Root cause:** the resolver encodes a host name as IDNA and raises a
  `UnicodeError` for a name with an empty label. `UnicodeError` is a
  `ValueError` and not an `OSError`, so the narrow `except` clauses of the
  library did not catch it.
- **`ethscan/{cert,geo,mac,ping}.py`**: `_resolve_host()` catches
  `ValueError` as well.
- **`ethscan/dnssec.py`**: `_resolve_nameservers()` catches `ValueError`.
- **`ethscan/{scanner,service}.py`**: the connection catches `ValueError`.
- **`ethscan/{osdetect,ssh}.py`**: the connection error catches `ValueError`.
- **`ethscan/{smtp,ftp}.py`**: the connection failure catches `ValueError`.
- Such a host is now reported the way **every host that cannot be resolved**
  is reported: as a failed probe inside the output (**exit 0**), not as a
  usage error.

## Verification
- Full suite: **4319 passed, 1 skipped** (4272 before + 47 new tests).
- Ruff: the same **48** pre-existing errors, **no new ones**
  (`ruff check ethscan/ tests/`).
- `git diff --check`: clean.
- Sweep: **42 commands x 11 hostile targets = 462 invocations, 0 leaked
  tracebacks** (the 11 timeouts of the sweep are the commands that probe a
  real host: `brute`, `snmp`, `ssh` and `trace` need more than 15 s in this
  sandbox, with or without a change).
- **Mutation checks** (the fix was reverted and the tests were run again):
  - reverting the three port options to `type=int` fails 6 of the 8 new
    port tests and reproduces the original
    `OverflowError('connect(): port must be 0-65535.')`;
  - reverting the decoded-host check and the userinfo strip fails 15 of the
    new tests (4 of them at the CLI level);
  - every new test of the malformed-host class fails without the
    `ValueError` in the `except` clauses.

## Remaining
- The **`--timeout` option is not range-checked** is now **done**: all 43
  `--timeout` CLI options were changed from `type=float` to
  `click.FloatRange(min=0.001)` (`ethscan/cli.py`), so `--timeout -1` and
  `--timeout 0` are refused by click before the command runs (exit 2, single
  `Error:` line), fixing the traceback in `ldap`, `memcached`, `netbios`,
  `ntp`, `redis`, `smb`, `snmp`, `trace`, `whois` and the `BlockingIOError`
  in `whois`. Four regression tests were added to `tests/test_cli.py`.
  Evidence and the fix notes are in `HANDOFF_NEXT.md`.
- The 48 pre-existing ruff errors are unrelated and left alone.
- The `--ports` option (the plural form) is validated in every command that
  has it - checked in this session, no change needed.
