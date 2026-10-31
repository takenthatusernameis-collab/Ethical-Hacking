## Status: COMPLETE (this session)

### What changed
- Added an MD4 availability guard to `_compute_ntlm` in ethscan/hash.py, mirroring the existing guard in `_compute_md4`, so NTLM hashing raises a clear ValueError when MD4 is unavailable instead of relying on hashlib.new.

### What was actually verified
- tests/test_hash.py: 126 passed.
- ruff check ethscan/hash.py: all checks passed.

### What remains unresolved
- Coverage on ethscan/hash.py still misses defensive unavailable-MD4 branches (36-37, 62, 85, 228) because MD4 is available on this platform.

### One precise next task
- Inspect ethscan/cidr.py for input validation edge cases and add targeted tests; maintain existing patterns.
