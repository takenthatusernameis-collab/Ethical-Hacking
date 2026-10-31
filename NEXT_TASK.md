## Status: COMPLETE (this session)

### What changed
- Added ``test_hash_passwords_from_config_list`` to tests/test_cli.py covering ``_config_value_text``'s multiple-option scalar-list branch at ethscan/cli.py:467-468, via a config file with ``commands:\n  hash:\n    passwords:\n    - password`` and invoking ``hash`` directly, following the config-file pattern at tests/test_cli.py:4661-4684.
- Investigated ethscan/cli.py:523/531 (``_CheckedDefaultMap.get`` / ``_param`` when a config key matches no command param): one ``_CheckedDefaultMap`` is built per command bound to that command's params (cli.py:422-424) and Click only queries known option names of the invoked command, so ``_param(name)`` always resolves; line 523 (``return value`` on ``param is None``) and 531 (``return None``) are provably unreachable defensive lines -- documented as skip per the radix.py precedent.

### What was actually verified
- tests/test_cli.py::test_hash_passwords_from_config_list passes.
- Coverage on ethscan/cli.py: 467-468 now covered (absent from the coverage missing list); remaining cli.py misses are 464 (non-scalar multiple item), 469-473 (non-multiple branch), 4818, 523, 531.
- ruff check tests/test_cli.py ethscan/cli.py: all checks passed.
- Full suite: python -m pytest -q -> 5430 passed, 53 skipped (was 5428 before the change; no regressions).

### What remains unresolved
- cli.py:464 (_config_value_text non-scalar multiple item).
- cli.py:469-473 (_config_value_text non-multiple non-scalar branch).
- cli.py:4818 (netbios ``if suffix is None: suffix_value = 0x00``) -- provably unreachable (skip, radix precedent).
- cli.py:523/531 -- provably unreachable defensive lines, documented above, skip.
- All other modules: remaining gaps are provably unreachable defensive branches or env-dependent import branches -- skip per precedent; hash.py gaps are MD4-availability/env-dependent or unreachable.

### Which approaches failed and why
- None new this session. (Prior: ``cli ["--version", ...]`` failed exit code 2 because ``--version`` is group-level; fixed by invoking the ``version`` subcommand directly.)

### One precise next task
- Optionally cover cli.py:464 and 469-473 with config-file wrong-type tests, following tests/test_cli.py:12780-12787. Then verify focused coverage on ethscan/cli.py + ruff + full suite. Otherwise the coverage work is complete: all remaining gaps are documented as provably unreachable / env-dependent and skipped per precedent.
