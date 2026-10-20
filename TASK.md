# TASK.md

Date: 2026-10-20T13:40:00Z
Status: the **content** of the input files of the CLI is hardened. A file
whose content is hostile (bytes that are not valid UTF-8, a null byte, a
line that holds a space, a JSON file that is not JSON, an XML file that is
not XML) used to leak **7 different tracebacks** in **19 commands**; it now
leaks **none**.

The path of a file option was already covered (a missing file or a directory
is a usage error, see `tests/test_file_option_sweep.py`). The content of the
file was not.

## What changed

### 1. A file that holds bytes that are not valid UTF-8
- **Root cause:** every text file was read with `open(path, "r",
  encoding="utf-8")`, which raises a `UnicodeDecodeError` for a byte that is
  not valid UTF-8. The error is a `ValueError` and not an `OSError`, so it
  reached the user as a raw traceback in **14 commands** (`audit`, `brute`,
  `config`, `cve`, `dnsbrute`, `fuzz`, `hash`, `nmap`, `osdetect`, `radix`,
  `recon`, `report`, `s3`, `stale`, `subdomains`, `subtake`, `urlcheck`,
  `vuln`).
- **`ethscan/fileio.py`** (new): the shared readers of the input files.
  `read_text()` and `read_lines()` decode leniently (the bytes that cannot be
  decoded are replaced), `load_json()` reads a JSON file, `is_utf8()` reports
  whether a file holds valid UTF-8.
- **Every text loader** now uses the shared reader: `brute`, `fuzz`, `hash`,
  `stale`, `subdomains`, `report`, `config` and the two readers of the CLI
  (`audit --file`, `radix --cidr-file`).
- The **standard input** of the commands that read one (`audit`, `hash`,
  `jwt`) is read leniently as well (`ethscan/cli.py`: `_read_stdin_text`).
- A file that holds **credentials** (`--file`, `--user-file`, `--pass-file`,
  `--audit-file`) is refused instead, because its content cannot be read
  without changing the credentials it holds: a mangled password would be
  hashed silently (`ethscan/cli.py`: `_require_utf8`, a usage error).

### 2. A JSON file that is not JSON (or that is not an object)
- **Root cause:** the JSON files (`--services-file`, `--tls-file`,
  `--ssl-file`, `--banners-file`) were read with a bare `json.load()`, so a
  file that is not JSON raised a `json.JSONDecodeError` (a traceback), and a
  file that holds a list or a string raised an `AttributeError` when the
  command called `.get()` on it.
- **`ethscan/cli.py`**: the new `_load_json_file()` reports a file that is not
  valid JSON (or that does not hold an object) as a usage error (**exit 2**)
  that names the option. The `cve` command reported the same problem before
  (on stderr, exit 0) and now uses the same report as the other commands.

### 3. An Nmap XML file that is not XML
- **Root cause:** `ET.fromstring()` raises a `ParseError` for a file that is
  not XML, and `int(port_elem.get("portid", 0))` raised a `ValueError` for a
  port whose id is not a number.
- **`ethscan/nmap.py`**: `parse_nmap_xml()` raises the new `NmapParseError`,
  which the CLI reports as a usage error (**exit 2**). A port whose id is not
  a number (or is out of range) is skipped, so one bad port does not abort
  the report of the other ports.

### 4. A wordlist entry that cannot be requested or resolved
- **Root cause:** `http.client.InvalidURL` (raised for a path that holds a
  space or a control character) derives from `HTTPException` and not from
  `ValueError`, so it escaped the `except` of `fuzz_path` (a traceback in
  `fuzz` and `urlcheck`). `socket.gethostbyname()` refuses a name that holds
  a null byte with a `TypeError`, which escaped the `except` of
  `resolve_subdomain` (a traceback in `subdomains`).
- **`ethscan/fuzz.py`**: `fuzz_path()` catches `http.client.HTTPException`
  and reports the path as a failed probe, the same way `ethscan/s3.py`
  already did.
- **`ethscan/subdomains.py`**: `resolve_subdomain()` catches the `TypeError`
  and reports the label as unresolved.

## Verification

- Full suite: **4484 passed, 45 skipped** (before: 4439 passed, 10 skipped;
  the new sweep adds 18 cases and skips the 35 commands that have no input
  file option).
- Ruff: `ruff check ethscan/ tests/` → **All checks passed** (the 3 errors
  that the previous session left in `tests/test_file_option_sweep.py` are
  fixed as well).
- `git diff --check`: clean.
- The new permanent sweep `tests/test_file_content_sweep.py` walks every
  input file option of every command (18 commands, 4 hostile contents each)
  and asserts that no traceback leaks. Before the fix **all 18 commands
  failed**; now all of them pass.
- The standard input of `audit`, `hash` and `jwt` is read leniently (the
  traceback is gone).

## Remaining

- The `cve` command still reports a file it cannot read inside its own
  output when it is used as a library (`ethscan/cve.py`: the `notes` entry
  "Failed to read services file"). The CLI reports it as a usage error
  before the module runs, so the note is only reachable for a direct API
  user.
- The options that hold a *value* read from the environment or from the
  config file were not touched by this task; the config file already
  reports a value of the wrong type as a usage error.
