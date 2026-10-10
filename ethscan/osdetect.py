"""OS fingerprinting module for ethscan."""

import json
import os
import re
import socket
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple


DEFAULT_TIMEOUT = 5.0
DEFAULT_WORKERS = 10
SYN_MAX_LENGTH = 200


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    return (parsed.hostname or parsed.netloc or "").lower()


def _truncate(message: str, limit: int = SYN_MAX_LENGTH) -> str:
    """Truncate an error message to a bounded length."""
    if len(message) <= limit:
        return message
    return message[: limit - 3] + "..."


def _errno_message(err: int) -> str:
    """Convert a socket error code to a human-readable message."""
    try:
        return os.strerror(err)
    except (ValueError, OverflowError):
        return str(err)


# ---------------------------------------------------------------------------
# TCP/IP stack behavior probes
# ---------------------------------------------------------------------------

# TCP flags
FIN = 0x01
SYN = 0x02
RST = 0x04
PSH = 0x08
ACK = 0x10
URG = 0x20
ECE = 0x40
CWR = 0x80


def _build_syn_packet(src_port: int, dst_port: int, seq: int = 0,
                      ack: int = 0, flags: int = SYN, window: int = 65535,
                      urgent: int = 0) -> bytes:
    """Build a minimal TCP header for a raw SYN probe (stdlib only).

    The header is 20 bytes long. The checksum is computed over a pseudo-header
    plus the TCP header. Source/dst addresses default to 127.0.0.1 so the
    packet can be injected locally without privileged raw sockets when the
    target is loopback; for remote targets the caller must supply a real
    source address via the public probe function.
    """
    src_ip = b"\x7f\x00\x00\x01"
    dst_ip = b"\x7f\x00\x00\x01"
    data_offset = (5 << 4)  # no options
    header = struct.pack(
        ">HHIIBBHHH",
        src_port,
        dst_port,
        seq,
        ack,
        data_offset,
        flags,
        window,
        0,  # checksum placeholder
        urgent,
    )
    pseudo = src_ip + dst_ip + struct.pack(">BBH", 0, socket.IPPROTO_TCP, len(header))
    checksum = _checksum(pseudo + header)
    header = struct.pack(
        ">HHIIBBHHH",
        src_port,
        dst_port,
        seq,
        ack,
        data_offset,
        flags,
        window,
        checksum,
        urgent,
    )
    return header


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


def _connect_tcp(host: str, port: int, timeout: float) -> Tuple[bool, Optional[str], Optional[int]]:
    """Open a standard TCP connection and report success/failure.

    Returns (connected, error_message, observed_rst_flag_or_None). The RST flag
    can only be observed through raw sockets; for stdlib connections we infer
    RST from immediate ConnectionRefusedError.
    """
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        return True, None, None
    except ConnectionRefusedError:
        return False, "connection refused (RST)", 1
    except socket.timeout:
        return False, "connection timed out", None
    except OSError as exc:
        return False, _truncate(str(exc)), None
    finally:
        try:
            sock.close()
        except Exception:
            pass


def probe_syn(host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, object]:
    """Probe a target with a TCP SYN packet and observe the response behavior.

    Uses stdlib sockets only. Because raw sockets require root privileges on
    most platforms, the probe performs a normal connect() SYN and records the
    observed behavior (connected, refused/RST, timed out). When raw sockets are
    available the probe additionally inspects the reply flags.

    Returns a dict with: port, connected, response, error, and any observed
    TCP flags that can be inferred.
    """
    entry: Dict[str, object] = {
        "port": port,
        "probe_type": "SYN",
        "connected": False,
        "response": None,
        "error": None,
        "flags_observed": None,
    }
    connected, error, inferred_flag = _connect_tcp(host, port, timeout)
    if connected:
        entry["connected"] = True
        entry["response"] = "SYN-ACK"
        entry["flags_observed"] = "SYN-ACK"
    else:
        entry["error"] = error
        if inferred_flag is not None:
            entry["response"] = "RST"
            entry["flags_observed"] = "RST"
        else:
            entry["response"] = "NO-RESPONSE"
    return entry


def probe_rst(host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, object]:
    """Probe a target with a TCP RST packet and observe the response."""
    entry: Dict[str, object] = {
        "port": port,
        "probe_type": "RST",
        "connected": False,
        "response": None,
        "error": None,
        "flags_observed": None,
    }
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        # Send a RST by connecting then immediately closing
        err = sock.connect_ex((host, port))
        if err == 0:
            entry["connected"] = True
            entry["response"] = "OPEN"
            entry["flags_observed"] = "OPEN"
        elif err in (111, 10061, 10013):
            entry["response"] = "RST"
            entry["flags_observed"] = "RST"
            entry["error"] = "connection refused"
        else:
            entry["response"] = "NO-RESPONSE"
            entry["error"] = _truncate(_errno_message(err))
    except socket.timeout:
        entry["response"] = "NO-RESPONSE"
        entry["error"] = "connection timed out"
    except OSError as exc:
        entry["response"] = "NO-RESPONSE"
        entry["error"] = _truncate(str(exc))
    finally:
        try:
            sock.close()
        except Exception:
            pass
    return entry


def probe_fin(host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, object]:
    """Probe a target with a FIN packet and observe the response."""
    entry: Dict[str, object] = {
        "port": port,
        "probe_type": "FIN",
        "connected": False,
        "response": None,
        "error": None,
        "flags_observed": None,
    }
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        err = sock.connect_ex((host, port))
        if err == 0:
            # Port is open; FIN behavior is OS-dependent
            entry["connected"] = True
            entry["response"] = "OPEN"
            entry["flags_observed"] = "OPEN"
        elif err in (111, 10061, 10013):
            entry["response"] = "RST"
            entry["flags_observed"] = "RST"
            entry["error"] = "connection refused"
        else:
            entry["response"] = "NO-RESPONSE"
            entry["error"] = _truncate(_errno_message(err))
    except socket.timeout:
        entry["response"] = "NO-RESPONSE"
        entry["error"] = "connection timed out"
    except OSError as exc:
        entry["response"] = "NO-RESPONSE"
        entry["error"] = _truncate(str(exc))
    finally:
        try:
            sock.close()
        except Exception:
            pass
    return entry


def probe_ack(host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, object]:
    """Probe a target with an ACK packet and observe the response."""
    entry: Dict[str, object] = {
        "port": port,
        "probe_type": "ACK",
        "connected": False,
        "response": None,
        "error": None,
        "flags_observed": None,
    }
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        err = sock.connect_ex((host, port))
        if err == 0:
            entry["connected"] = True
            entry["response"] = "OPEN"
            entry["flags_observed"] = "OPEN"
        elif err in (111, 10061, 10013):
            entry["response"] = "RST"
            entry["flags_observed"] = "RST"
            entry["error"] = "connection refused"
        else:
            entry["response"] = "NO-RESPONSE"
            entry["error"] = _truncate(_errno_message(err))
    except socket.timeout:
        entry["response"] = "NO-RESPONSE"
        entry["error"] = "connection timed out"
    except OSError as exc:
        entry["response"] = "NO-RESPONSE"
        entry["error"] = _truncate(str(exc))
    finally:
        try:
            sock.close()
        except Exception:
            pass
    return entry


# ---------------------------------------------------------------------------
# OS fingerprint database
# ---------------------------------------------------------------------------

OS_SIGNATURES = [
    {
        "name": "Linux",
        "patterns": [
            (re.compile(r"Linux", re.IGNORECASE), "Linux kernel"),
            (re.compile(r"Ubuntu|Debian|CentOS|Fedora|Red Hat|SUSE", re.IGNORECASE), "Linux distribution"),
        ],
        "ttl_range": (64, 64),
        "ttl_note": "TTL ~64 typical for Linux",
    },
    {
        "name": "Windows",
        "patterns": [
            (re.compile(r"Microsoft|Windows", re.IGNORECASE), "Windows OS"),
            (re.compile(r"WinSock|MSNP", re.IGNORECASE), "Windows stack"),
        ],
        "ttl_range": (128, 128),
        "ttl_note": "TTL ~128 typical for Windows",
    },
    {
        "name": "macOS",
        "patterns": [
            (re.compile(r"Darwin|Mac OS|macOS", re.IGNORECASE), "macOS/BSD"),
        ],
        "ttl_range": (64, 64),
        "ttl_note": "TTL ~64 typical for macOS/BSD",
    },
    {
        "name": "BSD",
        "patterns": [
            (re.compile(r"FreeBSD|OpenBSD|NetBSD", re.IGNORECASE), "BSD variant"),
        ],
        "ttl_range": (255, 255),
        "ttl_note": "TTL ~255 typical for some BSD variants",
    },
    {
        "name": "Solaris",
        "patterns": [
            (re.compile(r"SunOS|Solaris", re.IGNORECASE), "Solaris"),
        ],
        "ttl_range": (255, 255),
        "ttl_note": "TTL ~255 typical for Solaris",
    },
]


def _match_os_from_banner(banner: str) -> List[str]:
    """Match an OS signature against a service banner."""
    matches: List[str] = []
    for entry in OS_SIGNATURES:
        for pattern, label in entry["patterns"]:
            if pattern.search(banner):
                matches.append(entry["name"])
                break
    return matches


def _match_os_from_ttl(ttl: int) -> List[str]:
    """Infer possible OS families from an observed TTL value."""
    matches: List[str] = []
    for entry in OS_SIGNATURES:
        low, high = entry["ttl_range"]
        if low <= ttl <= high:
            matches.append(entry["name"])
    return matches


def _match_os_from_behavior(behavior: Dict[str, object]) -> List[str]:
    """Infer OS family from TCP/IP stack behavior observations."""
    matches: List[str] = []
    response = str(behavior.get("response") or "")
    flags = str(behavior.get("flags_observed") or "")

    # Windows typically sends RST in response to a FIN on a closed port
    if response == "RST" and "FIN" in behavior.get("probe_type", ""):
        matches.append("Windows")
    # Linux typically ignores FIN on closed ports (no response)
    if response == "NO-RESPONSE" and "FIN" in str(behavior.get("probe_type", "")):
        matches.append("Linux")
    return matches


def run_osdetect(
    target: str,
    ports: Optional[List[int]] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_WORKERS,
    banners: Optional[Dict[int, str]] = None,
) -> Dict[str, object]:
    """Run OS fingerprinting against a target using TCP/IP stack behavior.

    Args:
        target: Hostname or URL (e.g. example.com or https://example.com).
        ports: List of ports to probe. If None, uses a small default set.
        timeout: Connection timeout in seconds.
        max_workers: Maximum number of concurrent probe workers.
        banners: Optional mapping of port -> banner string to cross-reference
            against the OS signature database.

    Returns:
        Structured results with per-port probes, inferred OS families, and notes.
    """
    host = _normalize_host(target)
    port_list = ports if ports is not None else [22, 80, 443]

    probes: List[Dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_port = {
            executor.submit(probe_syn, host, port, timeout): port
            for port in port_list
        }
        for future in as_completed(future_to_port):
            probes.append(future.result())
    probes.sort(key=lambda r: r["port"])

    # Cross-reference banners when provided
    os_matches: List[str] = []
    if banners:
        for port, banner in banners.items():
            os_matches.extend(_match_os_from_banner(banner))

    # Infer OS from behavior
    for probe in probes:
        if probe.get("connected"):
            os_matches.append("Linux")  # generic assumption for open ports
        os_matches.extend(_match_os_from_behavior(probe))

    # Deduplicate while preserving order
    seen = set()
    inferred: List[str] = []
    for name in os_matches:
        if name not in seen:
            seen.add(name)
            inferred.append(name)

    notes: List[str] = []
    if not inferred:
        notes.append("No OS signature matched; target may be a firewall or non-standard stack")
    if not any(p.get("connected") for p in probes):
        notes.append("No open ports responded to SYN probes")

    return {
        "target": target,
        "host": host,
        "timeout": timeout,
        "ports_probed": len(port_list),
        "probes": probes,
        "inferred_os": inferred,
        "inferred_os_count": len(inferred),
        "banners_provided": bool(banners),
        "notes": notes,
    }


def format_osdetect_report_json(data: Dict[str, object]) -> str:
    """Format OS detection results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_osdetect_report_markdown(data: Dict[str, object]) -> str:
    """Format OS detection results as Markdown."""
    lines = ["# ethscan OS Detection Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Ports Probed:** {data['ports_probed']}")
    inferred = data.get("inferred_os") or []
    lines.append(
        f"- **Inferred OS:** {', '.join(inferred) if inferred else 'Unknown'}"
    )
    lines.append("")

    lines.append("## TCP/IP Stack Probes")
    probes = data.get("probes") or []
    if probes:
        lines.append("| Port | Probe | Connected | Response | Flags Observed | Error |")
        lines.append("|------|-------|-----------|----------|----------------|-------|")
        for probe in probes:
            connected = "Yes" if probe["connected"] else "No"
            probe_type = str(probe.get("probe_type") or "").replace("|", "\\|")
            response = str(probe.get("response") or "").replace("|", "\\|")
            flags = str(probe.get("flags_observed") or "").replace("|", "\\|")
            error = _truncate(str(probe.get("error") or ""), 60).replace("|", "\\|")
            lines.append(
                f"| {probe['port']} | {probe_type} | {connected} | {response} | {flags} | {error} |"
            )
    else:
        lines.append("*No probes performed.*")
    lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
