"""Consolidated web assessment module for ethscan (urlcheck).

Combines:
- web: security headers, information disclosure, SSL configuration
- fuzz: HTTP path discovery via wordlist
- ssl: SSL/TLS certificate inspection
"""

import json
from typing import Dict, List, Optional, Tuple

from ethscan.fuzz import (
    DEFAULT_WORDLIST as FUZZ_DEFAULT_WORDLIST,
    load_wordlist as load_fuzz_wordlist,
    run_fuzz,
)
from ethscan.ssl import run_ssl
from ethscan.web import run_web_checks


def _normalize_url(target: str) -> str:
    """Ensure target has a scheme for HTTP requests."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    return normalized


def run_urlcheck(
    target: str,
    checks: List[str],
    wordlist: Optional[List[str]] = None,
    fuzz_paths: bool = True,
    port: int = 443,
    timeout: float = 5.0,
    workers: int = 10,
) -> Dict[str, object]:
    """Run consolidated web assessment against target.

    Args:
        target: Target URL (e.g., https://example.com).
        checks: List of web checks to run: "headers", "info_disclosure", "ssl".
        wordlist: Custom wordlist for fuzzing. If None, uses built-in default.
        fuzz_paths: Whether to run HTTP fuzzing/path discovery.
        port: TLS port for SSL certificate inspection (default: 443).
        timeout: Per-request timeout in seconds.
        workers: Maximum concurrent workers for fuzzing.

    Returns:
        Structured results with sections for web, fuzz, ssl, and summary.
    """
    normalized_target = _normalize_url(target)
    results: Dict[str, object] = {
        "target": target,
        "normalized_target": normalized_target,
        "checks_requested": checks,
        "fuzz_enabled": fuzz_paths,
        "port": port,
        "timeout": timeout,
        "workers": workers,
    }

    web_results = run_web_checks(normalized_target, checks, timeout=timeout)
    results["web"] = web_results

    if fuzz_paths:
        fuzz_results = run_fuzz(normalized_target, wordlist=wordlist, timeout=timeout)
        results["fuzz"] = fuzz_results
    else:
        results["fuzz"] = None

    host = web_results.get("host")
    if host and "ssl" in checks:
        ssl_results = run_ssl(host, port=port, timeout=timeout)
        results["ssl"] = ssl_results
    else:
        results["ssl"] = None

    total_findings = 0
    if results.get("web", {}).get("security_headers", {}).get("missing_count", 0) > 0:
        total_findings += results["web"]["security_headers"]["missing_count"]
    if results.get("web", {}).get("information_disclosure"):
        total_findings += len(results["web"]["information_disclosure"])
    fuzz_findings = results.get("fuzz", {}).get("findings") if results.get("fuzz") else None
    if fuzz_findings:
        total_findings += len(fuzz_findings)
    ssl_data = results.get("ssl")
    if ssl_data and ssl_data.get("cert"):
        cert = results["ssl"]["cert"]
        if cert.get("key_size") and cert["key_size"] < 2048:
            total_findings += 1
        if cert.get("signature_algorithm") and "sha1" in cert["signature_algorithm"].lower():
            total_findings += 1
        if not results["ssl"].get("valid", False):
            total_findings += 1

    results["summary"] = {
        "total_findings": total_findings,
        "web_checks_run": [c for c in checks if c in {"headers", "info_disclosure", "ssl"}],
        "fuzz_enabled": fuzz_paths,
        "ssl_checked": results["ssl"] is not None,
    }

    return results


def format_urlcheck_report_json(data: Dict[str, object]) -> str:
    """Format urlcheck results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_urlcheck_report_markdown(data: Dict[str, object]) -> str:
    """Format urlcheck results as Markdown."""
    lines = ["# ethscan Consolidated Web Assessment Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Normalized Target:** {data['normalized_target']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **Workers:** {data['workers']}")
    lines.append("")

    summary = data.get("summary", {})
    lines.append("## Summary")
    lines.append(f"- **Total Findings:** {summary.get('total_findings', 0)}")
    lines.append(f"- **Web Checks Run:** {', '.join(summary.get('web_checks_run', [])) or 'None'}")
    lines.append(f"- **Fuzzing Enabled:** {'Yes' if summary.get('fuzz_enabled') else 'No'}")
    lines.append(f"- **SSL Checked:** {'Yes' if summary.get('ssl_checked') else 'No'}")
    lines.append("")

    web = data.get("web", {})
    if web:
        lines.append("## Web Security Checks")
        lines.append(f"- **Host:** {web.get('host')}")
        lines.append(f"- **Port:** {web.get('port')}")
        lines.append(f"- **HTTPS:** {'Yes' if web.get('secure') else 'No'}")
        lines.append("")

        if "security_headers" in web:
            sh = web["security_headers"]
            lines.append("### Security Headers")
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

        if "information_disclosure" in web:
            findings = web["information_disclosure"]
            lines.append("### Information Disclosure")
            if findings:
                lines.append("| Header | Value | Description |")
                lines.append("|--------|-------|-------------|")
                for finding in findings:
                    lines.append(f"| {finding['header']} | {finding['value']} | {finding['description']} |")
            else:
                lines.append("No information disclosure headers detected.")
            lines.append("")

        if "ssl" in web:
            ssl_info = web["ssl"]
            lines.append("### SSL Configuration (from web check)")
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

    fuzz = data.get("fuzz")
    if fuzz:
        lines.append("## HTTP Fuzzing / Path Discovery")
        lines.append(f"- **Base URL:** {fuzz['base_url']}")
        lines.append(f"- **Paths Tested:** {fuzz['paths_tested']}")
        lines.append(f"- **Findings (non-404):** {len(fuzz['findings'])}")
        lines.append("")

        if fuzz["findings"]:
            lines.append("### Findings")
            lines.append("| Path | Status Code |")
            lines.append("|------|-------------|")
            for finding in fuzz["findings"]:
                code = finding["status_code"]
                path = finding["path"]
                lines.append(f"| {path} | {code} |")
            lines.append("")

        lines.append("### All Results")
        lines.append("| Path | Status Code | Error |")
        lines.append("|------|-------------|-------|")
        for result in fuzz["all_results"]:
            code = result["status_code"] if result["status_code"] is not None else "N/A"
            error = result["error"] or ""
            lines.append(f"| {result['path']} | {code} | {error} |")
        lines.append("")

    ssl_data = data.get("ssl")
    if ssl_data:
        lines.append("## SSL/TLS Certificate Inspection")
        lines.append(f"- **Host:** {ssl_data['host']}")
        lines.append(f"- **Port:** {ssl_data['port']}")
        lines.append("")

        if ssl_data.get("error"):
            lines.append(f"- **Error:** {ssl_data['error']}")
            lines.append("")

        cert = ssl_data.get("cert") or {}
        if cert:
            lines.append("### Certificate")
            lines.append(f"- **Valid:** {'Yes' if ssl_data.get('valid') else 'No'}")
            if cert.get("subject"):
                lines.append(f"- **Subject:** {cert['subject']}")
            if cert.get("issuer"):
                lines.append(f"- **Issuer:** {cert['issuer']}")
            if cert.get("not_before"):
                lines.append(f"- **Not Before:** {cert['not_before']}")
            if cert.get("not_after"):
                lines.append(f"- **Not After:** {cert['not_after']}")
            if cert.get("signature_algorithm"):
                lines.append(f"- **Signature Algorithm:** {cert['signature_algorithm']}")
            if cert.get("key_size"):
                lines.append(f"- **Key Size:** {cert['key_size']} bits")
            if cert.get("sans"):
                lines.append("- **Subject Alternative Names:**")
                for san in cert["sans"]:
                    lines.append(f"  - {san}")
            lines.append(f"- **Chain Length:** {ssl_data.get('chain_length', 0)}")
            lines.append("")

    return "\n".join(lines)