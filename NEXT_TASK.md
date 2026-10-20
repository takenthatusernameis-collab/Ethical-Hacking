# NEXT TASK

## Status: COMPLETE

The hostile **file content** task assigned by the previous agent has been
completed. Every input file of every command (a wordlist, a credential list,
a list of domains, a list of CIDR networks, a JSON report of another
command, an Nmap XML file) is now read without leaking a traceback, and the
standard input of the commands that read one is read leniently as well.

## What was done

- **New module `ethscan/fileio.py`**: the shared readers of the input files
  (`read_text`, `read_lines`, `load_json`, `is_utf8`). The text readers
  decode leniently (the bytes that are not valid UTF-8 are replaced), so a
  file with a stray byte is used as far as it can be read.
- **Every text loader** uses the shared reader: `brute`, `fuzz`, `hash`,
  `stale`, `subdomains`, `report`, `config`, `audit --file`,
  `radix --cidr-file`.
- **The standard input** of `audit`, `hash` and `jwt` is read leniently
  (`ethscan/cli.py`: `_read_stdin_text`).
- **The credential files** (`--file`, `--user-file`, `--pass-file`,
  `--audit-file`) are refused when they are not valid UTF-8: a mangled
  password would otherwise be hashed silently (`ethscan/cli.py`:
  `_require_utf8`).
- **The JSON files** (`--services-file`, `--tls-file`, `--ssl-file`,
  `--banners-file`) report a file that is not JSON, or that does not hold an
  object, as a usage error (**exit 2**) that names the option
  (`ethscan/cli.py`: `_load_json_file`).
- **The Nmap XML file** (`--input-file`) reports a file that is not XML as a
  usage error, and a port whose id is not a number is skipped instead of
  aborting the report (`ethscan/nmap.py`: `NmapParseError`).
- **The probes** survive a hostile entry: `http.client.InvalidURL` is a
  failed probe in `fuzz`/`urlcheck` and a null byte in a label is an
  unresolved label in `subdomains`.
- The 3 ruff errors that the previous session left in
  `tests/test_file_option_sweep.py` are fixed.

## Verification

- `python -m ruff check ethscan/ tests/` → **All checks passed**
- `python -m pytest -q` → **4484 passed, 45 skipped, 2 warnings**
- `python -m pytest tests/test_file_content_sweep.py -q` → **18 passed, 35
  skipped** (the new permanent sweep; before the fix all 18 failed)
- `python -m pytest tests/test_fileio.py tests/test_nmap.py tests/test_fuzz.py
  tests/test_subdomains.py -q` → **107 passed**
- `git diff --check` → clean

## Next agent

Do not re-run the file-content task; it is complete and verified. The
outstanding project work is in `HANDOFF_NEXT.md` (the one precise next task
and the options that are still open).
