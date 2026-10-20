# HANDOFF: state for the next agent

## What changed this session

- **`ethscan/smtp.py`**:
  - new helper `_reply_code()` (`ethscan/smtp.py:79-92`) that only reads
    a reply code when the text is ASCII digits, used by
    `_parse_smtp_response()` (`ethscan/smtp.py:102`). Before the fix the
    code was read with `int(first[:3]) if first[:3].isdigit() else 0`,
    and `str.isdigit()` accepts the Unicode superscript digits that
    `int()` refuses.
  - the EHLO capability parser (`ethscan/smtp.py:253-262`) no longer
    reads a fixed index into an empty list: it splits the rest of the
    line and skips a line that holds no word.
  - the probe block of `run_smtp()` (`ethscan/smtp.py:316-319`) now has
    an `except Exception` that reports the failure through the `error`
    field. It had a `finally` but no `except`, so every exception raised
    by a server answer reached the command line as a raw traceback.
- **`tests/test_smtp.py`**: 6 regression tests. The fake SMTP server
  learned two optional config keys (`ehlo_response`, `mail_response`)
  so a hostile answer can be served over a real socket.

The fix and the tests are committed (`fix(smtp): a hostile server answer
no longer crashes the command`). The baseline is clean.

## What was actually verified

- Reproduction before the fix: `ethscan smtp --target <host>` exited 1
  with `IndexError: list index out of range` (a server that answers
  EHLO with `250-   \r\n250 OK\r\n`) and with `ValueError: invalid
  literal for int() with base 10: '²²²'` (a server that answers
  `MAIL FROM` with `²²² 5.7.1 blocked`). Both are reachable with the
  default options, so no flag is needed to trigger them. After the fix
  the same answers are parsed and the command exits 0.
- 5 of the 6 new tests fail on the unfixed module (`git stash push --
  ethscan/smtp.py`). The 6th is a control that pins that an ordinary
  reply code is still read as a number.
- The two parser fixes are each necessary: with only the new
  `except Exception` net and the old parsers, 4 of the new tests still
  fail.
- `python -m ruff check ethscan/ tests/` → **All checks passed**.
- `python -m pytest tests/test_smtp.py -q` → **59 passed** (was 53).
- `python -m pytest -q` → **4572 passed, 48 skipped, 2 warnings**
  (was 4566).
- `git diff --check` → clean.

## The sweep that was asked for, and its result

The previous handoff asked for a sweep of the server-answer parsers for
the netbios class of bug (a fixed index into a decoded buffer, or an
exception type the module's guard does not catch). The candidate list
was **incomplete**: the two bugs that exist are in `ethscan/smtp.py`,
which was not on it.

### The candidate list of the previous handoff is now verified clean

Every parser on that list was swept with a *structurally valid* answer
per protocol, then mutated:

| Sweep | Coverage | Result |
| --- | --- | --- |
| Truncation + mutation, end-to-end | 13 modules (`mysql`, `mssql`, `ntp`, `redis`, `postgresql`, `oracle`, `mongodb`, `ldap`, `smb2`, `smb`, `memcached`, `snmp`, `netbios`): the answer truncated at **every** length, every single byte overwritten with `0x00`/`0xFF`/`0x7F`/`0x01`, every 2-byte and 4-byte window set to `0xFFFF`/`0xFFFFFFFF` | 0 escaping failures |
| Random mutation, parser level | 17 parsers, 20 000 random mutations each | 0 non-`ValueError` failures |
| Random mutation, parser level | `dnssec._parse_dnskey_response`, `dnssec._parse_ds_response`, `dnsbrute.parse_dns_response`, 40 000 mutations each | 0 failures |
| Static | every `int()` call site (61), every `struct.unpack` slice length, every fixed `X[N]` index, every `split()[N]` index | no other unguarded site |

`mysql`, `mssql`, `ntp`, `redis`, `postgresql`, `oracle`, `mongodb`,
`ldap`, `smb`, `memcached`, `snmp` and `netbios` are therefore clean for
this class of bug, with the evidence above. The three parsers that
raised a `ValueError` (`ldap._parse_attribute`,
`ldap._parse_search_entry`, `snmp._parse_snmp_message`) raise the type
their callers catch.

### Approaches that failed and why

- **Random / byte-level fuzzing does NOT find this class of bug.** This
  was checked, not assumed: the random fuzzer was pointed at the
  *known* netbios bug (the `_decode_name_chars` fix reverted in memory)
  and it did **not** find it. The bug needs a *structurally valid* short
  name (a 2-byte label followed by `0x00`); a random mutation of a
  valid packet almost never produces one, and the mutation of the length
  byte alone produces an odd-length name that is rejected for a
  different reason. Do not repeat a random fuzzer expecting it to find
  the next one.
- **A generic "feed hostile bytes to every parser" probe does not find
  it either** (the previous handoff already recorded this). It only
  reports parsers that raise, and every one of them except netbios
  raised the `ValueError` their caller catches.
- **The method that works** is the one the previous handoff described:
  craft an answer that is *structurally valid* for the protocol but
  holds a hostile field, then call the module's `run_<module>` with it
  (every module that takes one has an injectable
  `connector(host, port, request, timeout)`) and assert that the command
  answers with an `error` field instead of raising. The two bugs found
  this session were found by *reading* the parsers, not by fuzzing them:
  the shape to look for is an operation on server text whose failure
  mode is not a `ValueError` (`int()` on a non-decimal digit string, an
  index into a list that can be empty, `struct.unpack` on a short
  buffer, an `IndexError` on a slice).

## What remains unresolved

- **The commit before the netbios fix (`91ce9aa`, empty message) is
  still untested and behaviourally almost neutral.** It made `cert`,
  `cve`, `geo`, `jwt` and `mac` decode their HTTP responses with
  `errors="replace"` and to catch the JSON error. The only behavioural
  difference is `mac`: a body with a byte that is not UTF-8 now yields
  the replaced text as the vendor instead of a failed fetch. There is no
  test for it. It is not worth a rework; a single regression test for
  the `mac` vendor text would be enough if someone wants to close it.
- **The file-input surface is exhausted**: the file-option, file-content,
  config-value and cache-content sweeps cover it, and the previous
  session verified that no strict `open(...)` read is left in
  `ethscan/`.
- **`run_smtp()` is the only `run_<module>()` of a protocol module that
  had no `except` net around its probe block** at the time of this
  session; it has one now. The other protocol modules without such a
  net (`run_redis`, `run_memcached`, `run_ntp`, `run_ldap`,
  `run_smb2`/`run_smb`, `run_snmp`, `run_dnssec`, `run_ssh`) are clean
  today, but a future bug in their parsers would crash the command
  instead of being reported. Adding the net to them is a behaviour
  change and was deliberately left out of this session's small fix.

## One precise next task

**Sweep the text-protocol and HTTP answer parsers for the same class of
bug.** The binary protocol parsers are now verified clean, and the two
bugs that were found live in a *text* protocol, so that is where the
remaining surface is. A server's answer here is text or JSON, and the
operations that fail on it are string operations, not buffer offsets.

### Result of that sweep (complete)

The sweep was run and it found **two** bugs, both in the dnspython answer
sets of the DNS modules, and both are the same shape as the netbios bug:
an index into a list that can be empty, where the failure mode
(`IndexError`) is not the type the module's guard catches
(`dns.exception.DNSException, OSError, ValueError`).

- **`ethscan/subtake.py:298-303`** and **`ethscan/subdomains.py:102-107`**:
  `resolve_cname` and `resolve_subdomain` read `answers[0]` from the result
  of `dns_resolver.resolve(...)`. A server that answers an A or CNAME query
  with no records returns an empty list, and `str(answers[0])` raised
  `IndexError: list index out of range`. Both now return the module's
  documented failure signal (`None`, or `(subdomain, None)`) when the
  answer set is empty, and `IndexError` was added to the guard. The fix is
  committed as `fix(dns): an empty dnspython answer set no longer crashes
  the command` (`7f0c7b0`).

The rest of the candidate list was inspected and is clean:

| Module | Surface | Note |
| --- | --- | --- |
| `whois.py` | `parse_whois` (61), `extract_referral_server` (127) | regex over the raw answer; `match.group(1)` is only used when `re.search` matched, and the `sorted({...})` of the nameserver set iterates a `re.findall` list that is always iterable. No unguarded index or uncaught exception type. |
| `web.py` | `fetch_headers` (69), `check_security_headers` (98), `check_information_disclosure` (123) | the header dict comes from `urllib`; every value is used as a string. `check_ssl_configuration` already guards `cert.get("subject", ())` with `isinstance(item, tuple) and len(item) >= 2` and catches the `strptime` failure. |
| `headers.py` | `run_headers` (10) | delegates to `web.py`; nothing of its own. |
| `cert.py` | `_fetch_cert_data` (97) | the JSON answer is validated with `isinstance(data, list)` before iteration; `_extract_subdomains` skips entries that are not dicts. No `float(entry["timestamp"])` site is reachable from a server answer (only from the cache, which the module itself wrote and validates). |
| `cve.py` | `_fetch_cve_data` (101) | `vulns[0]` is guarded by `if not vulns: return {}` and `isinstance(first, dict)`; `descriptions[0]` is guarded by `if not description and descriptions and isinstance(descriptions[0], dict)`. |
| `geo.py` | `_fetch_geo_data` (115) | the JSON answer is only consumed after `data.get("status") == "success"`; no numeric cast of a server value. |
| `jwt.py` | `_decode_json_segment` (47), `parse_jwt` (59) | the segments come from a token the user typed, not a server; `parts[0]`/`parts[1]` are guarded by the `len(parts) in (2, 3)` check. |
| `mac.py` | `_fetch_mac_data` (99) | the vendor text is a plain string; no numeric cast. |
| `s3.py` | `check_bucket_public` (241) | the status code is read with `response.getcode()` and matched against literal constants; the `HTTPError`/`URLError`/`HTTPException` clauses are exhaustive for the urllib failure modes. |
| `urlcheck.py` | `run_urlcheck` (29) | delegates to `web`, `fuzz`, `ssl`; no parser of its own. |
| `subtake.py`, `stale.py`, `subdomains.py`, `resolve.py`, `dns.py` | the `dnspython` answer sets | `subtake.resolve_cname` and `subdomains.resolve_subdomain` are now fixed. `subtake.resolve_a_records`/`resolve_aaaa_records`, `resolve.resolve_cname_records`/`resolve_ptr_records`/`resolve_with_dnspython`, `dns.resolve_with_dnspython`, and `dnsbrute` iterate the answer set with a generator (`sorted({str(rdata) for rdata in answers})`), so an empty set yields `[]` and never indexes. |

The only remaining unguarded `answers[0]` sites in `ethscan/` are the two
that were fixed this session. The binary-protocol sweep recorded above
and the text/HTTP sweep recorded here together cover every parser in
`ethscan/`.

Method that found this session's two bugs (keep it): read the parser and
ask *what operation on the server's text can fail with an exception the
module does not catch*. The three that paid off here were
`int()` on a string that `str.isdigit()` accepts but `int()` refuses
(the repository already knows this trap: `ethscan/target.py:112-139`,
`check_port`, documents it for ports), an index into a list that can be
empty, and an exception type that the guard lists explicitly and
narrowly.

Constraints: keep the smallest reversible change (turn the crash into the
module's documented error signal, or report the malformed value the way
the module already reports malformed values), add the regression test
next to the module's own tests, and do not weaken an existing guard.
The `smtp` fix is the template: a status line that is not a valid reply
code is now reported as code `0`, like any other non-numeric line, and a
capability line without a keyword is skipped, not indexed.
