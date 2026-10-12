# Next Task for Next Agent

## Current State

The `--output-format csv` output is now **complete for ALL commands** (previously 13 commands had the option in their CLI decorators but lacked CSV formatters, function signatures, and routing logic).

### Completed in this session

**CSV formatters added to 12 modules** (hash already had one, but with a field-name bug):
| Command | Module | New function |
|---------|--------|--------------|
| `fuzz` | `ethscan/fuzz.py` | `format_fuzz_report_csv()` — columns: target,base_url,path,status_code,error,is_finding |
| `resolve` | `ethscan/resolve.py` | `format_resolve_report_csv()` — columns: target,normalized,record_type,record_value |
| `dnsbrute` | `ethscan/dnsbrute.py` | `format_dnsbrute_report_csv()` — columns: target,domain,subdomain,hostname,a_records,aaaa_records,resolved |
| `tls` | `ethscan/tls.py` | `format_tls_report_csv()` — columns: target,host,port,probe_type,probe,supported,negotiated,error |
| `urlcheck` | `ethscan/urlcheck.py` | `format_urlcheck_report_csv()` — long-format: section,key,value |
| `osdetect` | `ethscan/osdetect.py` | `format_osdetect_report_csv()` — columns: target,host,port,probe_type,connected,response,flags_observed,error |
| `trace` | `ethscan/trace.py` | `format_trace_report_csv()` — columns: target,hop,ip,host,response_type,rtt_ms,reached_destination |
| `ping` | `ethscan/ping.py` | `format_ping_report_csv()` — columns: target,ip,sequence,rtt_ms,ttl,response_type,error |
| `recon` | `ethscan/recon.py` | `format_recon_report_csv()` — long-format: module,field,value |
| `cert` | `ethscan/cert.py` | `format_cert_report_csv()` — columns: target,domain,ip,subdomain |
| `dnssec` | `ethscan/dnssec.py` | `format_dnssec_report_csv()` — columns: target,domain,validated,dnskey_success,dnskey_count,ds_success,ds_count |
| `mac` | `ethscan/mac.py` | `format_mac_report_csv()` — columns: target,mac,oui,vendor,cached,offline_fallback,error |
| `hash` (check mode) | `ethscan/hash.py` | `format_check_report_csv()` — columns: password,digest,algorithm,salt,pepper,iterations,computed,match,error |

**cli.py changes:**
- Imported all 13 new CSV formatters
- Fixed `fuzz` command: added missing `output_fmt` parameter (was raising `TypeError: fuzz() got an unexpected keyword argument 'output_fmt'` for ANY `--output-format` value — a runtime crash)
- Fixed routing for all 13 commands to use the pattern:
  ```python
  chosen_format = output_fmt if output_fmt is not None else fmt
  if chosen_format == "json": ...
  elif chosen_format == "csv": ...
  else: ...  # markdown
  ```
- Fixed the shadowed/dead `hash` command (line ~503, overridden by `hash_cmd` registered later with `name="hash"`) to also accept `output_fmt` and route to CSV
- Fixed pre-existing bug in `format_hash_report_csv`: read `entry.get("digest")` but the actual result field is `hash`; now reads `entry.get("hash") or entry.get("digest")` and uses per-entry `algorithm`

**Tests added (67 new: 40 unit + 27 CLI):**
- `tests/test_fuzz.py` — 3 CSV unit tests
- `tests/test_resolve.py` — 3 CSV unit tests
- `tests/test_dnsbrute.py` — 3 CSV unit tests
- `tests/test_tls.py` — 2 CSV unit tests
- `tests/test_urlcheck.py` — 3 CSV unit tests
- `tests/test_osdetect.py` — 2 CSV unit tests
- `tests/test_trace.py` — 2 CSV unit tests
- `tests/test_ping.py` — 2 CSV unit tests
- `tests/test_recon.py` — 3 CSV unit tests
- `tests/test_cert.py` — 2 CSV unit tests
- `tests/test_dnssec.py` — 2 CSV unit tests
- `tests/test_mac.py` — 2 CSV unit tests
- `tests/test_cli.py` — 41 CLI integration tests (3 per command: `--output-format csv`, `--output-format csv --out`, deprecated `--format csv` alias; plus 5 for `hash` including check-mode CSV)

### Verification
- `python -m pytest -q` -> **2067 passed, 1 skipped** (1997 baseline + 67 new + 3 urlcheck unit = 2067)
- End-to-end: every command now supports `--output-format csv`, deprecated `--format csv` alias, and `--out <file>` with CSV content
- Default format (no flag) remains JSON
- Live runs confirmed correct CSV headers for all 13 commands

## Suggested next task

**Add `--output-format csv` to the remaining commands that still only expose `--format` (no `--output-format` option).** Run `python -m ethscan <cmd> --help` and check for commands lacking the `--output-format` option. Candidates from the earlier audit: `service`, `vuln`, `scan`, `audit`, `report`, `subdomains`, `subtake`, `whois`, `headers`, `dns`, `ssl`, `brute`, `wifi`, `geo`, `cve`, `cidr`, `radix`, `config`, `jwt`, `completion`, `validate`, `nmap`, `stale`, `ssh`, `s3` — these already HAVE `--output-format` with csv support (verified working). Re-audit with a script to confirm none are missed:
```python
# Check every @cli.command block for "--output-format" and output_fmt param
```
If all 36 commands already have it, the CSV work is fully complete and the next agent should pick a new feature from TASK.md's suggested-next-task list (e.g., a new recon module or a new command).

## Requirements for next agent
- Follow existing module conventions (`run_*`, `format_*_report_json`, `format_*_report_markdown`, `format_*_report_csv`).
- Register commands/options in `ethscan/cli.py` with `--target`, `--format`, `--output-format`, `--out`.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an optional dependency is already declared in `requirements.txt` (use a graceful `*_AVAILABLE` flag pattern as in `dns.py`/`dnsbrute.py`).
- Do not manually commit or push; the outer workflow handles checkpointing.
