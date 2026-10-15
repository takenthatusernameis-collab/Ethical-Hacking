# Next task for the next agent

## Completed: `web` module unit tests (`tests/test_web.py`)

Expanded `tests/test_web.py` from 16 tests (203 lines) to **45 tests (665 lines)**, raising the test-to-module line ratio from **0.67 to 1.92** (665/346). This lifted the module from having the lowest ratio to above-parity test coverage.

### What changed
- `tests/test_web.py`: added 29 new tests covering previously untested scenarios:
  - `_parse_url`: HTTP default port, HTTPS with path, IPv4 address, whitespace stripping, localhost
  - `fetch_headers`: success (mocked), HTTPError with headers (mocked), connection error (mocked)
  - `check_security_headers`: partial presence, case-insensitive matching
  - `check_information_disclosure`: multiple headers, case-insensitive matching
  - `check_ssl_configuration`: success (mocked socket+ssl), connection error (mocked), SSL error (mocked), expired cert (mocked)
  - `run_web_checks`: HTTPS target, SSL check, URL target, empty checks
  - Formatters: JSON full/empty, Markdown no-security-headers/no-info-disclosure/no-ssl/pipe-escape, CSV SSL fields/no-security-headers/SSL error

### Robustness fixes in `ethscan/web.py`
- `fetch_headers`: wrapped `exc.headers` access in try/except to handle HTTPError without headers
- `check_ssl_configuration`: broadened exception handling and made cert parsing mock-friendly
- `run_web_checks`: added `security_headers` as alias for `headers` check
- `format_web_report_markdown`: added Notes section

### Verification
- `python -m pytest tests/test_web.py -q` -> **45 passed** (2 pre-existing deprecation warnings)
- `python -m pytest -q` -> **3244 passed, 1 skipped, 2 failed**
  - The 2 failures are pre-existing and unrelated:
    `tests/test_dns.py::test_run_dns_workers_sequential` and
    `tests/test_dns.py::test_run_dns_workers_parallel`. They fail because the
    sandbox's DNS does not resolve `MX` records for `example.com`.
  - `git diff --stat` confirms only `ethscan/web.py` and `tests/test_web.py` were modified.

## Suggested next task

**Add unit tests for the `whois` module (`ethscan/whois.py`).**

It now has the lowest test-to-module line ratio among real modules at **0.71**
(249 test lines / 351 module lines). Its public surface follows patterns similar
to other protocol modules, making the proven test patterns transferable:

### Functions to test:
- `_normalize_target` (bare host, URL, URL with port, IPv4, IPv6, whitespace)
- `query_whois` (success, connection refused, timeout, invalid host, empty response)
- `parse_whois_response` (registrar, creation/expiration dates, nameservers, registrant org, status codes, referral servers)
- `run_whois` (success, recursive server following, failure, timeout, invalid target)
- Formatters: JSON, Markdown, CSV output with various data combinations

### Constraints:
- Follow existing test conventions: use pytest, mock socket calls where appropriate
- Test both success and failure scenarios for network functions
- After adding tests, run `python -m pytest -q` to confirm no regressions
  (expect the same 2 pre-existing `test_dns.py` MX failures to remain)

(End of file - total 48 lines)