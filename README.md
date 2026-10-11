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
- **Port & CIDR validation: `validate` command to validate and expand port specifications (comma-separated lists/ranges) and CIDR inputs offline, with JSON/Markdown output** (implemented)
- **DNS resolution: `resolve` command for forward/reverse DNS resolution of a target (A, AAAA, CNAME, PTR record types), with optional custom resolver and JSON/Markdown output** (implemented)
- **Nmap XML parser: `nmap` command to parse Nmap XML scan output (`-oX`) and cross-reference detected service versions against the built-in vulnerability database, producing a consolidated report of matched CVEs in JSON, Markdown, or CSV** (implemented)
- **Stale DNS detection: `stale` command to detect stale DNS records (A/AAAA/CNAME) pointing to deallocated or unresolvable IPs/dead cloud resources, with configurable timeout, concurrency, and JSON/Markdown output** (implemented)
- **SSH security assessment: `ssh` command to enumerate supported key exchange algorithms, ciphers, MACs, and host key types on a target SSH server; check for weak/deprecated algorithms (e.g., `diffie-hellman-group1-sha1`, `arcfour`, `3des-cbc`, `ssh-rsa`); report host key fingerprint and algorithm; supports `--target` (host:port), `--timeout`, `--format [json|markdown]`, `--out`; stdlib-only with optional `paramiko` for host key details** (implemented)
- **AWS S3 bucket enumeration: `s3` command to detect publicly accessible S3 buckets via HTTP probing of generated candidate bucket names (from the target domain with optional `--wordlist`); supports `--region` (including `all`), `--timeout`, `--workers`, `--format [json|markdown]`, and `--out`** (implemented)

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