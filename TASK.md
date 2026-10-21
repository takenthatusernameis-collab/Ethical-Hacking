# TASK

## Status: COMPLETE

The task of the previous handoff: add the ten socket commands that the session
before had given a `RuntimeError` net (ftp, smtp, netbios, scanner, dnsbrute,
mysql, mongodb, postgresql, mssql, oracle) to the permanent protocol sweep, and
put a regression test next to each module's own tests. Both parts are done, and
the sweep found three crash paths the previous handoff had listed as safe.

1. **The ten commands are in the permanent sweep.** `tests/test_protocol_hostile_sweep.py`
   grew from 119 to 256 checks: the six modules that take a
   `connector(host, port, request, timeout)` seam (netbios, mysql, mongodb,
   postgresql, mssql, oracle) are checked with the same two checks as the
   group above them (a hostile answer and a failing probe), the database
   modules are additionally checked on the socket they really use, and ftp,
   smtp, scanner and dnsbrute have their own checks.

2. **Three crash paths found and fixed** — the previous handoff had listed
   `netbios` as covered, but only its socket *send/receive* was: the
   connector seam raised, a socket that could not be created raised, and an
   answer of `None` (which the connector contract allows) raised a `TypeError`
   in the parser.

3. **Two more crash paths found in the survey of the rest of the command
   surface** — `dnsbrute` reported a `RuntimeError` of the dnspython paths in
   the raw path only; the dnspython zone transfer and the dnspython resolver
   still let it escape.

## What changed

### Source (`ethscan/`)

- `netbios.py`: `_send_recv` reports a failing connector (the way the database
  modules do: `connector error: <reason>`) and opens the socket inside the
  guarded block, so a socket that cannot be created is reported like any other
  transport failure. `run_netbios` reports a `TypeError` of the parser as a
  failed parse, the way it already reported a `ValueError`.
- `dnsbrute.py`: the dnspython zone transfer and the two dnspython resolvers
  report a `RuntimeError` like the raw socket path already did.

### Tests (`tests/`)

- `test_protocol_hostile_sweep.py` (137 new checks): the ten commands of the
  previous handoff.
- `test_netbios.py` (5), `test_dnsbrute.py` (4), `test_scanner.py` (2),
  `test_ftp.py` (2), `test_smtp.py` (1), `test_mysql.py` (1), `test_mongodb.py`
  (1), `test_postgresql.py` (1), `test_mssql.py` (1), `test_oracle.py` (1):
  the regression test of each module next to its own tests (19).

## What was actually verified

- The crash paths were reproduced **before** the fix: with the transport
  raising a `RuntimeError`, `netbios.run_netbios` raised (connector seam and
  socket creation) and an answer of `None` raised a `TypeError`; with the
  dnspython path stubbed, `dnsbrute._axfr_dnspython`, `dnsbrute.attempt_axfr`
  and `dnsbrute._resolve_label` raised. After the fix every one of them
  answers with a result.
- The new sweep test is meaningful: with the pre-fix sources restored, 2 of
  its checks fail with the `RuntimeError` escaping; with the fix they pass.
  The same holds for the 9 new module tests that lock in the source changes.
- The CLI was run against an unreachable target for every command of the
  sweep: `ethscan netbios|ftp|smtp|mysql|mongodb|postgresql|mssql|oracle
  --target 127.0.0.1` each reports its own error field and exits 0.
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **5032 passed, 48 skipped, 2 warnings** (the
  two warnings are the pre-existing `test_main.py` runpy ones; the baseline was
  4876 passed, 48 skipped).
- `git diff --check` -> clean.
- Nothing is committed (commit only if explicitly asked).

## What remains unresolved

- **Six commands still let a transport failure of an unnamed type escape**:
  `ping.run_ping`, `osdetect.run_osdetect`, `resolve.run_resolve`,
  `dns.run_dns`, `stale.run_stale` and `subdomains.run_subdomains`. The exact
  crash sites and the method are in "One precise next task" below.
- `trace.run_trace` is safe: its socket creation and its name lookup are both
  wrapped in `except Exception`.
- `dnsbrute` and `subdomains` still resolve a label through
  `ethscan/dns.py` (`resolve_a_records`, `resolve_aaaa_records`,
  `resolve_with_dnspython`) in the branch without dnspython; those helpers
  catch `(socket.timeout, socket.gaierror, OSError, ValueError)` and not a
  `RuntimeError`.

## Approaches that failed and why

- **The previous handoff's list of covered modules was wrong for `netbios`.**
  It reported the `RuntimeError` of the transport, but the `RuntimeError` of
  the *socket creation* and of the *connector* was outside the guarded block,
  and the `None` answer crashed the parser. A module is only safe on the paths
  that were exercised.
- **The sweep could not be written with one uniform check for the ten
  commands.** Their failure signals differ (an `error` field, a closed port,
  an error inside the zone-transfer entry), so the sweep asserts each module's
  own failure signal instead of a fixed wording.

## One precise next task

Give the six remaining commands the same net the ten commands of this session
got, and add them to the permanent sweep. The evidence is in "What remains
unresolved": with the transport seam raising a `RuntimeError`, these calls
raise instead of reporting it:

- `ping.run_ping("127.0.0.1")` -> `ethscan/ping.py:122` (`_try_create_raw_socket`).
- `osdetect.run_osdetect("127.0.0.1")` -> `ethscan/osdetect.py:123` (`_connect_tcp`).
- `resolve.run_resolve("example.com")` -> `ethscan/resolve.py:60` (`resolve_a_records`).
- `dns.run_dns("example.com")` -> `ethscan/dns.py:58` (`resolve_a_records`).
- `stale.run_stale("example.com")` -> `ethscan/stale.py:48` (`resolve_a_records`).
- `subdomains.run_subdomains("example.com")` -> `ethscan/subdomains.py:110`
  (`socket.gethostbyname`).

The method is the one used in this session: patch the transport seam to raise,
call the public `run_*`, assert the module's own failure field, add the
command to `tests/test_protocol_hostile_sweep.py` (a new group, because these
six have no connector seam: the sweep patches `socket.getaddrinfo`,
`socket.gethostbyname`, `socket.create_connection` or `socket.socket` in the
module itself), and put the regression test next to the module's own tests.
Keep the smallest reversible change (the crash becomes the module's documented
error signal; do not weaken an existing guard), and do not commit unless
explicitly asked.
