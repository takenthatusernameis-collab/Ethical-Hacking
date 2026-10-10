"""OS fingerprinting module for ethscan."""

import json
import socket
import struct
from typing import Dict, List, Optional, Tuple

DEFAULT_TIMEOUT = 3.0
DEFAULT_WORKERS = 10
TTL_MAX_LENGTH = 255
TCP_WINDOW_SIZES = {
    65535: ["Windows"],
    8192: ["Linux", "FreeBSD"],
    16384: ["Linux", "FreeBSD", "macOS"],
    32768: ["Linux", "FreeBSD", "macOS"],
    5840: ["macOS"],
    20480: ["Linux"],
    43690: ["Linux"],
}

DEFAULT_PORTS = [22, 80, 443]


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    return (parsed.hostname or parsed.netloc or "").lower()


def _parse_ip_packet(data: bytes) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """Parse an IPv4 packet and extract TTL, window size, and flags."""
    if len(data) < 20:
        return None, None, None, None
    version_ihl = data[0]
    version = version_ihl >> 4
    if version != 4:
        return None, None, None, None
    ihl = version_ihl & 0x0F
    header_len = ihl * 4
    if len(data) < header_len:
        return None, None, None, None
    ttl = data[8]
    protocol = data[9]
    total_length = struct.unpack("!H", data[2:4])[0]
    flags_offset = struct.unpack("!H", data[6:8])[0]
    flags = (flags_offset >> 13) & 0x07
    if protocol == 6 and len(data) >= header_len + 20:
        tcp = data[header_len:header_len + 20]
        window = struct.unpack("!H", tcp[14:16])[0]
    else:
        window = None
    return ttl, window, flags, total_length
