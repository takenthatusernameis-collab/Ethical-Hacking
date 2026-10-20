# TASK.md

Date: 2026-10-20T19:37:05Z
Status: the **content of the cache files** of the `geo`, `cert`, `mac` and
`cve` commands is hardened and is now covered by a permanent sweep. A cache
file that cannot be used used to leak **4 different tracebacks**; it now leaks
**none** and is treated as an empty cache.

The path of a file option was covered before (`tests/test_file_option_sweep.py`),
the content of an input file before that (`tests/test_file_content_sweep.py`)
and the values of the config file last (`tests/test_config_value_sweep.py`).
The content of the cache files was not: nothing kept them from holding bytes
that are not UTF-8, entries that are not mappings or timestamps that are not
numbers.

## What changed

### 1. A cache file that is not valid UTF-8
- **Root cause:** the cache was read with a strict
  `open(CACHE_FILE, "r", encoding="utf-8")` and `json.load`. The `except`
  clause caught `json.JSONDecodeError` and `OSError`, but not a
  `UnicodeDecodeError` (a `ValueError`), so a cache file with a stray byte
  leaked a traceback.
- **`ethscan/geo.py`, `ethscan/cert.py`, `ethscan/mac.py`,
  `ethscan/cve.py`**: the cache is now read with `ethscan.fileio.load_json`,
  which decodes leniently, so a file with a stray byte is used as far as it
  can be read (the same contract the CLI already used for the JSON files it
  accepts).

### 2. A cache entry that is not a mapping
- **Root cause:** `_load_cache` returned every entry of the file, so an entry
  that is a number, a list, a string or `null` was copied with
  `dict(cache[ip])` and leaked a `TypeError` (or a `ValueError`).
- **The four modules**: only the entries that are mappings are returned, so
  the callers can copy them without a type check. An entry that is not a
  mapping is an empty cache for that key.

### 3. A timestamp that is not a number
- **Root cause:** `_is_cache_valid` did `"timestamp" not in entry` and
  `time.time() - entry["timestamp"]` without a type check, so a timestamp
  that is a string, `null`, a mapping or a list leaked a `TypeError`.
- **The four modules**: the timestamp is read with `float()` and the entry is
  never fresh when it is not a number (`TypeError` and `ValueError` are
  caught). A timestamp that is not **finite** is refused as well, so an
  infinite timestamp cannot make an entry live forever.

### 4. A permanent sweep
- **`tests/test_cache_content_sweep.py`** (new): every command that has a
  cache gets a cache file that is hostile in one of **fourteen** ways (not
  UTF-8, not JSON, not a JSON object, an entry that is not a mapping, a
  timestamp that is not a number, and more). The cache must be read as an
  empty cache, a hostile entry must never be served as fresh, and no command
  may leak a traceback - at the library level and on the command line. A
  fifth test keeps the happy path: a cache file that the toolkit wrote is
  still served from the cache.

## Verification

- Full suite: **4557 passed, 48 skipped** (before: 4538 passed, 48 skipped;
  the new sweep adds 19 cases).
- Ruff: `ruff check ethscan/ tests/` → **All checks passed**.
- `git diff --check`: clean.
- The new permanent sweep `tests/test_cache_content_sweep.py` is a real
  regression test: with the production code reverted (`git stash push --
  ethscan/`) **15 of its 19 cases fail**. Counted over the whole matrix,
  **32 of the 56 hostile cache cases leak a traceback** in the old code
  (4 different exceptions: `UnicodeDecodeError`, `TypeError`, `ValueError`);
  in the new code **0 of 56** leak one.
- The real command line (a subprocess, not the test runner) was run over the
  whole matrix as well: **42 of 42** invocations of `geo`, `cert` and `mac`
  exit with 0 and print no traceback.

## Remaining

- The **`--services-file` of the `cve` command** is still read with a strict
  `open(..., encoding="utf-8")` in `ethscan/cve.py`, while the CLI reads the
  same file leniently, so a services file with a byte that is not UTF-8
  passes the CLI check and then leaks a `UnicodeDecodeError`. This is the
  next task; see `HANDOFF_NEXT.md` for the reproduction.
- The `cve` command still reports a services file it cannot read inside its
  own output when it is used as a library (`ethscan/cve.py`: the `notes`
  entry "Failed to read services file"). The CLI reports it as a usage error
  before the module runs, so the note is only reachable for a direct API
  user. It was left alone on purpose: it is the module's own contract.
- A config file whose `defaults` or `commands` section is not a mapping is
  still a warning, not a usage error (the existing contract of
  `ethscan/config.py`: `validate_config`).
