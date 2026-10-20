# NEXT TASK

## Status: COMPLETE (netbios: a short first-level name no longer crashes the command)

1. **`_decode_name_chars` in `ethscan/netbios.py`** now rejects a name that
   is shorter than 32 chars with a `ValueError`. It used to accept any even
   length, decode it and read the suffix byte out of range, so an `IndexError`
   escaped the `except ValueError` guards of `_parse_dns_name`,
   `_parse_nbns_response` and `run_netbios`.
2. **Library and command-line regression tests added** in
   `tests/test_netbios.py`: 5 tests, all of which fail with the `IndexError`
   on the unfixed module.

## Verification

- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/test_netbios.py -q` → **78 passed** (was 73).
- `python -m pytest -q` → **4566 passed, 48 skipped, 2 warnings** (was 4561).
- `git diff --check` → clean.

## Next agent

One bounded task is described in `HANDOFF_NEXT.md`: sweep the remaining
server-answer parsers for the same class of bug (a fixed index into a decoded
buffer, or an exception type that is not caught by the module's guard).
The candidate list and the method that found the netbios bug are in
`HANDOFF_NEXT.md`.
