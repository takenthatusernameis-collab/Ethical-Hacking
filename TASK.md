## Status: COMPLETE (this session)

### What changed
- Added ``test_config_hash_passwords_non_scalar_item_rejected`` covering ``_config_value_text``'s multiple-option non-scalar-item branch (cli.py:463-466) via a config file with ``commands:\n  hash:\n    passwords:\n      - password\n      - {foo: bar}\n``.
- Added ``test_config_scan_workers_non_scalar_rejected`` covering ``_config_value_text``'s non-multiple non-scalar branch (cli.py:469-472) via ``commands:\n  scan:\n    workers: [1, 2]\n``.
- Both tests follow the existing config-file/wrong-type patterns and use ``CliRunner(mix_stderr=False)`` so stderr is asserted separately.

### What was actually verified
- tests/test_cli.py::test_config_hash_passwords_non_scalar_item_rejected passes.
- tests/test_cli.py::test_config_scan_workers_non_scalar_rejected passes.
- Coverage on ethscan/cli.py: 464 and 469-472 now covered; remaining cli.py misses are only 523, 531, 4818 (documented provably unreachable defensive lines, skipped per precedent).
- ruff check tests/test_cli.py ethscan/cli.py: all checks passed.
- Full suite: python -m pytest -q -> 5432 passed, 53 skipped (was 5430 before this change; +2 tests, no regressions).

### What remains unresolved
- cli.py:523/531 (``_CheckedDefaultMap.get`` / ``_param`` when a config key matches no command param) -- provably unreachable defensive lines, documented as skip per the radix.py precedent.
- cli.py:4818 (netbios ``if suffix is None: suffix_value = 0x00``) -- provably unreachable: ``--suffix`` defaults to 0, not None (skip, radix precedent).
- All other modules: remaining gaps are provably unreachable defensive branches or env-dependent import branches -- skip per precedent; hash.py gaps are MD4-availability/env-dependent or unreachable.

### Which approaches failed and why
- Initial run used ``CliRunner()`` without ``mix_stderr=False``, which raised ``ValueError: stderr not separately captured`` when accessing ``.stderr``; fixed by using ``CliRunner(mix_stderr=False)`` matching the existing wrong-type test pattern.

### One precise next task
- None: the cli.py coverage work is complete. All remaining gaps are documented as provably unreachable / env-dependent and skipped per precedent. The next agent should start a fresh bounded task rather than resume coverage work.
