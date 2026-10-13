# Ethical Hacking

A modular, offline-first ethical hacking toolkit written in Python.

## Features

- Network reconnaissance and scanning utilities (implemented)
- Password strength auditing with JSON/Markdown/CSV output (`audit`) (implemented)
- **Password hash generation: `hash` command for MD5, SHA-1, SHA-256, SHA-512, NTLM, and MD4 hashing with `--algorithm` selection and JSON/Markdown output** (implemented)
- Web application security checks (implemented)
- **Security headers check: `headers` command for quick security header analysis** (implemented)
- **ICMP ping: `ping` command for host discovery with ICMP echo requests and TCP connect fallback** (implemented)
- **CIDR network calculator: `cidr` command for offline network calculations (network address, netmask, broadcast, host range, membership test, and set difference via `--diff`)** (implemented)
- **Radix tree visualization: `radix` command for merging overlapping/supernettable CIDR blocks and rendering a hierarchical binary radix tree** (implemented, `--contains` option for IP membership testing)
- HTTP fuzzing (implemented)
- Subdomain enumeration (implemented)
- DNS record enumeration (implemented)
- DNS brute force: AXFR zone transfer attempts + subdomain brute forcing (implemented)
- WHOIS lookup (implemented)
- SSL/TLS certificate inspection (implemented)
- TLS protocol/cipher enumeration (implemented)
- Brute-force login testing (FTP/SSH) with `--output-format csv` for credential dumps (implemented)
- Service/banner detection (implemented)
- Vulnerability checks against a built-in CVE/weakness database, with `--severity`, `--min-severity`, `--recursive/--no-recursive`, `--max-depth`, `--salt`/`--pepper`/`--algorithm` for salted & peppered banner matching, and JSON/Markdown output (implemented)
- Report generation (`report` command combining port scan + password audit, with `--output-format [json|markdown|csv]`, `--open-only` to filter scan results to open ports only, `--sort {score|verdict|length} [--sort-asc|--sort-desc]` to reorder audit rows) (implemented)
- Consolidated web assessment: `urlcheck` command combining web checks, HTTP fuzzing, and SSL certificate inspection (implemented)
- OS fingerprinting: `osdetect` command using TCP/IP stack behavior analysis, banner cross-referencing, and TTL-based inference (implemented)
- TCP traceroute: `trace` command using TTL-incremented TCP SYN probes with per-hop IP/RTT reporting (implemented)
- Wi-Fi reconnaissance: `wifi` command for wireless interface scanning and access point discovery (Linux, implemented)
- IP geolocation: `geo` command for IP-to-location lookup using a public API with caching and offline fallback (implemented)
- Consolidated reconnaissance: `recon` command running multiple modules (subdomains, dns, whois, geo, trace) in sequence with a unified report (implemented)
- Certificate Transparency log search: `cert` command to discover subdomains via CT logs (crt.sh-compatible APIs) with caching and offline fallback (implemented)
- CVE lookup: `cve` command to query the NVD/CVE API for known vulnerabilities affecting detected service versions, with a built-in CVE/weakness database cross-reference, caching, offline fallback, JSON/Markdown output, `--out`, `--severity`, and `--min-severity` (implemented)
- Subdomain takeover detection: `subtake` command to detect subdomain takeover vulnerabilities by checking CNAME records against known vulnerable cloud services, with `--output-format [json|markdown|csv]` (implemented)
- **Password hash generation: `hash` command to generate password hashes (MD5, SHA-1, SHA-256, SHA-512, NTLM, MD4) for password-audit workflows with `--password` flags, `--file` batch input (one password per line), and JSON/Markdown output** (implemented)
- **Password hash checking: `hash --check DIGEST` to compare a plaintext password against a known hash digest, with algorithm inference from digest length or explicit `--algorithm`, reporting MATCH/MISMATCH/UNKNOWN in JSON or Markdown** (implemented)
- **Salted & peppered hashing: `hash --salt SALT` (prepend salt before hashing) and `hash --pepper PEPPER` (HMAC keyed hash, e.g. HMAC-SHA-256); combinable for `HMAC(pepper, salt+password, algo)`. Both options also work in `--check` mode to verify salted/peppered digests.** (implemented)
- Configuration file: `ethscan.yaml` (or `~/.ethscan.yaml`) to persist default options across commands (global `defaults` plus per-command overrides); `ethscan config` command to inspect or initialize the config (implemented)
- **MAC address vendor lookup: `mac` command to look up OUI vendor information via public API (api.macvendors.com) with filesystem caching, offline fallback, and JSON/Markdown output** (implemented)
- **DNSSEC validation: `dnssec` command for DNSSEC validation of a domain's DNS records (check DS records, validate chain of trust, report algorithm/key details)** (implemented)
- **Shell completion: `completion` command to generate bash/zsh/fish completion scripts for interactive tab completion of commands, options, and option values** (implemented)
- **JWT inspection: `jwt` command to decode and analyze JWT tokens (header, claims, algorithm type, expiration/not-before/issued-at status, security findings like alg=none and expired tokens) without verifying the signature, with JSON/Markdown output** (implemented)
- **Port & CIDR validation: `validate` command to validate and expand port specifications (comma-separated lists/ranges) and CIDR inputs offline, with JSON, Markdown, or CSV output** (implemented)
- **DNS resolution: `resolve` command for forward/reverse DNS resolution of a target (A, AAAA, CNAME, PTR record types), with optional custom resolver and JSON/Markdown output** (implemented)
- **Nmap XML parser: `nmap` command to parse Nmap XML scan output (`-oX`) and cross-reference detected service versions against the built-in vulnerability database, producing a consolidated report of matched CVEs in JSON, Markdown, or CSV** (implemented)
- **Stale DNS detection: `stale` command to detect stale DNS records (A/AAAA/CNAME) pointing to deallocated or unresolvable IPs/dead cloud resources, with configurable timeout, concurrency, and JSON/Markdown/CSV output** (implemented)
- **SSH security assessment: `ssh` command to enumerate supported key exchange algorithms, ciphers, MACs, and host key types on a target SSH server; check for weak/deprecated algorithms (e.g., `diffie-hellman-group1-sha1`, `arcfour`, `3des-cbc`, `ssh-rsa`); report host key fingerprint and algorithm; supports `--target` (host:port), `--timeout`, `--format [json|markdown]`, `--out`; stdlib-only with optional `paramiko` for host key details** (implemented)
 - **AWS S3 bucket enumeration: `s3` command to detect publicly accessible S3 buckets via HTTP probing of generated candidate bucket names (from the target domain with optional `--wordlist`); supports `--region` (including `all`), `--timeout`, `--workers`, `--format [json|markdown]`, and `--out`** (implemented)
  - **SMTP reconnaissance: `smtp` command to grab the server banner, enumerate supported capabilities via `EHLO` (including STARTTLS support), optionally probe users with `VRFY` (`--users`), and check for open relays; supports `--target` (host or host:port), `--port`, `--users`, `--timeout`, `--no-starttls-check`/`--no-relay-check`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
  - **FTP reconnaissance: `ftp` command to grab the server banner/greeting and attempt an anonymous-login probe (`USER anonymous` / `PASS anonymous@`); supports `--target` (host, host:port, or URL), `--port`, `--no-anonymous-check`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
  - **NTP reconnaissance: `ntp` command to send an NTP time request (mode 3) and a monlist request (mode 7, implementation 42) to detect vulnerable/reflector NTP servers susceptible to amplification attacks; reports stratum, refid, root delay/dispersion, reference timestamp, peer count, reflector status, and amplification factor; supports `--target` (host, host:port, or URL), `--port`, `--no-monlist-check`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
   - **SNMP reconnaissance: `snmp` command to send SNMP GET requests (stdlib-only raw BER encoding) for standard MIB-II OIDs (sysDescr, sysObjectID, sysUpTime, sysName) and probe common community strings (public, private, default, empty) to identify valid/misconfigured community strings; reports SNMP version detection (v1/v2c), per-community validity, and system information; supports `--target` (host, host:port, or URL), `--port`, `--communities`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
   - **NetBIOS reconnaissance: `netbios` command to send an NBNS NODE STATUS request (UDP 137, stdlib-only raw RFC 1002 packet encoding) for a target NetBIOS name (default ``"*"`` to enumerate all registered names) and parse the NBSTAT response for the MAC address (``Unit ID``) and the name table with per-name service suffix, name flags (group/unique, permanent/active, owner node type, conflict/deregister), and registered-name heuristics (file-server/server detection, hostname, domain membership); supports `--target` (host, host:port, or URL), `--port`, `--name`, `--suffix`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
   - **Redis reconnaissance: `redis` command to probe Redis servers via RESP over TCP (PING, INFO server, CONFIG GET *) to detect accessible instances; reports server info (version, OS, arch, process id, role, connected clients), configuration highlights, and dangerous findings (bind 0.0.0.0, no requirepass, writable dir); supports `--target` (host, host:port, or redis:// URL), `--port`, `--probes`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
    - **SMB/CIFS reconnaissance: `smb` command to perform an SMB1 `SMB_COM_NEGOTIATE` dialect probe (stdlib-only `socket`/`struct` raw packet crafting) over TCP; reports whether an SMB1 endpoint is accessible, the negotiated dialect (or no-common-dialect), server security mode, message-signing policy (required/enabled), and NTLMSSP presence/challenge; with `--smb2` it also runs an SMB2/SMB3 `SMB2_NEGOTIATE` probe (protocol id `\xfeSMB`, dialects 2.0.2/2.1/3.0/3.0.2/3.1.1, preauth-integrity negotiate context for 3.1.1) and reports the negotiated dialect/version, security mode, ServerGUID, capabilities, and negotiate contexts (preauth hash algorithm, encryption ciphers) on modern hosts with SMB1 disabled; supports `--target` (host, host:port, or smb:// URL), `--port` (default 445), `--smb2/--no-smb2`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
    - **LDAP reconnaissance: `ldap` command to probe LDAP servers with an anonymous BindRequest (RFC 4511, stdlib-only BER encoding) plus a RootDSE search; reports whether anonymous bind is allowed, the bind result code/name, matched DN, diagnostic message, and server identity from the RootDSE (vendor name/version, naming contexts, supported LDAP versions, SASL mechanisms, controls); LDAPS implied by `ldaps://` URLs or port 636 (TLS-wrapped, cert verification disabled as a recon probe); supports `--target` (host, host:port, or ldap:// URL), `--port` (default 389), `--ldap-version [2|3]`, `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)
- **Memcached reconnaissance: `memcached` command to probe Memcached servers via the text protocol over TCP 11211; runs a `version` probe (reports memcached version string) and a `stats` probe (parses STAT lines into structured map: uptime, bytes, current connections, command counters, hit/miss ratios, evictions); identifies noteworthy conditions (evictions, zero hits with misses, unbounded cache); supports `--target` (host, host:port, or memcached:// URL), `--port` (default 11211), `--probes` (comma-separated: version,stats), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`** (implemented)


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

## Requirements

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m ethscan --help
```

## Disclaimer

This project is for **authorized security testing only**. Use only against
systems you own or have explicit written permission to test.