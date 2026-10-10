"""Certificate Transparency log search module for ethscan.

Searches public CT log APIs (crt.sh) for certificates issued for a target
domain, extracting associated subdomains. Stdlib only with filesystem caching
and offline fallback.
"""

import json
import os
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_API_URL = "https://crt.sh/"
DEFAULT_TIMEOUT = 10.0
CACHE_DIR = Path.home() / ".cache" / "ethscan"
CACHE_FILE = CACHE_DIR / "cert_cache.json"
CACHE_TTL = 3600  # 1 hour


def _normalize_target(target: str) -> str:
    """Extract a bare domain from a target that may be a URL."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
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
    """Load the cert cache from disk."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: Dict[str, Dict]) -> None:
    """Save the cert cache to disk."""
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


def _fetch_cert_data(
    domain: str, timeout: float = DEFAULT_TIMEOUT, api_url: Optional[str] = None
) -> Optional[Dict]:
    """Fetch certificate transparency data from the public API."""
    base = (api_url or DEFAULT_API_URL).rstrip("/") + "/"
    url = f"{base}?q=%25.{domain}&output=json"
    req = urllib.request.Request(url, headers={"User-Agent": "ethscan/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, list):
            return None
        return {"domain": domain, "entries": data, "count": len(data)}
    except Exception:
        return None


def _get_cached_or_fetch(
    domain: str,
    timeout: float,
    use_cache: bool,
    offline_fallback: bool,
    api_url: Optional[str],
) -> Dict[str, object]:
    """Get cert data from cache or fetch from API."""
    cache = _load_cache() if use_cache else {}

    if use_cache and domain in cache and _is_cache_valid(cache[domain]):
        result = dict(cache[domain])
        result["cached"] = True
        return result

    data = _fetch_cert_data(domain, timeout, api_url)

    if data is None:
        if offline_fallback and use_cache and domain in cache:
            result = dict(cache[domain])
            result["cached"] = True
            result["offline_fallback"] = True
            return result
        return {
            "domain": domain,
            "entries": [],
            "count": 0,
            "error": "Failed to fetch certificate transparency data",
            "cached": False,
        }

    if use_cache:
        cache[domain] = data
        _save_cache(cache)

    data["cached"] = False
    return data


def _extract_subdomains(cert_data: Dict[str, object]) -> List[str]:
    """Extract unique subdomain names from CT entries."""
    names: List[str] = []
    seen: set = set()
    entries = cert_data.get("entries") or []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name_value") or entry.get("common_name") or ""
        if not name:
            continue
        for token in str(name).splitlines():
            token = token.strip().lower()
            if token and token not in seen:
                seen.add(token)
                names.append(token)
    return sorted(names)


def run_cert(
    target: str,
    timeout: float = DEFAULT_TIMEOUT,
    use_cache: bool = True,
    offline_fallback: bool = True,
    api_url: Optional[str] = None,
) -> Dict[str, object]:
    """Search Certificate Transparency logs for TARGET.

    Args:
        target: Domain or URL (e.g. "example.com" or "https://example.com").
        timeout: API request timeout in seconds.
        use_cache: Whether to use local filesystem cache.
        offline_fallback: Whether to use stale cache when API is unavailable.
        api_url: Optional custom CT API base URL (crt.sh-compatible JSON output).

    Returns:
        Structured results dict with CT entries and extracted subdomains.
    """
    global DEFAULT_API_URL
    original_api = DEFAULT_API_URL
    if api_url:
        DEFAULT_API_URL = api_url

    domain = _normalize_target(target)
    ip = _resolve_host(domain)

    notes: List[str] = []

    if ip is None:
        notes.append(f"Could not resolve host {domain!r} to an IPv4 address")
        return {
            "target": target,
            "domain": domain,
            "ip": None,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": None,
            "subdomains": [],
            "notes": notes,
        }

    cert_data = _get_cached_or_fetch(domain, timeout, use_cache, offline_fallback, api_url)
    subdomains = _extract_subdomains(cert_data)

    if cert_data.get("cached"):
        notes.append("Result served from cache")
    if cert_data.get("offline_fallback"):
        notes.append("API unavailable; used stale cached data (offline fallback)")

    result = {
        "target": target,
        "domain": domain,
        "ip": ip,
        "timeout": timeout,
        "use_cache": use_cache,
        "offline_fallback": offline_fallback,
        "cert_data": cert_data,
        "subdomains": subdomains,
        "notes": notes,
    }

    DEFAULT_API_URL = original_api
    return result


def format_cert_report_json(data: Dict[str, object]) -> str:
    """Format cert results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_cert_report_markdown(data: Dict[str, object]) -> str:
    """Format cert results as Markdown."""
    lines = ["# ethscan Certificate Transparency Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Domain:** {data['domain']}")
    if data.get("ip"):
        lines.append(f"- **Resolved IP:** {data['ip']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **Cache Enabled:** {'Yes' if data['use_cache'] else 'No'}")
    lines.append(f"- **Offline Fallback:** {'Yes' if data['offline_fallback'] else 'No'}")
    lines.append("")

    cert = data.get("cert_data")
    subdomains = data.get("subdomains") or []
    lines.append(f"- **Subdomains Found:** {len(subdomains)}")
    lines.append("")

    if cert:
        lines.append("## Certificate Transparency Data")
        if cert.get("error"):
            lines.append(f"- **Error:** {cert['error']}")
        else:
            lines.append(f"- **Entries Found:** {cert.get('count', 0)}")
            if cert.get("cached"):
                lines.append("- **Cached:** Yes")
            if cert.get("offline_fallback"):
                lines.append("- **Offline Fallback:** Yes")
        lines.append("")

    if subdomains:
        lines.append("## Subdomains Discovered")
        lines.append("| Subdomain |")
        lines.append("|-----------|")
        for name in subdomains:
            lines.append(f"| {name} |")
        lines.append("")
    else:
        lines.append("*No subdomains discovered.*")
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)