# Next task for the next agent

## Completed: `postgresql` module unit tests (`tests/test_postgresql.py`)

Added 3 new unit tests to `tests/test_postgresql.py`, raising the test count from 44 to 47 and
improving the test-to-module line ratio from 0.80 (388/485) to 1.15 (560/485). This lifted the
module from having one of the lowest ratios to having above-parity test coverage.

### What changed
- `tests/test_postgresql.py`: added tests for previously untested scenarios:
  - Authentication-required scenarios (MD5 password authentication)
  - Unknown probe handling (should not perform startup probe)
  - Formatter handling of None host (from invalid targets)

### New test functions

#### `test_run_postgresql_auth_required` (new: 1 test)
- Tests run_postgresql when server returns authentication requiring credentials (MD5Password)
- Verifies accessible=True, correct auth type parsing, and appropriate findings generation

#### `test_run_postgresql_unknown_probe` (new: 1 test)
- Tests run_postgresql with unknown probe (e.g., "foobar")
- Verifies that no network calls are made and accessible=False is returned

#### `test_format_postgresql_report_with_none_host` (new: 1 test)
- Tests all formatters (JSON, Markdown, CSV) handle None host correctly
- Verifies None host displays as "N/A" in markdown, empty field in CSV
- Checks that error messages are properly included in all formats

### Verification
- `python -m pytest tests/test_postgresql.py -q` -> **47 passed** (44 baseline + 3 new)
- `python -m pytest -q` -> **3199 passed**, 2 failed, 1 skipped
  - The 2 failures are pre-existing and unrelated to this change:
    `tests/test_dns.py::test_run_dns_workers_sequential` and
    `tests/test_dns.py::test_run_dns_workers_parallel`. They fail in isolation
    (running only those two tests reproduces them) because the sandbox's DNS
    does not resolve `MX` records for `example.com`, so the MX resolver is
    never invoked and the expected third call / result is missing.
    `git diff --stat` confirms only `tests/test_postgresql.py` was modified.

## Suggested next task

**Add unit tests for the `web` module (`ethscan/web.py`).**

It now has the lowest test-to-module line ratio among all modules at **0.67**
(208 test lines / 308 module lines). Its public surface follows patterns similar to
other protocol modules, making the proven test patterns transferable:

### Functions to test:
- `_parse_url` (HTTPS/HTTP URLs, default ports, error cases)
- `fetch_headers` (success, connection refused, timeout, invalid host, SSL errors)
- `check_security_headers` (present headers, missing headers, header values)
- `check_information_disclosure` (present info headers, missing info headers)
- `check_ssl_configuration` (valid certs, expired certs, self-signed, protocol errors)
- `run_web_checks` (success, failure, timeout, invalid target, custom checks)
- Formatters: JSON, Markdown, CSV output with various data combinations

### Constraints:
- Follow existing test conventions: use pytest, mock network calls where appropriate
- Test both success and failure scenarios for network functions
- After adding tests, run `python -m pytest -q` to confirm no regressions
  (expect the same 2 pre-existing `test_dns.py` MX failures to remain)

(End of file - total 94 lines)