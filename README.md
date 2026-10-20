# Ethical Hacking

A modular, offline-first ethical hacking toolkit written in Python.

## Features

- **Network reconnaissance and scanning utilities: `scan` command to run a TCP port scan against a target; supports `--target` (host/IP), `--ports` (`common`, `all`, or comma-separated lists/ranges like `80,443,8000-9000`), `--profile` (`fast|normal|full`) to override scan parameters, `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Password strength auditing: `audit` command to audit passwords for strength and common weaknesses; reads from `--file` or stdin, supports `--min-length`, `--salt`/`--pepper`/`--algorithm` for salted/peppered evaluation, `--sort` (`score|verdict|length`) with direction, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Password hash generation: `hash` command to generate password hashes (MD5, SHA-1, SHA-256, SHA-512, NTLM, MD4) for password-audit workflows; supports `--password` (repeatable), `--file` batch input (one password per line), `--algorithm`, `--salt`, `--pepper` (HMAC with hashlib algorithms), `--iterations` (PBKDF2-HMAC when `--salt` is set), `--check` (compare against hex digest), and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Web application security checks: `web` command to run web application security checks against a target URL; runs a configurable set of checks (`--checks` comma-separated: `headers`, `info_disclosure`, `ssl`) reporting security header presence/absence, information disclosure patterns (server version, powered-by, etc.), and optional SSL/TLS certificate inspection; supports `--target` (URL, required), `--checks`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Security headers check: `headers` command for quick security header analysis; supports `--target` (URL), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **ICMP ping: `ping` command for host discovery with ICMP echo requests and TCP connect fallback; supports `--target`, `--count` (default 4), `--timeout` (default 2.0), `--ttl` (default 64), `--tcp-port` (default 80 for fallback), and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **CIDR network calculator: `cidr` command for offline network calculations (network address, netmask, broadcast, host range, membership test, and set difference via `--diff`); supports `--cidr` (required), `--contains` (IP membership test), `--diff` (set difference), and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Radix tree visualization: `radix` command for merging overlapping/supernettable CIDR blocks and rendering a hierarchical binary radix tree; supports `--cidrs`/`--cidr-file`, `--diff`, `--no-merge`, `--max-depth` (default 64), `--contains`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **HTTP fuzzing: `fuzz` command to run HTTP fuzzing against a target URL using a wordlist of paths; supports `--target` (URL), `--wordlist` (path to wordlist file, uses built-in default if omitted), `--timeout`, `--workers` (default 1; concurrent HTTP probing via a thread pool when `> 1`), and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Subdomain enumeration: `subdomains` command to enumerate subdomains for a target; supports `--target` (domain or URL), `--wordlist` (path to wordlist file, uses built-in default if omitted), `--resolver` (custom DNS resolver, requires dnspython), `--recursive`/`--no-recursive`, `--max-depth` (default 2), `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **DNS record enumeration: `dns` command to enumerate DNS records for a target; supports `--target` (URL), `--types` (comma-separated: A, AAAA, MX, NS, TXT, CNAME, SOA), `--server` (custom resolver, requires dnspython), `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **DNS brute force: `dnsbrute` command to attempt AXFR zone transfers against authoritative nameservers and brute-force subdomains for a target; attempts raw AXFR over TCP (default port 53) with optional dnspython fallback, discovers nameservers via NS lookup (requires dnspython) or accepts a comma-separated `--ns` list, concurrently brute-forces subdomain labels against a wordlist (built-in default or `--wordlist` file) reporting resolved A/AAAA records, and supports recursive AXFR (`--recursive`/`--no-recursive`, `--max-depth` default 2); supports `--target` (domain or URL), `--ns`, `--wordlist`, `--resolver` (custom DNS resolver, requires dnspython), `--recursive`/`--no-recursive`, `--max-depth`, `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **WHOIS lookup: `whois` command to query a WHOIS server for a target domain or IP address and parse key registration fields (registrar, creation/expiry dates, nameservers, registrant organization, and status codes); follows referral servers recursively via `--recursive` / `--max-depth` (default: 2); supports `--target`, `--server` (default: whois.iana.org), `--port` (default: 43), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **SSL/TLS certificate inspection: `ssl` command to connect to a target over TLS (default port 443) and inspect the X.509 certificate; extracts subject, issuer, subject alternative names, validity dates, signature algorithm, key size, and chain length, and reports days remaining to expiry; supports `--target` (host or URL), `--port` (default 443), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **TLS protocol/cipher enumeration: `tls` command to enumerate supported TLS protocol versions and cipher suites for a target; runs per-version handshake probes with pinned min/max TLS version and per-cipher probes with a pinned OpenSSL cipher string, reporting the negotiated cipher/protocol and flagging obsolete versions (SSLv3, TLSv1.0, TLSv1.1); supports `--target` (host or URL), `--port` (default 443), `--versions` (comma-separated list to test), `--ciphers` (comma-separated list, defaults to a built-in common set), `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Brute-force login testing: `brute` command to brute-force FTP or SSH login credentials against a target; supports `--target`, `--protocol` (`ftp|ssh`), `--port` (defaults 21/22), `--user-file`, `--pass-file`, `--timeout`, `--workers`, and JSON/Markdown/CSV credential dump output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Service/banner detection: `service` command to detect services and grab banners on open ports (nmap-style); supports `--target`, `--ports` (`common`, `all`, or comma-separated ranges, defaults to common ports), `--profile` (`fast|normal|full`), `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Vulnerability checks: `vuln` command to check targets for known service, protocol, and certificate vulnerabilities against a built-in database; supports `--target`, `--ports` (`common`, `all`, or comma-separated ranges, defaults to common ports), `--services-file` (skip live detection), `--tls-file`, `--ssl-file`, `--severity`/`--min-severity`, `--recursive`/`--no-recursive`, `--max-depth`, `--salt`/`--pepper`/`--algorithm` for salted/peppered banner matching, `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Report generation: `report` command combining port scan and password audit results; supports `--target`, `--ports` (`common`, `all`, or comma-separated ranges, defaults to common ports), `--profile`, `--timeout`, `--workers`, `--audit-file`, `--min-length`, `--salt`/`--pepper`/`--algorithm`, `--open-only`/`--no-open-only`, `--sort` (`score|verdict|length`) with `--sort-desc`/`--sort-asc`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out` (alias `--output`)** (implemented)
- **Consolidated web assessment: `urlcheck` command combining web checks, HTTP fuzzing, and SSL certificate inspection; supports `--target` (required), `--checks` (comma-separated: headers, info_disclosure, ssl), `--wordlist`, `--fuzz-paths`/`--no-fuzz-paths`, `--port` (TLS port for SSL inspection), `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **OS fingerprinting: `osdetect` command using TCP/IP stack behavior analysis and banner cross-referencing; supports `--target`, `--ports` (`common`, `all`, or comma-separated ranges, defaults to common ports), `--banners-file` (JSON from `service`), `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **TCP traceroute: `trace` command using TTL-incremented TCP SYN probes; supports `--target`, `--port` (default 80), `--max-hops` (default 30, max 128), `--probes-per-hop` (default 3), `--timeout`, `--recursive`/`--no-recursive`, `--max-depth` (default 2), and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Wi-Fi reconnaissance: `wifi` command for wireless interface scanning and access point discovery (Linux); supports `--interface`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **IP geolocation: `geo` command for IP-to-location lookup using a public API with caching and offline fallback; supports `--target`, `--recursive`/`--max-depth` (recursive hop geolocation), `--no-cache`, `--no-offline-fallback`, `--api-url`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Consolidated reconnaissance: `recon` command running multiple modules (subdomains, dns, whois, geo, trace) in sequence; supports `--target`, `--modules` (comma-separated, default all), `--subdomains-wordlist`, `--dns-types`, `--dns-server`/`--resolver`, `--whois-server`, `--whois-port`, `--no-geo-cache`, `--no-geo-offline-fallback`, `--geo-api-url`, `--trace-port`/`--trace-max-hops`/`--trace-probes-per-hop`, `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Certificate Transparency log search: `cert` command to discover subdomains via CT logs (crt.sh-compatible APIs) with caching and offline fallback; supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **CVE lookup: `cve` command to query the NVD/CVE API for known vulnerabilities affecting detected service versions, with a built-in CVE/weakness database cross-reference, caching, offline fallback; supports `--target`, `--services-file`, `--ports` (`common`, `all`, or comma-separated ranges, defaults to common ports), `--profile`, `--timeout`/`--service-timeout`, `--workers`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`/`--min-severity`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Subdomain takeover detection: `subtake` command to detect subdomain takeover vulnerabilities by checking CNAME records against known vulnerable cloud services, with `--target`, `--wordlist`, `--resolver`, `--timeout`, `--workers`, `--http-timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Password hash checking: `hash --check DIGEST` to compare a plaintext password against a known hash digest, with algorithm inference from digest length or explicit `--algorithm`, reporting MATCH/MISMATCH/UNKNOWN in JSON, Markdown, or CSV** (implemented)
- **Salted & peppered hashing: `hash --salt SALT` (prepend salt before hashing) and `hash --pepper PEPPER` (HMAC keyed hash, e.g. HMAC-SHA-256); combinable for `HMAC(pepper, salt+password, algo)`. Both options also work in `--check` mode to verify salted/peppered digests. JSON/Markdown/CSV output available.** (implemented)
- **Configuration management: `config` command to inspect or initialize the `ethscan.yaml` config file; persists default options across commands (global `defaults` plus per-command overrides); supports `--config` (path to config file), `--init` (write sample config to path), `--format`/`--output-format` for loaded config, and `--out`** (implemented)
- **MAC address vendor lookup: `mac` command to look up OUI vendor information via public API (api.macvendors.com) with filesystem caching, offline fallback, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **DNSSEC validation: `dnssec` command for DNSSEC validation of a domain's DNS records (check DS records, validate chain of trust, report algorithm/key details); supports `--target`, `--server` (custom resolver), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Shell completion: `completion` command to generate bash/zsh/fish completion scripts for interactive tab completion of commands, options, and option values; supports `--shell` (`bash|zsh|fish`, default bash), `--prog-name` (default ethscan), and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **JWT inspection: `jwt` command to decode and analyze JWT tokens (header, claims, algorithm type, expiration/not-before/issued-at status, security findings like alg=none and expired tokens) without verifying the signature, with JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Port & CIDR validation: `validate` command to validate and expand port specifications (comma-separated lists/ranges) and CIDR inputs offline, with JSON, Markdown, or CSV output** (implemented)
- **DNS resolution: `resolve` command for forward/reverse DNS resolution of a target (A, AAAA, CNAME, PTR record types), with optional custom resolver and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Nmap XML parser: `nmap` command to parse Nmap XML scan output (`-oX`) and cross-reference detected service versions against the built-in vulnerability database, producing a consolidated report of matched CVEs in JSON, Markdown, or CSV** (implemented)
- **Stale DNS detection: `stale` command to detect stale DNS records (A/AAAA/CNAME) pointing to deallocated or unresolvable IPs/dead cloud resources; supports `--target` (can be specified multiple times), `--file` (one domain per line), `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **SSH security assessment: `ssh` command to enumerate supported key exchange algorithms, ciphers, MACs, and host key types on a target SSH server; check for weak/deprecated algorithms (e.g., `diffie-hellman-group1-sha1`, `arcfour`, `3des-cbc`, `ssh-rsa`); report host key fingerprint and algorithm; supports `--target` (host:port), `--port`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`; stdlib-only with optional `paramiko` for host key details** (implemented)
- **AWS S3 bucket enumeration: `s3` command to detect publicly accessible S3 buckets via HTTP probing of generated candidate bucket names (from the target domain with optional `--wordlist`); supports `--target`, `--wordlist`, `--region` (including `all`), `--timeout`, `--workers`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **SMTP reconnaissance: `smtp` command to grab the server banner, enumerate supported capabilities via `EHLO` (including STARTTLS support), optionally probe users with `VRFY` (`--users`), and check for open relays; supports `--target` (host or host:port), `--port`, `--users`, `--timeout`, `--no-starttls-check`/`--no-relay-check`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **FTP reconnaissance: `ftp` command to grab the server banner/greeting and attempt an anonymous-login probe (`USER anonymous` / `PASS anonymous@`); supports `--target` (host, host:port, or URL), `--port`, `--no-anonymous-check`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **NTP reconnaissance: `ntp` command to send an NTP time request (mode 3) and a monlist request (mode 7, implementation 42) to detect vulnerable/reflector NTP servers susceptible to amplification attacks; reports stratum, refid, root delay/dispersion, reference timestamp, peer count, reflector status, and amplification factor; supports `--target` (host, host:port, or URL), `--port`, `--no-monlist-check`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **SNMP reconnaissance: `snmp` command to send SNMP GET requests (stdlib-only raw BER encoding) for standard MIB-II OIDs (sysDescr, sysObjectID, sysUpTime, sysName) and probe common community strings (public, private, default, empty) to identify valid/misconfigured community strings; reports SNMP version detection (v1/v2c), per-community validity, and system information; supports `--target` (host, host:port, or URL), `--port`, `--communities`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **NetBIOS reconnaissance: `netbios` command to send an NBNS NODE STATUS request (UDP 137, stdlib-only raw RFC 1002 packet encoding) for a target NetBIOS name (default ``"*"`` to enumerate all registered names) and parse the NBSTAT response for the MAC address (``Unit ID``) and the name table with per-name service suffix, name flags (group/unique, permanent/active, owner node type, conflict/deregister), and registered-name heuristics (file-server/server detection, hostname, domain membership); supports `--target` (host, host:port, or URL), `--port`, `--name`, `--suffix`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Redis reconnaissance: `redis` command to probe Redis servers via RESP over TCP (PING, INFO server, CONFIG GET *) to detect accessible instances; reports server info (version, OS, arch, process id, role, connected clients), configuration highlights, and dangerous findings (bind 0.0.0.0, no requirepass, writable dir); supports `--target` (host, host:port, or redis:// URL), `--port`, `--probes`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **SMB/CIFS reconnaissance: `smb` command to perform an SMB1 `SMB_COM_NEGOTIATE` dialect probe (stdlib-only `socket`/`struct` raw packet crafting) over TCP; reports whether an SMB1 endpoint is accessible, the negotiated dialect (or no-common-dialect), server security mode, message-signing policy (required/enabled), and NTLMSSP presence/challenge; with `--smb2` it also runs an SMB2/SMB3 `SMB2_NEGOTIATE` probe (protocol id `\xfeSMB`, dialects 2.0.2/2.1/3.0/3.0.2/3.1.1, preauth-integrity negotiate context for 3.1.1) and reports the negotiated dialect/version, security mode, ServerGUID, capabilities, and negotiate contexts (preauth hash algorithm, encryption ciphers) on modern hosts with SMB1 disabled; supports `--target` (host, host:port, or smb:// URL), `--port` (default 445), `--smb2/--no-smb2`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **LDAP reconnaissance: `ldap` command to probe LDAP servers with an anonymous BindRequest (RFC 4511, stdlib-only BER encoding) plus a RootDSE search; reports whether anonymous bind is allowed, the bind result code/name, matched DN, diagnostic message, and server identity from the RootDSE (vendor name/version, naming contexts, supported LDAP versions, SASL mechanisms, controls); LDAPS implied by `ldaps://` URLs or port 636 (TLS-wrapped, cert verification disabled as a recon probe); supports `--target` (host, host:port, or ldap:// URL), `--port` (default 389), `--ldap-version [2|3]`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Memcached reconnaissance: `memcached` command to probe Memcached servers via the text protocol over TCP 11211; runs a `version` probe (reports memcached version string) and a `stats` probe (parses STAT lines into structured map: uptime, bytes, current connections, command counters, hit/miss ratios, evictions); identifies noteworthy conditions (evictions, zero hits with misses, unbounded cache); supports `--target` (host, host:port, or memcached:// URL), `--port` (default 11211), `--probes` (comma-separated: version,stats), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **MySQL reconnaissance: `mysql` command to probe MySQL/MariaDB servers over TCP 3306 by reading the initial handshake packet (Protocol::HandshakeV10); extracts `server_version`, `protocol_version`, `thread_id`, capabilities, charset, status, and auth plugin; flags old versions (5.0/5.1/4.x) and MariaDB; supports `--target` (host, host:port, or mysql:// URL), `--port` (default 3306), `--probes` (default: handshake), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **MongoDB reconnaissance: `mongodb` command to probe MongoDB servers over TCP 27017 by sending a `buildInfo` command via the MongoDB Wire Protocol (OP_QUERY); extracts `version`, `sysInfo`, `modules`, and `versionArray`; flags old versions (2.0-2.6); supports `--target` (host, host:port, or mongodb:// URL), `--port` (default 27017), `--probes` (default: buildInfo), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **PostgreSQL reconnaissance: `postgresql` command to probe PostgreSQL servers over TCP 5432 by sending a minimal wire-protocol `StartupMessage` (protocol 3.0) and parsing the server greeting; extracts `server_version` from `ParameterStatus` messages, the authentication method/type from the `Authentication` message, and the backend process id from `BackendKeyData` -- no login or password is sent; flags old versions (major < 10) and trust/no-credential auth; supports `--target` (host, host:port, or postgresql:// / postgres:// URL), `--port` (default 5432), `--probes` (default: startup), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **MSSQL reconnaissance: `mssql` command to probe MSSQL servers over TCP 1433 by sending a TDS PRELOGIN message and parsing the server response; extracts `version`, `encryption` support, `instance_name`, and `thread_id` (SPID) -- no login or password is sent; supports `--target` (host, host:port, or mssql:// / ms-sql:// URL), `--port` (default 1433), `--probes` (default: prelogin), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)

- **Oracle reconnaissance: `oracle` command to probe Oracle TNS listeners over TCP 1521 by sending a TNS Connect request and parsing the server response; extracts `version` from the Accept packet -- no login is attempted; supports `--target` (host, host:port, or oracle:// / tns:// URL), `--port` (default 1521), `--probes` (default: version), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)

## Configuration

ethscan reads an optional YAML config file that persists default options across commands. The file may live in the current working directory (`ethscan.yaml` / `ethscan.yml`) or in your home directory (`~/.ethscan.yaml` / `~/.ethscan.yml`).

```yaml
# Global defaults applied to every command that does not override them.
defaults:
  timeout: 5.0
  workers: 50
  format: json

# Per-command overrides (keys are Click option dest names).
commands:
  scan:
    ports: common
    profile: normal
    timeout: 1.0
    workers: 100
  subdomains:
    timeout: 3.0
    resolver: 8.8.8.8
```

CLI arguments always take precedence over config values. Use `ethscan config --init PATH` to write a sample config file, or `ethscan config` to inspect the loaded configuration.

## Caching

The `geo`, `cert`, `mac` and `cve` commands keep a cache in `~/.cache/ethscan`
(`geo_cache.json`, `cert_cache.json`, `mac_cache.json`, `cve_cache.json`) so
that a lookup is not repeated while the API is reachable. Use `--no-cache` to
turn the cache off, and `--no-offline-fallback` to stop a stale entry from
being used when the API cannot be reached.

The cache is written by ethscan itself, so a cache file that cannot be used is
never an error: a file that is not valid JSON, that is not a JSON object, that
holds an entry that is not a mapping, or that holds a timestamp that is not a
finite number is treated as an empty cache. An entry that cannot be checked is
never served as fresh; it can only be used as stale data through the offline
fallback, which says so in the output.

## Requirements

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m ethscan --help
```

Invalid option values are reported as usage errors (exit code 2) instead of
Python tracebacks. A malformed `--ports` specification, for example, gives:

```console
$ python -m ethscan scan --target 127.0.0.1 --ports bogus
Usage: python -m ethscan scan [OPTIONS]
Try 'python -m ethscan scan --help' for help.

Error: Invalid value for '--ports': Invalid port number 'bogus'
```

The same applies to the CIDR options of the `cidr` and `radix` commands:

```console
$ python -m ethscan cidr --cidr bogus
Usage: python -m ethscan cidr [OPTIONS]
Try 'python -m ethscan cidr --help' for help.

Error: Invalid value for '--cidr': 'bogus/128' does not appear to be an IPv4 or IPv6 network
```

A `radix` tree covers a single address family, so mixing IPv4 and IPv6
networks in one `--cidrs` list is rejected as well:

```console
$ python -m ethscan radix --cidrs 192.168.1.0/24,2001:db8::/32
Usage: python -m ethscan radix [OPTIONS]
Try 'python -m ethscan radix --help' for help.

Error: Invalid value for '--cidrs': Cannot mix IPv4 and IPv6 networks in a single radix tree
```

A `--target` that does not contain a usable host is rejected the same way by
the protocol commands (`redis`, `memcached`, `ntp`, `snmp`, `ftp`, `ldap`,
`netbios`, `smb`, `smtp`):

```console
$ python -m ethscan redis --target ""
Usage: python -m ethscan redis [OPTIONS]
Try 'python -m ethscan redis --help' for help.

Error: Invalid value for '--target': Could not parse host from target ''
```

A `--target` whose port is not a number is rejected the same way. This
applies to the protocol commands above and to the commands that read the
target as a URL (`web`, `headers`, `urlcheck`, `ssh`, `fuzz`):

```console
$ python -m ethscan web --target "host:notaport"
Usage: python -m ethscan web [OPTIONS]
Try 'python -m ethscan web --help' for help.

Error: Invalid value for '--target': Port could not be cast to integer value as 'notaport'
```

A `--target` whose host contains a space or a control character is rejected
the same way. This applies to the commands that turn a target into a host
(`web`, `headers`, `urlcheck`, `fuzz`, `s3`):

```console
$ python -m ethscan web --target "host name"
Usage: python -m ethscan web [OPTIONS]
Try 'python -m ethscan web --help' for help.

Error: Invalid value for '--target': Target host contains a space or control character
```

The path and the query of a `--target` are validated the same way. A target
whose path or query contains a space or a control character is rejected, but a
fragment (`#...`) is not, because it is never sent to the server. This applies
to the commands that send the raw target to the server (`web`, `headers`,
`urlcheck`):

```console
$ python -m ethscan web --target "https://example.com/a b"
Usage: python -m ethscan web [OPTIONS]
Try 'python -m ethscan web --help' for help.

Error: Invalid value for '--target': Target path contains a space or control character
```

The `validate` command is the exception: it reports invalid specifications
inside its own JSON/CSV output and still exits 0. The same holds for the
`mysql`, `mongodb`, `oracle`, `postgresql` and `mssql` commands, whose
contract is "the probe failed" rather than "the option is invalid": they
report an unusable target inside their own output and still exit 0.

The `trace` command rejects a target without a usable host the same way:

```console
$ python -m ethscan trace --target ""
Usage: python -m ethscan trace [OPTIONS]
Try 'python -m ethscan trace --help' for help.

Error: Invalid value for '--target': Invalid target
```

The `recon` and `geo` commands run the traceroute as one of their modules,
so they report the same problem in their own output and still exit 0.

The `s3` command reports an unusable target inside its own output, because
its contract is "the probe failed". A candidate that cannot be an S3 bucket
name is reported as a failed probe instead of being requested, and a probe
that fails never aborts the report of the other candidates:

```console
$ python -m ethscan s3 --target "[::1]:443"
{
  "bucket": "::1",
  "region": "us-east-1",
  "url": "https://::1.s3.amazonaws.com/",
  "dns_resolved": null,
  "status_code": null,
  "exists": false,
  "public": false,
  "error": "Invalid bucket name: contains characters that are not allowed in a bucket name"
}
```

A port outside 0-65535 is refused the same way in both forms of a target,
the bare `host:port` and the scheme-qualified `redis://host:port`:

```console
$ python -m ethscan redis --target "example.com:99999"
Usage: python -m ethscan redis [OPTIONS]
Try 'python -m ethscan redis --help' for help.

Error: Invalid value for '--target': Port out of range 0-65535
```

The `mysql`, `mongodb`, `oracle`, `postgresql` and `mssql` commands report
the same problem inside their own output and still exit 0.

The options that take a file are checked for the path they name (a missing
file or a directory is a usage error) and for the content they hold. A JSON
file that is not JSON, a JSON file that holds something else than an object
and an Nmap XML file that is not XML are usage errors as well:

```console
$ python -m ethscan vuln --target example.com --services-file broken.json
Usage: python -m ethscan vuln [OPTIONS]
Try 'python -m ethscan vuln --help' for help.

Error: Invalid value for '--services-file': Expecting value: line 1 column 1 (char 0)
```

```console
$ python -m ethscan nmap --input-file broken.xml
Usage: python -m ethscan nmap [OPTIONS]
Try 'python -m ethscan nmap --help' for help.

Error: Invalid value for '--input-file': invalid Nmap XML: syntax error: line 1, column 0
```

A text file (a wordlist, a list of domains, a list of CIDR networks) is read
as UTF-8. The bytes that are not valid UTF-8 are replaced, so a file with a
stray byte is used as far as it can be read. The standard input of the
commands that read one (`audit`, `hash`, `jwt`) is read the same way. A file
that holds credentials (`--file`, `--user-file`, `--pass-file`,
`--audit-file`) is refused instead, because its content cannot be read
without changing the credentials it holds:

```console
$ python -m ethscan audit --file passwords.txt
Usage: python -m ethscan audit [OPTIONS]
Try 'python -m ethscan audit --help' for help.

Error: Invalid value for '--file': the file is not valid UTF-8
```

## Disclaimer

This project is for **authorized security testing only**. Use only against
systems you own or have explicit written permission to test.
