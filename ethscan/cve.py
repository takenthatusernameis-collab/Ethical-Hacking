"""CVE lookup module for ethscan.

Queries the public NVD/CVE API for known vulnerabilities affecting detected
service versions, with filesystem caching and offline fallback. Stdlib only.
"""

import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ethscan.service import run_service

DEFAULT_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFAULT_TIMEOUT = 10.0
CACHE_DIR = Path.home() / ".cache" / "ethscan"
CACHE_FILE = CACHE_DIR / "cve_cache.json"
CACHE_TTL = 3600  # 1 hour

SEVERITIES = ("critical", "high", "medium", "low")

PRODUCT_ALIASES = {
    "openssh": ["openssh", "ssh"],
    "proftpd": ["proftpd", "ftp"],
    "vsftpd": ["vsftpd", "ftp"],
    "pure-ftpd": ["pure-ftpd", "ftp"],
    "filezilla": ["filezilla", "ftp"],
    "dovecot": ["dovecot", "imap", "pop3"],
    "postfix": ["postfix", "smtp"],
    "exim": ["exim", "smtp"],
    "sendmail": ["sendmail", "smtp"],
    "apache": ["apache", "http"],
    "nginx": ["nginx", "http"],
    "iis": ["iis", "http"],
    "mysql": ["mysql"],
    "mariadb": ["mariadb"],
    "postgresql": ["postgresql"],
    "redis": ["redis"],
    "mongodb": ["mongodb"],
    "openssh": ["openssh", "ssh"],
}


def _normalize_target(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    parsed = urllib.parse.urlparse(normalized)
    return (parsed.hostname or parsed.netloc or "").lower()


def _resolve_host(host: str) -> Optional[str]:
    """Resolve a hostname to an IPv4 address, returning None on failure."""
    try:
        return socket.gethostbyname(host)
    except (socket.gaierror, socket.herror):
        return None


def _load_cache() -> Dict[str, Dict]:
    """Load the CVE cache from disk."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: Dict[str, Dict]) -> None:
    """Save the CVE cache to disk."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except OSError:
        pass


def _is_cache_valid(entry: Dict, ttl: int = CACHE_TTL) -> bool:
    """Check if a cache entry is still valid."""
    if "timestamp" not in entry:
        return False
    return (time.time() - entry["timestamp"]) < ttl


def _fetch_cve_data(
    product: str,
    version: str,
    timeout: float = DEFAULT_TIMEOUT,
    api_url: Optional[str] = None,
) -> Optional[Dict]:
    """Fetch CVE data from the public NVD API."""
    base = (api_url or DEFAULT_API_URL).rstrip("/")
    query = urllib.parse.quote(f"{product} {version}")
    url = f"{base}?keywordSearch={query}&resultsPerPage=5"
    req = urllib.request.Request(url, headers={"User-Agent": "ethscan/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def _parse_cve_response(data: Dict) -> List[Dict]:
    """Parse NVD API response into a list of CVE findings."""
    findings: List[Dict] = []
    vulns = data.get("vulnerabilities") or []
    for entry in vulns:
        cve = entry.get("cve") or {}
        cve_id = cve.get("id") or ""
        descriptions = cve.get("descriptions") or []
        title = ""
        description = ""
        for desc in descriptions:
            if desc.get("lang") == "en":
                title = desc.get("value") or ""
                if not description:
                    description = title
                break
        if not title and descriptions:
            title = descriptions[0].get("value") or ""
            description = title
        metrics = cve.get("metrics") or {}
        severity = "unknown"
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric_list = metrics.get(key) or []
            if metric_list:
                score = (metric_list[0].get("cvssData") or {}).get("baseScore")
                severity = _score_to_severity(score)
                break
        published = cve.get("published") or ""
        findings.append({
            "id": cve_id,
            "title": title,
            "description": description,
            "severity": severity,
            "published": published,
        })
    return findings


def _score_to_severity(score: Optional[float]) -> str:
    """Map a CVSS score to a severity label."""
    if score is None:
        return "unknown"
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score > 0.0:
        return "low"
    return "unknown"


def _get_cached_or_fetch(
    product: str,
    version: str,
    timeout: float,
    use_cache: bool,
    offline_fallback: bool,
    api_url: Optional[str],
) -> Dict[str, object]:
    """Get CVE data from cache or fetch from API."""
    cache_key = f"{product}|{version}"
    cache = _load_cache() if use_cache else {}

    if use_cache and cache_key in cache and _is_cache_valid(cache[cache_key]):
        result = dict(cache[cache_key])
        result["cached"] = True
        return result

    data = _fetch_cve_data(product, version, timeout, api_url)

    if data is None:
        if offline_fallback and use_cache and cache_key in cache:
            result = dict(cache[cache_key])
            result["cached"] = True
            result["offline_fallback"] = True
            return result
        return {
            "product": product,
            "version": version,
            "findings": [],
            "error": "Failed to fetch CVE data",
            "cached": False,
        }

    findings = _parse_cve_response(data)
    payload = {
        "product": product,
        "version": version,
        "findings": findings,
        "count": len(findings),
        "cached": False,
    }

    if use_cache:
        cache[cache_key] = payload
        _save_cache(cache)

    return payload


def _parse_banner_product(banner: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract product name and version from a service banner."""
    patterns = [
        (re.compile(r"OpenSSH[_-]([0-9]+(?:\.[0-9]+)*(?:p[0-9]+)?)", re.IGNORECASE), "OpenSSH"),
        (re.compile(r"ProFTPD\s+([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE), "ProFTPD"),
        (re.compile(r"vsFTPd\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "vsftpd"),
        (re.compile(r"Pure-FTPd\s+([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE), "Pure-FTPd"),
        (re.compile(r"FileZilla\s+Server\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "FileZilla"),
        (re.compile(r"Dovecot\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "Dovecot"),
        (re.compile(r"Postfix\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "Postfix"),
        (re.compile(r"Exim\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "Exim"),
        (re.compile(r"Apache[/\s]([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "Apache"),
        (re.compile(r"nginx[/\s]([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "nginx"),
        (re.compile(r"MySQL\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "MySQL"),
        (re.compile(r"MariaDB\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "MariaDB"),
        (re.compile(r"PostgreSQL\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "PostgreSQL"),
        (re.compile(r"Redis\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE), "Redis"),
    ]
    for pattern, product in patterns:
        match = pattern.search(banner)
        if match:
            return product, match.group(1)
    return None, None


def _normalize_product(product: str) -> str:
    """Normalize product name for cache key consistency."""
    return product.strip().lower()


def run_cve(
    target: str,
    services: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
    use_cache: bool = True,
    offline_fallback: bool = True,
    api_url: Optional[str] = None,
    severity: Optional[str] = None,
) -> Dict[str, object]:
    """Query the NVD/CVE API for known vulnerabilities in detected services.

    Args:
        target: Hostname or URL (e.g. example.com or https://example.com).
        services: Pre-computed ``service`` command results. If None, service
            detection is run against the target.
        timeout: API request timeout in seconds.
        use_cache: Whether to use local filesystem cache.
        offline_fallback: Whether to use stale cache when API is unavailable.
        api_url: Optional custom NVD API base URL.
        severity: Restrict findings to a single severity level.

    Returns:
        Structured results with per-service CVE findings and notes.
    """
    host = _normalize_target(target)

    if services is None:
        services = run_service(host)

    findings: List[Dict[str, object]] = []
    services_checked = 0
    cve_queries: List[Dict[str, object]] = []

    for entry in services.get("results") or []:
        banner = entry.get("banner") or ""
        product, version = _parse_banner_product(banner)
        if not product or not version:
            continue
        services_checked += 1
        cve_data = _get_cached_or_fetch(
            product, version, timeout, use_cache, offline_fallback, api_url
        )
        cve_queries.append({
            "product": product,
            "version": version,
            "port": entry.get("port"),
            "cached": cve_data.get("cached", False),
            "offline_fallback": cve_data.get("offline_fallback", False),
            "findings": cve_data.get("findings") or [],
        })
        for finding in cve_data.get("findings") or []:
            findings.append({
                "product": product,
                "version": version,
                "port": entry.get("port"),
                "id": finding.get("id"),
                "title": finding.get("title"),
                "description": finding.get("description"),
                "severity": finding.get("severity"),
                "published": finding.get("published"),
            })

    if severity:
        findings = [f for f in findings if f.get("severity") == severity]

    severity_counts: Dict[str, int] = {name: 0 for name in SEVERITIES}
    for finding in findings:
        level = str(finding.get("severity") or "unknown")
        severity_counts[level] = severity_counts.get(level, 0) + 1

    notes: List[str] = []
    if services_checked == 0:
        notes.append("No service banners with parseable product/version detected")
    if not findings:
        notes.append("No known CVEs matched")

    return {
        "target": target,
        "host": host,
        "timeout": timeout,
        "use_cache": use_cache,
        "offline_fallback": offline_fallback,
        "api_url": api_url,
        "severity_filter": severity,
        "services_checked": services_checked,
        "cve_queries": cve_queries,
        "findings": findings,
        "finding_count": len(findings),
        "severity_counts": severity_counts,
        "notes": notes,
    }


def format_cve_report_json(data: Dict[str, object]) -> str:
    """Format CVE lookup results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def format_cve_report_markdown(data: Dict[str, object]) -> str:
    """Format CVE lookup results as Markdown."""
    lines = ["# ethscan CVE Lookup Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **Cache Enabled:** {'Yes' if data['use_cache'] else 'No'}")
    lines.append(f"- **Offline Fallback:** {'Yes' if data['offline_fallback'] else 'No'}")
    if data.get("api_url"):
        lines.append(f"- **API URL:** {data['api_url']}")
    if data.get("severity_filter"):
        lines.append(f"- **Severity Filter:** {data['severity_filter']}")
    lines.append("")

    lines.append(f"- **Services Checked:** {data.get('services_checked', 0)}")
    lines.append(f"- **Findings:** {data.get('finding_count', 0)}")
    lines.append("")

    severity_counts = data.get("severity_counts") or {}
    lines.append("## Severity Summary")
    for name in SEVERITIES:
        lines.append(f"- **{name.capitalize()}:** {severity_counts.get(name, 0)}")
    lines.append("")

    findings = data.get("findings") or []
    lines.append("## CVE Findings")
    if findings:
        lines.append("| CVE ID | Product | Version | Port | Severity | Title |")
        lines.append("|--------|---------|---------|------|----------|-------|")
        for finding in findings:
            cve_id = _escape(str(finding.get("id") or ""))
            product = _escape(str(finding.get("product") or ""))
            version = _escape(str(finding.get("version") or ""))
            port = finding.get("port")
            port_str = str(port) if port is not None else ""
            severity_label = str(finding.get("severity") or "unknown").upper()
            title = _escape(str(finding.get("title") or ""))
            lines.append(f"| {cve_id} | {product} | {version} | {port_str} | {severity_label} | {title} |")
    else:
        lines.append("*No known CVEs matched.*")
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
