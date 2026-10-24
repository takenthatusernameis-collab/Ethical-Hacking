# NEXT_TASK

## Status: READY

### Suggested task: tighten ruff cleanliness in dns/dnsbrute

41 pre-existing ruff errors remain in `ethscan/dns.py` and `ethscan/dnsbrute.py` (DNS import guards and try/except/pass). These are not runtime issues. A small, reversible pass can clean them up without changing behavior.

### What to verify

- Run `python -m ruff check ethscan/dns.py ethscan/dnsbrute.py` to see current errors
- Fix with minimal changes (narrow excepts/logging or targeted `# noqa` where appropriate)
- Ensure behavior unchanged

### Verification commands

- `python -m ruff check ethscan/dns.py ethscan/dnsbrute.py`
- `python -m ruff check ethscan/ tests/`
- `python -m pytest tests/test_dns.py tests/test_dnsbrute.py -q`
- `python -m pytest tests/test_protocol_hostile_sweep.py -q`

### Constraints

- Smallest reversible change
- No behavior changes
- Do not weaken safety controls
- Do not commit unless explicitly asked

### Evidence of completion

Ruff errors reduced/cleared in those files, all related tests pass.
