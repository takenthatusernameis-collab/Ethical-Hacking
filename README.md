# Ethical Hacking

A modular, offline-first ethical hacking toolkit written in Python.

## Features

- Network reconnaissance and scanning utilities (implemented)
- Password strength auditing with JSON/Markdown output (`audit`) (implemented)
- Web application security checks (implemented)
- **Security headers check: `headers` command for quick security header analysis** (implemented)
- **ICMP ping: `ping` command for host discovery with ICMP echo requests and TCP connect fallback** (implemented)
- **CIDR network calculator: `cidr` command for offline network calculations (network address, netmask, broadcast, host range, membership test)** (implemented)
- HTTP fuzzing (implemented)
- Subdomain enumeration (implemented)
- DNS record enumeration (implemented)
- DNS brute force: AXFR zone transfer attempts + subdomain brute forcing (implemented)
- WHOIS lookup (implemented)
- SSL/TLS certificate inspection (implemented)
- TLS protocol/cipher enumeration (implemented)
- Brute-force login testing (FTP/SSH) with `--output-format csv` for credential dumps (implemented)
- Service/banner detection (implemented)
- Vulnerability checks against a built-in CVE/weakness database (implemented)
- Report generation (JSON / Markdown) (implemented)
- Consolidated web assessment: `urlcheck` command combining web checks, HTTP fuzzing, and SSL certificate inspection (implemented)
- OS fingerprinting: `osdetect` command using TCP/IP stack behavior analysis, banner cross-referencing, and TTL-based inference (implemented)
- TCP traceroute: `trace` command using TTL-incremented TCP SYN probes with per-hop IP/RTT reporting (implemented)
- Wi-Fi reconnaissance: `wifi` command for wireless interface scanning and access point discovery (Linux, implemented)
- IP geolocation: `geo` command for IP-to-location lookup using a public API with caching and offline fallback (implemented)
- Consolidated reconnaissance: `recon` command running multiple modules (subdomains, dns, whois, geo, trace) in sequence with a unified report (implemented)
- Certificate Transparency log search: `cert` command to discover subdomains via CT logs (crt.sh-compatible APIs) with caching and offline fallback (implemented)
- CVE lookup: `cve` command to query the NVD/CVE API for known vulnerabilities affecting detected service versions, with a built-in CVE/weakness database cross-reference, caching, offline fallback, JSON/Markdown output, `--out`, `--severity`, and `--min-severity` (implemented)
- Subdomain takeover detection: `subtake` command to detect subdomain takeover vulnerabilities by checking CNAME records against known vulnerable cloud services (implemented)
- Configuration file: `ethscan.yaml` (or `~/.ethscan.yaml`) to persist default options across commands (global `defaults` plus per-command overrides); `ethscan config` command to inspect or initialize the config (implemented)
- **MAC address vendor lookup: `mac` command to look up OUI vendor information via public API (api.macvendors.com) with filesystem caching, offline fallback, and JSON/Markdown output** (implemented)

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