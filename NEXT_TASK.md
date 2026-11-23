## Next task
COMPLETED. `ethscan/version.py` is now 100% branch-covered (84 statements, 12 branches, 0 missing). The previously assigned coverage gaps are closed:
- nonzero git return codes (branches 30->35, 44->49);
- git subprocess exceptions (lines 32-33, 46-47);
- empty git info (branch 90->92);
- ImportError/AttributeError fallbacks for click/yaml/dns (lines 57-58, 63-64, 69-70);
- `get_version_data()` delegation (line 165).

Full suite: 47428 passed, 147 skipped, 0 failed. mypy, ruff, and check_readme all clean. No production code changed.

`ethscan/ping.py` remains 100% covered. `oracle`/`postgresql` empty-target handling remains intentionally out of scope. No further task is pending; see `HANDOFF_NEXT.md` for the full handoff record.