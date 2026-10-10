"""Ping module for ethscan.

ICMP echo request probes with per-probe RTT and TTL reporting, plus a
TCP-ping fallback (connect-based latency measurement on a configurable port)
when raw ICMP sockets are unavailable (non-root).
"""

import json
import socket
import struct
import time
from typing import Dict, List, Optional

DEFAULT_COUNT = 4
DEFAULT_TIMEOUT = 2.0
DEFAULT_TTL = 64
DEFAULT_PORT = 80

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0

CONN_REFUSED_CODES = (111, 10061, 10013)

RESP_ECHO_REPLY = "ECHO_REPLY"
RESP_CONNECTED = "CONNECTED"
RESP_RST = "RST"
RESP_NO_RESPONSE = "NO-RESPONSE"
RESP_TIMEOUT = "TIMEOUT"


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    return (parsed.hostname or parsed.netloc or "").lower()


def _checksum(data: bytes) -> int:
    """Compute the Internet checksum (one's complement) for raw packets."""
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return (~total) & 0xFFFF


def _build_icmp_echo_request(identifier: int, sequence: int, payload: bytes = b"") -> bytes:
    """Build an ICMP Echo Request packet."""
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, identifier, sequence)
    checksum = _checksum(header + payload)
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, checksum, identifier, sequence)
    return header + payload


def _parse_icmp_reply(data: bytes, expected_id: int) -> Optional[Dict[str, object]]:
    """Parse an ICMP Echo Reply packet.

    Returns a dict with keys: type, code, identifier, sequence, payload, error.
    Returns None if the packet is not a valid Echo Reply for our identifier.
    """
    if len(data) < 20:
        return {"error": "packet too short for IP header"}

    ip_version = (data[0] >> 4) & 0x0F
    if ip_version != 4:
        return {"error": "not IPv4"}

    ihl = data[0] & 0x0F
    ip_header_len = ihl * 4
    if ip_header_len < 20 or len(data) < ip_header_len:
        return {"error": "IP header truncated"}

    protocol = data[9]
    src_ip = socket.inet_ntoa(data[12:16])

    if len(data) < ip_header_len + 8:
        return {"error": "ICMP header truncated"}

    icmp_offset = ip_header_len
    icmp_type = data[icmp_offset]
    icmp_code = data[icmp_offset + 1]
    icmp_checksum = struct.unpack("!H", data[icmp_offset + 2:icmp_offset + 4])[0]
    icmp_identifier = struct.unpack("!H", data[icmp_offset + 4:icmp_offset + 6])[0]
    icmp_sequence = struct.unpack("!H", data[icmp_offset + 6:icmp_offset + 8])[0]

    if icmp_type != ICMP_ECHO_REPLY or icmp_code != 0:
        return {"error": f"not echo reply: type={icmp_type}, code={icmp_code}"}

    if icmp_identifier != expected_id:
        return {"error": f"identifier mismatch: expected {expected_id}, got {icmp_identifier}"}

    payload = data[icmp_offset + 8:]

    return {
        "type": icmp_type,
        "code": icmp_code,
        "identifier": icmp_identifier,
        "sequence": icmp_sequence,
        "payload": payload,
        "src_ip": src_ip,
        "protocol": protocol,
        "error": None,
    }


def _try_create_raw_socket() -> Optional[socket.socket]:
    """Attempt to create a raw ICMP socket for sending/receiving echo requests.

    Returns the socket if available, or ``None`` if raw sockets are not
    permitted (e.g. running without root privileges).
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        return sock
    except (OSError, PermissionError):
        return None


def _resolve_host(host: str) -> Optional[str]:
    """Resolve a hostname to an IPv4 address, returning ``None`` on failure."""
    try:
        return socket.gethostbyname(host)
    except (socket.gaierror, socket.herror):
        return None


def probe_icmp(
    host: str,
    timeout: float = DEFAULT_TIMEOUT,
    ttl: int = DEFAULT_TTL,
    raw_socket: Optional[socket.socket] = None,
    identifier: int = 0,
    sequence: int = 0,
    payload: bytes = b"",
    resolved_ip: Optional[str] = None,
    port: int = DEFAULT_PORT,
) -> Dict[str, object]:
    """Send an ICMP Echo Request and wait for a reply.

    When a raw ICMP socket is provided (privileged/root), the function
    sends an ICMP Echo Request and listens for an Echo Reply.

    Without a raw socket the function falls back to a TCP connect-based
    ping on the specified port.

    Args:
        host: Target hostname or IP address.
        timeout: Socket timeout in seconds.
        ttl: Time-to-live value for the probe.
        raw_socket: Optional pre-created raw ICMP socket.
        identifier: ICMP identifier (PID-like).
        sequence: ICMP sequence number.
        payload: Optional payload bytes.
        resolved_ip: Pre-resolved IP of *host* (used in fallback mode).
        port: Target TCP port for connect-based fallback (default 80).

    Returns:
        Dict with ip, rtt_ms, ttl, sequence, response_type, and error.
    """
    start = time.monotonic()

    if raw_socket is not None:
        try:
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        except (OSError, PermissionError):
            # Fall back to TCP mode if raw socket creation fails
            raw_socket = None
        else:
            send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
            send_sock.settimeout(timeout)

            request = _build_icmp_echo_request(identifier, sequence, payload)
            try:
                send_sock.sendto(request, (host, 0))
            except OSError as exc:
                send_sock.close()
                rtt = (time.monotonic() - start) * 1000
                return {
                    "ip": resolved_ip or host,
                    "rtt_ms": round(rtt, 2),
                    "ttl": ttl,
                    "sequence": sequence,
                    "response_type": RESP_NO_RESPONSE,
                    "error": str(exc),
                }

            try:
                raw_socket.settimeout(timeout)
                data, _addr = raw_socket.recvfrom(512)
                rtt = (time.monotonic() - start) * 1000
                reply = _parse_icmp_reply(data, identifier)
                send_sock.close()

                if reply is None or reply.get("error"):
                    return {
                        "ip": resolved_ip or host,
                        "rtt_ms": round(rtt, 2),
                        "ttl": ttl,
                        "sequence": sequence,
                        "response_type": RESP_NO_RESPONSE,
                        "error": reply.get("error") if reply else "parse failed",
                    }

                return {
                    "ip": reply.get("src_ip", resolved_ip or host),
                    "rtt_ms": round(rtt, 2),
                    "ttl": ttl,
                    "sequence": sequence,
                    "response_type": RESP_ECHO_REPLY,
                    "error": None,
                }
            except socket.timeout:
                rtt = (time.monotonic() - start) * 1000
                send_sock.close()
                return {
                    "ip": None,
                    "rtt_ms": round(rtt, 2),
                    "ttl": ttl,
                    "sequence": sequence,
                    "response_type": RESP_TIMEOUT,
                    "error": "timeout",
                }
            except OSError as exc:
                rtt = (time.monotonic() - start) * 1000
                send_sock.close()
                return {
                    "ip": None,
                    "rtt_ms": round(rtt, 2),
                    "ttl": ttl,
                    "sequence": sequence,
                    "response_type": RESP_NO_RESPONSE,
                    "error": str(exc),
                }

    # Fallback mode: TCP connect-based ping
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
    send_sock.settimeout(timeout)
    try:
        err = send_sock.connect_ex((host, port))
    finally:
        send_sock.close()

    rtt = (time.monotonic() - start) * 1000

    if err == 0:
        return {
            "ip": resolved_ip or host,
            "rtt_ms": round(rtt, 2),
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_CONNECTED,
            "error": None,
        }
    if err in CONN_REFUSED_CODES:
        return {
            "ip": resolved_ip or host,
            "rtt_ms": round(rtt, 2),
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_RST,
            "error": None,
        }
    return {
        "ip": None,
        "rtt_ms": round(rtt, 2),
        "ttl": ttl,
        "sequence": sequence,
        "response_type": RESP_NO_RESPONSE,
        "error": f"connect error {err}",
    }


def run_ping(
    target: str,
    count: int = DEFAULT_COUNT,
    timeout: float = DEFAULT_TIMEOUT,
    ttl: int = DEFAULT_TTL,
    port: int = DEFAULT_PORT,
    raw_socket: Optional[socket.socket] = None,
) -> Dict[str, object]:
    """Run ICMP ping (or TCP fallback) against *target*.

    Args:
        target: Hostname or URL (e.g. ``example.com`` or ``https://example.com``).
        count: Number of echo requests to send (default 4).
        timeout: Per-probe timeout in seconds (default 2.0).
        ttl: Time-to-live value for probes (default 64).
        port: Target TCP port for TCP fallback (default 80).
        raw_socket: Optional pre-created raw ICMP socket.

    Returns:
        Structured results dict with per-probe data, summary fields, and notes.
    """
    host = _normalize_host(target)
    ip = _resolve_host(host)

    count = max(count, 1)
    timeout = max(timeout, 0.1)
    ttl = max(min(ttl, 255), 1)

    own_raw_socket = False
    if raw_socket is None:
        raw_socket = _try_create_raw_socket()
        own_raw_socket = raw_socket is not None

    identifier = 0xFFFF & int(time.time() * 1000)

    probes: List[Dict[str, object]] = []
    notes: List[str] = []

    if ip is None:
        notes.append(f"Could not resolve host {host!r} to an IPv4 address")
    if raw_socket is None:
        notes.append(
            "Raw ICMP socket unavailable; running in TCP connect fallback "
            f"mode on port {port} (ICMP ping not available)"
        )

    for seq in range(1, count + 1):
        result = probe_icmp(
            host,
            timeout=timeout,
            ttl=ttl,
            raw_socket=raw_socket,
            identifier=identifier,
            sequence=seq,
            resolved_ip=ip,
            port=port,
        )
        probes.append(result)

    if own_raw_socket and raw_socket is not None:
        raw_socket.close()

    successful = [p for p in probes if p.get("response_type") in (RESP_ECHO_REPLY, RESP_CONNECTED, RESP_RST)]
    failed = [p for p in probes if p.get("response_type") in (RESP_NO_RESPONSE, RESP_TIMEOUT)]

    rtts = [p["rtt_ms"] for p in successful if p.get("rtt_ms") is not None]
    rtt_min = min(rtts) if rtts else None
    rtt_max = max(rtts) if rtts else None
    rtt_avg = round(sum(rtts) / len(rtts), 2) if rtts else None

    if successful:
        notes.append(f"{len(successful)}/{count} probes successful")
    else:
        notes.append(f"0/{count} probes successful")

    return {
        "target": target,
        "host": host,
        "ip": ip,
        "count": count,
        "timeout": timeout,
        "ttl": ttl,
        "port": port,
        "raw_socket_available": raw_socket is not None,
        "probes": probes,
        "successful": len(successful),
        "failed": len(failed),
        "rtt_min_ms": rtt_min,
        "rtt_max_ms": rtt_max,
        "rtt_avg_ms": rtt_avg,
        "notes": notes,
    }


def format_ping_report_json(data: Dict[str, object]) -> str:
    """Format ping results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_ping_report_markdown(data: Dict[str, object]) -> str:
    """Format ping results as Markdown."""
    lines = ["# ethscan Ping Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    if data.get("ip"):
        lines.append(f"- **Resolved IP:** {data['ip']}")
    lines.append(f"- **Count:** {data['count']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **TTL:** {data['ttl']}")
    lines.append(f"- **TCP Fallback Port:** {data['port']}")
    raw_avail = data.get("raw_socket_available")
    lines.append(
        f"- **Raw ICMP Socket:** "
        f"{'available' if raw_avail else 'unavailable (TCP fallback mode)'}"
    )
    lines.append(f"- **Successful:** {data['successful']}/{data['count']}")
    lines.append(f"- **Failed:** {data['failed']}/{data['count']}")
    if data.get("rtt_min_ms") is not None:
        lines.append(f"- **RTT Min:** {data['rtt_min_ms']} ms")
        lines.append(f"- **RTT Max:** {data['rtt_max_ms']} ms")
        lines.append(f"- **RTT Avg:** {data['rtt_avg_ms']} ms")
    lines.append("")

    probes = data.get("probes") or []
    if probes:
        lines.append("## Probe Results")
        lines.append("| Seq | IP | RTT (ms) | Response |")
        lines.append("|-----|-----|----------|----------|")
        for probe in probes:
            seq = probe.get("sequence", "")
            ip = str(probe.get("ip") or "*").replace("|", "\\|")
            rtt = probe.get("rtt_ms")
            rtt_str = str(rtt) if rtt is not None else "N/A"
            response = str(probe.get("response_type") or "").replace("|", "\\|")
            lines.append(f"| {seq} | {ip} | {rtt_str} | {response} |")
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)