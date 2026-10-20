# TASK.md

Date: 2026-10-20T00:40:00Z
Status: the **out-of-range port in the bare `host:port` form** is fixed
for **all 14 commands** that parse such a target, not only for the seven
the previous session found. The same expression had a second crash
(`str.isdigit()` accepts text that `int()` refuses), which is fixed too.
A third, related surface was found and measured but deliberately left
alone: the explicit `--port` option (next task, `HANDOFF_NEXT.md`).

## What changed
- **`ethscan/target.py`**
  - `check_port(port)` now accepts the port as a **number or as the text**
    of a number (`int | str`), converts the text itself and raises
    `TargetSpecError` for text that `int()` refuses. The range check
    (0-65535) and the message `Port out of range 0-65535` are unchanged.
- **`ethscan/{redis,ldap,memcached,netbios,ntp,smb,snmp}.py`**
  (completed from the previous session, which had left them without
  tests): the hand-parsed port of the bare `host:port` form now goes
  through `check_port()`.
- **`ethscan/{ftp,smtp,mysql,mongodb,postgresql,mssql,oracle}.py`** (new)
  - the same seven modules parse the port of a bare `host:port` target by
    hand as well; they now call `check_port()` too. Before the change they
    did **not** crash, they silently connected to the **wrong port**:
    `socket.getaddrinfo()` wraps a port above 65535, so
    `example.com:99999` was probed on port **34463**.
- All 14 modules pass the port text to `check_port()` instead of calling
  `int()` at the call site.

## Verification
- `python -m ethscan <cmd> --target 'example.com:99999'` for the 9 commands
  with a usage-error contract (`redis`, `ldap`, `memcached`, `netbios`,
  `ntp`, `smb`, `snmp`, `ftp`, `smtp`) -> **exit 2**, one-line
  `Error: Invalid value for '--target': Port out of range 0-65535`.
- The same target for the 5 commands with a probe-failure contract
  (`mysql`, `mongodb`, `postgresql`, `mssql`, `oracle`) -> **exit 0** with
  `"error": "Port out of range 0-65535"` in the output, exactly like the
  scheme-qualified form of the same target.
- `python -m ethscan redis --target 'example.com:²'` (a superscript digit:
  `str.isdigit()` accepts it, `int()` refuses it) -> **exit 2**,
  `Error: Invalid value for '--target': Invalid port '²'` (before the
  change: a raw `ValueError` traceback).
- The valid forms are unchanged: `host`, `host:1234`, `host:65535`,
  `[::1]:443` and the scheme forms parse to the same values in all 14
  modules.
- Full suite: **4272 passed, 1 skipped** (4215 before + 57 new tests).
  Ruff: the same **48** pre-existing errors, no new ones.
- Sweep: 20 target-consuming commands x 12 hostile targets = **240
  invocations, 0 leaked tracebacks**.

## Remaining
- The explicit **`--port` option** is still not range-checked: 9 commands
  leak an `OverflowError` traceback (`ldap`, `memcached`, `redis`, `smb`,
  `netbios`, `ntp`, `snmp`, `trace`, `whois`) and 12 commands silently
  probe the wrapped port. Evidence and the suggested fix are in
  `HANDOFF_NEXT.md`.
- The backlog of the wider sweep is unchanged and still reproduces: a host
  of only dots (`UnicodeError`, 13 commands), a percent-encoded NUL
  (`InvalidURL`, 4 commands) and a URL with userinfo (`InvalidURL`, 4
  commands). See `HANDOFF_NEXT.md`.
- The 48 pre-existing ruff errors are unrelated and left alone.
