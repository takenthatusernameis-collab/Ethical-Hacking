# Next Task

None pending from current evidence. Repository is fully green:

- `pytest -q` -> 46744 passed, 146 skipped, 0 failed
- `mypy ethscan/ tests/` -> Success (267 source files)
- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift
- `coverage` -> 100% statement/branch on every module (including cli.py)

## Investigated and found already done (do not re-implement)
- ICMPv6 raw ping in `ethscan/ping.py` (`_build_icmpv6_echo_request`, `_parse_icmpv6_reply`, `_try_create_raw_socket(AF_INET6/IPPROTO_ICMPV6)`, ICMPv6 probe path) — fully implemented and tested at 100% branch coverage (`tests/test_ping.py` has 70 ICMPv6 references). The prior suggested follow-up is stale.

## Remaining / known limitations (intentional, out of scope)
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope (exit 0, in-band error) per their documented contract.
- PBKDF2+NTLM intentionally unsupported.

## Next session guidance
Re-run the full gate suite to confirm steady state is still green; only then select a new bounded task if a genuine evidenced gap is reproduced. Do not fabricate work.
