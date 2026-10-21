# HANDOFF: state for the next agent

## What changed this session

The task of the previous handoff (extend the permanent CLI-level sweep to the
HTTP-facing commands) is done and verified. The ten HTTP-facing commands now
have a permanent check each at the command line, so the CLI-level sweep
covers every command that fetches over HTTP.

### Tests (`tests/`)

- `tests/test_cli_http_unreachable_sweep.py` (10 checks): the CLI-level check
  for `web`, `headers`, `fuzz`, `urlcheck`, `cert`, `geo`, `mac`, `s3`, `cve`
  and `subtake`. Each check patches the transport the module really opens
  (`urllib.request.urlopen` for the HTTP fetches, `ethscan.web.socket`/
  `ethscan.ssl.socket` for the TLS probes, `ethscan.s3.socket.gethostbyname`
  and `ethscan.subtake.socket.getaddrinfo` for the name lookups), runs the
  command through `CliRunner` and asserts that the command exits 0, leaks no
  traceback and prints its own failure signal. The sweep is hermetic: the
  transport is patched, so it needs no network and does not depend on what the
  machine that runs it can reach.

The file was already in the repository as a draft (added by the commit before
this session). It was rewritten in this session, because the draft was not
usable as a permanent check:

- `test_fuzz` had **no assertion at all** and passed `--wordlist /dev/null`,
  so it probed nothing and proved nothing. It now probes two paths of a
  wordlist file and asserts the error of every probe.
- `cert`, `geo`, `mac` and `cve` ran with the **filesystem cache enabled**,
  so a warm cache in `~/.cache/ethscan` (a real lookup of the same target
  less than an hour old) made the commands report a success and the checks
  fail. They now run with `--no-cache --no-offline-fallback`.
- `s3` and `subtake` resolved their names through the **real resolver**. The
  name lookup is now patched to fail the way a missing name does, so the
  checks do not depend on the network.
- The draft had no docstrings, no type annotations and a stray `"""` at the
  end of the file; it now follows the conventions of
  `tests/test_cli_unreachable_sweep.py`.

No source file under `ethscan/` was changed in this session.

## What was actually verified

- **The ten commands were run through the CLI against a hostile transport.**
  Every one prints its own failure signal and exits 0:

  | command    | transport seam patched                          | own failure signal                                     |
  |------------|-------------------------------------------------|--------------------------------------------------------|
  | `web`      | `urllib.request.urlopen`, `ethscan.web.socket`  | `error="header fetch failed: hostile transport"`, `ssl.error="hostile transport"` |
  | `headers`  | `urllib.request.urlopen`                        | `error="header fetch failed: hostile transport"`       |
  | `fuzz`     | `urllib.request.urlopen`                        | `error="hostile transport"` on every probed path       |
  | `urlcheck` | `urllib.request.urlopen`, `ethscan.ssl.socket`   | `web.error`, `ssl.error` and the error of every fuzzed path |
  | `cert`     | `urllib.request.urlopen`                        | `cert_data.error="Failed to fetch certificate transparency data"` |
  | `geo`      | `urllib.request.urlopen`                        | `geolocation.error="Failed to fetch geolocation data"`|
  | `mac`      | `urllib.request.urlopen`                        | `mac_data.error="Failed to fetch MAC vendor data"`    |
  | `s3`       | `urllib.request.urlopen`, `ethscan.s3.socket`    | `error="hostile transport"` on every probed bucket    |
  | `cve`      | `urllib.request.urlopen`                        | `error="NVD lookup failed for CVE-2016-6210: Failed to fetch CVE data"` |
  | `subtake`  | `urllib.request.urlopen`, `ethscan.subtake.socket` | the subdomain is reported without a CNAME, `vulnerable=false` |

- **The ten checks are meaningful.** Each one was proved by reverting the
  guard of its own module and watching the check fail. The mutation was
  applied to a copy of the file and restored afterwards, so no source file was
  changed:

  | check                    | mutation                                                              |
  |--------------------------|-----------------------------------------------------------------------|
  | `web`                    | `ethscan/web.py`: `except Exception` -> `except ValueError`            |
  | `headers`                | `ethscan/headers.py`: `fetch_error = getattr(fetched, "error", None)` -> `fetch_error = None` |
  | `fuzz`                   | `ethscan/fuzz.py`: `except Exception` -> `except ValueError`           |
  | `urlcheck`               | `ethscan/ssl.py`: drop `RuntimeError` from the caught tuple            |
  | `cert`                   | `ethscan/cert.py`: `except Exception` -> `except ValueError`           |
  | `geo`                    | `ethscan/geo.py`: `except Exception` -> `except ValueError`            |
  | `mac`                    | `ethscan/mac.py`: `except Exception` -> `except ValueError`            |
  | `s3`                     | `ethscan/s3.py`: `except Exception` -> `except ValueError`             |
  | `cve`                    | `ethscan/cve.py`: `except Exception` -> `except ValueError`            |
  | `subtake`                | `ethscan/subtake.py`: `except (socket.timeout, socket.gaierror, OSError, ValueError)` -> `except (socket.timeout, ValueError)` |

  With the guards restored all ten pass.

- **The checks are hermetic.** The whole file was run with the network
  blocked (a plugin that raises on every `socket.connect` and on every name
  lookup that is not a numeric address): **10 passed**. The plugin was used
  for the proof only and is not part of the repository.

- `python -m pytest tests/` -> **5082 passed, 48 skipped, 2 warnings** (the
  two warnings are the pre-existing `test_main.py` runpy ones; the committed
  baseline was 5072 passed, 48 skipped; the +10 are the checks of the file
  that was rewritten).
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `git diff --check` -> clean. Nothing is committed.

## What remains unresolved

- **The CLI level still has no failure-field check for `trace` and `brute`**
  (and for the aggregators `vuln`, `recon` and `report`, whose modules are
  already covered one level down).
  - `trace`: `tests/test_trace_cli.py` only mocks `run_trace` wholesale, so
    the transport of the command itself is never exercised. The seams are
    `ethscan.trace.socket.gethostbyname` and `ethscan.trace.socket.socket`.
  - `brute`: the seam is `ethscan.brute.FTP` (the `ftplib` class the module
    imported). The SSH path needs paramiko, which is **not installed** in
    this environment.
- **`ethscan/brute.py:110` builds the FTP client outside its guard.**
  `ftp = FTP()` sits before the `try:` of `_attempt_ftp`, and `run_brute`
  appends `future.result()` without catching, so a failure of the constructor
  escapes the command: measured, the CLI exits 1 with a bare
  `RuntimeError('hostile transport')` instead of reporting the failure field.
  A failure of `ftp.connect()` is inside the guard and is reported properly
  (exit 0, `results[0]["error"] == "hostile transport"`).
- **`socket.setdefaulttimeout()` is a process-wide side effect.** The
  resolution helpers of `ethscan/dns.py`, `ethscan/resolve.py`,
  `ethscan/stale.py`, `ethscan/subtake.py` and `ethscan/s3.py` set the
  default timeout of the process. The two CLI sweeps restore it after every
  check; the other test files do not, so a later test inherits a 2s default
  socket timeout.

## Approaches that failed and why

- **The first mutation of the `subtake` check was a no-op.**
  `socket.gaierror` derives from `OSError` (`socket.gaierror.__mro__` is
  `gaierror -> OSError -> Exception`), so dropping `socket.gaierror` from
  the caught tuple of `resolve_cname` changes nothing: the error is still
  caught by `OSError`. The mutation has to drop `OSError` as well to prove
  anything. The same trap applies to every other module that catches
  `OSError`.
- **A check that fails while another process mutates the sources is not
  evidence.** The mutation run and a test run were started in parallel once;
  the test run imported a module that the mutation run was editing at that
  moment and reported a failure that had nothing to do with the code. Run
  the mutation runs alone.

## One precise next task

Extend the permanent CLI-level sweep to the two commands that still open a
transport of their own without a failure-field check at the command line:
`trace` and `brute`.

The method is the one of `tests/test_cli_unreachable_sweep.py` and
`tests/test_cli_http_unreachable_sweep.py`: patch the transport the module
really opens, run the command through `CliRunner`, and assert that it exits
0, leaks no traceback and prints the module's own failure signal.

What is already measured, and can be taken as the expected signal:

- `trace`: patching `ethscan.trace.socket.gethostbyname` with a failure gives
  exit 0, `error="hostile transport"`, `reached=false` and no hop. Patching
  `ethscan.trace.socket.socket` gives exit 0, `error="hostile transport"` and
  a hop whose `error_code` is the failure.
- `brute`: patching `ethscan.brute.FTP` with a stand-in class whose
  `connect` raises gives exit 0, `attempts=1`, `successful_count=0` and
  `results[0]["error"]="hostile transport"`. The command line takes the
  wordlists as `--user-file` and `--pass-file`, not as options.

Constraints:

- Smallest reversible change; do not weaken an existing guard; turn the
  crash into the module's documented error signal.
- Keep the permanent sweeps in the repository.
- The brute check may expose the defect of `ethscan/brute.py:110` (the FTP
  client is built outside the guard). The smallest fix is to build the
  client inside the `try:` of `_attempt_ftp`; the `finally:` already
  suppresses the error of the `close()` of a client that was never built.
- Do not commit unless explicitly asked.
