# Ethical Hacking

A modular, offline-first ethical hacking toolkit written in Python.

## Features

- Network reconnaissance and scanning utilities (implemented)
- Password strength auditing with JSON/Markdown output (`audit`) (implemented)
- Web application security checks (implemented)
- **Security headers check: `headers` command for quick security header analysis** (implemented)
- HTTP fuzzing (implemented)
- Subdomain enumeration (implemented)
- DNS record enumeration (implemented)
- DNS brute force: AXFR zone transfer attempts + subdomain brute forcing (implemented)
- WHOIS lookup (implemented)
- SSL/TLS certificate inspection (implemented)
- TLS protocol/cipher enumeration (implemented)
- Brute-force login testing (FTP/SSH) (implemented)
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
- Host discovery: `ping` command for ICMP echo requests with per-probe RTT/TTL reporting and TCP connect fallback for non-root environments (implemented)
- MAC address vendor lookup: `mac` command for OUI-based vendor identification via public API with caching and offline fallback (implemented)
- JWT inspection: `jwt` command for decoding and analyzing JSON Web Tokens (header, claims, expiration, security findings) without signature verification (implemented)

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