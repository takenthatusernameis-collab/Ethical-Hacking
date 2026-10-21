# NEXT TASK

## Status: COMPLETE (socket-command transport failures reported + cve error + permanent protocol sweep)

The task assigned by the previous handoff is done and committed in HEAD `baf31c4` (plus this session's cve top-level error field):

1. **Socket commands report transport failures.** `ssl.run_ssl`, `tls.run_tls`, `whois.run_whois` and `service.run_service` guard `RuntimeError` from `socket.create_connection`/`socket.socket` and report it through their own failure field instead of raising. `service` uses its existing empty-results convention.

2. **cve reports a failed NVD lookup as its own error.** `run_cve` now returns a top-level `"error"` field (`"NVD lookup failed for <cve_id>: <reason>"`) in addition to the existing note, so a user can tell an unreachable NVD API from "no CVEs matched" even when built-in findings are present.

3. **Permanent protocol sweep.** `tests/test_protocol_hostile_sweep.py` covers redis, memcached, ntp, ldap, smb2, smb, snmp, ssh, ssl, tls, whois and service; `tests/test_http_hostile_sweep.py` covers the ten HTTP-facing commands.

`python -m ruff check ethscan/ tests/` passes; `python -m pytest tests/` passes (4876 passed, 48 skipped). CLI verified: `ethscan ssl --target 127.0.0.1:9` reports `"error": "[Errno 111] Connection refused"` and exits 0.

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash into the module's documented error signal.
- Add regression tests next to the module's own tests; keep the permanent sweeps in the repository.
- Do not commit unless explicitly asked.

## One precise next task (optional extension)

The assigned theme is complete with no pending item. If extending coverage, survey the remaining socket-based commands (`ftp`, `smtp`, `netbios`, `ping`, `trace`, `scan`, `brute`, `dnsbrute`, `mysql`, `mongodb`, `postgresql`, `mssql`, `oracle`) for transport failures of an unnamed type that escape instead of being reported, then add guards + sweep coverage using the ssl/tls/whois/service method (patch the transport seam to raise `RuntimeError`, call the public `run_*`, assert the module's own failure field, add to `tests/test_protocol_hostile_sweep.py`). Do not commit unless explicitly asked.
