# Handoff: README documentation completion for remaining commands

## What changed

### README documentation
`README.md` — Added detailed per-command bullets for all remaining commands that previously had only brief summary entries in the Features list. Added bullets for:
- `scan`, `brute`, `service`, `vuln`, `urlcheck`, `osdetect`, `trace`, `wifi`, `recon`, `cert`, `cve`, `subtake`, `fuzz`, `subdomains`, `dns`, `headers`, `report`
- Also added detailed bullets for `stale`, `ssh`, `s3`, `dnssec`, `completion`, `jwt`, `validate`, `resolve`, `nmap`, `ping`, `cidr`, `radix`, `hash`, `audit`, `mac`, `config`

Each bullet documents CLI options (flags, defaults, types) and output format support (`--output-format [json|markdown|csv]` / `--format` alias / `--out` where applicable), matching the style of existing detailed bullets for `mysql`, `postgresql`, `geo`, `whois`, `ssl`, `mssql`, `oracle`, etc.

## What was verified
- `python -m pytest -q` → **2808 passed, 3 failed** (3 failures are pre-existing network-dependent DNS tests: `test_dns.py::test_run_dns_offline_basic`, `test_dnsbrute.py::test_run_dnsbrute_resolver_used_for_resolution`, `test_resolve.py::test_run_resolve_domain_defaults` - environmental, no internet access in sandbox; not caused by documentation changes)
- No code changes - only README.md modified. Working tree changes are isolated to documentation.
- `git diff --stat` → `README.md | 36 ++++++++++++++++++++++++++++++++++--` (added comprehensive command documentation)

## What remains unresolved
- The 3 network-dependent DNS test failures remain (environmental). They should pass in an environment with network access.
- No functional gaps; all commands have implementations and CLI wiring as verified by tests.

## Next precise task
No further documentation tasks are obvious from the handoff chain. All summary-only commands now have detailed bullets. Consider any other remaining improvements - but the stated task (complete README documentation coverage for remaining summary-only commands) is complete. If continuing, pick another bounded, high-value task such as improving edge case coverage or refactoring a small, well-defined component. Otherwise, mark as complete.
