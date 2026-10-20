"""MAC address vendor lookup module for ethscan.

Resolves a MAC address to its vendor via OUI lookup using a public OUI
database API (api.macvendors.com) with filesystem caching and offline
fallback. Stdlib only.
"""
from __future__ import annotations

import csv
import io
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

from ethscan.fileio import load_json
from ethscan.target import parse_url

DEFAULT_API_URL = "https://api.macvendors.com/"
DEFAULT_TIMEOUT = 5.0
CACHE_DIR = Path.home() / ".cache" / "ethscan"
CACHE_FILE = CACHE_DIR / "mac_cache.json"
CACHE_TTL = 86400  # 24 hours


def _normalize_target(target: str) -> str:
    """Extract a bare MAC address from a target that may be a URL or MAC string."""
    normalized = target.strip().lower()
    if "://" in normalized:
        parsed = parse_url(normalized)
        normalized = (parsed.hostname or parsed.netloc or "").lower()
    # Strip any surrounding whitespace again after URL parsing
    normalized = normalized.strip()
    return normalized


def _resolve_host(host: str) -> str | None:
    """Resolve a hostname to an IPv4 address, returning None on failure."""
    try:
        import socket

        return socket.gethostbyname(host)
    # A host that is not a valid host name ("....") raises a UnicodeError,
    # which is a ValueError, when the resolver encodes it.
    except (socket.gaierror, socket.herror, ValueError):
        return None


def _load_cache() -> dict[str, dict]:
    """Load the MAC cache from disk.

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
    """Save the MAC cache to disk."""
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


def _fetch_mac_data(
    mac: str, timeout: float = DEFAULT_TIMEOUT, api_url: str | None = None
) -> dict | None:
    """Fetch MAC vendor data from the public OUI API."""
    base = (api_url or DEFAULT_API_URL).rstrip("/") + "/"
    url = f"{base}{mac}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ethscan/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        return {"mac": mac, "vendor": raw, "timestamp": time.time()}
    except Exception:  # noqa: BLE001 - urlopen can raise any failure; swallow to None
        return None


def _get_cached_or_fetch(
    mac: str,
    timeout: float,
    use_cache: bool,
    offline_fallback: bool,
    api_url: str | None,
) -> dict[str, object]:
    """Get MAC vendor data from cache or fetch from API."""
    cache = _load_cache() if use_cache else {}

    if use_cache and mac in cache and _is_cache_valid(cache[mac]):
        result = dict(cache[mac])
        result["cached"] = True
        return result

    data = _fetch_mac_data(mac, timeout, api_url)

    if data is None:
        if offline_fallback and use_cache and mac in cache:
            result = dict(cache[mac])
            result["cached"] = True
            result["offline_fallback"] = True
            return result
        return {
            "mac": mac,
            "vendor": None,
            "error": "Failed to fetch MAC vendor data",
            "cached": False,
        }

    if use_cache:
        cache[mac] = data
        _save_cache(cache)

    data["cached"] = False
    return data


def _extract_oui(mac: str) -> str:
    """Extract the 24-bit OUI prefix (first 8 hex chars) from a MAC address."""
    cleaned = mac.replace(":", "").replace("-", "").replace(".", "").lower()
    return cleaned[:8]


def run_mac(
    target: str,
    timeout: float = DEFAULT_TIMEOUT,
    use_cache: bool = True,
    offline_fallback: bool = True,
    api_url: str | None = None,
) -> dict[str, object]:
    """Look up the vendor for a MAC address (target).

    Args:
        target: MAC address, hostname, or URL (e.g., "00:1A:2B:3C:4D:5E", "00-1A-2B-3C-4D-5E").
        timeout: API request timeout in seconds.
        use_cache: Whether to use local filesystem cache.
        offline_fallback: Whether to use stale cache when API is unavailable.
        api_url: Optional custom OUI API base URL (api.macvendors.com compatible).

    Returns:
        Structured results dict with MAC vendor data and metadata.
    """
    global DEFAULT_API_URL
    original_api = DEFAULT_API_URL
    if api_url:
        DEFAULT_API_URL = api_url

    try:
        mac = _normalize_target(target)

        # If the target looks like a hostname or URL, try resolving to a MAC first
        # (only if it is not already a MAC address).
        notes: list[str] = []
        if not _is_mac_address(mac):
            resolved_mac = _resolve_host(mac)
            if resolved_mac is not None:
                notes.append(f"Resolved host {mac!r} to {resolved_mac}")
                mac = resolved_mac
            else:
                notes.append(f"Could not resolve host {mac!r} to a MAC address")
                return {
                    "target": target,
                    "mac": None,
                    "oui": None,
                    "timeout": timeout,
                    "use_cache": use_cache,
                    "offline_fallback": offline_fallback,
                    "mac_data": None,
                    "notes": notes,
                }

        mac_data = _get_cached_or_fetch(mac, timeout, use_cache, offline_fallback, api_url)

        if mac_data.get("cached"):
            notes.append("Result served from cache")
        if mac_data.get("offline_fallback"):
            notes.append("API unavailable; used stale cached data (offline fallback)")

        result = {
            "target": target,
            "mac": mac,
            "oui": _extract_oui(mac),
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "mac_data": mac_data,
            "notes": notes,
        }
        return result
    finally:
        DEFAULT_API_URL = original_api


def _is_mac_address(value: str) -> bool:
    """Return True if the value looks like a MAC address."""
    cleaned = value.replace(":", "").replace("-", "").replace(".", "")
    if len(cleaned) != 12:
        return False
    try:
        int(cleaned, 16)
    except ValueError:
        return False
    return True


def format_mac_report_json(data: dict[str, object]) -> str:
    """Format MAC vendor results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_mac_report_markdown(data: dict[str, object]) -> str:
    """Format MAC vendor results as Markdown."""
    lines = ["# ethscan MAC Vendor Lookup Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    if data.get("mac"):
        lines.append(f"- **MAC Address:** {data['mac']}")
    if data.get("oui"):
        lines.append(f"- **OUI:** {data['oui']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **Cache Enabled:** {'Yes' if data['use_cache'] else 'No'}")
    lines.append(f"- **Offline Fallback:** {'Yes' if data['offline_fallback'] else 'No'}")
    lines.append("")

    mac_data = data.get("mac_data")
    if mac_data:
        lines.append("## MAC Vendor Data")
        if mac_data.get("error"):
            lines.append(f"- **Error:** {mac_data['error']}")
        else:
            vendor = mac_data.get("vendor")
            if vendor:
                lines.append(f"- **Vendor:** {vendor}")
            if mac_data.get("cached"):
                lines.append("- **Cached:** Yes")
            if mac_data.get("offline_fallback"):
                lines.append("- **Offline Fallback:** Yes")
        lines.append("")
    else:
        lines.append("*No MAC vendor data available.*")
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def format_mac_report_csv(data: dict[str, object]) -> str:
    """Format MAC vendor results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "mac",
        "oui",
        "vendor",
        "cached",
        "offline_fallback",
        "error",
    ])
    mac_data = data.get("mac_data") or {}
    writer.writerow([
        data.get("target", ""),
        data.get("mac") or "",
        data.get("oui") or "",
        mac_data.get("vendor") or "",
        "true" if mac_data.get("cached") else "false",
        "true" if mac_data.get("offline_fallback") else "false",
        mac_data.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")