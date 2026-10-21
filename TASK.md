# TASK

## Status: COMPLETE

Three parts, all verified in this session:

1. **The `run_*` probe-block net** (open item 1 of the previous handoff) — the eight protocol modules that lacked it now report a failure through their own field instead of letting it escape, with a permanent sweep test that locks the behaviour in.
2. **The `mac` vendor-text regression test** (open item 2 of the previous handoff) — the behaviour change made by `91ce9aa` is now covered by a test.
3. **Two new crash classes found while checking the rest of the input surface** — a document that nests too deeply for its parser, and a number with more digits than Python converts. Both crashed the CLI with a raw traceback; both are fixed and covered.

## What changed

### Source (`ethscan/`)

**Probe-block net** (the `smtp` template: the crash becomes the module's own failure signal):

- `redis.py` (`run_redis`), `memcached.py` (`run_memcached`), `ntp.py` (`run_ntp`), `ldap.py` (`run_ldap`), `smb.py` (`run_smb2` and `run_smb`), `snmp.py` (`run_snmp`): `results["error"] = f"<module> probe failed: {exc}"`.
- `ssh.py` (`run_ssh`): a new `except Exception` after the existing `(OSError, ValueError)` handler: `result["error"] = f"ssh probe failed: {exc}"`.
- `dnssec.py` (`run_dnssec`): the module has no top-level error field, so the failure lands in `dnskey_result["error"]` and `ds_result["error"]`; the report then reads `DNSKEY query failed: dnssec probe failed: ...`.

**A document that nests too deeply for its parser** (the parser raises `RecursionError`, which no guard named):

- `fileio.py` (`load_json`): a file whose JSON nests too deeply is now an unusable value (`ValueError`), so every caller of `load_json` is fixed at once — the CLI's `_load_json_file` (`--services-file`, `--tls-file`, `--ssl-file`, `--banners-file`), `cve.run_cve`'s services file, and the `cert`/`cve`/`geo`/`mac` cache readers.
- `config.py` (`load_config`): a config file whose YAML nests too deeply is now a `_parse_error`, like a file with broken YAML.
- `cve.py` (`_fetch_cve_data`): a body whose JSON nests too deeply is a failed lookup (`None`).
- `jwt.py` (`_decode_json_segment`): a segment whose JSON nests too deeply is an unreadable segment (`None`).

**A number with more digits than Python converts** (`int()` refuses more than 4300 digits):

- `vuln.py` (`_version_tuple`): such a version is read as no version, so it matches no range instead of crashing the command. It was reached through a banner in a `--services-file`.

### Tests (`tests/`)

- `test_protocol_hostile_sweep.py` (new, 115 checks): every hostile answer is answered with a result, never a traceback, and a failure inside the probe block is reported through the module's own field, for the seven modules with a connector seam (redis, memcached, ntp, ldap, smb2, smb, snmp) plus the SSH and DNSSEC variants.
- `test_mac.py`: the vendor text of a body that is not UTF-8.
- `test_fileio.py`, `test_config.py`, `test_jwt.py`, `test_cve.py`, `test_vuln.py`, `test_cli.py`: the regression tests for the two new crash classes (module level and command level).
- `test_file_content_sweep.py`: a deeply nested JSON is now one of the hostile file contents, so the permanent sweep covers every command that reads a file.

## What was actually verified

- The four nesting crash paths and the huge-digit crash path were reproduced **before** the fix as CLI tracebacks: `ethscan vuln --services-file <deep .json>`, `ethscan cve --services-file <deep .json>`, `ethscan config --config <deep .yaml>`, `ethscan jwt --token <deep segment>`, `ethscan vuln --services-file <banner with 5000 digits>`. After the fix each reports a usage error, a parse error or an empty result, with no traceback.
- The new sweep test is meaningful: with the pre-net `redis.py` restored, `test_probe_failure_is_reported_not_raised[redis]` fails with the `RuntimeError` escaping; with the net it passes.
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **4758 passed, 48 skipped, 2 warnings** (the two warnings are the pre-existing `test_main.py` runpy ones; the baseline was 4635 passed, 48 skipped).
- `git diff --check` -> clean.
- Nothing is committed (commit only if explicitly asked).

## What remains unresolved

- The HTTP-facing commands still let an unexpected transport failure escape: with `urllib.request.urlopen` raising a type that is not an `OSError` (a `RuntimeError`, for instance), `web.run_web_checks`, `fuzz.run_fuzz`, `headers.run_headers` and `urlcheck.run_urlcheck` raise instead of reporting it. The protocol commands no longer do, because of the net added this session. The bodies themselves are clean: ten hostile bodies (a truncated response, a lying `Content-Length`, a chunked body, a body that is not HTTP, a deeply nested JSON, ...) against eight HTTP commands produced no crash.
- `tests/test_file_option_sweep.py` hit its 5-second per-invocation timeout once for `recon --out /tmp` and `s3 --out ...` while the whole suite was running. Both pass in isolation and in a re-run of the full suite; they are DNS-dependent commands, and the timeout is pre-existing.

## Approaches that failed and why

- **Fuzzing the protocol parsers found nothing.** A random corpus (1500 payloads per module, plus structured hostile answers) against redis, memcached, ntp, ldap, smb2, smb and snmp produced no crash: the parsers are careful. The bug this session found was the *digit limit* of `int()`, which a random corpus never reaches (4300 consecutive digits). The finding came from reading the conversion sites, not from fuzzing.
- **The `socket.connect` path never raises `UnicodeError` for a malformed host.** `socket.getaddrinfo` raises it for a host that cannot be IDNA-encoded, but `socket.connect` reports a `gaierror` (an `OSError`) instead, so the `UnicodeError` guard that `smtp`/`mac`/`ssh` carry cannot be reached that way.

## One precise next task

Extend the permanent sweep to the HTTP-facing commands, and decide the same question the protocol modules got this session: should an unexpected transport failure be reported instead of raised? The evidence is in "What remains unresolved" above: `web.run_web_checks`, `fuzz.run_fuzz`, `headers.run_headers` and `urlcheck.run_urlcheck` raise a `RuntimeError` from `urlopen`, while `cert`, `cve`, `geo`, `mac`, `ssl`, `tls`, `whois`, `stale` and `service` report it. The method is the one used this session: patch `urllib.request.urlopen` to raise, call the public `run_*`, and assert the module's own failure signal. Add the checks to the permanent sweep test, keep the smallest reversible change, and do not commit unless explicitly asked.
