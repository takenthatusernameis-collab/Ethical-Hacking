"""CVE lookup module for ethscan.

Queries the public NVD/CVE API for known vulnerabilities affecting detected
service versions (provided via ``--services-file`` JSON output from the
``service`` command). Stdlib only with filesystem caching and offline fallback.
"""

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFAULT_TIMEOUT = 10.0
CACHE_DIR = Path.home() / ".cache" / "ethscan"
CACHE_FILE = CACHE_DIR / "cve_cache.json"
CACHE_TTL = 3600  # 1 hour

from ethscan.vuln import (  # noqa: E402
    BANNER_SIGNATURES,
    SEVERITIES,
    SERVICE_VULNS,
    VULN_DB,
    match_service_vulns,
    parse_banner,
    version_in_range,
)


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
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
    if not isinstance(entry, dict) or "timestamp" not in entry:
        return False
    try:
        return (time.time() - float(entry["timestamp"])) < ttl
    except (TypeError, ValueError):
        return False


def _fetch_cve_data(
    cve_id: str, timeout: float = DEFAULT_TIMEOUT, api_url: Optional[str] = None
) -> Optional[Dict]:
    """Fetch CVE details from the public NVD API."""
    base = (api_url or DEFAULT_API_URL).rstrip("/")
    url = f"{base}?cveId={urllib.parse.quote(cve_id)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ethscan/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def _get_cached_or_fetch(
    cve_id: str,
    timeout: float,
    use_cache: bool,
    offline_fallback: bool,
    api_url: Optional[str],
) -> Dict[str, object]:
    """Get CVE data from cache or fetch from API."""
    cache = _load_cache() if use_cache else {}

    if use_cache and cve_id in cache and _is_cache_valid(cache[cve_id]):
        result = dict(cache[cve_id])
        result["cached"] = True
        return result

    data = _fetch_cve_data(cve_id, timeout, api_url)

    if data is None:
        if offline_fallback and use_cache and cve_id in cache:
            result = dict(cache[cve_id])
            result["cached"] = True
            result["offline_fallback"] = True
            return result
        return {
            "cve_id": cve_id,
            "error": "Failed to fetch CVE data",
            "cached": False,
        }

    if use_cache:
        data["timestamp"] = time.time()
        cache[cve_id] = data
        _save_cache(cache)

    data["cached"] = False
    return data


def _extract_cve_summary(cve_data: Dict[str, object]) -> Dict[str, object]:
    """Extract a normalized CVE summary from raw NVD API response."""
    vulns = (cve_data.get("vulnerabilities") or [])
    if not vulns:
        return {}
    first = vulns[0]
    if not isinstance(first, dict):
        return {}
    cve = first.get("cve") or {}
    if not isinstance(cve, dict):
        return {}

    cve_id = cve.get("id") or ""
    descriptions = cve.get("descriptions") or []
    description = ""
    for entry in descriptions:
        if isinstance(entry, dict) and entry.get("lang") == "en":
            description = entry.get("value") or ""
            break
    if not description and descriptions and isinstance(descriptions[0], dict):
        description = descriptions[0].get("value") or ""

    metrics = cve.get("metrics") or {}
    cvss = {}
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key) or []
        if entries and isinstance(entries[0], dict):
            cvss = entries[0].get("cvssData") or {}
            break

    severity = (cvss.get("baseSeverity") or "").upper() or None
    score = cvss.get("baseScore")
    published = cve.get("published") or ""
    last_modified = cve.get("lastModified") or ""

    references = [
        r.get("url")
        for r in (cve.get("references") or [])
        if isinstance(r, dict) and r.get("url")
    ]

    return {
        "id": cve_id,
        "description": description,
        "severity": severity,
        "score": score,
        "published": published,
        "last_modified": last_modified,
        "references": references,
    }


def run_cve(
    target: str,
    services_file: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
    use_cache: bool = True,
    offline_fallback: bool = True,
    api_url: Optional[str] = None,
    severity: Optional[str] = None,
) -> Dict[str, object]:
    """Query the NVD/CVE API for known vulnerabilities affecting TARGET's services.

    Args:
        target: Hostname or URL (e.g. example.com or https://example.com).
        services_file: Optional JSON file with ``service`` command output. When
            omitted, live service detection is run against the target.
        timeout: API request timeout in seconds.
        use_cache: Whether to use local filesystem cache.
        offline_fallback: Whether to use stale cache when API is unavailable.
        api_url: Optional custom NVD API base URL.
        severity: Restrict findings to a single severity level
            (critical/high/medium/low). If None, all severities are reported.

    Returns:
        Structured results with per-service CVE lookups, counts, and notes.
    """
    global DEFAULT_API_URL
    original_api = DEFAULT_API_URL
    if api_url:
        DEFAULT_API_URL = api_url.rstrip("/") + "/"

    host = _normalize_host(target)
    notes: List[str] = []

    services = None
    if services_file:
        try:
            with open(services_file, "r", encoding="utf-8") as handle:
                services = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            notes.append(f"Failed to read services file: {exc}")
            services = None

    if services is None:
        from ethscan.service import run_service

        services = run_service(host, timeout=timeout)

    cve_entries: List[Dict[str, object]] = []
    services_checked = 0
    for entry in services.get("results") or []:
        banner = entry.get("banner") or ""
        product, version = parse_banner(banner)
        port = entry.get("port")
        services_checked += 1

        # Cross-reference against the built-in CVE/weakness database so offline
        # results are still useful even when the NVD API is unreachable.
        builtin_findings = match_service_vulns(product, version, port=port)
        for finding in builtin_findings:
            cve_entries.append(
                {
                    "source": "builtin",
                    "port": port,
                    "product": product,
                    "version": version,
                    "finding": finding,
                }
            )

        if product and version:
            cve_id = _lookup_cve_id(product, version)
            if cve_id:
                cve_data = _get_cached_or_fetch(
                    cve_id, timeout, use_cache, offline_fallback, api_url
                )
                summary = _extract_cve_summary(cve_data) if cve_data else {}
                if summary:
                    cve_entries.append(
                        {
                            "source": "nvd",
                            "port": port,
                            "product": product,
                            "version": version,
                            "cve_id": cve_id,
                            "cve": summary,
                            "cached": bool(cve_data.get("cached")),
                            "offline_fallback": bool(cve_data.get("offline_fallback")),
                        }
                    )

    if severity:
        filtered: List[Dict[str, object]] = []
        for entry in cve_entries:
            finding = entry.get("finding") or {}
            cve = entry.get("cve") or {}
            sev = finding.get("severity") or cve.get("severity")
            if sev and str(sev).lower() == severity:
                filtered.append(entry)
        cve_entries = filtered

    severity_counts: Dict[str, int] = {name: 0 for name in SEVERITIES}
    for entry in cve_entries:
        finding = entry.get("finding") or {}
        cve = entry.get("cve") or {}
        level = finding.get("severity") or cve.get("severity")
        if level:
            severity_counts[str(level).lower()] = severity_counts.get(
                str(level).lower(), 0
            ) + 1

    if services_checked == 0:
        notes.append("No service banners detected")
    if not cve_entries:
        notes.append("No CVEs matched")

    DEFAULT_API_URL = original_api
    return {
        "target": target,
        "host": host,
        "timeout": timeout,
        "use_cache": use_cache,
        "offline_fallback": offline_fallback,
        "api_url": api_url,
        "severity_filter": severity,
        "services_checked": services_checked,
        "cve_entries": cve_entries,
        "cve_count": len(cve_entries),
        "severity_counts": severity_counts,
        "notes": notes,
    }


def _lookup_cve_id(product: str, version: str) -> Optional[str]:
    """Return a representative CVE id for a product/version, if known."""
    product_lower = str(product).lower()
    version_lower = str(version).lower()
    for entry in SERVICE_VULNS:
        if str(entry["product"]).lower() != product_lower:
            continue
        if version_in_range(version_lower, entry):
            return str(entry["id"])
    return None


def format_cve_report_json(data: Dict[str, object]) -> str:
    """Format CVE lookup results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _finding_detail(finding: Dict[str, object]) -> str:
    """Render the per-finding details line for Markdown output."""
    kind = str(finding.get("kind", ""))
    if kind == "service":
        product = str(finding.get("product") or "Unknown")
        version = str(finding.get("version") or "")
        detail = f"{product} {version}".strip()
        port = finding.get("port")
        if port is not None:
            detail = f"{detail} (port {port})"
        return detail
    return ""


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def format_cve_report_markdown(data: Dict[str, object]) -> str:
    """Format CVE lookup results as Markdown."""
    lines = ["# ethscan CVE Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **Cache Enabled:** {'Yes' if data['use_cache'] else 'No'}")
    lines.append(
        f"- **Offline Fallback:** {'Yes' if data['offline_fallback'] else 'No'}"
    )
    if data.get("api_url"):
        lines.append(f"- **API URL:** {data['api_url']}")
    if data.get("severity_filter"):
        lines.append(f"- **Severity Filter:** {data['severity_filter']}")
    lines.append("")

    severity_counts = data.get("severity_counts") or {}
    lines.append("## Severity Summary")
    for name in SEVERITIES:
        lines.append(f"- **{name.capitalize()}:** {severity_counts.get(name, 0)}")
    lines.append("")

    entries = data.get("cve_entries") or []
    lines.append("## CVE Findings")
    if entries:
        for entry in entries:
            source = str(entry.get("source", ""))
            if source == "builtin":
                finding = entry.get("finding") or {}
                lines.append(
                    f"### {finding.get('id', 'Unknown')} "
                    f"({str(finding.get('severity', '')).upper()})"
                )
                lines.append(f"- **Source:** Built-in database")
                detail = _escape(_finding_detail(finding))
                if detail:
                    lines.append(f"- **Details:** {detail}")
                lines.append(f"- **Title:** {_escape(str(finding.get('title', '')))}")
                lines.append(
                    f"- **Description:** {_escape(str(finding.get('description', '')))}"
                )
            else:
                cve = entry.get("cve") or {}
                cve_id = entry.get("cve_id") or cve.get("id") or "Unknown"
                lines.append(
                    f"### {cve_id} ({str(cve.get('severity', '')).upper()})"
                )
                lines.append(f"- **Source:** NVD API")
                product = str(entry.get("product") or "")
                version = str(entry.get("version") or "")
                if product or version:
                    lines.append(f"- **Product:** {product} {version}".strip())
                port = entry.get("port")
                if port is not None:
                    lines.append(f"- **Port:** {port}")
                if cve.get("score") is not None:
                    lines.append(f"- **CVSS Score:** {cve.get('score')}")
                if cve.get("published"):
                    lines.append(f"- **Published:** {cve.get('published')}")
                if cve.get("last_modified"):
                    lines.append(f"- **Last Modified:** {cve.get('last_modified')}")
                if cve.get("description"):
                    lines.append(
                        f"- **Description:** {_escape(str(cve.get('description')))}"
                    )
                refs = cve.get("references") or []
                if refs:
                    lines.append("- **References:**")
                    for ref in refs:
                        lines.append(f"  - {ref}")
                if entry.get("cached"):
                    lines.append("- **Cached:** Yes")
                if entry.get("offline_fallback"):
                    lines.append("- **Offline Fallback:** Yes")
            lines.append("")
    else:
        lines.append("*No CVEs matched.*")
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
