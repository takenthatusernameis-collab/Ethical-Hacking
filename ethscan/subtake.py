"""Subdomain takeover detection module for ethscan.

Enumerates subdomains, resolves their CNAME/A records, and checks if they
point to known vulnerable cloud services (AWS S3, GitHub Pages, Heroku, Azure,
Shopify, etc.) where the target resource no longer exists.
"""
from __future__ import annotations

import csv
import io
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

from ethscan.target import parse_url

try:
    import dns.exception
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

DEFAULT_SUBDOMAINS = [
    "www",
    "mail",
    "api",
    "admin",
    "dev",
    "staging",
    "test",
    "blog",
    "shop",
    "cdn",
    "ftp",
    "smtp",
    "imap",
    "webmail",
    "vpn",
    "remote",
    "portal",
    "app",
    "m",
    "mobile",
    "secure",
    "support",
    "ns1",
    "ns2",
    "dns",
    "dns2",
]

TAKEOVER_SIGNATURES = [
    {
        "service": "AWS S3",
        "cname_patterns": [".s3.amazonaws.com", ".s3-website.", ".s3."],
        "fingerprint": "NoSuchBucket",
        "description": "S3 bucket does not exist",
    },
    {
        "service": "GitHub Pages",
        "cname_patterns": ["github.io", "github.com"],
        "fingerprint": "There isn't a GitHub Pages site here",
        "description": "GitHub Pages site not found",
    },
    {
        "service": "Heroku",
        "cname_patterns": [".herokuapp.com", ".herokudns.com"],
        "fingerprint": "No such app",
        "description": "Heroku app does not exist",
    },
    {
        "service": "Azure",
        "cname_patterns": [".azurewebsites.net", ".cloudapp.net", ".trafficmanager.net"],
        "fingerprint": "404 Web Site not found",
        "description": "Azure web app not found",
    },
    {
        "service": "Shopify",
        "cname_patterns": [".myshopify.com"],
        "fingerprint": "Sorry, this shop is currently unavailable",
        "description": "Shopify store not found",
    },
    {
        "service": "Pantheon",
        "cname_patterns": [".pantheonsite.io", ".pantheon.io"],
        "fingerprint": "The gods are wise, but they do not know this site",
        "description": "Pantheon site not found",
    },
    {
        "service": "Bitbucket",
        "cname_patterns": ["bitbucket.io"],
        "fingerprint": "Repository not found",
        "description": "Bitbucket Pages repository not found",
    },
    {
        "service": "Tumblr",
        "cname_patterns": ["tumblr.com"],
        "fingerprint": "There's nothing here",
        "description": "Tumblr blog not found",
    },
    {
        "service": "WordPress.com",
        "cname_patterns": ["wordpress.com"],
        "fingerprint": "Do you want to register",
        "description": "WordPress.com site not found",
    },
    {
        "service": "Squarespace",
        "cname_patterns": ["squarespace.com"],
        "fingerprint": "No such account",
        "description": "Squarespace site not found",
    },
    {
        "service": "Wix",
        "cname_patterns": ["wix.com", "wixsite.com"],
        "fingerprint": "This domain has not been connected",
        "description": "Wix site not found",
    },
    {
        "service": "Weebly",
        "cname_patterns": ["weebly.com"],
        "fingerprint": "There isn't a site here",
        "description": "Weebly site not found",
    },
    {
        "service": "Surge.sh",
        "cname_patterns": ["surge.sh"],
        "fingerprint": "project not found",
        "description": "Surge.sh project not found",
    },
    {
        "service": "Netlify",
        "cname_patterns": ["netlify.app", "netlify.com"],
        "fingerprint": "Not Found",
        "description": "Netlify site not found",
    },
    {
        "service": "Vercel",
        "cname_patterns": ["vercel.app", "now.sh"],
        "fingerprint": "This deployment could not be found",
        "description": "Vercel deployment not found",
    },
    {
        "service": "Firebase",
        "cname_patterns": ["firebaseapp.com", "web.app"],
        "fingerprint": "Site not found",
        "description": "Firebase hosting not found",
    },
    {
        "service": "CloudFront",
        "cname_patterns": [".cloudfront.net"],
        "fingerprint": "The request could not be satisfied",
        "description": "CloudFront distribution not found",
    },
    {
        "service": "Fastly",
        "cname_patterns": ["fastly.net", "fastlylb.net"],
        "fingerprint": "Fastly error: unknown domain",
        "description": "Fastly service not found",
    },
    {
        "service": "Pagely",
        "cname_patterns": ["pagelyhosting.com"],
        "fingerprint": "The site you were looking for doesn't exist",
        "description": "Pagely site not found",
    },
    {
        "service": "Desk.com",
        "cname_patterns": ["desk.com"],
        "fingerprint": "This help center no longer exists",
        "description": "Desk.com help center not found",
    },
    {
        "service": "Help Scout",
        "cname_patterns": ["helpscoutdocs.com"],
        "fingerprint": "No such help center",
        "description": "Help Scout docs not found",
    },
    {
        "service": "Statuspage.io",
        "cname_patterns": ["statuspage.io"],
        "fingerprint": "This page doesn't exist",
        "description": "Statuspage not found",
    },
    {
        "service": "UserVoice",
        "cname_patterns": ["uservoice.com"],
        "fingerprint": "This UserVoice subdomain is not available",
        "description": "UserVoice forum not found",
    },
    {
        "service": "Zendesk",
        "cname_patterns": ["zendesk.com"],
        "fingerprint": "Help Center Closed",
        "description": "Zendesk help center not found",
    },
    {
        "service": "Intercom",
        "cname_patterns": ["intercom.io", "intercom.com"],
        "fingerprint": "This site is not available",
        "description": "Intercom site not found",
    },
    {
        "service": "Ghost",
        "cname_patterns": ["ghost.io"],
        "fingerprint": "The site you are looking for doesn't exist",
        "description": "Ghost blog not found",
    },
    {
        "service": "ReadMe.io",
        "cname_patterns": ["readme.io"],
        "fingerprint": "Project doesn't exist",
        "description": "ReadMe.io documentation not found",
    },
    {
        "service": "Freshdesk",
        "cname_patterns": ["freshdesk.com"],
        "fingerprint": "This helpdesk no longer exists",
        "description": "Freshdesk helpdesk not found",
    },
    {
        "service": "Unbounce",
        "cname_patterns": ["unbouncepages.com"],
        "fingerprint": "The page you're looking for doesn't exist",
        "description": "Unbounce landing page not found",
    },
    {
        "service": "BigCartel",
        "cname_patterns": ["bigcartel.com"],
        "fingerprint": "This store doesn't exist",
        "description": "BigCartel store not found",
    },
    {
        "service": "LaunchRock",
        "cname_patterns": ["launchrock.com"],
        "fingerprint": "This site has not been claimed",
        "description": "LaunchRock site not found",
    },
    {
        "service": "UptimeRobot",
        "cname_patterns": ["uptimerobot.com"],
        "fingerprint": "page not found",
        "description": "UptimeRobot status page not found",
    },
    {
        "service": "Simplebooklet",
        "cname_patterns": ["simplebooklet.com"],
        "fingerprint": "This booklet does not exist",
        "description": "Simplebooklet not found",
    },
    {
        "service": "Tilda",
        "cname_patterns": ["tilda.ws"],
        "fingerprint": "The page you are looking for doesn't exist",
        "description": "Tilda site not found",
    },
    {
        "service": "Cargo",
        "cname_patterns": ["cargo.site", "cargocollective.com"],
        "fingerprint": "404 Not Found",
        "description": "Cargo portfolio not found",
    },
    {
        "service": "Carrd",
        "cname_patterns": ["carrd.co"],
        "fingerprint": "This site can't be reached",
        "description": "Carrd site not found",
    },
]


def _normalize_domain(target: str) -> str:
    """Extract a bare domain from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    parsed = parse_url(normalized)
    return parsed.netloc.lower()


def resolve_cname(hostname: str, timeout: float = 2.0, resolver: str | None = None) -> str | None:
    """Resolve CNAME record for a hostname.

    Args:
        hostname: Hostname to resolve.
        timeout: DNS resolution timeout in seconds.
        resolver: Custom DNS resolver IP address (requires dnspython).

    Returns:
        CNAME target if found, None otherwise.
    """
    if resolver and DNS_AVAILABLE:
        try:
            dns_resolver = dns.resolver.Resolver()
            dns_resolver.timeout = timeout
            dns_resolver.lifetime = timeout
            dns_resolver.nameservers = [resolver]
            answers = dns_resolver.resolve(hostname, "CNAME")
            if not answers:
                return None
            return str(answers[0]).rstrip(".")
        except (dns.exception.DNSException, OSError, ValueError, IndexError, AttributeError, KeyError):
            return None

    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, socket.AI_CANONNAME)
        for r in results:
            canonname = r[3]
            if canonname and canonname != hostname:
                return canonname.rstrip(".")
    except (socket.timeout, socket.gaierror, OSError, ValueError):
        pass
    return None


def resolve_a_records(hostname: str, timeout: float = 2.0, resolver: str | None = None) -> list[str]:
    """Resolve A records (IPv4 addresses) for a hostname."""
    ips: list[str] = []
    if resolver and DNS_AVAILABLE:
        try:
            dns_resolver = dns.resolver.Resolver()
            dns_resolver.timeout = timeout
            dns_resolver.lifetime = timeout
            dns_resolver.nameservers = [resolver]
            answers = dns_resolver.resolve(hostname, "A")
            ips = sorted({str(rdata) for rdata in answers})
            return ips
        except (dns.exception.DNSException, OSError, ValueError, IndexError, AttributeError, KeyError):
            pass

    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        ips = sorted({r[4][0] for r in results})
    except (socket.timeout, socket.gaierror, OSError, ValueError):
        pass
    return ips


def resolve_aaaa_records(hostname: str, timeout: float = 2.0, resolver: str | None = None) -> list[str]:
    """Resolve AAAA records (IPv6 addresses) for a hostname."""
    ips: list[str] = []
    if resolver and DNS_AVAILABLE:
        try:
            dns_resolver = dns.resolver.Resolver()
            dns_resolver.timeout = timeout
            dns_resolver.lifetime = timeout
            dns_resolver.nameservers = [resolver]
            answers = dns_resolver.resolve(hostname, "AAAA")
            ips = sorted({str(rdata) for rdata in answers})
            return ips
        except (dns.exception.DNSException, OSError, ValueError, IndexError, AttributeError, KeyError):
            pass

    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(hostname, None, socket.AF_INET6)
        ips = sorted({r[4][0] for r in results})
    except (socket.timeout, socket.gaierror, OSError, ValueError):
        pass
    return ips


def check_takeover_signature(cname: str, timeout: float = 5.0) -> dict[str, object] | None:
    """Check if a CNAME points to a vulnerable service with takeover signature.

    Args:
        cname: CNAME target to check.
        timeout: HTTP request timeout in seconds.

    Returns:
        Dictionary with takeover details if vulnerable, None otherwise.
    """
    cname_lower = cname.lower()
    for sig in TAKEOVER_SIGNATURES:
        for pattern in sig["cname_patterns"]:
            if pattern in cname_lower:
                return {
                    "service": sig["service"],
                    "cname": cname,
                    "fingerprint": sig["fingerprint"],
                    "description": sig["description"],
                }
    return None


def check_http_fingerprint(hostname: str, timeout: float = 5.0) -> str | None:
    """Check HTTP response for takeover fingerprint.

    Args:
        hostname: Hostname to check.
        timeout: HTTP request timeout in seconds.

    Returns:
        Response body snippet if successful, None otherwise.
    """
    import http.client
    import urllib.error
    import urllib.request

    for scheme in ("https://", "http://"):
        url = f"{scheme}{hostname}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ethscan/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="ignore")
                return body[:5000]
        # ``http.client.BadStatusLine`` (a server that answers with a
        # malformed status line) derives from ``HTTPException`` and not from
        # ``OSError`` or ``ValueError``, so it escapes the ``except`` below.
        # A server that cannot answer is a failed probe, not a crash.
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            socket.timeout,
            ValueError,
            OSError,
            http.client.HTTPException,
        ):
            continue
    return None


def run_subtake(
    target: str,
    subdomains: list[str] | None = None,
    timeout: float = 2.0,
    max_workers: int = 50,
    resolver: str | None = None,
    http_timeout: float = 5.0,
) -> dict[str, object]:
    """Detect subdomain takeover vulnerabilities.

    Args:
        target: Bare domain or URL (e.g. example.com or https://example.com).
        subdomains: List of subdomain labels to test. If None, uses DEFAULT_SUBDOMAINS.
        timeout: DNS resolution timeout in seconds.
        max_workers: Maximum number of concurrent resolution workers.
        resolver: Custom DNS resolver IP address (requires dnspython).
        http_timeout: HTTP request timeout for fingerprinting in seconds.

    Returns:
        Structured results with target, domain, vulnerable subdomains, and all results.
    """
    domain = _normalize_domain(target)
    labels = subdomains if subdomains is not None else DEFAULT_SUBDOMAINS

    all_results: list[dict[str, object]] = []
    vulnerable: list[dict[str, object]] = []
    seen_hostnames: set[str] = set()

    def _resolve_and_check(label: str) -> dict[str, object]:
        hostname = f"{label}.{domain}"
        cname = resolve_cname(hostname, timeout, resolver)
        a_records = resolve_a_records(hostname, timeout, resolver)
        aaaa_records = resolve_aaaa_records(hostname, timeout, resolver)

        result: dict[str, object] = {
            "subdomain": label,
            "hostname": hostname,
            "cname": cname,
            "a_records": a_records,
            "aaaa_records": aaaa_records,
            "vulnerable": False,
            "takeover": None,
        }

        if cname:
            takeover = check_takeover_signature(cname)
            if takeover:
                http_body = check_http_fingerprint(hostname, http_timeout)
                if http_body and takeover["fingerprint"].lower() in http_body.lower():
                    takeover["http_confirmed"] = True
                    takeover["evidence"] = http_body[:500]
                else:
                    takeover["http_confirmed"] = False
                    takeover["evidence"] = "CNAME points to vulnerable service (no HTTP confirmation)"
                result["vulnerable"] = True
                result["takeover"] = takeover
                vulnerable.append(result)
            else:
                result["takeover"] = {"service": "Unknown", "cname": cname, "fingerprint": "", "description": "CNAME does not match known vulnerable services"}

        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_label = {
            executor.submit(_resolve_and_check, label): label
            for label in labels
        }
        for future in as_completed(future_to_label):
            result = future.result()
            hostname = result["hostname"]
            if hostname not in seen_hostnames:
                seen_hostnames.add(hostname)
                all_results.append(result)

    return {
        "target": target,
        "domain": domain,
        "subdomains_tested": len(labels),
        "vulnerable_count": len(vulnerable),
        "vulnerable": vulnerable,
        "all_results": sorted(all_results, key=lambda r: r["hostname"]),
        "resolver": resolver,
        "dnspython_available": DNS_AVAILABLE,
    }


def format_subtake_report_json(data: dict[str, object]) -> str:
    """Format subdomain takeover results as JSON."""
    import json
    return json.dumps(data, indent=2, default=str)


def format_subtake_report_csv(data: dict[str, object]) -> str:
    """Format subdomain takeover results as CSV.

    Produces a header row followed by one row per candidate with columns:
    subdomain, hostname, cname, a_records, aaaa_records, vulnerable, service,
    fingerprint, http_confirmed.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "subdomain",
            "hostname",
            "cname",
            "a_records",
            "aaaa_records",
            "vulnerable",
            "service",
            "fingerprint",
            "http_confirmed",
        ]
    )
    for entry in data.get("all_results", []) or []:
        takeover = entry.get("takeover") or {}
        a_records = entry.get("a_records") or []
        aaaa_records = entry.get("aaaa_records") or []
        writer.writerow(
            [
                entry.get("subdomain", ""),
                entry.get("hostname", ""),
                entry.get("cname") or "",
                ", ".join(str(record) for record in a_records),
                ", ".join(str(record) for record in aaaa_records),
                "true" if entry.get("vulnerable") else "false",
                takeover.get("service") or "",
                takeover.get("fingerprint") or "",
                "true" if takeover.get("http_confirmed") else "false",
            ]
        )
    return output.getvalue().rstrip("\r\n")


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def format_subtake_report_markdown(data: dict[str, object]) -> str:
    """Format subdomain takeover results as Markdown."""
    lines = ["# ethscan Subdomain Takeover Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Domain:** {data['domain']}")
    resolver = data.get("resolver")
    if resolver:
        lines.append(f"- **Resolver:** {resolver} (dnspython: {'Yes' if data.get('dnspython_available') else 'No'})")
    lines.append(f"- **Subdomains Tested:** {data['subdomains_tested']}")
    lines.append(f"- **Vulnerable:** {data['vulnerable_count']}")
    lines.append("")

    lines.append("## Vulnerable Subdomains (Potential Takeover)")
    if data["vulnerable"]:
        lines.append("| Subdomain | Hostname | CNAME | Service | Fingerprint | HTTP Confirmed |")
        lines.append("|-----------|----------|-------|---------|-------------|----------------|")
        for entry in data["vulnerable"]:
            takeover = entry.get("takeover") or {}
            lines.append(
                f"| {entry['subdomain']} | {entry['hostname']} | "
                f"{_escape(str(takeover.get('cname', 'N/A')))} | "
                f"{_escape(str(takeover.get('service', 'Unknown')))} | "
                f"{_escape(str(takeover.get('fingerprint', '')))} | "
                f"{'Yes' if takeover.get('http_confirmed') else 'No'} |"
            )
    else:
        lines.append("*No vulnerable subdomains detected.*")
    lines.append("")

    lines.append("## All Results")
    lines.append("| Subdomain | Hostname | CNAME | A Records | AAAA Records | Vulnerable |")
    lines.append("|-----------|----------|-------|-----------|--------------|------------|")
    for entry in data["all_results"]:
        takeover = entry.get("takeover") or {}
        cname = entry.get("cname") or "N/A"
        a_recs = ", ".join(entry.get("a_records") or []) or "N/A"
        aaaa_recs = ", ".join(entry.get("aaaa_records") or []) or "N/A"
        vuln = "Yes" if entry.get("vulnerable") else "No"
        lines.append(
            f"| {entry['subdomain']} | {entry['hostname']} | "
            f"{_escape(str(cname))} | {_escape(a_recs)} | {_escape(aaaa_recs)} | {vuln} |"
        )
    lines.append("")

    return "\n".join(lines)