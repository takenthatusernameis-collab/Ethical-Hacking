"""Certificate Transparency log search module for ethscan.

Searches public CT log APIs (crt.sh) for certificates issued for a target
domain, extracting associated subdomains. Stdlib only with filesystem caching
and offline fallback.
"""
from __future__ import annotations

import csv
import io
import json
import math
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

from ethscan.fileio import load_json
from ethscan.target import parse_url

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
    parsed = parse_url(normalized)
    host = (parsed.hostname or parsed.netloc or "").lower()
    return host


def _resolve_host(host: str) -> str | None:
    """Resolve a hostname to an IPv4 address, returning None on failure."""
    try:
        return socket.gethostbyname(host)
    # A host that is not a valid host name ("....") raises a UnicodeError,
    # which is a ValueError, when the resolver encodes it. A resolver that
    # fails with any other error type is a failed lookup as well.
    except Exception:  # noqa: BLE001 - resolver can raise any type
        return None


def _load_cache() -> dict[str, dict]:
    """Load the cert cache from disk.

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
    """Save the cert cache to disk."""
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


def _fetch_cert_data(
    domain: str, timeout: float = DEFAULT_TIMEOUT, api_url: str | None = None
) -> dict | None:
    """Fetch certificate transparency data from the public API."""
    base = (api_url or DEFAULT_API_URL).rstrip("/") + "/"
    url = f"{base}?q=%25.{domain}&output=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ethscan/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return None
        if not isinstance(data, list):
            return None
        return {"domain": domain, "entries": data, "count": len(data)}
    except Exception:  # noqa: BLE001 - urlopen/JSON can raise any failure; swallow to None
        return None


def _get_cached_or_fetch(
    domain: str,
    timeout: float,
    use_cache: bool,
    offline_fallback: bool,
    api_url: str | None,
) -> dict[str, object]:
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


def _extract_subdomains(cert_data: dict[str, object]) -> list[str]:
    """Extract unique subdomain names from CT entries."""
    names: list[str] = []
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
    api_url: str | None = None,
) -> dict[str, object]:
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

    try:
        domain = _normalize_target(target)
        ip = _resolve_host(domain)

        notes: list[str] = []

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
        return result
    finally:
        DEFAULT_API_URL = original_api


def format_cert_report_json(data: dict[str, object]) -> str:
    """Format cert results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_cert_report_markdown(data: dict[str, object]) -> str:
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


def format_cert_report_csv(data: dict[str, object]) -> str:
    """Format cert results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target", "domain", "ip", "subdomain"])
    target = data.get("target", "")
    domain = data.get("domain", "")
    ip = data.get("ip") or ""
    subdomains = data.get("subdomains") or []
    if subdomains:
        for name in subdomains:
            writer.writerow([target, domain, ip, name])
    else:
        writer.writerow([target, domain, ip, ""])
    return output.getvalue().rstrip("\r\n")