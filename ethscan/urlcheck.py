"""Consolidated web assessment module for ethscan (urlcheck).

Combines:
- web: security headers, information disclosure, SSL configuration
- fuzz: HTTP path discovery via wordlist
- ssl: SSL/TLS certificate inspection
"""
from __future__ import annotations

import csv
import io
import json

from ethscan.fuzz import (
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
    checks: list[str],
    wordlist: list[str] | None = None,
    fuzz_paths: bool = True,
    port: int = 443,
    timeout: float = 5.0,
    workers: int = 10,
) -> dict[str, object]:
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
    results: dict[str, object] = {
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
        fuzz_results = run_fuzz(
            normalized_target, wordlist=wordlist, timeout=timeout, workers=workers
        )
        results["fuzz"] = fuzz_results
    else:
        results["fuzz"] = None

    host = None
    if isinstance(web_results, dict):
        host = web_results.get("host")
    if isinstance(host, str) and "ssl" in checks:
        ssl_results = run_ssl(host, port=port, timeout=timeout)
        results["ssl"] = ssl_results
    else:
        results["ssl"] = None

    total_findings = 0
    web_dict = results.get("web")
    if isinstance(web_dict, dict):
        sec_headers = web_dict.get("security_headers")
        if isinstance(sec_headers, dict):
            missing_count = sec_headers.get("missing_count", 0)
            if isinstance(missing_count, int) and missing_count > 0:
                total_findings += missing_count
        info_disc = web_dict.get("information_disclosure")
        if isinstance(info_disc, (list, tuple, set)):
            total_findings += len(info_disc)
    fuzz_obj = results.get("fuzz")
    fuzz_findings = None
    if isinstance(fuzz_obj, dict):
        fuzz_findings = fuzz_obj.get("findings")
    if isinstance(fuzz_findings, (list, tuple, set)):
        total_findings += len(fuzz_findings)
    ssl_data = results.get("ssl")
    if isinstance(ssl_data, dict):
        cert = ssl_data.get("cert")
        if isinstance(cert, dict):
            key_size = cert.get("key_size")
            if isinstance(key_size, int) and key_size < 2048:
                total_findings += 1
            sig_alg = cert.get("signature_algorithm")
            if isinstance(sig_alg, str) and "sha1" in sig_alg.lower():
                total_findings += 1
        valid = ssl_data.get("valid")
        if not valid:
            total_findings += 1

    results["summary"] = {
        "total_findings": total_findings,
        "web_checks_run": [c for c in checks if c in {"headers", "info_disclosure", "ssl"}],
        "fuzz_enabled": fuzz_paths,
        "ssl_checked": results["ssl"] is not None,
    }

    return results


def format_urlcheck_report_json(data: dict[str, object]) -> str:
    """Format urlcheck results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_urlcheck_report_markdown(data: dict[str, object]) -> str:
    """Format urlcheck results as Markdown."""
    lines = ["# ethscan Consolidated Web Assessment Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Normalized Target:** {data['normalized_target']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **Workers:** {data['workers']}")
    lines.append("")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    lines.append("## Summary")
    lines.append(f"- **Total Findings:** {summary.get('total_findings', 0)}")
    web_checks_run = summary.get("web_checks_run")
    if isinstance(web_checks_run, (list, tuple)):
        wcr_str = ", ".join(str(x) for x in web_checks_run) or "None"
    else:
        wcr_str = str(web_checks_run) if web_checks_run else "None"
    lines.append(f"- **Web Checks Run:** {wcr_str}")
    lines.append(f"- **Fuzzing Enabled:** {'Yes' if summary.get('fuzz_enabled') else 'No'}")
    lines.append(f"- **SSL Checked:** {'Yes' if summary.get('ssl_checked') else 'No'}")
    lines.append("")

    web = data.get("web")
    if isinstance(web, dict):
        lines.append("## Web Security Checks")
        host_w = web.get("host")
        port_w = web.get("port")
        if host_w is not None:
            lines.append(f"- **Host:** {host_w}")
        if port_w is not None:
            lines.append(f"- **Port:** {port_w}")
        if "secure" in web:
            lines.append(f"- **HTTPS:** {'Yes' if web.get('secure') else 'No'}")
        web_error = web.get("error")
        if isinstance(web_error, str):
            lines.append(f"- **Error:** {web_error}")
        lines.append("")

        sec_headers = web.get("security_headers")
        if isinstance(sec_headers, dict):
            sh = sec_headers
            lines.append("### Security Headers")
            present_count = sh.get("present_count")
            total_sh = sh.get("total")
            if present_count is not None and total_sh is not None:
                lines.append(f"- Present: {present_count}/{total_sh}")
            present_list = sh.get("present")
            if isinstance(present_list, (list, tuple)) and present_list:
                lines.append("- Present headers:")
                for header in present_list:
                    if isinstance(header, str):
                        lines.append(f"  - `{header}`")
            missing_list = sh.get("missing")
            if isinstance(missing_list, (list, tuple)) and missing_list:
                    lines.append("- Missing headers:")
                    for header in missing_list:
                        if isinstance(header, str):
                            lines.append(f"  - `{header}`")
            lines.append("")

        info_disc = web.get("information_disclosure")
        if isinstance(info_disc, (list, tuple)):
            findings = info_disc
            lines.append("### Information Disclosure")
            if findings:
                lines.append("| Header | Value | Description |")
                lines.append("|--------|-------|-------------|")
                for finding in findings:
                    if isinstance(finding, dict):
                        header_f = finding.get("header", "")
                        value_f = finding.get("value", "")
                        desc_f = finding.get("description", "")
                        lines.append(f"| {header_f} | {value_f} | {desc_f} |")
            else:
                lines.append("No information disclosure headers detected.")
            lines.append("")

        ssl_info = web.get("ssl")
        if isinstance(ssl_info, dict):
            lines.append("### SSL Configuration (from web check)")
            ssl_err = ssl_info.get("error")
            if isinstance(ssl_err, str):
                lines.append(f"- **Error:** {ssl_err}")
            else:
                valid_si = ssl_info.get("valid")
                if "valid" in ssl_info:
                    lines.append(f"- **Valid:** {'Yes' if valid_si else 'No'}")
                subj = ssl_info.get("subject")
                if subj is not None:
                    lines.append(f"- **Subject:** {subj}")
                iss = ssl_info.get("issuer")
                if iss is not None:
                    lines.append(f"- **Issuer:** {iss}")
                na = ssl_info.get("not_after")
                if na is not None:
                    lines.append(f"- **Expires:** {na}")
                dr = ssl_info.get("days_remaining")
                if dr is not None:
                    lines.append(f"- **Days Remaining:** {dr}")
            lines.append("")

    fuzz = data.get("fuzz")
    if isinstance(fuzz, dict):
        lines.append("## HTTP Fuzzing / Path Discovery")
        base_url_f = fuzz.get("base_url")
        paths_tested = fuzz.get("paths_tested")
        if base_url_f is not None:
            lines.append(f"- **Base URL:** {base_url_f}")
        if paths_tested is not None:
            lines.append(f"- **Paths Tested:** {paths_tested}")
        findings_f = fuzz.get("findings") or []
        if isinstance(findings_f, (list, tuple)):
            lines.append(f"- **Findings (non-404):** {len(findings_f)}")
        else:
            findings_f = []
        lines.append("")

        if findings_f:
            lines.append("### Findings")
            lines.append("| Path | Status Code |")
            lines.append("|------|-------------|")
            for finding in findings_f:
                if isinstance(finding, dict):
                    code = finding.get("status_code")
                    path = finding.get("path")
                    lines.append(f"| {path} | {code} |")
            lines.append("")

        lines.append("### All Results")
        lines.append("| Path | Status Code | Error |")
        lines.append("|------|-------------|-------|")
        all_res = fuzz.get("all_results") or []
        if isinstance(all_res, (list, tuple)):
            for result in all_res:
                if isinstance(result, dict):
                    code_r = result.get("status_code")
                    code_str = str(code_r) if code_r is not None else "N/A"
                    err_r = result.get("error") or ""
                    path_r = result.get("path", "")
                    lines.append(f"| {path_r} | {code_str} | {err_r} |")
        lines.append("")

    ssl_data = data.get("ssl")
    if isinstance(ssl_data, dict):
        lines.append("## SSL/TLS Certificate Inspection")
        host_s = ssl_data.get("host")
        port_s = ssl_data.get("port")
        if host_s is not None:
            lines.append(f"- **Host:** {host_s}")
        if port_s is not None:
            lines.append(f"- **Port:** {port_s}")
        lines.append("")

        ssl_data_err = ssl_data.get("error")
        if isinstance(ssl_data_err, str):
            lines.append(f"- **Error:** {ssl_data_err}")
            lines.append("")

        cert = ssl_data.get("cert")
        if isinstance(cert, dict) and cert:
            lines.append("### Certificate")
            valid_sd = ssl_data.get("valid")
            if "valid" in ssl_data:
                lines.append(f"- **Valid:** {'Yes' if valid_sd else 'No'}")
            subj_c = cert.get("subject")
            if subj_c is not None:
                lines.append(f"- **Subject:** {subj_c}")
            iss_c = cert.get("issuer")
            if iss_c is not None:
                lines.append(f"- **Issuer:** {iss_c}")
            nb = cert.get("not_before")
            if nb is not None:
                lines.append(f"- **Not Before:** {nb}")
            na_c = cert.get("not_after")
            if na_c is not None:
                lines.append(f"- **Not After:** {na_c}")
            sa = cert.get("signature_algorithm")
            if sa is not None:
                lines.append(f"- **Signature Algorithm:** {sa}")
            ks = cert.get("key_size")
            if ks is not None:
                lines.append(f"- **Key Size:** {ks} bits")
            sans = cert.get("sans")
            if isinstance(sans, (list, tuple)):
                lines.append("- **Subject Alternative Names:**")
                for san in sans:
                    if isinstance(san, str):
                        lines.append(f"  - {san}")
            chain_len = ssl_data.get("chain_length", 0)
            lines.append(f"- **Chain Length:** {chain_len}")
            lines.append("")

    return "\n".join(lines)


def format_urlcheck_report_csv(data: dict[str, object]) -> str:
    """Format urlcheck results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "key", "value"])

    summary = data.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    writer.writerow(["summary", "target", data.get("target", "")])
    writer.writerow(["summary", "normalized_target", data.get("normalized_target", "")])
    writer.writerow(["summary", "total_findings", summary.get("total_findings", 0)])
    web_checks_run = summary.get("web_checks_run") or []
    if isinstance(web_checks_run, (list, tuple)):
        writer.writerow(["summary", "web_checks_run", ",".join(str(x) for x in web_checks_run)])
    else:
        writer.writerow(["summary", "web_checks_run", web_checks_run])
    writer.writerow(["summary", "fuzz_enabled", "true" if summary.get("fuzz_enabled") else "false"])
    writer.writerow(["summary", "ssl_checked", "true" if summary.get("ssl_checked") else "false"])

    web = data.get("web")
    if not isinstance(web, dict):
        web = {}
    security_headers = web.get("security_headers")
    if not isinstance(security_headers, dict):
        security_headers = {}
    if web.get("error"):
        writer.writerow(["web", "error", web["error"]])
    for header in security_headers.get("present") or []:
        if isinstance(header, str):
            writer.writerow(["web", "header_present", header])
    for header in security_headers.get("missing") or []:
        if isinstance(header, str):
            writer.writerow(["web", "header_missing", header])
    for finding in web.get("information_disclosure") or []:
        if isinstance(finding, dict):
            writer.writerow(["web", "information_disclosure", finding.get("header", "")])

    fuzz = data.get("fuzz")
    if isinstance(fuzz, dict):
        for finding in fuzz.get("findings") or []:
            if isinstance(finding, dict):
                writer.writerow(
                    ["fuzz", "finding", f"{finding.get('path', '')} ({finding.get('status_code')})"]
                )

    ssl_data = data.get("ssl")
    if isinstance(ssl_data, dict):
        writer.writerow(["ssl", "valid", "true" if ssl_data.get("valid") else "false"])
        cert = ssl_data.get("cert")
        if not isinstance(cert, dict):
            cert = {}
        for key in ("subject", "issuer", "signature_algorithm"):
            if cert.get(key):
                writer.writerow(["ssl", key, cert.get(key)])
        if cert.get("key_size"):
            writer.writerow(["ssl", "key_size", cert.get("key_size")])

    return output.getvalue().rstrip("\r\n")