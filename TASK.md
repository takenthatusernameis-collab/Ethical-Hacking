# TASK

Status: COMPLETE (dnspython + paramiko: an exception type the client library raises no longer crashes the command)

## What was done

This session swept the two client libraries the previous handoff left unchecked: **dnspython** and **paramiko**. Both are not installed in this environment, so every dnspython module's library path was dead code (`DNS_AVAILABLE = False`) and the paramiko path in `ssh.py` was dead code (`PARAMIKO_AVAILABLE = False`) until a fake library module was injected on `sys.path`.

A fake `dns` package whose `Resolver.resolve` raises one exception type was used to call every dnspython call site with `IndexError`, `AttributeError` and `KeyError`. Every call site whose guard was only `(dns.exception.DNSException, OSError, ValueError)` crashed — the exception escaped as a traceback through the public `run_*` command. The same happened for `dns.query.udp` (dnssec) and `dns.query.xfr` (dnsbrute AXFR). The fix, per the established template, is to turn the crash into the module's documented failure signal and add exactly the missing type to the guard.

### Guards changed (ethscan/)
`except (...)` gained `, IndexError, AttributeError, KeyError` at these sites:

| Module | Guard before | Guard after | Sites |
|---|---|---|---|
| `dns.py` | `DNSException, OSError, ValueError` | `..., IndexError, AttributeError, KeyError` | `resolve_with_dnspython` (107), `run_dns` custom-server (154) |
| `resolve.py` | `DNSException, OSError, ValueError` | `..., IndexError, AttributeError, KeyError` | `resolve_cname_records` (94), `resolve_ptr_records` (118), `resolve_with_dnspython` (138) |
| `subtake.py` | `DNSException, OSError, ValueError` | `..., IndexError, AttributeError, KeyError` | `resolve_a_records` (329), `resolve_aaaa_records` (353) |
| `subtake.py` | `..., IndexError` | `..., IndexError, AttributeError, KeyError` | `resolve_cname` (302) |
| `subdomains.py` | `..., TypeError, IndexError` | `..., TypeError, IndexError, AttributeError, KeyError` | `resolve_subdomain` (106) |
| `dnsbrute.py` | `DNSException, OSError, ValueError` | `..., IndexError, AttributeError, KeyError` | `_resolve_label` A (381), `_resolve_label` AAAA (390) |
| `dnsbrute.py` | `..., ValueError) as exc` | `..., ValueError, IndexError, AttributeError, KeyError) as exc` | `_axfr_dnspython` (312) |
| `dnssec.py` | `..., ValueError) as exc` | `..., ValueError, IndexError, AttributeError, KeyError) as exc` | `_query_dnskey_dnspython` (404), `_query_ds_dnspython` (436) |

The indexing answer-set sites (`subtake.resolve_cname`, `subdomains.resolve_subdomain`) already listed `IndexError` from the previous session; they were missing `AttributeError`/`KeyError` and now list them.

### paramiko (`ethscan/ssh.py`)
The paramiko host-key path is already wrapped in `except Exception`, so `paramiko.SSHException`, `paramiko.AuthenticationException` and `EOFError` are swallowed there. The stdlib path of `run_ssh` uses only `socket`/`struct`, so it cannot raise a paramiko type. Confirmed with a fake `paramiko` module raising each of the three types: `_get_host_key_info_paramiko` returns `None` in every case, and `run_ssh`'s stdlib path is unaffected.

### Tests added (next to each module's own tests)
- `tests/test_dns.py`: 3 parametrized (`IndexError`/`AttributeError`/`KeyError`) for `resolve_with_dnspython` and both `run_dns` dnspython paths.
- `tests/test_resolve.py`: 3 parametrized for `resolve_cname_records`, `resolve_ptr_records`, `resolve_with_dnspython`.
- `tests/test_subtake.py`: 3 parametrized for `resolve_cname`, `resolve_a_records`, `resolve_aaaa_records`.
- `tests/test_subdomains.py`: 3 parametrized for `resolve_subdomain`.
- `tests/test_dnsbrute.py`: 3 parametrized for `_resolve_label`, `_axfr_dnspython`, `attempt_axfr`.
- `tests/test_dnssec.py`: 3 parametrized for `_query_dnskey_dnspython`, `_query_ds_dnspython`, `run_dnssec`.
- `tests/test_ssh.py`: 3 tests for `SSHException`, `AuthenticationException`, `EOFError` on `_get_host_key_info_paramiko`.

### Verification
- Before the fix, every one of the above call sites raised the injected type through the public command (reproduced with the fake `dns`/`paramiko` module).
- After the fix, each returns the module's documented failure signal and does not raise.
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **4635 passed, 48 skipped** (was 4584).
- `git diff --check` -> clean.
- Only the 13 intended files are modified; nothing else changed.

## What remains unresolved
Nothing from this task.

## Approaches that failed and why
None for this task. The method from the previous session (fake library module raising one exception type) worked for every candidate type.

## One precise next task
See `NEXT_TASK.md` and `HANDOFF_NEXT.md`. The baseline is clean: the fixes, the tests and the verification are in the working tree but **not committed** (commit only if explicitly asked).
