"""Security headers check for ethscan."""

import json
import urllib.request
import urllib.error
from typing import Dict, List, Tuple

from ethscan.web import SECURITY_HEADERS, _parse_url, fetch_headers, check_security_headers


def run_headers(target: str, timeout: float = 5.0) -> Dict[str, object]:
    """Run security headers check against TARGET.

    Args:
        target: URL to check (e.g. ``https://example.com``).
        timeout: Connection timeout in seconds.

    Returns:
        Structured results with security headers analysis.
    """
    host, port, is_secure = _parse_url(target)
    url = target if "://" in target.strip() else ("https://" + target.strip() if is_secure else "http://" + target.strip())
    headers = fetch_headers(url, timeout=timeout)

    results: Dict[str, object] = {
        "target": target,
        "host": host,
        "port": port,
        "secure": is_secure,
        "headers": dict(headers),
    }

    results["security_headers"] = check_security_headers(headers)

    return results


def format_headers_report_json(data: Dict[str, object]) -> str:
    """Format security headers check results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_headers_report_markdown(data: Dict[str, object]) -> str:
    """Format security headers check results as Markdown."""
    lines = ["# ethscan Security Headers Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append(f"- **HTTPS:** {'Yes' if data['secure'] else 'No'}")
    lines.append("")

    sh = data["security_headers"]
    lines.append("## Security Headers")
    lines.append(f"- Present: {sh['present_count']}/{sh['total']}")
    if sh["present"]:
        lines.append("- Present headers:")
        for header in sh["present"]:
            lines.append(f"  - `{header}`")
    if sh["missing"]:
        lines.append("- Missing headers:")
        for header in sh["missing"]:
            lines.append(f"  - `{header}`")
    lines.append("")

    return "\n".join(lines)