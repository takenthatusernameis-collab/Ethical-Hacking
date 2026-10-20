# NEXT TASK

## Status: COMPLETE (dnspython + paramiko guard sweep)

The previous task closed the FTP/HTTP parser sweep. This session swept the two remaining client libraries:

1. **dnspython** (`ethscan/dns.py`, `dnssec.py`, `resolve.py`, `subtake.py`, `subdomains.py`, `dnsbrute.py`): a fake `dns` package whose `Resolver.resolve` (and `dns.query.udp` / `dns.query.xfr`) raises `IndexError`, `AttributeError` or `KeyError` was injected on `sys.path`. Every call site whose guard was `(dns.exception.DNSException, OSError, ValueError)` crashed through the public `run_*` command. All 14 guard sites now list `IndexError, AttributeError, KeyError` (the two answer-set indexing sites already listed `IndexError` and now also list `AttributeError, KeyError`).
2. **paramiko** (`ethscan/ssh.py`): the paramiko host-key path is already `except Exception`; `SSHException`, `AuthenticationException` and `EOFError` were injected via a fake `paramiko` module and `_get_host_key_info_paramiko` returns `None` in every case. The stdlib path of `run_ssh` uses only `socket`/`struct` and cannot raise a paramiko type.

Tests were added next to each module's own tests (7 test files). `python -m ruff check ethscan/ tests/` passes; `python -m pytest tests/` passes (4635 passed, 48 skipped).

## One precise next task (candidate 2 — a behaviour change)

`run_smtp()` is the only `run_<module>()` of a protocol module that wraps its probe block in an `except` net. The other protocol modules without one are `run_redis`, `run_memcached`, `run_ntp`, `run_ldap`, `run_smb2`/`run_smb`, `run_snmp`, `run_dnssec` and `run_ssh`. They are clean today, but a future parser bug in them crashes the command instead of being reported. Adding the net (the `smtp` template: `except Exception as exc: results["error"] = f"probe failed: {exc}"`) is a behaviour change, so it was deliberately left out of this session's small fix.

## One precise next task (candidate 3 — a one-line close-out)

The commit before the netbios fix (`91ce9aa`, empty message) made `cert`, `cve`, `geo`, `jwt` and `mac` decode their HTTP responses with `errors="replace"`. The only behavioural difference is `mac`: a body with a byte that is not UTF-8 now yields the replaced text as the vendor instead of a failed fetch. There is no test for it. A single regression test for the `mac` vendor text is enough to close it.

## Constraints
- Keep the smallest reversible change (turn the crash into the module's documented error signal; do not weaken an existing guard).
- Add regression tests next to the module's own tests.
- The `ftp` and `web`/`cve`/`subtake` fixes are the template: the crash becomes the module's own failure signal, and the guard gains exactly the type that was missing.
- Do not commit unless explicitly asked; the working tree holds the changes but nothing is committed.
