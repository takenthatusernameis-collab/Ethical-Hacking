"""Security headers check for ethscan."""

import csv
import io
import json
from typing import Any

from ethscan.web import _parse_url, check_security_headers, fetch_headers


def run_headers(target: str, timeout: float = 5.0) -> dict[str, Any]:
    """Run security headers check against TARGET.

    Args:
        target: URL to check (e.g. ``https://example.com``).
        timeout: Connection timeout in seconds.

    Returns:
        Structured results with security headers analysis.
    """
    host, port, is_secure = _parse_url(target)
    url = target if "://" in target.strip() else ("https://" + target.strip() if is_secure else "http://" + target.strip())
    fetched = fetch_headers(url, timeout=timeout)
    headers = dict(fetched)

    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": port,
        "secure": is_secure,
        "headers": headers,
        "error": None,
    }

    # A caller that replaces ``fetch_headers`` may hand back a plain dict,
    # which carries no reason of its own.
    fetch_error = getattr(fetched, "error", None)
    if fetch_error:
        results["error"] = fetch_error

    results["security_headers"] = check_security_headers(headers)

    return results


def format_headers_report_json(data: dict[str, Any]) -> str:
    """Format security headers check results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_headers_report_markdown(data: dict[str, Any]) -> str:
    """Format security headers check results as Markdown."""
    lines = ["# ethscan Security Headers Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Host:** {data.get('host', '')}")
    lines.append(f"- **Port:** {data.get('port', '')}")
    lines.append(f"- **HTTPS:** {'Yes' if data.get('secure') else 'No'}")
    if data.get("error"):
        lines.append(f"- **Error:** {data.get('error')}")
    lines.append("")

    sh = data.get("security_headers") or {}
    if isinstance(sh, dict):
        lines.append("## Security Headers")
        lines.append(f"- Present: {sh.get('present_count', 0)}/{sh.get('total', 0)}")
        present = sh.get("present") or []
        missing = sh.get("missing") or []
        if present:
            lines.append("- Present headers:")
            for header in present:
                lines.append(f"  - `{header}`")
        if missing:
            lines.append("- Missing headers:")
            for header in missing:
                lines.append(f"  - `{header}`")
    lines.append("")

    return "\n".join(lines)


def format_headers_report_csv(data: dict[str, Any]) -> str:
    """Format security headers check results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    sh = data.get("security_headers") or {}
    if not isinstance(sh, dict):
        sh = {}
    writer.writerow(["field", "value"])
    writer.writerow(["target", data.get("target", "")])
    writer.writerow(["host", data.get("host", "")])
    writer.writerow(["port", data.get("port", "")])
    writer.writerow(["https", "true" if data.get("secure") else "false"])
    writer.writerow(["error", data.get("error") or ""])
    writer.writerow(["present_count", sh.get("present_count", 0)])
    writer.writerow(["missing_count", sh.get("missing_count", 0)])
    writer.writerow(["total", sh.get("total", 0)])
    writer.writerow([])
    writer.writerow(["header", "status"])
    for header in sh.get("present", []) or []:
        writer.writerow([header, "present"])
    for header in sh.get("missing", []) or []:
        writer.writerow([header, "missing"])
    return output.getvalue().rstrip("\r\n")