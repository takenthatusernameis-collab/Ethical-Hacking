# NEXT_TASK.md

## Status (2026-10-20T11:35:00Z)

- The **hostile option sweep** of the CLI is **complete**. A sweep over
  every string option and every file option of all 42 commands used to leak
  **110 tracebacks**; it now leaks **none**.
- The six root causes behind them are fixed: a URL that `urllib.parse`
  refuses (`--target 'http://[::1'`), an API base URL that `urllib` refuses
  (`--api-url 'not a url'`), a file option that points at a missing file or
  a directory, a WHOIS server that cannot be reached, an output path that
  cannot be written and a nameserver whose label is too long.
- Verified: **4389 passed / 7 skipped** (4342/1 before + 47 new); ruff rule
  set identical to the baseline (48 pre-existing errors, no new ones);
  `git diff --check` clean.
- The **permanent sweep test** asked for in the previous handoff is **done**:
  `tests/test_option_sweep.py` walks every string option of every command
  with a small hostile value set and a 5s per-invocation timeout. It passes
  **47 / 6 skipped in 9.2s** and keeps the "no traceback leak" guarantee
  alive for a new option that is added later.

## The URL fix in one paragraph

`urllib.parse.urlparse` raises a bare `ValueError` (`Invalid IPv6 URL`) for
a URL whose authority holds an unmatched bracket. The error is a `ValueError`
and not an `OSError`, so the narrow `except` clauses of the library did not
catch it and it reached the user as a raw traceback in 36 of the 42 target
commands. `ethscan/target.py` now has a `parse_url(url)` helper that re-raises
it as a `TargetSpecError`, every target normalizer uses that helper, and
`ethscan/cli.py` translates the error into the click usage error for **every**
command (a group class, not a per-command decorator, so a command added later
cannot leak it either).

## Sweep of every option (current evidence)

Every string option of every command was invoked with hostile values, and
every file option with a missing path, a directory and an over-long name.
Reproduce with:

```python
import signal
from click.testing import CliRunner
from ethscan import cli

class _Timeout(BaseException):
    pass

signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(_Timeout()))
runner = CliRunner()
hostile = {"target": ["http://[::1", "[::1", "http://a]b", "%00", "host name"],
           "api_url": ["not a url", "http://[::1"],
           "server": ["not a host", ""]}

for name, cmd in sorted(cli.cli.commands.items()):
    has_target = any(p.name == "target" for p in cmd.params)
    for p in cmd.params:
        if type(p.type).__name__ == "StringParamType" and p.opts:
            for value in hostile.get(p.name, ["", "x" * 300, "/nonexistent/path"]):
                args = [name, p.opts[0], value]
                if has_target and p.name != "target":
                    args += ["--target", "127.0.0.1"]
                signal.setitimer(signal.ITIMER_REAL, 20)
                try:
                    res = runner.invoke(cli.cli, args)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                if res.exception is not None and not isinstance(res.exception, SystemExit):
                    print(name, p.opts[0], repr(value), type(res.exception).__name__)
```

Result: **no traceback leaked** (196 invocations for the string options, 225
for the file options). The permanent version of the string sweep is
`tests/test_option_sweep.py` (47 passed, 6 skipped, 9.2s).

## Remaining tasks (bounded, high-value)

### 1. The 48 pre-existing ruff errors
Most of them are `BLE001` (a broad `except Exception`) and `TRY002` (a
`raise Exception` in a test). They are unrelated to the behaviour of the
toolkit and were deferred by four sessions, because fixing them means
reviewing 48 places in the code. Two of them are auto-fixable
(`PLR0402` in `tests/test_brute.py`).

### 2. A permanent sweep test for the file options
The file-option sweep is still a script outside the repository (it needs a
per-invocation timeout and covers 225 invocations). The string options are now
covered permanently by `tests/test_option_sweep.py`; the file options are
pinned by the per-option regression tests in `tests/test_cli.py`
(`test_a_file_option_with_a_missing_file_is_a_usage_error` and
`test_a_file_option_with_a_directory_is_a_usage_error`).

## Verified working forms (do not break)
- `host`, `host:443`, `host:65535`, `http://host`, `https://host:8443`,
  `[::1]:443`
- `https://example.com/path`, `https://example.com/a%20b`,
  `https://example.com/?q=1`, `https://example.com/path?query=1#frag`
- `http://[::1]:8443` (a **closed** bracket is a valid IPv6 URL and must
  keep working; only an unmatched bracket is refused)
- The empty-host -> `localhost` mapping of `web._parse_url` and the
  lower-casing of `s3._normalize_target` must stay as they are.
- `trace` still accepts `example.com`, `example.com:80` and
  `http://example.com/`.
- `s3` still derives the same candidates in the same order, keeps the
  original case of a `--wordlist` entry, and still resolves the DNS of a
  valid candidate before requesting it.
- All 14 protocol modules still parse `host:1234`, `host:65535` and
  `[::1]:443` to the same values as before.
- A target with a userinfo (`http://user:pass@example.com`) is scanned as
  `example.com` (the credentials are dropped), the way whois, mongodb and
  ssh already did it.
- A host that is not a valid host name (`....`) is reported as a failed
  probe (**exit 0**), exactly like a host that cannot be resolved
  (`no-such-host.invalid`).
- A WHOIS server that cannot be reached is a **failed lookup** inside the
  output (**exit 0**), the way a recursive hop that cannot be reached
  already was.
- The `config` command keeps its own contract for an output path that
  cannot be written: **exit 1** with `Error writing output: ...`.