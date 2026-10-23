"""CVE lookup module for ethscan.

Queries the public NVD/CVE API for known vulnerabilities affecting detected
service versions (provided via ``--services-file`` JSON output from the
``service`` command). Stdlib only with filesystem caching and offline fallback.
"""
from __future__ import annotations

import http.client
import json
import math
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ethscan.fileio import load_json
from ethscan.target import parse_url

DEFAULT_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFAULT_TIMEOUT = 10.0
CACHE_DIR = Path.home() / ".cache" / "ethscan"
CACHE_FILE = CACHE_DIR / "cve_cache.json"
CACHE_TTL = 3600  # 1 hour

from ethscan.vuln import (
    SERVICE_VULNS,
    SEVERITIES,
    match_service_vulns,
    parse_banner,
    version_in_range,
)


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    parsed = parse_url(normalized)
    return (parsed.hostname or parsed.netloc or "").lower()


def _resolve_host(host: str) -> str | None:
    """Resolve a hostname to an IPv4 address, returning None on failure."""
    try:
        return socket.gethostbyname(host)
    except Exception:  # noqa: BLE001 - resolver can raise any type
        return None


def _load_cache() -> dict[str, dict]:
    """Load the CVE cache from disk.

    The cache is written by the toolkit itself, so a cache file that cannot be
    used is an empty cache and never an error: it is read leniently, so a
    file that holds a stray byte is used as far as it can be read, and only
    the entries that are mappings are returned, so that the callers can copy
    them without a type check.
    """
    if not CACHE_FILE.exists():
        return {}
    try:
        data = load_json(str(CACHE_FILE))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: entry for key, entry in data.items() if isinstance(entry, dict)}


def _save_cache(cache: dict[str, dict]) -> None:
    """Save the CVE cache to disk."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except OSError:
        pass


def _is_cache_valid(entry: dict, ttl: int = CACHE_TTL) -> bool:
    """Check if a cache entry is still valid.

    An entry that is not a mapping, or whose timestamp is not a finite
    number, is never fresh: it is stale data that must not be served as a
    current result.
    """
    if not isinstance(entry, dict) or "timestamp" not in entry:
        return False
    try:
        timestamp = float(entry["timestamp"])
    except (TypeError, ValueError):
        return False
    if not math.isfinite(timestamp):
        return False
    return (time.time() - timestamp) < ttl


def _fetch_cve_data(
    cve_id: str, timeout: float = DEFAULT_TIMEOUT, api_url: str | None = None
) -> dict | None:
    """Fetch CVE details from the public NVD API."""
    base = (api_url or DEFAULT_API_URL).rstrip("/")
    url = f"{base}?cveId={urllib.parse.quote(cve_id)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ethscan/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            try:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            # A body whose JSON nests deeper than the parser can read raises a
            # ``RecursionError``, which is neither a ``ValueError`` nor a
            # ``TypeError``: it is a body that cannot be read.
            except (ValueError, TypeError, RecursionError):
                return None
        if not isinstance(data, dict):
            return None
        return data
    except http.client.HTTPException:
        # ``http.client.BadStatusLine`` (an API that answers with a malformed
        # status line) derives from ``HTTPException`` and not from ``OSError``
        # or ``ValueError``, so it escapes the ``except`` below. An API that
        # cannot answer is a failed lookup, not a crash.
        return None
    except (OSError, ValueError):
        return None
    except Exception:  # noqa: BLE001 - urlopen can raise any failure; swallow to None
        return None


def _get_cached_or_fetch(
    cve_id: str,
    timeout: float,
    use_cache: bool,
    offline_fallback: bool,
    api_url: str | None,
) -> dict[str, object]:
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


def _extract_cve_summary(cve_data: dict[str, object]) -> dict[str, object]:
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


_SEVERITY_RANK: dict[str, int] = {
    name: idx for idx, name in enumerate(reversed(SEVERITIES))
}


def _severity_rank(level: str | None) -> int | None:
    """Return the numeric rank for a severity label, or None if unknown.

    Higher rank means higher severity: critical=3, high=2, medium=1, low=0.
    """
    if not level:
        return None
    return _SEVERITY_RANK.get(str(level).lower())


def run_cve(
    target: str,
    services_file: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    service_timeout: float = 3.0,
    workers: int = 50,
    use_cache: bool = True,
    offline_fallback: bool = True,
    api_url: str | None = None,
    severity: str | None = None,
    min_severity: str | None = None,
    ports: list[int] | None = None,
    profile: str | None = None,
) -> dict[str, object]:
    """Query the NVD/CVE API for known vulnerabilities affecting TARGET's services.

    Args:
        target: Hostname or URL (e.g. example.com or https://example.com).
        services_file: Optional JSON file with ``service`` command output. When
            omitted, live service detection is run against the target.
        timeout: API request timeout in seconds.
        service_timeout: Connection timeout in seconds for live service detection.
        workers: Maximum concurrent workers for live service detection.
        use_cache: Whether to use local filesystem cache.
        offline_fallback: Whether to use stale cache when API is unreachable.
        api_url: Optional custom NVD API base URL.
        severity: Restrict findings to a single severity level
            (critical/high/medium/low). If None, all severities are reported.
        min_severity: Drop findings below this severity threshold
            (critical/high/medium/low). If None, no lower bound is applied.
        ports: Optional list of ports to scan for live service detection.
            If None, uses default common ports.
        profile: Optional scan profile (fast/normal/full) that maps to predefined
            port sets and service-detection presets.

    Returns:
        Structured results with per-service CVE lookups, counts, and notes.
    """
    global DEFAULT_API_URL
    original_api = DEFAULT_API_URL
    if api_url:
        DEFAULT_API_URL = api_url.rstrip("/") + "/"

    try:
        host = _normalize_host(target)
        notes: list[str] = []

        services = None
        if services_file:
            try:
                services = load_json(services_file)
            except (json.JSONDecodeError, OSError) as exc:
                notes.append(f"Failed to read services file: {exc}")
                services = None

        if services is None and not services_file:
            try:
                try:
                    from ethscan.service import run_service as _rs
                    run_service = _rs
                except ImportError:
                    import ethscan.service as _svc
                    run_service = _svc.run_service

                service_result = run_service(
                    target,
                    ports=ports,
                    timeout=service_timeout,
                    max_workers=workers,
                )
                services = {
                    "target": service_result.get("target"),
                    "services": service_result.get("services", service_result.get("results", [])),
                    "service_count": service_result.get("service_count", service_result.get("services_found", 0)),
                    "notes": service_result.get("notes", []),
                    "results": service_result.get("results", service_result.get("services", [])),
                }
                if service_result.get("notes"):
                    for sn in service_result["notes"]:
                        notes.append(f"service: {sn}")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                notes.append(f"Service detection failed: {exc}")
                services = {"target": target, "services": []}
        elif services is None and services_file:
            services = {"target": target, "services": []}

        service_list = None
        if isinstance(services, dict):
            if services.get("services"):
                service_list = services.get("services")
            elif services.get("results"):
                service_list = services.get("results")
            else:
                service_list = []
        else:
            service_list = []
        cve_entries: list[dict[str, object]] = []
        services_checked = 0
        nvd_errors: list[str] = []

        items = service_list
        if isinstance(items, dict):
            items = items.get("services") or items.get("results") or []

        if items is None:
            items = []
        if isinstance(services, dict) and services_file:
            results = services.get("results")
            if results is not None and not isinstance(results, list):
                notes.append("Service data holds no 'results' list")
                items = []
            elif isinstance(results, list):
                bad_entries = [e for e in results if not isinstance(e, dict)]
                if bad_entries:
                    notes.append("Service data holds entries that are not objects")
                    items = [e for e in results if isinstance(e, dict)]
                else:
                    items = results
            elif services.get("services") is not None and not isinstance(services.get("services"), list):
                notes.append("Service data holds no 'results' list")
                items = []
            elif isinstance(services.get("services"), list):
                bad_entries = [e for e in services.get("services") if not isinstance(e, dict)]
                if bad_entries:
                    notes.append("Service data holds entries that are not objects")
                    items = [e for e in services.get("services") if isinstance(e, dict)]
                else:
                    items = services.get("services")
        for entry in items:
            if not isinstance(entry, dict):
                continue
            banner = entry.get("banner") or ""
            if not isinstance(banner, str):
                banner = ""
            try:
                product, version = parse_banner(banner)
            except (TypeError, ValueError):
                product, version = None, None
            port = entry.get("port")
            services_checked += 1

            builtin_findings = match_service_vulns(product, version, port=port)
            for finding in builtin_findings:
                cve_entries.append(
                    {
                        "source": "builtin",
                        "port": port,
                        "product": product,
                        "version": version,
                        "finding": finding,
                        "cve": finding,
                    }
                )

            try:
                cve_id = _lookup_cve_id(product, version)
                if cve_id:
                    cve_data = _get_cached_or_fetch(
                        cve_id, timeout, use_cache, offline_fallback, api_url
                    )

                    if isinstance(cve_data, dict) and cve_data.get("error"):
                        message = f"NVD lookup failed for {cve_id}: {cve_data['error']}"
                        notes.append(message)
                        nvd_errors.append(message)

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
            except (OSError, ValueError, json.JSONDecodeError):
                pass

        if severity:
            filtered: list[dict[str, object]] = []
            for entry in cve_entries:
                finding = entry.get("finding") or {}
                cve = entry.get("cve") or {}
                sev = finding.get("severity") or cve.get("severity")
                if sev and str(sev).lower() == severity:
                    filtered.append(entry)
            cve_entries = filtered

        if min_severity:
            min_rank = _severity_rank(min_severity)
            if min_rank is not None:
                filtered_min: list[dict[str, object]] = []
                for entry in cve_entries:
                    finding = entry.get("finding") or {}
                    cve = entry.get("cve") or {}
                    level = finding.get("severity") or cve.get("severity")
                    rank = _severity_rank(level)
                    if rank is not None and rank >= min_rank:
                        filtered_min.append(entry)
                cve_entries = filtered_min

        severity_counts: dict[str, int] = {name: 0 for name in SEVERITIES}
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

        return {
            "target": target,
            "host": host,
            "timeout": timeout,
            "service_timeout": service_timeout,
            "workers": workers,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "ports": ports,
            "profile": profile,
            "services_checked": services_checked,
            "error": nvd_errors[0] if nvd_errors else None,
            "cve_entries": cve_entries,
            "cve_count": len(cve_entries),
            "severity_counts": severity_counts,
            "notes": notes,
        }
    finally:
        DEFAULT_API_URL = original_api


def _lookup_cve_id(product: str, version: str) -> str | None:
    """Return a representative CVE id for a product/version, if known."""
    product_lower = str(product).lower()
    version_lower = str(version).lower()
    for entry in SERVICE_VULNS:
        if str(entry["product"]).lower() != product_lower:
            continue
        if version_in_range(version_lower, entry):
            return str(entry["id"])
    return None


def format_cve_report_json(data: dict[str, object]) -> str:
    """Format CVE lookup results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_cve_report_csv(data: dict[str, object]) -> str:
    """Format CVE lookup results as CSV."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["source", "port", "product", "version", "cve_id", "severity", "score", "title", "description", "references", "cached", "offline_fallback"])

    entries = data.get("cve_entries") or []
    for entry in entries:
        source = str(entry.get("source", ""))
        port = entry.get("port", "")
        product = str(entry.get("product") or "")
        version = str(entry.get("version") or "")

        if source == "builtin":
            finding = entry.get("finding") or {}
            cve_id = finding.get("id", "")
            severity = str(finding.get("severity", "")).upper()
            score = ""
            title = str(finding.get("title", ""))
            description = str(finding.get("description", ""))
            refs = ""
            cached = ""
            offline_fallback = ""
        else:
            cve = entry.get("cve") or {}
            cve_id = entry.get("cve_id") or cve.get("id", "")
            severity = str(cve.get("severity", "")).upper()
            score = cve.get("score", "")
            title = ""
            description = str(cve.get("description", ""))
            refs = "; ".join(cve.get("references") or [])
            cached = "true" if entry.get("cached") else "false"
            offline_fallback = "true" if entry.get("offline_fallback") else "false"

        writer.writerow([source, port, product, version, cve_id, severity, score, title, description, refs, cached, offline_fallback])

    return output.getvalue().rstrip("\r\n")


def _finding_detail(finding: dict[str, object]) -> str:
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


def format_cve_report_markdown(data: dict[str, object]) -> str:
    """Format CVE lookup results as Markdown."""
    lines = ["# ethscan CVE Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    if data.get("profile"):
        lines.append(f"- **Profile:** {data['profile']}")
    if data.get("service_timeout"):
        lines.append(f"- **Service Timeout:** {data['service_timeout']}s")
    if data.get("workers"):
        lines.append(f"- **Workers:** {data['workers']}")
    lines.append(f"- **Cache Enabled:** {'Yes' if data['use_cache'] else 'No'}")
    lines.append(
        f"- **Offline Fallback:** {'Yes' if data['offline_fallback'] else 'No'}"
    )
    if data.get("api_url"):
        lines.append(f"- **API URL:** {data['api_url']}")
    if data.get("severity_filter"):
        lines.append(f"- **Severity Filter:** {data['severity_filter']}")
    if data.get("min_severity_filter"):
        lines.append(f"- **Min Severity:** {data['min_severity_filter']}")
    if data.get("ports"):
        ports_str = ", ".join(str(p) for p in data["ports"])
        lines.append(f"- **Ports Scanned:** {ports_str}")
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
                lines.append("- **Source:** Built-in database")
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
                lines.append("- **Source:** NVD API")
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
