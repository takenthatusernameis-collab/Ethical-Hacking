# HANDOFF_NEXT.md

## Summary
The **trace** command now reports a `--target` without a usable host as a clean click usage error (exit code 2, one-line message, no traceback), instead of dying with a raw `ValueError: Invalid target` (`ethscan/trace.py:79`).

**`ping` is also done** (committed in `9a86aa0`, after these docs were written): `probe_icmp` catches `socket.gaierror` around `connect_ex` (`ethscan/ping.py:250`) and returns a `NO-RESPONSE` probe with the resolver error in `error`, so `ping --target <unresolvable>` exits 0 and reports the failure inside its JSON output. Verified: `--target no-such-host.invalid` and `--target 'host name'` both exit 0; `example.com` still exits 0. Full suite: **4207 passed, 1 skipped**. Covered by `tests/test_ping.py` and `tests/test_cli.py`.

These handoff files were written before commit `9a86aa0` and listed `ping` as unresolved; that is stale. `ping` is resolved. No code changed this session — only verification and doc correction.

## Remaining tasks

### 1. `s3` with a bracketed IPv6 target -> `http.client.InvalidURL` traceback (next agent task)
`--target "[::1]:443"` crashes, exit 1, with a raw traceback (`ethscan/s3.py`). Root cause:
- `_normalize_target("[::1]:443")` returns `"::1"` (`urlparse(...).hostname` strips brackets).
- `_build_bucket_candidates("::1")` derives candidates like `::1`, `::1-backup`, `backup-::1` — all contain `:`, so the S3 URL `https://::1.s3.amazonaws.com/` is malformed.
- `check_bucket_public` (`ethscan/s3.py:203`) catches `HTTPError`, `(URLError, socket.timeout, OSError)`, but `http.client.InvalidURL` (an `HTTPException`, not `OSError`) escapes.
- `run_s3` calls `future.result()` in the main thread, so the exception escapes the whole command. Non-deterministic (which concurrent thread re-raises first).

Confirmed reproduction:
```
$ python -m ethscan s3 --target '[::1]:443'
...
http.client.InvalidURL: nonnumeric port: '1.s3.amazonaws.com'
EXIT=1
```

Two decisions must be made explicitly before writing code:

1. **Which bucket names are usable.** S3 bucket names are DNS-compliant (lowercase letters, digits, hyphens, 3–63 chars). `::1` and `::1-backup` are not valid. Options: (a) filter invalid candidates out → zero candidates → existing `"No bucket candidates could be derived from the target."` path; (b) keep them and let each probe report an error. Option (a) matches the existing empty-candidates path; option (b) preserves per-candidate signal.

2. **Whether a failed probe should be reported inside the result.** `check_bucket_public` already reports `HTTPError`/`URLError`/`socket.timeout`/`OSError` inside the result dict's `error` field. Add `http.client.InvalidURL` (or `http.client.HTTPException`) to that except tuple (`ethscan/s3.py:255`) so a malformed S3 URL yields a failed probe result instead of escaping `future.result()`. This makes the outcome deterministic and matches every other probe command. Do NOT turn it into a usage error — for `s3` a malformed/unresolvable target is a probe failure, not an invalid option.

Suggested minimal fix shape: in `check_bucket_public`, extend the `except (...)` clause at `ethscan/s3.py:255` to include `http.client.HTTPException` (import `http.client`), setting `result["error"] = str(exc)`. Verify with `python -m ethscan s3 --target '[::1]:443'` → exit 0, JSON with per-bucket `error` results and no traceback; add a test that `run_s3`/`check_bucket_public` with `[::1]:443` returns structured results (no exception).

## Unchanged / deliberate non-changes
- `ping` needs no `TargetSpecError` / `_target_usage_errors` decorator (probe failure, not a usage error).
- The 48 pre-existing ruff errors are unrelated and left alone.
- The 14 `_normalize_target` copies remain duplicated (separate refactor; they differ on `host:` / bracketed-IPv6 edge cases).
- `web`, `headers`, `urlcheck`, `fuzz` already report probe failures inside output; `s3` is the one that still escapes.
