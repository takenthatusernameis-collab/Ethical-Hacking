"""Ping module for ethscan.

ICMP echo request probes with per-probe RTT and TTL reporting, plus a
TCP-ping fallback (connect-based latency measurement on a configurable port)
when raw ICMP sockets are unavailable (non-root).
"""
from __future__ import annotations

import csv
import io
import json
import socket
import struct
import time
from typing import Any, TypedDict, cast
from collections.abc import Mapping

from ethscan.target import normalize_host

DEFAULT_COUNT = 4
DEFAULT_TIMEOUT = 2.0
DEFAULT_TTL = 64
DEFAULT_PORT = 80

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0

ICMPV6_ECHO_REQUEST = 128
ICMPV6_ECHO_REPLY = 129
ICMPV6_NEXT_HEADER = 58

CONN_REFUSED_CODES = (111, 10061, 10013)

RESP_ECHO_REPLY = "ECHO_REPLY"
RESP_CONNECTED = "CONNECTED"
RESP_RST = "RST"
RESP_NO_RESPONSE = "NO-RESPONSE"
RESP_TIMEOUT = "TIMEOUT"


class _IcmpReply(TypedDict):
    type: int
    code: int
    identifier: int
    sequence: int
    payload: bytes
    src_ip: str
    protocol: int
    error: str | None


class _Icmpv6Reply(TypedDict):
    type: int
    code: int
    checksum: int
    identifier: int
    sequence: int
    payload: bytes
    error: str | None


class _ProbeResult(TypedDict):
    ip: str | None
    rtt_ms: float | None
    ttl: int
    sequence: int
    response_type: str
    error: str | None


class _PingResult(TypedDict):
    target: str
    host: str
    ip: str | None
    count: int
    timeout: float
    ttl: int
    port: int
    raw_socket_available: bool
    probes: list[_ProbeResult]
    successful: int
    failed: int
    rtt_min_ms: float | None
    rtt_max_ms: float | None
    rtt_avg_ms: float | None
    notes: list[str]


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host."""
    return normalize_host(target)


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


def _parse_icmp_reply(data: bytes, expected_id: int) -> _IcmpReply | None:
    """Parse an ICMP Echo Reply packet.

    Returns a dict with keys: type, code, identifier, sequence, payload, error.
    Returns None if the packet is not a valid Echo Reply for our identifier.
    """
    if len(data) < 20:
        return cast(_IcmpReply, {"error": "packet too short for IP header"})

    ip_version = (data[0] >> 4) & 0x0F
    if ip_version != 4:
        return cast(_IcmpReply, {"error": "not IPv4"})

    ihl = data[0] & 0x0F
    ip_header_len = ihl * 4
    if ip_header_len < 20 or len(data) < ip_header_len:
        return cast(_IcmpReply, {"error": "IP header truncated"})

    protocol = data[9]
    src_ip = socket.inet_ntoa(data[12:16])

    if len(data) < ip_header_len + 8:
        return cast(_IcmpReply, {"error": "ICMP header truncated"})

    icmp_offset = ip_header_len
    icmp_type = data[icmp_offset]
    icmp_code = data[icmp_offset + 1]
    struct.unpack("!H", data[icmp_offset + 2:icmp_offset + 4])[0]
    icmp_identifier = struct.unpack("!H", data[icmp_offset + 4:icmp_offset + 6])[0]
    icmp_sequence = struct.unpack("!H", data[icmp_offset + 6:icmp_offset + 8])[0]

    if icmp_type != ICMP_ECHO_REPLY or icmp_code != 0:
        return cast(_IcmpReply, {"error": f"not echo reply: type={icmp_type}, code={icmp_code}"})

    if icmp_identifier != expected_id:
        return cast(_IcmpReply, {"error": f"identifier mismatch: expected {expected_id}, got {icmp_identifier}"})

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


def _build_icmpv6_echo_request(
    identifier: int,
    sequence: int,
    payload: bytes = b"",
    src_ip: str = "::",
    dst_ip: str = "::1",
) -> bytes:
    """Build an ICMPv6 Echo Request (type 128) with a pseudo-header checksum.

    The checksum covers the IPv6 pseudo-header (source, destination, upper-layer
    packet length, zeroes, next header) followed by the ICMPv6 message, per
    RFC 2460 / RFC 4443. Returns the complete ICMPv6 message ready to send.
    """
    message = struct.pack("!BBHHH", ICMPV6_ECHO_REQUEST, 0, 0, identifier, sequence) + payload
    pseudo = (
        socket.inet_pton(socket.AF_INET6, src_ip)
        + socket.inet_pton(socket.AF_INET6, dst_ip)
        + struct.pack("!I", len(message))
        + b"\x00\x00\x00"
        + struct.pack("!B", ICMPV6_NEXT_HEADER)
    )
    checksum = _checksum(pseudo + message)
    return struct.pack("!BBHHH", ICMPV6_ECHO_REQUEST, 0, checksum, identifier, sequence) + payload


def _parse_icmpv6_reply(data: bytes, expected_id: int) -> _Icmpv6Reply:
    """Parse an ICMPv6 Echo Reply (type 129).

    ``data`` is expected to begin at the ICMPv6 header (raw ICMPv6 sockets do
    not prepend the IPv6 header). Returns a dict with an ``error`` key set on
    any validation failure.
    """
    if len(data) < 8:
        return cast(_Icmpv6Reply, {"error": "ICMPv6 header truncated"})

    icmp_type = data[0]
    icmp_code = data[1]
    # checksum = struct.unpack("!H", data[2:4])[0]  # not validated without the IP header
    icmp_identifier = struct.unpack("!H", data[4:6])[0]
    icmp_sequence = struct.unpack("!H", data[6:8])[0]

    if icmp_type != ICMPV6_ECHO_REPLY or icmp_code != 0:
        return cast(
            _Icmpv6Reply,
            {"error": f"not echo reply: type={icmp_type}, code={icmp_code}"},
        )

    if icmp_identifier != expected_id:
        return cast(
            _Icmpv6Reply,
            {"error": f"identifier mismatch: expected {expected_id}, got {icmp_identifier}"},
        )

    return {
        "type": icmp_type,
        "code": icmp_code,
        "checksum": struct.unpack("!H", data[2:4])[0],
        "identifier": icmp_identifier,
        "sequence": icmp_sequence,
        "payload": data[8:],
        "error": None,
    }


def _try_create_raw_socket(family: int = socket.AF_INET) -> Any:
    """Attempt to create a raw ICMP socket for sending/receiving echo requests.

    The socket family is chosen by *family*: ``AF_INET``/``IPPROTO_ICMP`` for
    IPv4 and ``AF_INET6``/``IPPROTO_ICMPV6`` for IPv6. Returns the socket if
    available, or ``None`` if raw sockets are not permitted (e.g. running
    without root privileges).
    """
    try:
        if family == socket.AF_INET6:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_ICMPV6)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except Exception:  # noqa: BLE001 - transport can raise any type
        return None
    else:
        return sock


def _resolve_host(host: str) -> tuple[str, int, tuple[Any, ...]] | tuple[None, None, None]:
    """Resolve a hostname to an IP address with family and sockaddr.

    Returns a tuple of (ip, family, sockaddr) on success, or (None, None, None)
    on failure. The sockaddr is a tuple suitable for socket.connect().
    """
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    except Exception:  # noqa: BLE001 - resolver can raise any type
        return None, None, None

    if not infos:
        return None, None, None

    info = infos[0]
    family = info[0]
    sockaddr = info[4]
    ip = sockaddr[0]
    return ip, family, sockaddr  # type: ignore[return-value]


def probe_icmp(
    host: str,
    timeout: float = DEFAULT_TIMEOUT,
    ttl: int = DEFAULT_TTL,
    raw_socket: Any = None,
    identifier: int = 0,
    sequence: int = 0,
    payload: bytes = b"",
    resolved_ip: str | None = None,
    resolved_family: int | None = None,
    resolved_sockaddr: tuple | None = None,
    port: int = DEFAULT_PORT,
) -> _ProbeResult:
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
        resolved_family: Address family of the resolved IP (AF_INET or AF_INET6).
        resolved_sockaddr: Resolved sockaddr tuple for direct connection.
        port: Target TCP port for connect-based fallback (default 80).

    Returns:
        Dict with ip, rtt_ms, ttl, sequence, response_type, and error.
    """
    start = time.monotonic()

    # --- ICMPv6 path: raw ICMPv6 socket for an IPv6 target -------------------
    if raw_socket is not None and resolved_family == socket.AF_INET6:
        send_sock = None
        try:
            send_sock = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_ICMPV6)
        except Exception:  # noqa: BLE001 - transport can raise any type
            send_sock = None
        if send_sock is not None:
            try:
                hop_limit_opt = getattr(socket, "IPV6_UNICAST_HOPS", None)
                if hop_limit_opt is not None:
                    send_sock.setsockopt(socket.IPPROTO_IPV6, hop_limit_opt, ttl)
                send_sock.settimeout(timeout)

                dst = resolved_ip or host
                request = _build_icmpv6_echo_request(
                    identifier, sequence, payload, resolved_ip or host, dst
                )
                try:
                    send_sock.sendto(request, (dst, 0))
                except Exception as exc:  # noqa: BLE001
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
                    v6_reply = _parse_icmpv6_reply(data, identifier)

                    if v6_reply.get("error"):
                        return {
                            "ip": resolved_ip or host,
                            "rtt_ms": round(rtt, 2),
                            "ttl": ttl,
                            "sequence": sequence,
                            "response_type": RESP_NO_RESPONSE,
                            "error": v6_reply.get("error") or "parse failed",
                        }

                    return {
                        "ip": resolved_ip or host,
                        "rtt_ms": round(rtt, 2),
                        "ttl": ttl,
                        "sequence": sequence,
                        "response_type": RESP_ECHO_REPLY,
                        "error": None,
                    }
                except socket.timeout:
                    rtt = (time.monotonic() - start) * 1000
                    return {
                        "ip": None,
                        "rtt_ms": round(rtt, 2),
                        "ttl": ttl,
                        "sequence": sequence,
                        "response_type": RESP_TIMEOUT,
                        "error": "timeout",
                    }
                except Exception as exc:  # noqa: BLE001
                    rtt = (time.monotonic() - start) * 1000
                    return {
                        "ip": None,
                        "rtt_ms": round(rtt, 2),
                        "ttl": ttl,
                        "sequence": sequence,
                        "response_type": RESP_NO_RESPONSE,
                        "error": str(exc),
                    }
            finally:
                send_sock.close()

    # --- ICMPv4 path: raw ICMP socket for an IPv4 target ---------------------
    raw_socket_usable = raw_socket is not None and resolved_family != socket.AF_INET6

    if raw_socket_usable:
        try:
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        except Exception:  # noqa: BLE001 - transport can raise any type
            # Fall back to TCP mode if raw socket creation fails
            raw_socket = None
        else:
            send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
            send_sock.settimeout(timeout)

            request = _build_icmp_echo_request(identifier, sequence, payload)
            try:
                send_sock.sendto(request, (host, 0))
            except Exception as exc:  # noqa: BLE001
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
            except Exception as exc:  # noqa: BLE001
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
    # Use resolved family and sockaddr if available, otherwise fall back to host string
    family = resolved_family if resolved_family is not None else socket.AF_INET
    sockaddr = resolved_sockaddr
    try:
        send_sock = socket.socket(family, socket.SOCK_STREAM)
        if family == socket.AF_INET6:
            hop_limit_opt = getattr(socket, "IPV6_UNICAST_HOPS", None)
            if hop_limit_opt is not None:
                send_sock.setsockopt(socket.IPPROTO_IPV6, hop_limit_opt, ttl)
        else:
            send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        send_sock.settimeout(timeout)
    except Exception as exc:  # noqa: BLE001 - transport can raise any type
        # A socket that cannot be created is a transport failure: report it as
        # a failed probe instead of letting the exception escape the command.
        rtt = (time.monotonic() - start) * 1000
        return {
            "ip": None,
            "rtt_ms": round(rtt, 2),
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_NO_RESPONSE,
            "error": str(exc),
        }
    try:
        if sockaddr is not None:
            # For IPv6, sockaddr may be a 4-tuple (ip, port, flowinfo, scopeid)
            # We need to replace the port with our target port
            if family == socket.AF_INET6 and len(sockaddr) >= 4:
                connect_sockaddr: tuple[Any, ...] = (sockaddr[0], port, sockaddr[2], sockaddr[3])
            else:
                connect_sockaddr = (sockaddr[0], port)
            err = send_sock.connect_ex(connect_sockaddr)
        else:
            err = send_sock.connect_ex((host, port))
    except Exception as exc:  # noqa: BLE001 - transport can raise any type
        # The name itself cannot be resolved (connect_ex only swallows errors
        # from connect(), not from getaddrinfo()) and a transport that fails
        # with any other error type must not escape the command either.
        # Report it as a failed probe instead.
        rtt = (time.monotonic() - start) * 1000
        return {
            "ip": None,
            "rtt_ms": round(rtt, 2),
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_NO_RESPONSE,
            "error": str(exc),
        }
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
    raw_socket: Any = None,
) -> _PingResult:
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
    ip, family, sockaddr = _resolve_host(host)

    count = max(count, 1)
    timeout = max(timeout, 0.1)
    ttl = max(min(ttl, 255), 1)

    own_raw_socket = False
    if raw_socket is None:
        try:
            raw_socket = _try_create_raw_socket(family if family is not None else socket.AF_INET)
        except Exception:  # noqa: BLE001 - transport can raise any type
            raw_socket = None
        own_raw_socket = raw_socket is not None

    identifier = 0xFFFF & int(time.time() * 1000)

    probes: list[_ProbeResult] = []
    notes: list[str] = []

    if ip is None:
        notes.append(f"Could not resolve host {host!r} to an IP address")
    else:
        # Note the address family for clarity
        family_name = "IPv6" if family == socket.AF_INET6 else "IPv4"
        notes.append(f"Resolved {host!r} to {ip} ({family_name})")
    ipv6_icmp = family == socket.AF_INET6 and raw_socket is not None
    if ipv6_icmp:
        notes.append(
            "Raw ICMPv6 socket available; sending ICMPv6 Echo Request "
            f"(type 128) on {ip} (ICMPv6 ping)"
        )
    elif raw_socket is None:
        notes.append(
            "Raw ICMP socket unavailable; running in TCP connect fallback "
            f"mode on port {port} (ICMP ping not available)"
        )

    for seq in range(1, count + 1):
        try:
            result = probe_icmp(
                host,
                timeout=timeout,
                ttl=ttl,
                raw_socket=raw_socket,
                identifier=identifier,
                sequence=seq,
                resolved_ip=ip,
                resolved_family=family,
                resolved_sockaddr=sockaddr,
                port=port,
            )
        except Exception as exc:  # noqa: BLE001 - transport can raise any type
            result = {
                "ip": ip,
                "rtt_ms": None,
                "ttl": ttl,
                "sequence": seq,
                "response_type": RESP_NO_RESPONSE,
                "error": str(exc),
            }
        probes.append(result)

    if own_raw_socket and raw_socket is not None:
        raw_socket.close()

    successful = [p for p in probes if p.get("response_type") in (RESP_ECHO_REPLY, RESP_CONNECTED, RESP_RST)]
    failed = [p for p in probes if p.get("response_type") in (RESP_NO_RESPONSE, RESP_TIMEOUT)]

    rtts: list[float] = []
    for p in successful:
        rtt_val = p.get("rtt_ms")
        if isinstance(rtt_val, (int, float)):
            rtts.append(float(rtt_val))
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


def format_ping_report_json(data: Mapping[str, object]) -> str:
    """Format ping results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_ping_report_markdown(data: Mapping[str, object]) -> str:
    """Format ping results as Markdown."""
    if not isinstance(data, dict):
        data = {}
    lines = ["# ethscan Ping Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Host:** {data.get('host', '')}")
    if data.get("ip"):
        lines.append(f"- **Resolved IP:** {data.get('ip', '')}")
    lines.append(f"- **Count:** {data.get('count', '')}")
    lines.append(f"- **Timeout:** {data.get('timeout', '')}s")
    lines.append(f"- **TTL:** {data.get('ttl', '')}")
    lines.append(f"- **TCP Fallback Port:** {data.get('port', '')}")
    raw_avail = data.get("raw_socket_available")
    lines.append(
        f"- **Raw ICMP Socket:** "
        f"{'available' if raw_avail else 'unavailable (TCP fallback mode)'}"
    )
    lines.append(f"- **Successful:** {data.get('successful', '')}/{data.get('count', '')}")
    lines.append(f"- **Failed:** {data.get('failed', '')}/{data.get('count', '')}")
    if data.get("rtt_min_ms") is not None:
        lines.append(f"- **RTT Min:** {data.get('rtt_min_ms', '')} ms")
        lines.append(f"- **RTT Max:** {data.get('rtt_max_ms', '')} ms")
        lines.append(f"- **RTT Avg:** {data.get('rtt_avg_ms', '')} ms")
    lines.append("")

    probes_list = data.get("probes") or []
    if not isinstance(probes_list, list):
        probes_list = []
    if probes_list:
        lines.append("## Probe Results")
        lines.append("| Seq | IP | RTT (ms) | Response |")
        lines.append("|-----|-----|----------|----------|")
        for probe in probes_list:
            if not isinstance(probe, dict):
                continue
            seq = probe.get("sequence", "")
            ip_val = probe.get("ip")
            ip = str(ip_val or "*").replace("|", "\\|")
            rtt = probe.get("rtt_ms")
            rtt_str = str(rtt) if rtt is not None else "N/A"
            response = str(probe.get("response_type") or "").replace("|", "\\|")
            lines.append(f"| {seq} | {ip} | {rtt_str} | {response} |")
        lines.append("")

    notes = data.get("notes") or []
    if not isinstance(notes, list):
        notes = []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def format_ping_report_csv(data: Mapping[str, object]) -> str:
    """Format ping results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "ip",
        "sequence",
        "rtt_ms",
        "ttl",
        "response_type",
        "error",
    ])
    if not isinstance(data, dict):
        return output.getvalue().rstrip("\r\n")
    probes_list = data.get("probes") or []
    if not isinstance(probes_list, list):
        probes_list = []
    for probe in probes_list:
        if not isinstance(probe, dict):
            continue
        rtt = probe.get("rtt_ms")
        writer.writerow([
            data.get("target", ""),
            probe.get("ip") or "",
            probe.get("sequence", ""),
            rtt if rtt is not None else "",
            probe.get("ttl", ""),
            probe.get("response_type") or "",
            probe.get("error") or "",
        ])
    return output.getvalue().rstrip("\r\n")