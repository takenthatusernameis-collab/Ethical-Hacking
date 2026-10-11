"""Combined report generation: port scan plus password audit."""

import csv
import io
import json
from typing import Any, Dict, List, Optional

from ethscan.passwords import audit_passwords
from ethscan.scanner import (
    get_common_ports,
    get_profile_defaults,
    get_profile_ports,
    parse_port_range,
    scan_ports,
)

CSV_COLUMNS = [
    "section",
    "port",
    "open",
    "password",
    "length",
    "entropy",
    "common",
    "patterns",
    "too_short",
    "score",
    "verdict",
]


def _parse_ports(ports: str) -> List[int]:
    if ports.lower() == "common":
        return get_common_ports()
    if ports.lower() == "all":
        return list(range(1, 65536))
    return parse_port_range(ports)


def _resolve_ports_and_defaults(
    ports: str,
    timeout: float,
    workers: int,
    profile: Optional[str],
) -> tuple:
    """Resolve the effective port list, timeout, and workers.

    Mirrors the profile logic in ``scan``/``service``: a profile overrides
    ``--ports``/``--timeout``/``--workers`` unless the corresponding CLI
    option was explicitly set. ``--ports`` can still override the profile's
    port selection; ``--timeout``/``--workers`` can still override the
    profile defaults.
    """
    if profile:
        defaults = get_profile_defaults(profile)
        if ports == "common":
            port_list = get_profile_ports(profile)
        else:
            port_list = parse_port_range(ports)
        if timeout == 1.0:
            timeout = defaults["timeout"]
        if workers == 100:
            workers = defaults["workers"]
    else:
        port_list = _parse_ports(ports)
    return port_list, timeout, workers


def _load_passwords(audit_file: Optional[str]) -> List[str]:
    if not audit_file:
        return []
    with open(audit_file, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def run_report(
    target: str,
    ports: str = "common",
    timeout: float = 1.0,
    workers: int = 100,
    audit_file: Optional[str] = None,
    min_length: Optional[int] = None,
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a port scan and an optional password audit, returning combined report data.

    Args:
        target: Target host (URL or bare IP/hostname).
        ports: Port specification ('common', 'all', or comma-separated list/ranges).
        timeout: Connection timeout in seconds.
        workers: Maximum concurrent workers.
        audit_file: Optional path to a file with one password per line.
        min_length: Optional minimum length threshold passed to the password audit.
        profile: Optional scan profile ('fast', 'normal', 'full') that overrides
            ports/timeout/workers unless explicitly set.

    Returns:
        Combined report dict with ``scan`` and ``audit`` sections.
    """
    port_list, timeout, workers = _resolve_ports_and_defaults(
        ports, timeout, workers, profile
    )

    scan_results = scan_ports(target, port_list, timeout=timeout, max_workers=workers)
    open_ports = [port for port, is_open in scan_results if is_open]

    passwords = _load_passwords(audit_file)
    audit_results = (
        audit_passwords(passwords, min_length=min_length) if passwords else []
    )

    return {
        "scan": {
            "target": target,
            "profile": profile,
            "ports_scanned": len(port_list),
            "open_ports": open_ports,
            "details": [{"port": port, "open": is_open} for port, is_open in scan_results],
        },
        "audit": {
            "passwords_audited": len(passwords),
            "min_length": min_length,
            "results": [
                {
                    "password": pwd,
                    "length": eval_data["length"],
                    "entropy": eval_data["entropy"],
                    "common": eval_data["common"],
                    "patterns": eval_data["patterns"],
                    "too_short": eval_data.get("too_short", False),
                    "score": eval_data["score"],
                    "verdict": eval_data["verdict"],
                }
                for pwd, eval_data in audit_results
            ],
        },
    }


def format_report_json(data: Dict[str, Any]) -> str:
    """Render the combined report as JSON."""
    return json.dumps(data, indent=2)


def format_report_markdown(data: Dict[str, Any]) -> str:
    """Render the combined report as Markdown."""
    lines = ["# ethscan Report", ""]

    scan = data["scan"]
    lines.append("## Port Scan")
    lines.append(f"- **Target:** {scan['target']}")
    lines.append(f"- **Ports Scanned:** {scan['ports_scanned']}")
    lines.append(
        f"- **Open Ports:** {', '.join(map(str, scan['open_ports'])) if scan['open_ports'] else 'None'}"
    )
    lines.append("")
    lines.append("| Port | Status |")
    lines.append("|------|--------|")
    for detail in scan["details"]:
        status = "Open" if detail["open"] else "Closed"
        lines.append(f"| {detail['port']} | {status} |")
    lines.append("")

    audit = data["audit"]
    lines.append("## Password Audit")
    lines.append(f"- **Passwords Audited:** {audit['passwords_audited']}")
    if audit.get("min_length") is not None:
        lines.append(f"- **Min Length:** {audit['min_length']}")
    lines.append("")
    if audit["results"]:
        lines.append("| Password | Length | Entropy | Common | Patterns | Too Short | Score | Verdict |")
        lines.append("|----------|--------|---------|--------|----------|-----------|-------|---------|")
        for result in audit["results"]:
            too_short = "Yes" if result.get("too_short", False) else "No"
            lines.append(
                f"| {result['password']!r} | {result['length']} | {result['entropy']} | "
                f"{'Yes' if result['common'] else 'No'} | {'Yes' if result['patterns'] else 'No'} | "
                f"{too_short} | "
                f"{result['score']} | {result['verdict']} |"
            )
    else:
        lines.append("*No passwords provided for audit.*")
    lines.append("")

    return "\n".join(lines)


def format_report_csv(data: Dict[str, Any]) -> str:
    """Render the combined report as CSV.

    Both sections share one table with a ``section`` discriminator column
    (``scan`` rows carry port/open, ``audit`` rows carry the password fields),
    so the output stays a single valid CSV document that any CSV reader can
    filter by section.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)

    for detail in data["scan"]["details"]:
        writer.writerow(
            [
                "scan",
                detail["port"],
                "true" if detail["open"] else "false",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    for result in data["audit"]["results"]:
        writer.writerow(
            [
                "audit",
                "",
                "",
                result["password"],
                result["length"],
                result["entropy"],
                "true" if result["common"] else "false",
                "true" if result["patterns"] else "false",
                "true" if result.get("too_short", False) else "false",
                result["score"],
                result["verdict"],
            ]
        )

    return output.getvalue()
