"""Web application security checks for ethscan."""

import csv
import io
import json
import socket
import ssl
import urllib.error
import urllib.request

# Recommended security headers and their importance.
SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": "Mitigates XSS and injection attacks.",
    "X-Content-Type-Options": "Prevents MIME type sniffing.",
    "X-Frame-Options": "Prevents clickjacking.",
    "Strict-Transport-Security": "Enforces HTTPS connections.",
    "Referrer-Policy": "Controls referrer information leakage.",
    "Permissions-Policy": "Restricts browser feature access.",
    "X-XSS-Protection": "Enables browser XSS filter (legacy).",
}

# Headers whose presence may indicate information disclosure.
INFO_DISCLOSURE_HEADERS: dict[str, str] = {
    "Server": "Reveals server software version.",
    "X-Powered-By": "Reveals technology stack.",
    "X-ASPNET-Version": "Reveals ASP.NET version.",
    "X-ASPNET-Mvc-Version": "Reveals ASP.NET MVC version.",
}


def _parse_url(target: str) -> tuple[str, int, bool]:
    """Parse a target URL into host, port, and secure flag.

    Args:
        target: URL like ``https://example.com`` or ``http://example.com:8080``.

    Returns:
        Tuple of (host, port, is_secure).
    """
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    parsed = urllib.request.urlparse(normalized)
    host = parsed.hostname or "localhost"
    scheme = parsed.scheme.lower()
    if scheme == "https":
        is_secure = True
        port = parsed.port or 443
    else:
        is_secure = False
        port = parsed.port or 80
    return host, port, is_secure


def fetch_headers(target: str, timeout: float = 5.0) -> dict[str, str]:
    """Fetch HTTP response headers from ``target``.

    Args:
        target: URL to request.
        timeout: Connection timeout in seconds.

    Returns:
        Dictionary of lowercase header names to values.
    """
    try:
        request = urllib.request.Request(target, method="HEAD")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        # HTTPError still carries headers.
        try:
            return {key.lower(): value for key, value in exc.headers.items()}
        except Exception:
            return {}
    except (urllib.error.URLError, OSError, ValueError):
        return {}


def check_security_headers(headers: dict[str, str]) -> dict[str, object]:
    """Check which recommended security headers are present or missing.

    Args:
        headers: Response headers (lowercase keys).

    Returns:
        Dict with ``present``, ``missing``, and ``total`` counts.
    """
    present: list[str] = []
    missing: list[str] = []
    for header in SECURITY_HEADERS:
        if header.lower() in headers:
            present.append(header)
        else:
            missing.append(header)
    return {
        "present": present,
        "missing": missing,
        "total": len(SECURITY_HEADERS),
        "present_count": len(present),
        "missing_count": len(missing),
    }


def check_information_disclosure(headers: dict[str, str]) -> list[dict[str, str]]:
    """Detect headers that may leak server technology information.

    Args:
        headers: Response headers (lowercase keys).

    Returns:
        List of findings, each with ``header``, ``value``, and ``description``.
    """
    findings: list[dict[str, str]] = []
    for header, description in INFO_DISCLOSURE_HEADERS.items():
        if header.lower() in headers:
            findings.append(
                {
                    "header": header,
                    "value": headers[header.lower()],
                    "description": description,
                }
            )
    return findings


def check_ssl_configuration(host: str, port: int = 443, timeout: float = 5.0) -> dict[str, object]:
    """Check SSL/TLS certificate validity for ``host``.

    Args:
        host: Target hostname.
        port: TLS port (default 443).
        timeout: Connection timeout in seconds.

    Returns:
        Dict with ``valid``, ``subject``, ``issuer``, ``not_after``,
        ``days_remaining``, ``error`` (if any), and ``chain_length``.
    """
    result: dict[str, object] = {
        "valid": False,
        "subject": None,
        "issuer": None,
        "not_after": None,
        "days_remaining": None,
        "error": None,
        "chain_length": 0,
    }
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock, context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = None
                # Try to get cert in a mock-friendly way
                try:
                    cert_bin = ssock.getpeercert(True)
                    if isinstance(cert_bin, dict):
                        cert = cert_bin
                    elif isinstance(cert_bin, bytes):
                        try:
                            pem = ssl.DER_cert_to_PEM_cert(cert_bin)
                            import os
                            import tempfile
                            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".pem") as handle:
                                handle.write(pem)
                                cert_path = handle.name
                            try:
                                cert = ssl._ssl._test_decode_cert(cert_path)
                            finally:
                                try:
                                    os.unlink(cert_path)
                                except Exception:
                                    pass
                        except Exception:
                            cert = ssock.getpeercert()
                    else:
                        cert = ssock.getpeercert()
                except Exception:
                    try:
                        cert = ssock.getpeercert()
                    except Exception:
                        cert = None
                result["chain_length"] = len(ssock.get_verified_chain()) if ssock.get_verified_chain() else 0
                if cert:
                    subject = dict(
                        item[0] for item in cert.get("subject", ()) if isinstance(item, tuple) and len(item) >= 2
                    )
                    issuer = dict(
                        item[0] for item in cert.get("issuer", ()) if isinstance(item, tuple) and len(item) >= 2
                    )
                    result["subject"] = subject.get("commonName") or subject or None
                    result["issuer"] = issuer.get("commonName") or issuer or None
                    not_after = cert.get("notAfter")
                    result["not_after"] = not_after
                    if not_after:
                        from datetime import datetime
                        try:
                            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                            from datetime import timezone
                            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                            now_utc = datetime.now(timezone.utc)
                            expiry_tz = expiry.replace(tzinfo=timezone.utc)
                            result["days_remaining"] = (expiry_tz - now_utc).days
                            result["valid"] = result["days_remaining"] > 0
                        except (ValueError, TypeError):
                            result["valid"] = False
    except Exception as exc:
        result["error"] = str(exc)
    return result


def run_web_checks(target: str, checks: list[str], timeout: float = 5.0) -> dict[str, object]:
    """Run the requested web application security checks.

    Args:
        target: URL to check (e.g. ``https://example.com``).
        checks: List of check names: ``headers``, ``ssl``, ``info_disclosure``.
        timeout: Per-request timeout in seconds.

    Returns:
        Structured results keyed by check name.
    """
    host, port, is_secure = _parse_url(target)
    results: dict[str, object] = {"target": target, "host": host, "port": port, "secure": is_secure}
    headers: dict[str, str] = {}

    needs_headers = any(c in checks for c in ["headers", "info_disclosure", "security_headers"])
    if needs_headers:
        url = target if "://" in target.strip() else ("https://" + target.strip() if is_secure else "http://" + target.strip())
        headers = fetch_headers(url, timeout=timeout)
        results["headers"] = dict(headers)

    if "headers" in checks or "security_headers" in checks:
        results["security_headers"] = check_security_headers(headers)

    if "info_disclosure" in checks:
        results["information_disclosure"] = check_information_disclosure(headers)

    if "ssl" in checks:
        if is_secure:
            results["ssl"] = check_ssl_configuration(host, port=port, timeout=timeout)
        else:
            results["ssl"] = {"error": "Target is not HTTPS", "valid": False}

    return results


def format_web_report_json(data: dict[str, object]) -> str:
    """Format web check results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_web_report_markdown(data: dict[str, object]) -> str:
    """Format web check results as Markdown."""
    lines = ["# ethscan Web Security Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append(f"- **HTTPS:** {'Yes' if data['secure'] else 'No'}")
    lines.append("")

    if "security_headers" in data:
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

    if "information_disclosure" in data:
        findings = data["information_disclosure"]
        lines.append("## Information Disclosure")
        if findings:
            lines.append("| Header | Value | Description |")
            lines.append("|--------|-------|-------------|")
            for finding in findings:
                lines.append(f"| {finding['header']} | {finding['value']} | {finding['description']} |")
        else:
            lines.append("No information disclosure headers detected.")
        lines.append("")

    if "ssl" in data:
        ssl_info = data["ssl"]
        lines.append("## SSL/TLS")
        if ssl_info.get("error"):
            lines.append(f"- **Error:** {ssl_info['error']}")
        else:
            lines.append(f"- **Valid:** {'Yes' if ssl_info.get('valid') else 'No'}")
            if ssl_info.get("subject"):
                lines.append(f"- **Subject:** {ssl_info['subject']}")
            if ssl_info.get("issuer"):
                lines.append(f"- **Issuer:** {ssl_info['issuer']}")
            if ssl_info.get("not_after"):
                lines.append(f"- **Expires:** {ssl_info['not_after']}")
            if ssl_info.get("days_remaining") is not None:
                lines.append(f"- **Days Remaining:** {ssl_info['days_remaining']}")
        lines.append("")

    if "notes" in data:
        lines.append("## Notes")
        lines.append(str(data["notes"]))
        lines.append("")

    return "\n".join(lines)


def format_web_report_csv(data: dict[str, object]) -> str:
    """Format web check results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["field", "value"])
    writer.writerow(["target", data.get("target", "")])
    writer.writerow(["host", data.get("host", "")])
    writer.writerow(["port", data.get("port", "")])
    writer.writerow(["https", "true" if data.get("secure") else "false"])

    if "security_headers" in data:
        sh = data["security_headers"]
        writer.writerow([])
        writer.writerow(["security_header", "status"])
        for header in sh.get("present", []):
            writer.writerow([header, "present"])
        for header in sh.get("missing", []):
            writer.writerow([header, "missing"])

    if "information_disclosure" in data:
        findings = data["information_disclosure"]
        writer.writerow([])
        writer.writerow(["disclosure_header", "value", "description"])
        for finding in findings:
            writer.writerow([finding.get("header", ""), finding.get("value", ""), finding.get("description", "")])

    if "ssl" in data:
        ssl_info = data["ssl"]
        writer.writerow([])
        writer.writerow(["ssl_field", "value"])
        writer.writerow(["valid", "true" if ssl_info.get("valid") else "false"])
        writer.writerow(["error", ssl_info.get("error") or ""])
        writer.writerow(["subject", ssl_info.get("subject") or ""])
        writer.writerow(["issuer", ssl_info.get("issuer") or ""])
        writer.writerow(["not_after", ssl_info.get("not_after") or ""])
        writer.writerow(["days_remaining", ssl_info.get("days_remaining") or ""])
        writer.writerow(["chain_length", ssl_info.get("chain_length", 0)])

    return output.getvalue().rstrip("\r\n")