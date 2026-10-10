"""TCP traceroute module for ethscan.

Discovers the network path to a target using TTL-incremented TCP SYN probes.
When a raw ICMP socket is available (privileged/root), intermediate hops are
identified from ICMP Time Exceeded responses. Without root privileges, the
module falls back to a connect-based approach that can still detect whether
the destination host was reached.
"""

import json
import socket
import struct
import time
from typing import Dict, List, Optional

DEFAULT_MAX_HOPS = 30
DEFAULT_TIMEOUT = 3.0
DEFAULT_PORT = 80
DEFAULT_PROBES_PER_HOP = 3
MAX_MAX_HOPS = 128

# ICMP message types
ICMP_ECHO_REPLY = 0
ICMP_DEST_UNREACH = 3
ICMP_TIME_EXCEEDED = 11
ICMP_ECHO_REQUEST = 8

# Destination Unreachable code 3 == "port unreachable"
PORT_UNREACHABLE_CODE = 3

# errno values that indicate a TCP RST (connection refused)
CONN_REFUSED_CODES = (111, 10061, 10013)

# Response type labels
RESP_TIME_EXCEEDED = "TIME_EXCEEDED"
RESP_PORT_UNREACHABLE = "PORT_UNREACHABLE"
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


def _build_ip_header(
    src_ip: bytes, dst_ip: bytes, protocol: int, payload: bytes
) -> bytes:
    """Build a minimal 20-byte IPv4 header for synthetic ICMP packet construction."""
    version_ihl = (4 << 4) | 5
    total_length = 20 + len(payload)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        0,
        0,
        64,
        protocol,
        0,
        src_ip,
        dst_ip,
    )
    checksum = _checksum(header)
    return struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        0,
        0,
        64,
        protocol,
        checksum,
        src_ip,
        dst_ip,
    )


def build_icmp_packet(
    icmp_type: int,
    code: int,
    hop_ip: str,
    dst_ip: str,
    orig_src_port: int = 12345,
    orig_dst_port: int = 80,
) -> bytes:
    """Build a synthetic ICMP response packet for testing ``parse_icmp_response``.

    The returned bytes contain an outer IP header (hop_ip as source), an ICMP
    header with the given type/code, and an embedded original IP header +
    TCP header (used by Time Exceeded and Port Unreachable messages).

    Args:
        icmp_type: ICMP message type (e.g. 11 for Time Exceeded).
        code: ICMP code value.
        hop_ip: IP address of the router/hop that supposedly sent the ICMP.
        dst_ip: Original destination IP (our target).
        orig_src_port: Original source TCP port.
        orig_dst_port: Original destination TCP port.

    Returns:
        Raw bytes representing a full IP/ICMP packet.
    """
    hop_ip_bytes = socket.inet_aton(hop_ip)
    dst_ip_bytes = socket.inet_aton(dst_ip)

    # Embedded original TCP header (source + destination ports only)
    orig_tcp_ports = struct.pack("!HH", orig_src_port, orig_dst_port)

    # Embedded original IP header
    orig_src_ip = socket.inet_aton("10.0.0.1")
    embedded_ip_header = _build_ip_header(
        src_ip=orig_src_ip,
        dst_ip=dst_ip_bytes,
        protocol=socket.IPPROTO_TCP,
        payload=orig_tcp_ports,
    )
    icmp_payload = embedded_ip_header + orig_tcp_ports

    # ICMP header (checksum placeholder = 0 during computation)
    icmp_header = struct.pack("!BBHHH", icmp_type, code, 0, 0, 0)
    icmp_checksum = _checksum(icmp_header + icmp_payload)
    icmp_header = struct.pack(
        "!BBHHH", icmp_type, code, icmp_checksum, 0, 0
    )

    # Outer IP header: hop_ip as source, protocol = ICMP
    outer_ip = _build_ip_header(
        src_ip=hop_ip_bytes,
        dst_ip=dst_ip_bytes,
        protocol=socket.IPPROTO_ICMP,
        payload=icmp_header + icmp_payload,
    )

    return outer_ip + icmp_header + icmp_payload


def parse_icmp_response(data: bytes) -> Dict[str, object]:
    """Parse a raw ICMP response received from a ``SOCK_RAW`` socket.

    On Linux, raw ICMP sockets return the full IP packet (IP header + ICMP
    message).  This function parses the outer IP header to find the source
    IP (the hop that generated the ICMP), reads the ICMP type/code, and --
    for Time Exceeded (type 11) and Destination Unreachable (type 3) --
    extracts the embedded original IP header and TCP ports.

    Returns:
        Dict with keys: type, code, hop_ip, protocol, error, and (for
        type 11/3) destination_ip, original_src_port, original_dst_port.
    """
    if len(data) < 20:
        return {
            "type": -1,
            "code": -1,
            "hop_ip": None,
            "protocol": None,
            "error": "packet too short for IP header",
        }

    ip_version = (data[0] >> 4) & 0x0F
    if ip_version != 4:
        return {
            "type": -1,
            "code": -1,
            "hop_ip": None,
            "protocol": None,
            "error": "not IPv4",
        }

    ihl = data[0] & 0x0F
    ip_header_len = ihl * 4
    if ip_header_len < 20 or len(data) < ip_header_len:
        return {
            "type": -1,
            "code": -1,
            "hop_ip": None,
            "protocol": None,
            "error": "IP header truncated",
        }

    protocol = data[9]
    src_ip = socket.inet_ntoa(data[12:16])

    if len(data) < ip_header_len + 8:
        return {
            "type": -1,
            "code": -1,
            "hop_ip": src_ip,
            "protocol": protocol,
            "error": "ICMP header truncated",
        }

    icmp_offset = ip_header_len
    icmp_type = data[icmp_offset]
    icmp_code = data[icmp_offset + 1]

    result: Dict[str, object] = {
        "type": icmp_type,
        "code": icmp_code,
        "hop_ip": src_ip,
        "protocol": protocol,
        "error": None,
    }

    # For Time Exceeded and Destination Unreachable, extract embedded info
    if icmp_type in (ICMP_TIME_EXCEEDED, ICMP_DEST_UNREACH):
        embedded_offset = icmp_offset + 8
        if len(data) >= embedded_offset + 20:
            result["destination_ip"] = socket.inet_ntoa(
                data[embedded_offset + 16 : embedded_offset + 20]
            )
            if len(data) >= embedded_offset + 24:
                ports = struct.unpack(
                    "!HH", data[embedded_offset + 20 : embedded_offset + 24]
                )
                result["original_src_port"] = ports[0]
                result["original_dst_port"] = ports[1]

    return result


def _icmp_response_label(icmp: Dict[str, object]) -> str:
    """Map a parsed ICMP response to a human-readable label."""
    icmp_type = icmp.get("type", -1)
    code = icmp.get("code", -1)
    if icmp_type == ICMP_TIME_EXCEEDED:
        return RESP_TIME_EXCEEDED
    if icmp_type == ICMP_DEST_UNREACH and code == PORT_UNREACHABLE_CODE:
        return RESP_PORT_UNREACHABLE
    return RESP_NO_RESPONSE


def _try_create_raw_socket() -> Optional[socket.socket]:
    """Attempt to create a raw ICMP socket for receiving traceroute responses.

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


def probe_ttl(
    host: str,
    port: int,
    ttl: int,
    timeout: float = DEFAULT_TIMEOUT,
    raw_socket: Optional[socket.socket] = None,
    resolved_ip: Optional[str] = None,
) -> Dict[str, object]:
    """Send a TCP SYN probe at a specific TTL and report the response.

    When a raw ICMP socket is provided (privileged/root), the function
    sends a TCP SYN via a non-blocking socket and listens for ICMP Time
    Exceeded or Port Unreachable responses to identify the hop.

    Without a raw socket the function falls back to a blocking
    ``connect_ex``: a connected result means the destination was reached
    (port open), a refused result means port closed, and a timeout means
    no response.

    Args:
        host: Target hostname or IP address.
        port: Target TCP port for the SYN probe.
        ttl: Time-to-live value for this probe.
        timeout: Socket timeout in seconds.
        raw_socket: Optional pre-created raw ICMP socket.
        resolved_ip: Pre-resolved IP of *host* (used in fallback mode).

    Returns:
        Dict with hop, ttl, ip, host, response_type, rtt_ms,
        reached_destination, and error_code.
    """
    start = time.monotonic()

    if raw_socket is not None:
        # --- privileged mode: send SYN, listen for ICMP on raw socket ---
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        send_sock.setblocking(False)
        try:
            send_sock.connect_ex((host, port))
        except OSError:
            pass
        finally:
            send_sock.close()

        try:
            raw_socket.settimeout(timeout)
            data, _addr = raw_socket.recvfrom(512)
            icmp = parse_icmp_response(data)
            rtt = (time.monotonic() - start) * 1000
            hop_ip = icmp.get("hop_ip")
            label = _icmp_response_label(icmp)
            reached = (
                icmp.get("type") == ICMP_DEST_UNREACH
                and icmp.get("code") == PORT_UNREACHABLE_CODE
            )
            return {
                "hop": ttl,
                "ttl": ttl,
                "ip": hop_ip,
                "host": hop_ip or "*",
                "response_type": label,
                "rtt_ms": round(rtt, 2),
                "reached_destination": reached,
                "error_code": None,
            }
        except socket.timeout:
            rtt = (time.monotonic() - start) * 1000
            return _no_response_result(ttl, rtt)
        except OSError:
            rtt = (time.monotonic() - start) * 1000
            return _no_response_result(ttl, rtt)

    # --- fallback mode: blocking connect_ex with TTL ---
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
            "hop": ttl,
            "ttl": ttl,
            "ip": resolved_ip or host,
            "host": host,
            "response_type": RESP_CONNECTED,
            "rtt_ms": round(rtt, 2),
            "reached_destination": True,
            "error_code": err,
        }
    if err in CONN_REFUSED_CODES:
        return {
            "hop": ttl,
            "ttl": ttl,
            "ip": resolved_ip or host,
            "host": host,
            "response_type": RESP_RST,
            "rtt_ms": round(rtt, 2),
            "reached_destination": True,
            "error_code": err,
        }
    return {
        "hop": ttl,
        "ttl": ttl,
        "ip": None,
        "host": "*",
        "response_type": RESP_NO_RESPONSE,
        "rtt_ms": round(rtt, 2),
        "reached_destination": False,
        "error_code": err,
    }


def _no_response_result(ttl: int, rtt: float) -> Dict[str, object]:
    """Build a standard 'no response' result dict for a given TTL."""
    return {
        "hop": ttl,
        "ttl": ttl,
        "ip": None,
        "host": "*",
        "response_type": RESP_NO_RESPONSE,
        "rtt_ms": round(rtt, 2),
        "reached_destination": False,
        "error_code": None,
    }


def run_trace(
    target: str,
    port: int = DEFAULT_PORT,
    max_hops: int = DEFAULT_MAX_HOPS,
    timeout: float = DEFAULT_TIMEOUT,
    probes_per_hop: int = DEFAULT_PROBES_PER_HOP,
    raw_socket: Optional[socket.socket] = None,
) -> Dict[str, object]:
    """Run TCP traceroute against *target* using TTL-incremented probes.

    For each TTL from 1 to ``max_hops`` a TCP SYN probe is sent.  When a
    raw ICMP socket is available intermediate hops are identified from ICMP
    Time Exceeded responses; without root a connect-based fallback is used.

    Args:
        target: Hostname or URL (e.g. ``example.com`` or ``https://example.com``).
        port: Target TCP port for SYN probes (default 80).
        max_hops: Maximum TTL / number of hops (default 30, capped at 128).
        timeout: Per-probe timeout in seconds (default 3.0).
        probes_per_hop: Number of probes per hop for RTT averaging (default 3).
        raw_socket: Optional pre-created raw ICMP socket.

    Returns:
        Structured results dict with per-hop data, summary fields, and notes.
    """
    host = _normalize_host(target)
    ip = _resolve_host(host)

    max_hops = min(max_hops, MAX_MAX_HOPS)
    probes_per_hop = max(probes_per_hop, 1)

    own_raw_socket = False
    if raw_socket is None:
        raw_socket = _try_create_raw_socket()
        own_raw_socket = raw_socket is not None

    hops: List[Dict[str, object]] = []
    destination_reached = False
    notes: List[str] = []

    if ip is None:
        notes.append(f"Could not resolve host {host!r} to an IPv4 address")
    if raw_socket is None:
        notes.append(
            "Raw ICMP socket unavailable; running in connect-only fallback "
            "mode (intermediate hops not visible)"
        )

    for ttl in range(1, max_hops + 1):
        if destination_reached:
            break

        probe_results: List[Dict[str, object]] = []
        for _ in range(probes_per_hop):
            result = probe_ttl(
                host,
                port,
                ttl,
                timeout=timeout,
                raw_socket=raw_socket,
                resolved_ip=ip,
            )
            probe_results.append(result)
            if result.get("reached_destination"):
                destination_reached = True

        rtts = [
            r["rtt_ms"]
            for r in probe_results
            if r.get("rtt_ms") is not None
        ]
        rtt_avg = round(sum(rtts) / len(rtts), 2) if rtts else None

        primary = probe_results[0]
        hop_entry = {
            "hop": ttl,
            "ttl": ttl,
            "ip": primary.get("ip"),
            "host": primary.get("host"),
            "response_type": primary.get("response_type"),
            "rtt_ms": primary.get("rtt_ms"),
            "rtt_avg_ms": rtt_avg,
            "probes": probe_results,
            "reached_destination": any(
                r.get("reached_destination") for r in probe_results
            ),
            "error_code": primary.get("error_code"),
        }
        hops.append(hop_entry)

    if own_raw_socket and raw_socket is not None:
        raw_socket.close()

    if destination_reached and hops:
        notes.append(f"Destination reached at hop {hops[-1]['hop']}")
    elif hops:
        notes.append("Destination not reached within max-hops")

    return {
        "target": target,
        "host": host,
        "ip": ip,
        "port": port,
        "max_hops": max_hops,
        "timeout": timeout,
        "probes_per_hop": probes_per_hop,
        "raw_socket_available": raw_socket is not None,
        "hops": hops,
        "hop_count": len(hops),
        "destination_reached": destination_reached,
        "notes": notes,
    }


def format_trace_report_json(data: Dict[str, object]) -> str:
    """Format traceroute results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_trace_report_markdown(data: Dict[str, object]) -> str:
    """Format traceroute results as Markdown."""
    lines = ["# ethscan TCP Traceroute Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    if data.get("ip"):
        lines.append(f"- **Resolved IP:** {data['ip']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append(f"- **Max Hops:** {data['max_hops']}")
    lines.append(f"- **Probes per Hop:** {data['probes_per_hop']}")
    raw_avail = data.get("raw_socket_available")
    lines.append(
        f"- **Raw Socket:** "
        f"{'available' if raw_avail else 'unavailable (fallback mode)'}"
    )
    dest = data.get("destination_reached")
    lines.append(f"- **Destination Reached:** {'Yes' if dest else 'No'}")
    lines.append("")

    hops = data.get("hops") or []
    if hops:
        lines.append("## Hop Table")
        lines.append("| Hop | IP | RTT (ms) | Response | Reached |")
        lines.append("|-----|-----|----------|----------|---------|")
        for hop in hops:
            hop_num = hop.get("hop", "")
            ip = str(hop.get("ip") or "*").replace("|", "\\|")
            rtt = hop.get("rtt_avg_ms")
            rtt_str = str(rtt) if rtt is not None else str(hop.get("rtt_ms"))
            response = str(hop.get("response_type") or "").replace("|", "\\|")
            reached = "Yes" if hop.get("reached_destination") else "No"
            lines.append(
                f"| {hop_num} | {ip} | {rtt_str} | {response} | {reached} |"
            )
        lines.append("")

        lines.append("## Hop Details")
        for hop in hops:
            lines.append(f"### Hop {hop.get('hop')}")
            probes = hop.get("probes") or []
            if probes:
                lines.append(
                    "| Probe | RTT (ms) | Response | Reached Destination |"
                )
                lines.append("|-------|----------|----------|----------------------|")
                for i, probe in enumerate(probes):
                    rtt = probe.get("rtt_ms", "N/A")
                    response = str(probe.get("response_type") or "").replace(
                        "|", "\\|"
                    )
                    reached = (
                        "Yes" if probe.get("reached_destination") else "No"
                    )
                    lines.append(
                        f"| {i + 1} | {rtt} | {response} | {reached} |"
                    )
            else:
                lines.append("*No probes.*")
            lines.append("")
    else:
        lines.append("*No hops recorded.*")
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
