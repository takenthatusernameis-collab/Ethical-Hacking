# NEXT TASK

## Status: COMPLETE (HTTP transport failures reported, permanent HTTP sweep)

The task of the previous handoff is closed, and the sweep it asked for found two more crash paths that the previous handoff had listed as safe.

1. **The four commands that raised now report.** `web.run_web_checks`, `fuzz.run_fuzz`, `headers.run_headers` and `urlcheck.run_urlcheck` answer a transport failure of an unnamed type with a result that carries the reason, instead of letting it escape as a traceback.
2. **New: `cve.run_cve` and `subtake.run_subtake` crashed too.** The previous handoff listed both as "report it", but that was only true for the paths the earlier probe did not reach: a `--services-file` whose banner matches a known product reaches the NVD lookup of `cve`, and a CNAME that matches a takeover signature reaches the fingerprint probe of `subtake`. Both now report. `s3.check_bucket_public` raised too (the command already guarded it); it now reports as well.
3. **New: the permanent HTTP sweep.** `tests/test_http_hostile_sweep.py` checks ten HTTP-facing commands against eight hostile bodies and a failing transport.

`python -m ruff check ethscan/ tests/` passes; `python -m pytest tests/` passes (4866 passed, 48 skipped).

## One precise next task

Give the four socket-based commands the same probe-block net the protocol commands got, and add them to the permanent protocol sweep.

With `socket.create_connection` / `socket.socket` raising a `RuntimeError` (a transport failure of a type the guard does not name):

- **raise** instead of reporting: `ssl.run_ssl`, `tls.run_tls`, `whois.run_whois`, `service.run_service`;
- **report it**: `redis.run_redis`, `memcached.run_memcached`, `ntp.run_ntp`, `ldap.run_ldap`, `smb.run_smb2`/`run_smb`, `snmp.run_snmp`, `ssh.run_ssh`, `dnssec.run_dnssec` (the net the session before this one added), and `stale.run_stale` (its guards are already broad).

The method is the one used in that session: patch the transport seam to raise, call the public `run_*`, and assert the module's own failure field, then add the command to `tests/test_protocol_hostile_sweep.py`. A second, smaller item: `cve.run_cve` still reports a failed NVD lookup only as a missing entry, so a user cannot tell an unreachable API from a product with no CVE — the command needs an error of its own for a failed lookup.

## Constraints
- Keep the smallest reversible change (turn the crash into the module's documented error signal; do not weaken an existing guard).
- Add regression tests next to the module's own tests, and keep the permanent sweeps in the repository (the long hostile sweep of the session that finished the CLI's hostile-option work lives outside the repository, because it needs a per-invocation timeout and takes about twenty minutes).
- The `ftp` and `web`/`cve`/`subtake` fixes are the template: the crash becomes the module's own failure signal, and the guard gains exactly the type that was missing.
- Do not commit unless explicitly asked; the working tree holds the changes but nothing is committed.
