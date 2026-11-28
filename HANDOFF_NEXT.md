# Handoff

## Session (Sat Nov 28 2026, `whois.extract_referral_server` property test)

- Executed the prior handoff's evidence-based lead, but it was STALE AGAIN:
  `tests/test_whois_referral_property.py` already existed in HEAD (commits
  19003f0/6775678). I re-verified HEAD first-hand (baseline: 6 passed) rather
  than trusting the handoff.
- The committed test worked but had two real weaknesses: (1) its `oracle`
  carried DEAD code — a `candidates`/`finditer` block that was computed, sorted,
  then never used (the live logic was `cand2`); (2) it omitted the documented
  empty-value-no-cross-line behaviour and had a weaker generator.

## What changed (test-only; NO production code)

- `tests/test_whois_referral_property.py` (improved in place, 7 tests):
  - Removed the dead oracle code; `_oracle` is now a clean from-scratch
    recomputation that does not call any ethscan helper.
  - Widened the random generator: 2000 -> 5000 cases with empty same-line
    values, `\r\n`/`\n` separators, scheme/port/path/query/fragment forms, mixed
    case, and `whois.iana.org` with/without port.
  - Added deterministic tests for empty-value-no-cross-line, no-match, and
    fragment stripping. Strict superset of prior coverage (7 vs 6 tests).
- No `ethscan/` source changed (verified correct, not a defect).

## What was actually verified (evidence)

- Differential fuzz BEFORE editing: 50,000 random cases vs an independent
  oracle -> 0 mismatches.
- Baseline HEAD test re-run first-hand: 6 passed.
- Mutation checks (each caught; source restored, `git diff ethscan/whois.py`
  empty): remove final `.lower()` -> 2 fail; remove `rstrip(".")` -> 2 fail;
  remove iana exclusion -> 2 fail; remove scheme strip -> 3 fail; remove path
  strip -> 2 fail; pattern-priority sort instead of position -> 2 fail.
- `python -m pytest tests/test_whois_referral_property.py -q` -> 7 passed.
- Full gate at this working tree:
  - `python -m coverage run --branch --source=ethscan -m pytest -q` -> 50084 passed,
    147 skipped, 0 failed; TOTAL 100% (16292 stmts, 6178 branches, 0 missing).
  - `python -m mypy ethscan/ tests/` -> Success: no issues in 288 source files.
  - `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
  - `python check_readme.py` -> 54 commands, 0 drift.
- `git status`: only `tests/test_whois_referral_property.py` modified; no
  production code touched; `git diff --check` clean; nothing committed
  (controller commits).

## Blockers

- None.

## Approaches already tried / ruled out

- redis `_parse_info`/`_parse_config`, osdetect matchers, `cert._extract_subdomains`,
  and `whois.extract_referral_server`: now property-tested — do NOT re-probe
  unchanged.
- All prior hostile/formatter/assessor/CLI sweeps, radix/target/hash/passwords/jwt/
  scanner/cidr wrong-output fuzz, whois/s3/mac/nmap/tls/version/netbios/config probes:
  covered in prior sessions — do not repeat unchanged.

## Next task

- One precise, evidence-based, NOT-yet-done lead: add a durable property test for
  `ethscan.validate._ports_to_ranges` (validate.py:357). It is a pure helper
  (int-coercion with `""` fallback, sort, consecutive-run collapsing, `", "`
  join) with ONLY example tests (`tests/test_validate.py:437-458, 686-687,
  799-802`) and NO property test. FIRST re-run a differential fuzz vs an
  independent hand oracle to confirm it is correct (do not change source without
  a reproduced defect), then add `tests/test_validate_ports_to_ranges_property.py`
  with a LOCAL oracle (do not import source helpers), mutation-check, and rerun
  the full gate (commands below).
- Do NOT fabricate work, repeat verification-only sessions as progress, or make
  empty/control-marker commits. `oracle`/`postgresql` empty-target handling and
  `ethscan/cli.py` unreachable guard remain intentionally out of scope.
  Do not modify `.github/workflows/**`.

## Environment / critical notes

- **Test deps are NOT preinstalled in this environment.** Run:
  `pip install --quiet pytest mypy ruff coverage dnspython` (installs to
  `~/.local/bin`, not on PATH; use `python -m <tool>`). `click`/`pyyaml` are
  preinstalled; `dnspython` is not.
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5. `coverage`
  is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.9 min (50084 tests). Do not commit manually; the
  workflow controller stages and commits.
- ALWAYS re-verify HEAD first-hand (install deps, run the gate) rather than trusting
  this handoff's "green" claim — prior handoffs were repeatedly stale.