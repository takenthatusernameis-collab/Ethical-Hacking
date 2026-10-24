# NEXT_TASK

## Status: COMPLETE

The task of the previous handoff (tighten ruff cleanliness in dns/dnsbrute) was
already satisfied, and this session extended it to the remaining files.

### What was done

- `python -m ruff check ethscan/ tests/` → **All checks passed** (was 33 errors).
- Minimal, reversible edits to `ethscan/dnssec.py`, `ethscan/resolve.py`,
  `ethscan/service.py`, `ethscan/smtp.py`, `ethscan/ssh.py`, `ethscan/subdomains.py`,
  `ethscan/subtake.py`, and `tests/test_ssl.py` (add `# noqa: BLE001, S110` to
  import guards and transport-failure `except Exception: pass` blocks; collapse a
  duplicate handler in `smtp.py`; drop unused imports in `test_ssl.py`).
- Behavior unchanged: `python -m pytest tests/ -q` → 5196 passed, 48 skipped, 3 warnings.

### Verification commands

- `python -m ruff check ethscan/ tests/`
- `python -m pytest tests/ -q`

### Constraints

- Smallest reversible change
- No behavior changes
- Do not weaken safety controls
- Do not commit unless explicitly asked

### Evidence of completion

Ruff errors reduced from 33 to 0; full test suite passes.

(End of file - total 26 lines)