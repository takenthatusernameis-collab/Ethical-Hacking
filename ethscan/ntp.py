"""NTP reconnaissance module for ethscan.

Offline-first NTP reconnaissance using only the Python standard library
(``socket`` / ``struct``). The module performs:

* Basic NTP time request (mode 3) to verify server responsiveness.
* NTP monlist request (mode 7, implementation 42) to detect vulnerable/reflector
  NTP servers susceptible to amplification attacks.

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw UDP socket so tests can substitute a local fake server.
"""
from __future__ import annotations

import csv
import io
import json
import socket
import struct
from typing import Any

from ethscan.target import TargetSpecError, check_port, url_port

DEFAULT_PORT = 123
DEFAULT_TIMEOUT = 3.0


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and port.

    Accepts ``host``, ``host:port``, and ``ntp://host:port`` forms.
    Defaults to port ``DEFAULT_PORT`` when none is supplied.
    """
    normalized = target.strip()
    if "://" in normalized:
        from urllib.parse import urlparse

        parsed = urlparse(normalized)
        host = parsed.hostname or ""
        port = url_port(parsed)
    else:
        host = normalized
        port = None
        if host and host.startswith("[") and "]:" in host:
            bracket_end = host.find("]:")
            if bracket_end > 0:
                port_part = host[bracket_end + 2:]
                if port_part.isdigit():
                    host = host[1:bracket_end]
                    port = port or check_port(int(port_part))
        elif host and ":" in host and "]" not in host:
            base, _, rest = host.rpartition(":")
            if rest.isdigit():
                host = base
                port = port or check_port(int(rest))
        elif host and host.startswith("[") and host.endswith("]"):
            host = host[1:-1]

    if not host:
        raise TargetSpecError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


def _build_time_request() -> bytes:
    """Build a minimal NTP time request packet (mode 3, client)."""
    li_vn_mode = (0 << 6) | (4 << 3) | 3
    stratum = 0
    poll = 4
    precision = -20
    root_delay = 0
    root_dispersion = 0
    ref_id = 0
    ref_ts = 0
    orig_ts = 0
    recv_ts = 0
    xmit_ts = 0
    return struct.pack(
        "!BBBbIIIQQQQ",
        li_vn_mode,
        stratum,
        poll,
        precision,
        root_delay,
        root_dispersion,
        ref_id,
        ref_ts,
        orig_ts,
        recv_ts,
        xmit_ts,
    )


def _build_monlist_request() -> bytes:
    """Build an NTP monlist request packet (mode 7, implementation 42)."""
    li_vn_mode = (0 << 6) | (4 << 3) | 7
    r_m_impl = (0 << 7) | 42
    request_code = 0
    sequence = 1
    status = 0
    assoc_id = 0
    offset = 0
    count = 0
    return struct.pack(
        "!BBBBHHHH",
        li_vn_mode,
        r_m_impl,
        request_code,
        sequence,
        status,
        assoc_id,
        offset,
        count,
    )


def _parse_time_response(data: bytes) -> dict[str, Any]:
    """Parse an NTP time response packet (mode 4, server)."""
    if len(data) < 48:
        return {"error": "Response too short for NTP time packet"}

    li_vn_mode = data[0]
    stratum = data[1]
    poll = data[2]
    precision = struct.unpack("!b", data[3:4])[0]
    root_delay = struct.unpack("!I", data[4:8])[0]
    root_dispersion = struct.unpack("!I", data[8:12])[0]
    ref_id = struct.unpack("!I", data[12:16])[0]
    ref_ts = struct.unpack("!Q", data[16:24])[0]
    orig_ts = struct.unpack("!Q", data[24:32])[0]
    recv_ts = struct.unpack("!Q", data[32:40])[0]
    xmit_ts = struct.unpack("!Q", data[40:48])[0]

    li = (li_vn_mode >> 6) & 0x3
    vn = (li_vn_mode >> 3) & 0x7
    mode = li_vn_mode & 0x7

    def ntp_to_unix(ntp_ts: int) -> float | None:
        if ntp_ts == 0:
            return None
        seconds = ntp_ts >> 32
        fraction = ntp_ts & 0xFFFFFFFF
        return seconds - 2208988800 + fraction / 2**32

    leap_indicator = {0: "no warning", 1: "last minute has 61 seconds", 2: "last minute has 59 seconds", 3: "alarm condition"}

    return {
        "leap_indicator": leap_indicator.get(li, f"unknown ({li})"),
        "version": vn,
        "mode": mode,
        "stratum": stratum,
        "poll": poll,
        "precision": precision,
        "root_delay_ms": round(root_delay / 2**16 * 1000, 3),
        "root_dispersion_ms": round(root_dispersion / 2**16 * 1000, 3),
        "reference_id": _format_ref_id(ref_id, stratum),
        "reference_timestamp": ntp_to_unix(ref_ts),
        "originate_timestamp": ntp_to_unix(orig_ts),
        "receive_timestamp": ntp_to_unix(recv_ts),
        "transmit_timestamp": ntp_to_unix(xmit_ts),
    }


def _format_ref_id(ref_id: int, stratum: int) -> str:
    """Format the reference identifier based on stratum."""
    if stratum == 0:
        return f"0x{ref_id:08x} (kiss-o'-death)"
    if stratum == 1:
        return ".".join(str((ref_id >> (8 * i)) & 0xFF) for i in reversed(range(4)))
    return f"0x{ref_id:08x}"


def _parse_monlist_response(data: bytes) -> dict[str, Any]:
    """Parse an NTP monlist response packet (mode 7)."""
    if len(data) < 12:
        return {"error": "Response too short for NTP control packet"}

    li_vn_mode = data[0]
    r_m_impl = data[1]
    request_code = data[2]
    sequence = data[3]
    status = struct.unpack("!H", data[4:6])[0]
    assoc_id = struct.unpack("!H", data[6:8])[0]
    offset = struct.unpack("!H", data[8:10])[0]
    count = struct.unpack("!H", data[10:12])[0]

    li = (li_vn_mode >> 6) & 0x3
    vn = (li_vn_mode >> 3) & 0x7
    mode = li_vn_mode & 0x7

    r_bit = (r_m_impl >> 7) & 0x1
    impl = r_m_impl & 0x7F

    error = None
    if (status & 0x8000) != 0:
        error = "Server returned error bit in status"

    peer_count = 0
    peers = []
    if len(data) >= 12 + count * 8:
        peer_data = data[12:12 + count * 8]
        for i in range(0, len(peer_data), 8):
            chunk = peer_data[i:i+8]
            if len(chunk) == 8:
                peer_addr = struct.unpack("!I", chunk[:4])[0]
                peer_port = struct.unpack("!H", chunk[4:6])[0]
                peer_mode = chunk[6]
                peer_version = chunk[7] & 0x7
                peer_count += 1
                peers.append({
                    "address": ".".join(str((peer_addr >> (8 * j)) & 0xFF) for j in reversed(range(4))),
                    "port": peer_port,
                    "mode": peer_mode,
                    "version": peer_version,
                })

    return {
        "leap_indicator": li,
        "version": vn,
        "mode": mode,
        "response_bit": r_bit,
        "implementation": impl,
        "request_code": request_code,
        "sequence": sequence,
        "status": status,
        "association_id": assoc_id,
        "offset": offset,
        "count": count,
        "peer_count": peer_count,
        "peers": peers,
        "error": error,
    }


def _send_recv(
    host: str,
    port: int,
    request: bytes,
    timeout: float,
    connector=None,
) -> tuple[bytes | None, str | None]:
    """Send a UDP request and receive the response (injectable for tests)."""
    if connector is not None:
        return connector(host, port, request, timeout)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(request, (host, port))
        data, _ = sock.recvfrom(65536)
        return data, None
    except socket.timeout:
        return None, "timeout"
    except OSError as exc:
        return None, str(exc)
    finally:
        sock.close()


def run_ntp(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    check_monlist: bool = True,
    connector=None,
) -> dict[str, Any]:
    """Run NTP reconnaissance against *target*.

    Args:
        target: Hostname, ``host:port``, or URL.
        port: Explicit NTP port; when ``None`` the port is parsed from the
            target (or defaults to 123).
        timeout: Per-request timeout in seconds.
        check_monlist: Whether to send a monlist request to detect amplification
            vulnerability.
        connector: Callable for sending/receiving UDP packets (for testing).

    Returns:
        Structured result dict consumed by the formatters below.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port

    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "time_response": None,
        "monlist_response": None,
        "is_reflector": False,
        "amplification_factor": None,
        "error": None,
    }

    time_req = _build_time_request()
    time_data, time_err = _send_recv(host, server_port, time_req, timeout, connector=connector)
    if time_err:
        results["error"] = f"time request failed: {time_err}"
        return results

    time_resp = _parse_time_response(time_data)
    results["time_response"] = time_resp

    if "error" in time_resp:
        results["error"] = time_resp["error"]
        return results

    if check_monlist:
        monlist_req = _build_monlist_request()
        mon_data, mon_err = _send_recv(host, server_port, monlist_req, timeout, connector=connector)
        if mon_err:
            results["monlist_response"] = {"error": f"monlist request failed: {mon_err}"}
        else:
            mon_resp = _parse_monlist_response(mon_data)
            results["monlist_response"] = mon_resp

            if mon_resp.get("peer_count", 0) > 0:
                results["is_reflector"] = True
                req_len = len(monlist_req)
                resp_len = len(mon_data)
                if req_len > 0:
                    results["amplification_factor"] = round(resp_len / req_len, 2)

    return results


def format_ntp_report_json(data: dict[str, Any]) -> str:
    """Format NTP reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_ntp_report_markdown(data: dict[str, Any]) -> str:
    """Format NTP reconnaissance results as Markdown."""
    lines = ["# ethscan NTP Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Host:** {data.get('host', '')}")
    lines.append(f"- **Port:** {data.get('port', '')}")

    time_resp = data.get("time_response")
    if time_resp:
        if "error" in time_resp:
            lines.append("")
            lines.append(f"- **Time Request Error:** {time_resp['error']}")
        else:
            lines.append("")
            lines.append("## NTP Time Response")
            lines.append(f"- **Leap Indicator:** {time_resp.get('leap_indicator', 'N/A')}")
            lines.append(f"- **Version:** {time_resp.get('version', 'N/A')}")
            lines.append(f"- **Mode:** {time_resp.get('mode', 'N/A')} (server)")
            lines.append(f"- **Stratum:** {time_resp.get('stratum', 'N/A')}")
            lines.append(f"- **Poll:** {time_resp.get('poll', 'N/A')}")
            lines.append(f"- **Precision:** {time_resp.get('precision', 'N/A')}")
            lines.append(f"- **Root Delay:** {time_resp.get('root_delay_ms', 'N/A')} ms")
            lines.append(f"- **Root Dispersion:** {time_resp.get('root_dispersion_ms', 'N/A')} ms")
            lines.append(f"- **Reference ID:** {time_resp.get('reference_id', 'N/A')}")
            for ts_key in ["reference_timestamp", "originate_timestamp", "receive_timestamp", "transmit_timestamp"]:
                ts_val = time_resp.get(ts_key)
                if ts_val is not None:
                    import datetime
                    dt = datetime.datetime.fromtimestamp(ts_val, tz=datetime.timezone.utc)
                    lines.append(f"- **{ts_key.replace('_', ' ').title()}:** {dt.isoformat()}")
                else:
                    lines.append(f"- **{ts_key.replace('_', ' ').title()}:** N/A")

    mon_resp = data.get("monlist_response")
    if mon_resp:
        lines.append("")
        lines.append("## Monlist Response (Amplification Check)")
        if mon_resp.get("error"):
            lines.append(f"- **Error:** {mon_resp['error']}")
        else:
            lines.append(f"- **Leap Indicator:** {mon_resp.get('leap_indicator', 'N/A')}")
            lines.append(f"- **Version:** {mon_resp.get('version', 'N/A')}")
            lines.append(f"- **Mode:** {mon_resp.get('mode', 'N/A')}")
            lines.append(f"- **Response Bit:** {mon_resp.get('response_bit', 'N/A')}")
            lines.append(f"- **Implementation:** {mon_resp.get('implementation', 'N/A')} (MON_GETLIST=42)")
            lines.append(f"- **Request Code:** {mon_resp.get('request_code', 'N/A')}")
            lines.append(f"- **Sequence:** {mon_resp.get('sequence', 'N/A')}")
            lines.append(f"- **Status:** 0x{mon_resp.get('status', 0):04x}")
            lines.append(f"- **Association ID:** {mon_resp.get('association_id', 'N/A')}")
            lines.append(f"- **Offset:** {mon_resp.get('offset', 'N/A')}")
            lines.append(f"- **Count:** {mon_resp.get('count', 'N/A')}")
            lines.append(f"- **Peer Count:** {mon_resp.get('peer_count', 0)}")
            if mon_resp.get("peer_count", 0) > 0:
                lines.append("- **Peers:**")
                for peer in mon_resp.get("peers", []):
                    lines.append(f"  - {peer['address']}:{peer['port']} (mode={peer['mode']}, version={peer['version']})")
            if mon_resp.get("error"):
                lines.append(f"- **Error:** {mon_resp['error']}")

    if data.get("is_reflector"):
        lines.append("")
        lines.append("## Amplification Assessment")
        lines.append("- **Reflector:** YES ⚠️")
        lines.append(f"- **Amplification Factor:** {data.get('amplification_factor', 'N/A')}x")
        lines.append("  (Server responded to monlist request with peer data)")
    elif data.get("monlist_response") is not None:
        lines.append("")
        lines.append("## Amplification Assessment")
        lines.append("- **Reflector:** NO")
        lines.append("  (Server did not return peer data in monlist response)")

    if data.get("error"):
        lines.append("")
        lines.append(f"- **Error:** {data['error']}")

    lines.append("")
    return "\n".join(lines)


def format_ntp_report_csv(data: dict[str, Any]) -> str:
    """Format NTP reconnaissance results as CSV.

    Emits a header row plus one row per peer (including a summary row).
    Header: ``target,port,version,port_open,peer_count,record_type,peer_address,peer_port,peer_mode,peer_version``
    - Summary row: record_type=summary (peer_* fields empty)
    - Peer rows: record_type=peer (with peer data)
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Unified header with record_type discriminator
    writer.writerow([
        "target", "port", "version", "port_open", "peer_count",
        "record_type", "peer_address", "peer_port", "peer_mode", "peer_version"
    ])

    time_resp = data.get("time_response") or {}
    mon_resp = data.get("monlist_response") or {}

    # Extract summary data
    version = time_resp.get("version", "") if not time_resp.get("error") else ""
    # Note: port_open is not available in current data structure, leaving empty
    port_open = ""
    peer_count = mon_resp.get("peer_count", 0) if not mon_resp.get("error") else 0

    # Summary row
    writer.writerow([
        data.get("target", ""),
        data.get("port", ""),
        version,
        port_open,
        peer_count,
        "summary",  # record_type
        "",  # peer_address
        "",  # peer_port
        "",  # peer_mode
        "",  # peer_version
    ])

    # Peer rows (one per peer)
    if not mon_resp.get("error") and mon_resp.get("peers"):
        for peer in mon_resp.get("peers", []):
            writer.writerow([
                data.get("target", ""),
                data.get("port", ""),
                version,
                port_open,
                peer_count,
                "peer",  # record_type
                peer.get("address", ""),
                peer.get("port", ""),
                peer.get("mode", ""),
                peer.get("version", ""),
            ])

    return output.getvalue().rstrip("\r\n")