## Status: COMPLETE (this session)

### What changed
- Fixed bare-IP version detection in ethscan/cidr.py::normalize_cidr. Previously used "." in value to decide IPv4, causing IPv4-mapped IPv6 addresses (e.g. ::ffff:192.168.1.1) to be treated as /32 and collapse to ::/32. Now uses ":" presence to identify IPv6.

### What was actually verified
- normalize_cidr('::ffff:192.168.1.1') == '::ffff:c0a8:101/128'
- tests/test_cidr.py: 93 passed.
- ruff check ethscan/cidr.py: all checks passed.

### What remains unresolved
- Coverage already 100% on ethscan/cidr.py.

### One precise next task
- Inspect ethscan/target.py for input validation edge cases (IP/hostname parsing) and add targeted tests; maintain existing patterns.