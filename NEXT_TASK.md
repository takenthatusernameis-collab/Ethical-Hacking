# NEXT TASK

## Status: COMPLETE (socket commands in the permanent sweep + the netbios/dnsbrute crash paths)

The optional extension of the previous `NEXT_TASK.md` is done: the commands
that were surveyed (ftp, smtp, netbios, scanner, dnsbrute, mysql, mongodb,
postgresql, mssql, oracle) are now covered by the permanent protocol sweep,
and the survey found three crash paths that the earlier handoff had listed as
safe.

1. **The permanent sweep covers the ten commands.**
   `tests/test_protocol_hostile_sweep.py` grew from 119 to 256 checks. The six
   modules that take a `connector(host, port, request, timeout)` seam (netbios,
   mysql, mongodb, postgresql, mssql, oracle) are checked with the same two
   checks as the group above them (a hostile answer, a failing probe), the
   database modules are additionally checked on the socket they really use, and
   ftp, smtp, scanner and dnsbrute have their own checks.

2. **The crash paths the earlier handoff listed as safe are fixed.**
   `netbios` raised on a failing connector, on a socket that could not be
   created and on an answer of `None`; `dnsbrute` raised on a `RuntimeError`
   of the dnspython zone transfer and of the dnspython resolver.

3. **The regression test of each module sits next to its own tests** (19
   tests in ten files).

`python -m ruff check ethscan/ tests/` passes; `python -m pytest tests/`
passes (5032 passed, 48 skipped; the baseline was 4876 passed, 48 skipped).
The CLI reports its own error field and exits 0 for every command of the
sweep.

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash into the module's documented error signal.
- Add regression tests next to the module's own tests; keep the permanent sweeps in the repository.
- Do not commit unless explicitly asked.

## One precise next task (optional extension)

Six commands still let a transport failure of an unnamed type escape:
`ping`, `osdetect`, `resolve`, `dns`, `stale` and `subdomains`. The exact
crash sites are listed in `TASK.md` ("One precise next task"): with the
transport seam raising a `RuntimeError`, these calls raise instead of
reporting it:

- `ping.run_ping` -> `ethscan/ping.py:122`
- `osdetect.run_osdetect` -> `ethscan/osdetect.py:123`
- `resolve.run_resolve` -> `ethscan/resolve.py:60`
- `dns.run_dns` -> `ethscan/dns.py:58`
- `stale.run_stale` -> `ethscan/stale.py:48`
- `subdomains.run_subdomains` -> `ethscan/subdomains.py:110`

`trace.run_trace` is safe (both its socket creation and its name lookup are
wrapped in `except Exception`).

The method is the one used in the last session: patch the transport seam to
raise, call the public `run_*`, assert the module's own failure field, add the
command to `tests/test_protocol_hostile_sweep.py` (a new group: these six have
no connector seam, so the sweep patches the socket function in the module
itself), and put the regression test next to the module's own tests. Do not
commit unless explicitly asked.
