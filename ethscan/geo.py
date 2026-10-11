"""IP geolocation lookup module for ethscan.

Performs IP geolocation using a public IP-to-location API with caching
and offline fallback. Stdlib only.
"""

import json
import os
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_API_URL = "http://ip-api.com/json/"
DEFAULT_TIMEOUT = 5.0
CACHE_DIR = Path.home() / ".cache" / "ethscan"
CACHE_FILE = CACHE_DIR / "geo_cache.json"
CACHE_TTL = 86400
DEFAULT_MAX_DEPTH = 30

FIELDS = [
    "query",
    "status",
    "country",
    "countryCode",
    "region",
    "regionName",
    "city",
    "zip",
    "lat",
    "lon",
    "timezone",
    "isp",
    "org",
    "as",
    "reverse",
]


def _normalize_target(target: str) -> str:
    """Extract a bare hostname or IP from a target that may be a URL."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "http://" + normalized
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    host = (parsed.hostname or parsed.netloc or "").lower()
    return host


def _resolve_host(host: str) -> Optional[str]:
    """Resolve a hostname to an IPv4 address, returning None on failure."""
    try:
        return socket.gethostbyname(host)
    except (socket.gaierror, socket.herror):
        return None


def _load_cache() -> Dict[str, Dict]:
    """Load the geolocation cache from disk."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: Dict[str, Dict]) -> None:
    """Save the geolocation cache to disk."""
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


def _fetch_geo_data(ip: str, timeout: float = DEFAULT_TIMEOUT) -> Optional[Dict]:
    """Fetch geolocation data from the public API."""
    url = f"{DEFAULT_API_URL}{ip}?fields={','.join(FIELDS)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ethscan/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("status") == "success":
            data["timestamp"] = time.time()
            return data
        return None
    except Exception:
        return None


def _get_cached_or_fetch(
    ip: str, timeout: float, use_cache: bool, offline_fallback: bool
) -> Dict[str, object]:
    """Get geolocation data from cache or fetch from API."""
    cache = _load_cache() if use_cache else {}

    if use_cache and ip in cache and _is_cache_valid(cache[ip]):
        result = dict(cache[ip])
        result["cached"] = True
        return result

    data = _fetch_geo_data(ip, timeout)

    if data is None:
        if offline_fallback and use_cache and ip in cache:
            result = dict(cache[ip])
            result["cached"] = True
            result["offline_fallback"] = True
            return result
        return {
            "query": ip,
            "status": "fail",
            "error": "Failed to fetch geolocation data",
            "cached": False,
        }

    if use_cache:
        cache[ip] = data
        _save_cache(cache)

    data["cached"] = False
    return data


def run_geo(
    target: str,
    timeout: float = DEFAULT_TIMEOUT,
    use_cache: bool = True,
    offline_fallback: bool = True,
    api_url: Optional[str] = None,
    recursive: bool = False,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> Dict[str, object]:
    """Run IP geolocation lookup against target.

    Args:
        target: IP address, hostname, or URL (e.g., "8.8.8.8", "example.com", "https://example.com").
        timeout: API request timeout in seconds.
        use_cache: Whether to use local filesystem cache.
        offline_fallback: Whether to use stale cache when API is unavailable.
        api_url: Optional custom API base URL (must support same query format as ip-api.com).
        recursive: If True, run a traceroute to the target and geolocate each discovered hop IP.
        max_depth: Maximum number of traceroute hops when recursive is enabled (default 30, capped at 128).

    Returns:
        Structured results dict with geolocation data, metadata, and optional per-hop geolocation.
    """
    global DEFAULT_API_URL
    original_api = DEFAULT_API_URL
    if api_url:
        DEFAULT_API_URL = api_url.rstrip("/") + "/"

    host = _normalize_target(target)
    ip = _resolve_host(host)

    notes: List[str] = []

    if ip is None:
        notes.append(f"Could not resolve host {host!r} to an IPv4 address")
        return {
            "target": target,
            "host": host,
            "ip": None,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "recursive": recursive,
            "max_depth": max_depth,
            "geolocation": None,
            "hops": [],
            "hop_count": 0,
            "notes": notes,
        }

    geo_data = _get_cached_or_fetch(ip, timeout, use_cache, offline_fallback)

    if geo_data.get("cached"):
        notes.append("Result served from cache")
    if geo_data.get("offline_fallback"):
        notes.append("API unavailable; used stale cached data (offline fallback)")

    hops: List[Dict[str, object]] = []
    hop_count = 0

    if recursive:
        try:
            from ethscan.trace import run_trace

            trace_result = run_trace(
                target,
                timeout=timeout,
                max_hops=max_depth,
            )
            seen_ips: set = set()
            for hop in trace_result.get("hops", []):
                hop_ip = hop.get("ip")
                if not hop_ip or hop_ip in seen_ips:
                    continue
                seen_ips.add(hop_ip)
                hop_geo = _get_cached_or_fetch(hop_ip, timeout, use_cache, offline_fallback)
                hops.append(
                    {
                        "hop": hop.get("hop"),
                        "ip": hop_ip,
                        "host": hop.get("host"),
                        "response_type": hop.get("response_type"),
                        "rtt_avg_ms": hop.get("rtt_avg_ms"),
                        "geolocation": hop_geo,
                    }
                )
            hop_count = len(hops)
            if trace_result.get("notes"):
                for trace_note in trace_result["notes"]:
                    notes.append(f"traceroute: {trace_note}")
        except Exception as exc:
            notes.append(f"recursive hop geolocation failed: {exc}")

    result = {
        "target": target,
        "host": host,
        "ip": ip,
        "timeout": timeout,
        "use_cache": use_cache,
        "offline_fallback": offline_fallback,
        "recursive": recursive,
        "max_depth": max_depth,
        "geolocation": geo_data,
        "hops": hops,
        "hop_count": hop_count,
        "notes": notes,
    }

    DEFAULT_API_URL = original_api
    return result


def format_geo_report_json(data: Dict[str, object]) -> str:
    """Format geolocation results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_geo_report_markdown(data: Dict[str, object]) -> str:
    """Format geolocation results as Markdown."""
    lines = ["# ethscan IP Geolocation Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    if data.get("ip"):
        lines.append(f"- **Resolved IP:** {data['ip']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **Cache Enabled:** {'Yes' if data['use_cache'] else 'No'}")
    lines.append(f"- **Offline Fallback:** {'Yes' if data['offline_fallback'] else 'No'}")
    if data.get("recursive"):
        lines.append(
            f"- **Recursive Hop Geolocation:** Yes (max depth: {data.get('max_depth', 30)})"
        )
    lines.append("")

    geo = data.get("geolocation")
    if geo:
        lines.append("## Geolocation Data")
        if geo.get("status") == "success":
            fields_map = {
                "query": "Query IP",
                "country": "Country",
                "countryCode": "Country Code",
                "region": "Region Code",
                "regionName": "Region Name",
                "city": "City",
                "zip": "ZIP/Postal Code",
                "lat": "Latitude",
                "lon": "Longitude",
                "timezone": "Timezone",
                "isp": "ISP",
                "org": "Organization",
                "as": "AS Number/Name",
                "reverse": "Reverse DNS",
            }
            for key, label in fields_map.items():
                value = geo.get(key)
                if value is not None and value != "":
                    lines.append(f"- **{label}:** {value}")
            if geo.get("cached"):
                lines.append("- **Cached:** Yes")
            if geo.get("offline_fallback"):
                lines.append("- **Offline Fallback:** Yes")
        else:
            lines.append(f"- **Status:** {geo.get('status', 'fail')}")
            if geo.get("error"):
                lines.append(f"- **Error:** {geo['error']}")
    else:
        lines.append("*No geolocation data available.*")
    lines.append("")

    hops = data.get("hops") or []
    if data.get("recursive") and hops:
        lines.append("## Hop Geolocation")
        lines.append("| Hop | IP | Host | Response | RTT Avg (ms) | Country | City | ISP |")
        lines.append("|-----|----|------|----------|--------------|---------|------|-----|")
        for hop in hops:
            hop_geo = hop.get("geolocation") or {}
            country = hop_geo.get("country", "")
            city = hop_geo.get("city", "")
            isp = hop_geo.get("isp", "")
            lines.append(
                f"| {_markdown_escape(hop.get('hop'))} | "
                f"{_markdown_escape(hop.get('ip'))} | "
                f"{_markdown_escape(hop.get('host'))} | "
                f"{_markdown_escape(hop.get('response_type'))} | "
                f"{_markdown_escape(hop.get('rtt_avg_ms'))} | "
                f"{_markdown_escape(country)} | "
                f"{_markdown_escape(city)} | "
                f"{_markdown_escape(isp)} |"
            )
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)