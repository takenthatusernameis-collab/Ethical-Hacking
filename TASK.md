# TASK

## Status: COMPLETE

The task of the previous handoff: extend the permanent sweep to the HTTP-facing commands, and decide per module whether an unexpected transport failure is reported instead of raised. All three parts are done, and the sweep found two crash paths the previous handoff had listed as safe.

1. **The four commands that raised now report** — `web.run_web_checks`, `fuzz.run_fuzz`, `headers.run_headers` and `urlcheck.run_urlcheck` answer a failing transport with a result that carries the reason.
2. **Two more crash paths found and fixed** — `cve.run_cve` and `subtake.run_subtake` crashed on a failing transport too, on the paths the previous session's probe did not reach (a banner that matches a known product, a CNAME that matches a takeover signature). The previous handoff listed both as "report it"; that was only true for the paths that do not reach the API.
3. **A permanent sweep for the HTTP surface** — `tests/test_http_hostile_sweep.py`: ten HTTP-facing commands, eight hostile bodies and a failing transport, checked for every command.

## What changed

### Source (`ethscan/`)

**The HTTP commands** (the crash becomes the module's own failure signal):

- `web.py`: `fetch_headers` never raises. It returns a `FetchedHeaders` — a plain mapping of lowercase header names to values that carries the reason of a failure in its `error` attribute — so the reason travels with the headers to every caller. `run_web_checks` puts that reason in its own `error` field, and the JSON, Markdown and CSV reports show it. Before this, a target that could not be reached was indistinguishable from a target with no security headers: both showed "0/7 present".
- `headers.py`: `run_headers` reports the same reason in its own `error` field; the Markdown and CSV reports show it.
- `fuzz.py`: `fuzz_path` reports a failure of an unnamed type in the `error` field of that path, the way it already reported the failures it knew.
- `cve.py`: `_fetch_cve_data` answers a failure of an unnamed type with the module's own signal for a failed lookup (`None`), like `cert`, `geo` and `mac` already did.
- `subtake.py`: `check_http_fingerprint` answers a failure of an unnamed type with `None`, the way it already answered the failures it knew; `run_subtake` reports a label whose probe failed in that label's result, the way `s3.run_s3` already reported a failed bucket probe.
- `s3.py`: `check_bucket_public` reports a failure of an unnamed type in its own `error` field (`run_s3` already guarded the probe, so the command did not crash).
- `urlcheck.py`: the report shows the `error` of the web section.

### Tests (`tests/`)

- `test_http_hostile_sweep.py` (new, 98 checks): ten HTTP-facing commands (web, headers, fuzz, urlcheck, cert, geo, mac, s3, cve, subtake) against eight hostile bodies and a failing transport. A hostile body is answered with a result and never with a traceback; a failing transport is reported through the command's own failure field.
- `test_web.py`, `test_headers.py`, `test_fuzz.py`, `test_urlcheck.py`, `test_cve.py`, `test_subtake.py`, `test_s3.py`: the regression test of each module next to its own tests (10 tests).

## What was actually verified

- The crash paths were reproduced **before** the fix: with `urllib.request.urlopen` raising a `RuntimeError`, `web.run_web_checks`, `fuzz.run_fuzz`, `headers.run_headers` and `urlcheck.run_urlcheck` raised. Two more raised as well, on the paths the previous handoff had listed as safe: `cve.run_cve` (with a `--services-file` whose banner matches a known product) and `subtake.run_subtake` (with a CNAME that matches a takeover signature). After the fix every one of them answers with a result.
- The new sweep test is meaningful: with the pre-fix sources restored, 10 of its checks fail with the `RuntimeError` escaping (`web`, `headers`, `fuzz`, `urlcheck`, `cve`, `subtake`); with the fix they pass.
- The CLI was run against an unreachable target: `ethscan web --target http://127.0.0.1:9/` prints `"error": "header fetch failed: <urlopen error [Errno 111] Connection refused>"` in the JSON report, the Markdown report and the CSV report; `ethscan headers` and `ethscan urlcheck` report the same; `ethscan fuzz` reports the error per path.
- Ten real-socket hostile answers (a garbled status line, a lying `Content-Length`, a truncated body, a broken chunked body, a body that nests too deeply, binary bytes, an empty answer) against the seven commands that talk to a socket produced no crash.
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **4866 passed, 48 skipped, 2 warnings** (the two warnings are the pre-existing `test_main.py` runpy ones; the baseline was 4758 passed, 48 skipped).
- `git diff --check` -> clean.
- Nothing is committed (commit only if explicitly asked).

## What remains unresolved

- **Four socket-based commands still let a transport failure of an unnamed type escape**: `ssl.run_ssl`, `tls.run_tls`, `whois.run_whois` and `service.run_service` raise a `RuntimeError` from `socket.create_connection` / `socket.socket` instead of reporting it. Their guards name the types they know (`(ssl.SSLError, OSError, ValueError)`, `(socket.gaierror, socket.timeout, ConnectionRefusedError, OSError)`, ...), but they have no net, and the permanent protocol sweep does not cover them. `stale.run_stale` is safe (its guards are already broad).
- **`cve.run_cve` still reports a failed NVD lookup only as a missing entry.** A lookup that failed and a lookup that found nothing both end up as "no CVE matched", and the built-in findings hide it. The command needs an error of its own for a failed lookup.
- `tests/test_file_option_sweep.py` hit its 5-second per-invocation timeout once for `recon --out /tmp` and `s3 --out ...` while the whole suite was running. In this session `tests/test_file_content_sweep.py::test_every_input_file_survives_hostile_content[s3]` hit the same 5-second timeout once in a full run and passed in 2.8 s in isolation and 3.2 s on the pristine sources: the `s3` command resolves its endpoint over DNS, and the timeout is pre-existing.

## Approaches that failed and why

- **The handoff's list of "safe" HTTP commands was wrong for two of them.** `cve` and `subtake` were listed as reporting a failed transport, but the probe that established it never reached the API lookup of `cve` (no service banner matched) and never reached the fingerprint probe of `subtake` (no CNAME matched). A command is only safe on the paths that were exercised.
- **A dict subclass was needed to carry the reason of a failure out of `web.fetch_headers`.** The helper is the seam that `run_web_checks`, `run_headers` and the tests replace, so it cannot change its return type without breaking them, and a plain `{}` carries no reason. `FetchedHeaders` is still a plain mapping (`headers == {}` holds, `dict(headers)` works), so every caller that treats the headers as a dict keeps working.

## One precise next task

Give the four socket-based commands the same probe-block net the protocol commands got, and add them to the permanent protocol sweep. The evidence is in "What remains unresolved": with `socket.create_connection` / `socket.socket` raising a `RuntimeError`, `ssl.run_ssl`, `tls.run_tls`, `whois.run_whois` and `service.run_service` raise instead of reporting it, while `redis`, `memcached`, `ntp`, `ldap`, `smb`, `snmp`, `ssh` and `dnssec` report it through their own field (the net added in the session before this one). The method is the one used in that session: patch the transport seam to raise, call the public `run_*`, and assert the module's own failure field; then add the command to `tests/test_protocol_hostile_sweep.py`. Keep the smallest reversible change (the crash becomes the module's documented error signal; do not weaken an existing guard), add the regression test next to the module's own tests, and do not commit unless explicitly asked.
