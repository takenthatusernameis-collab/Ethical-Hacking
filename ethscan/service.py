"""Service/banner detection module for ethscan."""
from __future__ import annotations

import csv
import io
import json
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

from ethscan.target import parse_url

DEFAULT_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
    993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888,
]

DEFAULT_TIMEOUT = 3.0
DEFAULT_WORKERS = 50
BANNER_MAX_LENGTH = 1024


SERVICE_SIGNATURES = {
    "ftp": [
        (re.compile(r"^220.*FTP", re.IGNORECASE), "FTP"),
        (re.compile(r"^220.*FileZilla", re.IGNORECASE), "FileZilla FTP"),
        (re.compile(r"^220.*ProFTPD", re.IGNORECASE), "ProFTPD"),
        (re.compile(r"^220.*vsftpd", re.IGNORECASE), "vsftpd"),
        (re.compile(r"^220.*Pure-FTPd", re.IGNORECASE), "Pure-FTPd"),
    ],
    "ssh": [
        (re.compile(r"^SSH-2\.0-OpenSSH", re.IGNORECASE), "OpenSSH"),
        (re.compile(r"^SSH-2\.0-.*Dropbear", re.IGNORECASE), "Dropbear SSH"),
        (re.compile(r"^SSH-2\.0-.*libssh", re.IGNORECASE), "libssh"),
    ],
    "telnet": [
        (re.compile(r"^.*login:", re.IGNORECASE), "Telnet"),
        (re.compile(r"^.*Password:", re.IGNORECASE), "Telnet"),
    ],
    "smtp": [
        (re.compile(r"^220.*ESMTP", re.IGNORECASE), "SMTP"),
        (re.compile(r"^220.*Postfix", re.IGNORECASE), "Postfix SMTP"),
        (re.compile(r"^220.*Exim", re.IGNORECASE), "Exim SMTP"),
        (re.compile(r"^220.*Sendmail", re.IGNORECASE), "Sendmail"),
    ],
    "pop3": [
        (re.compile(r"^\+OK.*POP3", re.IGNORECASE), "POP3"),
        (re.compile(r"^\+OK.*Dovecot", re.IGNORECASE), "Dovecot POP3"),
    ],
    "imap": [
        (re.compile(r"^\* OK.*IMAP", re.IGNORECASE), "IMAP"),
        (re.compile(r"^\* OK.*Dovecot", re.IGNORECASE), "Dovecot IMAP"),
    ],
    "http": [
        (re.compile(r"^HTTP/1\.[01] 200", re.IGNORECASE), "HTTP"),
        (re.compile(r"Server:\s*([^\r\n]+)", re.IGNORECASE), None),
    ],
    "https": [
        (re.compile(r"^HTTP/1\.[01] 200", re.IGNORECASE), "HTTPS"),
        (re.compile(r"Server:\s*([^\r\n]+)", re.IGNORECASE), None),
    ],
    "mysql": [
        (re.compile(r"^[0-9a-f]{8}.*mysql", re.IGNORECASE), "MySQL"),
        (re.compile(r"^[0-9a-f]{8}.*MariaDB", re.IGNORECASE), "MariaDB"),
    ],
    "rdp": [
        (re.compile(r"^\x03\x00\x00\x13\x0e\xd0", re.DOTALL), "RDP"),
    ],
    "vnc": [
        (re.compile(r"^RFB 003\.", re.IGNORECASE), "VNC"),
    ],
    "redis": [
        (re.compile(r"^\+PONG", re.IGNORECASE), "Redis"),
        (re.compile(r"^-ERR", re.IGNORECASE), "Redis"),
    ],
    "mongodb": [
        (re.compile(r"^It looks like you are trying to access MongoDB", re.IGNORECASE), "MongoDB"),
    ],
    "postgresql": [
        (re.compile(r"^E.*FATAL", re.IGNORECASE), "PostgreSQL"),
        (re.compile(r"^S.*FATAL", re.IGNORECASE), "PostgreSQL"),
    ],
}


COMMON_SERVICE_PORTS = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    80: "http",
    110: "pop3",
    143: "imap",
    443: "https",
    445: "smb",
    993: "imaps",
    995: "pop3s",
    3306: "mysql",
    3389: "rdp",
    5432: "postgresql",
    5900: "vnc",
    6379: "redis",
    8080: "http",
    8443: "https",
    27017: "mongodb",
}


def grab_banner(host: str, port: int, timeout: float) -> tuple[int, str | None, str | None]:
    """Connect to a port and attempt to grab the banner.

    Args:
        host: Target hostname or IP address.
        port: Port number to connect to.
        timeout: Connection timeout in seconds.

    Returns:
        Tuple of (port, banner, service_name).
    """
    service_name = COMMON_SERVICE_PORTS.get(port)
    banner = None

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            try:
                data = sock.recv(BANNER_MAX_LENGTH)
                if data:
                    banner = data.decode("utf-8", errors="ignore").strip()
            except (socket.timeout, OSError):
                pass

            if not banner and service_name in {"http", "https"}:
                try:
                    request = f"HEAD / HTTP/1.0\r\nHost: {host}\r\n\r\n"
                    sock.sendall(request.encode())
                    data = sock.recv(BANNER_MAX_LENGTH)
                    if data:
                        banner = data.decode("utf-8", errors="ignore").strip()
                except (socket.timeout, OSError):
                    pass

    # A host that is not a valid host name ("....") raises a UnicodeError,
    # which is a ValueError, when the resolver encodes it.
    except (socket.timeout, ConnectionRefusedError, OSError, ValueError):
        pass

    detected_service = None
    if banner and service_name and service_name in SERVICE_SIGNATURES:
        for pattern, name in SERVICE_SIGNATURES[service_name]:
            match = pattern.search(banner)
            if match:
                detected_service = name or (match.group(1) if match.groups() else service_name.upper())
                break
        if not detected_service:
            detected_service = service_name.upper()

    return port, banner, detected_service


def run_service(
    target: str,
    ports: list[int] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_WORKERS,
) -> dict[str, object]:
    """Run service/banner detection against a target.

    Args:
        target: Target host or IP address.
        ports: List of ports to check. If None, uses DEFAULT_PORTS.
        timeout: Connection timeout in seconds.
        max_workers: Maximum number of concurrent workers.

    Returns:
        Structured results with target, host, and service detection results.
    """
    host = target.strip()
    if "://" in host:
        parsed = parse_url(host)
        host = parsed.hostname or host

    port_list = ports if ports is not None else DEFAULT_PORTS

    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_port = {
            executor.submit(grab_banner, host, port, timeout): port for port in port_list
        }
        for future in as_completed(future_to_port):
            port, banner, service = future.result()
            if banner or service:
                entry: dict[str, object] = {"port": port}
                if banner:
                    entry["banner"] = banner[:500]
                if service:
                    entry["service"] = service
                results.append(entry)

    results.sort(key=lambda x: x["port"])

    return {
        "target": target,
        "host": host,
        "timeout": timeout,
        "ports_scanned": len(port_list),
        "services_found": len(results),
        "results": results,
    }


def format_service_report_json(data: dict[str, object]) -> str:
    """Format service detection results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_service_report_markdown(data: dict[str, object]) -> str:
    """Format service detection results as Markdown."""
    lines = ["# ethscan Service Detection Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Ports Scanned:** {data['ports_scanned']}")
    lines.append(f"- **Services Found:** {data['services_found']}")
    lines.append("")

    if data["results"]:
        lines.append("## Detected Services")
        lines.append("| Port | Service | Banner |")
        lines.append("|------|---------|--------|")
        for result in data["results"]:
            port = result["port"]
            service = result.get("service", "Unknown")
            banner = result.get("banner", "")
            if banner:
                banner = banner.replace("|", "\\|")
                if len(banner) > 80:
                    banner = banner[:77] + "..."
            lines.append(f"| {port} | {service} | {banner} |")
    else:
        lines.append("*No services detected.*")

    return "\n".join(lines)


def format_service_report_csv(data: dict[str, object]) -> str:
    """Format service detection results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["port", "service", "banner"])
    for result in data.get("results", []):
        port = result.get("port", "")
        service = result.get("service", "")
        banner = result.get("banner", "").replace("\n", " ").replace("\r", "")
        writer.writerow([port, service, banner])
    return output.getvalue().rstrip("\r\n")