"""Port scanner module for ethscan."""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple


def scan_port(host: str, port: int, timeout: float = 1.0) -> Tuple[int, bool]:
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
    except (socket.timeout, ConnectionRefusedError, OSError):
        return port, False


def scan_ports(
    host: str,
    ports: List[int],
    timeout: float = 1.0,
    max_workers: int = 100,
) -> List[Tuple[int, bool]]:
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


def parse_port_range(port_spec: str) -> List[int]:
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
    """
    ports = set()
    for part in port_spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ports.update(range(int(start), int(end) + 1))
        else:
            ports.add(int(part))
    return sorted(ports)


COMMON_PORTS = [
    20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
    993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888,
]


def get_common_ports() -> List[int]:
    """Return list of common ports to scan."""
    return COMMON_PORTS.copy()