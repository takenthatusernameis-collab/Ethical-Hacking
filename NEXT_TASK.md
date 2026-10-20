# NEXT TASK

## Status: COMPLETE

The **cache file** task assigned by the previous agent has been completed.
Every cache file that the `geo`, `cert`, `mac` and `cve` commands write is
now read without raising: a cache file that is not valid UTF-8, that is not a
JSON object, that holds an entry that is not a mapping, or that holds a
timestamp that is not a number used to leak a traceback. It is now an empty
cache. A permanent sweep keeps it that way.

## What was done

- **The content of the cache files** is read with `ethscan.fileio.load_json`,
  which decodes leniently (`ethscan/geo.py`, `ethscan/cert.py`,
  `ethscan/mac.py`, `ethscan/cve.py`: `_load_cache`). A file with a stray
  byte is used as far as it can be read; a file that is not JSON, or that is
  not a JSON object, is an empty cache.
- **Only the entries that are mappings** are returned, so the callers can
  copy them with `dict(cache[ip])` without a type check.
- **A timestamp that is not a finite number** is never fresh: the entry is
  stale data, which the offline fallback may still use (and says it used).
- **New permanent sweep `tests/test_cache_content_sweep.py`**: every command
  that has a cache gets a cache file that is hostile in fourteen ways. The
  cache must be an empty cache, a hostile entry must never be fresh, and no
  command may leak a traceback - at the library level and on the command
  line. A fifth test keeps the happy path.

## Verification

- `python -m ruff check ethscan/ tests/` → **All checks passed**
- `python -m pytest -q` → **4557 passed, 48 skipped, 2 warnings**
- `python -m pytest tests/test_cache_content_sweep.py -q` → **19 passed**
  (the new permanent sweep; with the production code reverted 15 of the 19
  fail, and 32 of the 56 hostile cache cases leak a traceback)
- The real command line over the whole matrix: **42 of 42** invocations of
  `geo`, `cert` and `mac` exit with 0 and print no traceback
- `git diff --check`: clean

## Next agent

Do not re-run the cache-file task; it is complete and verified. The
outstanding project work is in `HANDOFF_NEXT.md` (the one precise next task
and the options that are still open).
