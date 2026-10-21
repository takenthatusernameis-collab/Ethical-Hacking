"""Port scanner module for ethscan."""
from __future__ import annotations

import csv
import io
import json
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed


def scan_port(host: str, port: int, timeout: float = 1.0) -> tuple[int, bool]:
    """Scan a single port on the target host.

    Args:
        host: Target hostname or IP address.
        port: Port number to scan.
        timeout: Connection timeout in seconds.

    Returns:
        Tuple of (port, is_open).
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return port, True
    # A host that is not a valid host name ("....") raises a UnicodeError,
    # which is a ValueError, when the resolver encodes it. A transport
    # failure of an unnamed type must not escape the scanner.
    except (socket.timeout, ConnectionRefusedError, OSError, ValueError, RuntimeError):
        return port, False


def scan_ports(
    host: str,
    ports: list[int],
    timeout: float = 1.0,
    max_workers: int = 100,
) -> list[tuple[int, bool]]:
    """Scan multiple ports on the target host concurrently.

    Args:
        host: Target hostname or IP address.
        ports: List of port numbers to scan.
        timeout: Connection timeout in seconds.
        max_workers: Maximum number of concurrent threads.

    Returns:
        List of (port, is_open) tuples.
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_port = {
            executor.submit(scan_port, host, port, timeout): port for port in ports
        }
        for future in as_completed(future_to_port):
            results.append(future.result())
    return sorted(results, key=lambda x: x[0])


MAX_PORT = 65535


class PortSpecError(ValueError):
    """Raised when a port specification cannot be parsed.

    Subclasses :class:`ValueError` so that existing ``except ValueError``
    handlers keep working, while letting the CLI layer distinguish an
    invalid port specification from unrelated value errors and turn it into
    a usage error.
    """


def parse_port_range(port_spec: str) -> list[int]:
    """Parse a port specification string into a list of ports.

    Supports formats like:
    - "80" -> [80]
    - "80,443,8080" -> [80, 443, 8080]
    - "1-100" -> [1, 2, ..., 100]
    - "80,100-200,443" -> [80, 100, 101, ..., 200, 443]

    Args:
        port_spec: Port specification string.

    Returns:
        Sorted list of unique port numbers.

    Raises:
        PortSpecError: If a port is out of range (0-{max}), a range is inverted
            (start > end), or a token is non-numeric.
    """
    ports = set()
    for part in port_spec.split(","):
        part = part.strip()
        if not part:
            raise PortSpecError(f"Empty port token in specification: {port_spec!r}")
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start_str = start_str.strip()
            end_str = end_str.strip()
            if not start_str or not end_str:
                raise PortSpecError(
                    f"Invalid range {part!r}: missing start or end"
                )
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                raise PortSpecError(
                    f"Invalid port number in range {part!r}"
                )
            if start > end:
                raise PortSpecError(
                    f"Invalid range {part!r}: start ({start}) > end ({end})"
                )
            if not (0 <= start <= MAX_PORT and 0 <= end <= MAX_PORT):
                raise PortSpecError(
                    f"Port out of range (0-{MAX_PORT}) in range {part!r}"
                )
            ports.update(range(start, end + 1))
        else:
            try:
                port = int(part)
            except ValueError:
                raise PortSpecError(f"Invalid port number {part!r}")
            if not (0 <= port <= MAX_PORT):
                raise PortSpecError(f"Port {port} out of range (0-{MAX_PORT})")
            ports.add(port)
    return sorted(ports)


def resolve_port_list(ports: str, profile: str | None = None) -> list[int]:
    """Resolve a port specification into a list of ports.

    Supports the ``common`` and ``all`` keywords (case-insensitive) as well as
    comma-separated lists and ranges via :func:`parse_port_range`. When a
    profile is supplied, ``common`` resolves to that profile's port set and
    ``all`` resolves to every port 1-65535; without a profile, ``common``
    resolves to the common ports and ``all`` to every port.

    Args:
        ports: Port specification ('common', 'all', or comma-separated list/ranges).
        profile: Optional scan profile ('fast', 'normal', 'full').

    Returns:
        Sorted list of unique port numbers.

    Raises:
        PortSpecError: If the specification is invalid.
    """
    ports_spec = ports.lower()
    if profile:
        if ports_spec == "common":
            return get_profile_ports(profile)
        if ports_spec == "all":
            return get_all_ports()
    if ports_spec == "common":
        return get_common_ports()
    if ports_spec == "all":
        return get_all_ports()
    return parse_port_range(ports)


COMMON_PORTS = [
    20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
    993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888,
]


FAST_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995,
    3306, 3389, 5432, 8080, 8443,
]


FULL_PORTS = sorted(set(list(range(1, 1025)) + COMMON_PORTS))


PROFILE_DEFAULTS = {
    "fast": {"ports": FAST_PORTS, "timeout": 0.5, "workers": 200},
    "normal": {"ports": COMMON_PORTS, "timeout": 1.0, "workers": 100},
    "full": {"ports": FULL_PORTS, "timeout": 2.0, "workers": 50},
}


def get_common_ports() -> list[int]:
    """Return list of common ports to scan."""
    return COMMON_PORTS.copy()


def get_all_ports() -> list[int]:
    """Return the full list of TCP ports (1-65535) to scan."""
    return list(range(1, 65536))


def get_profile_ports(profile: str) -> list[int]:
    """Return list of ports for the given profile.

    Args:
        profile: Profile name ('fast', 'normal', 'full').

    Returns:
        Sorted list of unique port numbers for the profile.

    Raises:
        ValueError: If profile is not recognized.
    """
    profile = profile.lower()
    if profile not in PROFILE_DEFAULTS:
        raise ValueError(f"Unknown profile: {profile}. Valid profiles: {', '.join(sorted(PROFILE_DEFAULTS.keys()))}")
    return PROFILE_DEFAULTS[profile]["ports"].copy()


def get_profile_defaults(profile: str) -> dict:
    """Return default timeout and workers for the given profile.

    Args:
        profile: Profile name ('fast', 'normal', 'full').

    Returns:
        Dictionary with 'timeout' and 'workers' keys.

    Raises:
        ValueError: If profile is not recognized.
    """
    profile = profile.lower()
    if profile not in PROFILE_DEFAULTS:
        raise ValueError(f"Unknown profile: {profile}. Valid profiles: {', '.join(sorted(PROFILE_DEFAULTS.keys()))}")
    return {
        "timeout": PROFILE_DEFAULTS[profile]["timeout"],
        "workers": PROFILE_DEFAULTS[profile]["workers"],
    }


def format_scan_report_json(data: dict[str, object]) -> str:
    """Format scan results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_scan_report_markdown(data: dict[str, object]) -> str:
    """Format scan results as Markdown."""
    lines = ["# ethscan Port Scan Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Ports Scanned:** {data['ports_scanned']}")
    lines.append(f"- **Open Ports:** {', '.join(map(str, data['open_ports'])) if data['open_ports'] else 'None'}")
    lines.append("")

    if data["details"]:
        lines.append("## Port Details")
        lines.append("| Port | Status |")
        lines.append("|------|--------|")
        for detail in data["details"]:
            status = "Open" if detail["open"] else "Closed"
            lines.append(f"| {detail['port']} | {status} |")
    else:
        lines.append("*No ports scanned.*")

    return "\n".join(lines)


def format_scan_report_csv(data: dict[str, object]) -> str:
    """Format scan results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["port", "open"])
    for detail in data.get("details", []):
        writer.writerow([detail["port"], "true" if detail["open"] else "false"])
    return output.getvalue().rstrip("\r\n")