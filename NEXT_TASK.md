# Next Task for Next Agent

## Current State

The `--output-format csv` output for the `geo` command is **complete and verified**:
- `format_geo_report_csv()` implemented in `ethscan/geo.py`
- `--output-format [json|markdown|csv]` option registered in `ethscan/cli.py`
- Function signature updated to accept `output_fmt` parameter
- CSV routing logic implemented (`chosen_format = output_fmt if output_fmt is not None else fmt`)
- All 43 unit tests in `tests/test_geo.py` pass
- All 27 CLI integration tests for geo pass
- End-to-end verified: `python -m ethscan geo --target 8.8.8.8 --output-format csv` works correctly

## Remaining Work: CSV Output for Other Commands

**52 CLI integration tests failing** because 9 commands have the `--output-format [json|markdown|csv]` option defined in their decorators but lack:
1. `output_fmt` parameter in function signature
2. CSV formatter function in their module
3. Import and routing logic in `cli.py`

### Commands Needing CSV Formatters (Priority based on failing tests)

| Command | Module | Missing |
|---------|--------|---------|
| `subdomains` | `ethscan/subdomains.py` | `format_subdomains_report_csv()`, function signature, imports |
| `whois` | `ethscan/whois.py` | `format_whois_report_csv()`, function signature, imports |
| `ssl` | `ethscan/ssl.py` | `format_ssl_report_csv()`, function signature, imports |
| `headers` | `ethscan/headers.py` | `format_headers_report_csv()`, function signature, imports |
| `web` | `ethscan/web.py` | `format_web_report_csv()`, function signature, imports |
| `wifi` | `ethscan/wifi.py` | `format_wifi_report_csv()`, function signature, imports |
| `jwt` | `ethscan/jwt.py` | `format_jwt_report_csv()`, function signature, imports |
| `config` | `ethscan/config.py` | `format_config_report_csv()`, function signature, imports |
| `completion` | `ethscan/completion.py` | `format_completion_report_csv()`, function signature, imports |

### Implementation Pattern (follow existing commands like `dns`, `geo`, `vuln`)

For each command:
1. **Add CSV formatter** in module (e.g., `ethscan/subdomains.py`):
   ```python
   import csv
   import io

   def format_subdomains_report_csv(data: Dict[str, object]) -> str:
       output = io.StringIO()
       writer = csv.writer(output)
       writer.writerow(["subdomain", "hostname", "ip", "resolved"])
       for result in data.get("all_results", []):
           writer.writerow([
               result.get("subdomain", ""),
               result.get("hostname", ""),
               result.get("ip") or "",
               "true" if result.get("ip") else "false",
           ])
       return output.getvalue().rstrip("\r\n")
   ```

2. **Update `cli.py`**:
   - Import the CSV formatter
   - Add `output_fmt: Optional[str]` to function signature
   - Use `chosen_format = output_fmt if output_fmt is not None else fmt`
   - Route to CSV formatter when `chosen_format == "csv"`

3. **Add unit tests** in `tests/test_<module>.py`:
   - Basic CSV output
   - Empty results
   - Missing/None field handling
   - CSV escaping (commas, quotes)

4. **CLI integration tests** in `tests/test_cli.py` already exist and will pass once implementation is complete

### Commands That May Not Need CSV Output
- `config` - outputs configuration state (YAML/JSON more appropriate)
- `completion` - outputs shell completion scripts (plain text)

Consider removing `--output-format csv` from these two commands if CSV doesn't make sense.

## Verification
After implementation:
- `python -m pytest -q` should show 1932+ passing (1880 current + ~52 fixed)
- Each command should support `--output-format csv` and `--format csv` (deprecated alias)
- `--out` should work with CSV output
- Default format (no flag) should remain JSON

## Suggested Next Task (After CSV Formatters)
Add `--output-format csv` to remaining commands that don't have the option yet:
- `fuzz`, `trace`, `osdetect`, `urlcheck`, `recon`, `resolve`, `dnsbrute`, `cert`, `mac`, `cidr`, `radix`, `ssh`, `s3`, `hash`