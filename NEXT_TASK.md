# NEXT TASK

## Status: COMPLETE (probe-block net, mac vendor text, two new crash classes)

The two open items of the previous handoff are closed, and two new crash classes were found and fixed while checking the rest of the input surface.

1. **Probe-block net** (open item 1, a behaviour change): `run_redis`, `run_memcached`, `run_ntp`, `run_ldap`, `run_smb2`/`run_smb`, `run_snmp`, `run_ssh` and `run_dnssec` now wrap their probe block. A failure inside the probe is reported through the module's own field (`results["error"]`, `result["error"]`, and for `dnssec` the `dnskey`/`ds` error, which the report reads as `DNSKEY query failed: dnssec probe failed: ...`). The permanent check is `tests/test_protocol_hostile_sweep.py`: a hostile answer is answered with a result and a failing probe is reported, for every one of those modules.
2. **Mac vendor text** (open item 2, a one-line close-out): `tests/test_mac.py` now covers the `errors="replace"` behaviour — a body with a byte that is not UTF-8 yields the replaced text as the vendor instead of a failed fetch.
3. **New: a document that nests too deeply for its parser.** The JSON parser raises a `RecursionError` and the YAML parser raises one too, and no guard named that type, so four commands crashed with a raw traceback: `ethscan vuln --services-file <deep .json>`, `ethscan cve --services-file <deep .json>`, `ethscan config --config <deep .yaml>` and `ethscan jwt --token <deep segment>`. Fixed at the source (`fileio.load_json` -> `ValueError`), in `config.load_config` (-> `_parse_error`), in `cve._fetch_cve_data` (-> `None`) and in `jwt._decode_json_segment` (-> `None`).
4. **New: a number with more digits than Python converts.** `int()` refuses more than 4300 digits, so a banner in a `--services-file` crashed `ethscan vuln` with a `ValueError` traceback. `vuln._version_tuple` now reads such a version as no version, so it matches no range.

`python -m ruff check ethscan/ tests/` passes; `python -m pytest tests/` passes (4758 passed, 48 skipped).

## One precise next task

The HTTP-facing commands still let an unexpected transport failure escape. With `urllib.request.urlopen` raising a type that is not an `OSError` (a `RuntimeError`, for instance):

- **raise** instead of reporting: `web.run_web_checks`, `fuzz.run_fuzz`, `headers.run_headers`, `urlcheck.run_urlcheck` (the last two call `web.fetch_headers`);
- **report it**: `cert.run_cert`, `cve.run_cve`, `geo.run_geo`, `mac.run_mac`, `ssl.run_ssl`, `tls.run_tls`, `whois.run_whois`, `stale.run_stale`, `service.run_service`.

The protocol commands no longer raise, because of the net this session added. Extend the permanent sweep (`tests/test_protocol_hostile_sweep.py`, or a new `tests/test_http_hostile_sweep.py`) with the same two checks for the HTTP commands — a hostile body is answered with a result, and a failing transport is reported through the module's own field — and decide per module whether the failure is reported or raised. The bodies are already known to be clean: ten hostile bodies (a truncated response, a lying `Content-Length`, a chunked body, a body that is not HTTP, a deeply nested JSON, ...) against eight HTTP commands produced no crash.

## Constraints
- Keep the smallest reversible change (turn the crash into the module's documented error signal; do not weaken an existing guard).
- Add regression tests next to the module's own tests, and keep the permanent sweeps in the repository (the long hostile sweep of the session that finished the CLI's hostile-option work lives outside the repository, because it needs a per-invocation timeout and takes about twenty minutes).
- The `ftp` and `web`/`cve`/`subtake` fixes are the template: the crash becomes the module's own failure signal, and the guard gains exactly the type that was missing.
- Do not commit unless explicitly asked; the working tree holds the changes but nothing is committed.
