"""Redis reconnaissance module for ethscan.

Offline-first Redis reconnaissance using only the Python standard library
(``socket``). The module performs:

* Basic connectivity test via ``PING`` command (RESP protocol).
* Server information gathering via ``INFO server`` (or full ``INFO`` if
  server-specific data is not isolated).
* Configuration inspection via ``CONFIG GET *`` to identify dangerous
  configurations (e.g., bind to 0.0.0.0, no requirepass/authentication
  enabled, writable ``dir``/``dbfilename`` paths that may indicate
  misconfiguration).

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw TCP socket so tests can substitute a local fake server.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import socket
from typing import Any

from ethscan.target import TargetSpecError, check_port, url_port

DEFAULT_PORT = 6379
DEFAULT_TIMEOUT = 3.0
DEFAULT_PROBES = ("ping", "info", "config")


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and port.

    Accepts ``host``, ``host:port``, and ``redis://host:port`` forms.
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
        # Handle [IPv6]:port format
        if host and host.startswith("[") and "]:" in host:
            bracket_end = host.find("]:")
            if bracket_end > 0:
                port_part = host[bracket_end + 2:]
                if port_part.isdigit():
                    host = host[1:bracket_end]
                    port = port or check_port(int(port_part))
                else:
                    host = host[1:-1] if host.endswith("]") else host
            elif host.endswith("]"):
                host = host[1:-1]
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

def _build_resp_array(*args: str) -> bytes:
    """Build a RESP array command.

    RESP: *<num>\r\n followed by bulk strings $<len>\r\n<data>\r\n for each arg.
    """
    parts: list[bytes] = []
    parts.append(("*" + str(len(args)) + "\r\n").encode("ascii"))
    for arg in args:
        b = arg.encode("utf-8") if isinstance(arg, str) else bytes(arg)
        parts.append(("$" + str(len(b)) + "\r\n").encode("ascii"))
        parts.append(b)
        parts.append(b"\r\n")
    return b"".join(parts)


def _parse_resp_simple_string(line: bytes) -> str:
    if line.startswith(b"+") and line.endswith(b"\r\n"):
        return line[1:-2].decode("utf-8", errors="replace")
    return line.decode("utf-8", errors="replace")


def _parse_resp_bulk_string(data: bytes) -> tuple[str | None, int]:
    """Parse a bulk string starting at data[0:].

    Returns (value, consumed_bytes). For null bulk string ($-1\r\n), returns (None, 5).
    """
    if not data.startswith(b"$"):
        return None, 0
    try:
        idx = data.find(b"\r\n")
        if idx == -1:
            return None, 0
        length_str = data[1:idx].decode("ascii")
        length = int(length_str)
        if length == -1:
            return None, idx + 2  # $-1\r\n
        start = idx + 2
        end = start + length
        if len(data) < end + 2:  # need trailing \r\n
            return None, 0  # incomplete
        value = data[start:end].decode("utf-8", errors="replace")
        return value, end + 2
    except (UnicodeDecodeError, ValueError):
        return None, 0


def _parse_resp(data: bytes) -> tuple[Any | None, int]:
    """Parse a RESP response starting from data.

    Returns (parsed_value, consumed_bytes). Handles simple strings (+), integers (:),
    bulk strings ($), and arrays (*). Errors return (None, 0).
    """
    if len(data) == 0:
        return None, 0
    if data[0:1] == b"+":
        idx = data.find(b"\r\n")
        if idx == -1:
            return None, 0
        return _parse_resp_simple_string(data[0 : idx + 2]), idx + 2
    if data[0:1] == b"-":
        idx = data.find(b"\r\n")
        if idx == -1:
            return None, 0
        return data[1:idx].decode("utf-8", errors="replace"), idx + 2
    if data[0:1] == b":":
        idx = data.find(b"\r\n")
        if idx == -1:
            return None, 0
        try:
            return int(data[1:idx]), idx + 2
        except ValueError:
            return data[1:idx].decode("utf-8", errors="replace"), idx + 2
    if data[0:1] == b"$":
        val, cons = _parse_resp_bulk_string(data)
        return val, cons
    if data[0:1] == b"*":
        try:
            idx = data.find(b"\r\n")
            if idx == -1:
                return None, 0
            count = int(data[1:idx])
            pos = idx + 2
            items: list[Any] = []
            for _ in range(count):
                if pos >= len(data):
                    return None, 0
                item, c = _parse_resp(data[pos:])
                if c == 0 and item is None and data[pos:pos+1] == b"$" and data[pos:pos+3] == b"$-1":
                    # null bulk string case - need to consume properly
                    pass  # try again
                if c == 0:
                    # try to handle null bulk string
                    if data[pos:pos+3] == b"$-1":
                        items.append(None)
                        pos += 5
                        continue
                    return None, 0
                items.append(item)
                pos += c
            return items, pos
        except ValueError:
            return None, 0
    return None, 0


def _send_recv(
    host: str,
    port: int,
    request: bytes,
    timeout: float,
    connector=None,
) -> tuple[bytes | None, str | None]:
    """Send a TCP request and receive the response (injectable for tests)."""
    if connector is not None:
        return connector(host, port, request, timeout)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.sendall(request)
        data = sock.recv(65536)
        return data, None
    except socket.timeout:
        return None, "timeout"
    except OSError as exc:
        return None, str(exc)
    finally:
        with contextlib.suppress(Exception):
            sock.close()


def _parse_info(data: bytes) -> dict[str, str]:
    """Parse Redis INFO response into a dict.

    INFO returns a bulk string with lines like "key:value\r\n".
    """
    info: dict[str, str] = {}
    with contextlib.suppress(Exception):
        resp, _ = _parse_resp(data)
        if isinstance(resp, str):
            text = resp
        else:
            text = str(resp) if resp is not None else ""
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
    return info


def _parse_config(data: bytes) -> dict[str, str]:
    """Parse CONFIG GET * response.

    Returns a dict of key->value from the array of bulk strings.
    """
    config: dict[str, str] = {}
    with contextlib.suppress(Exception):
        resp, _ = _parse_resp(data)
        if isinstance(resp, list) and len(resp) % 2 == 0:
            for i in range(0, len(resp), 2):
                k = resp[i]
                v = resp[i + 1]
                if k is not None:
                    config[str(k)] = "" if v is None else str(v)
    return config


def _assess_dangerous(config: dict[str, str]) -> list[str]:
    """Identify dangerous Redis configurations."""
    findings: list[str] = []
    bind = config.get("bind", "")
    if bind and ("0.0.0.0" in bind):
        findings.append("bind is set to 0.0.0.0 (exposed to network)")
    requirepass = config.get("requirepass", "")
    if not requirepass:
        findings.append("no authentication (requirepass not set)")
    dir_val = config.get("dir", "")
    if dir_val:
        findings.append(f"writable dir configured: {dir_val}")
    dbfilename = config.get("dbfilename", "")
    if dbfilename:
        findings.append(f"dbfilename configured: {dbfilename}")
    return findings


def run_redis(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    probes: list[str] | None = None,
    connector=None,
) -> dict[str, Any]:
    """Run Redis reconnaissance against *target*.

    Args:
        target: Hostname, ``host:port``, or URL.
        port: Explicit Redis port; when ``None`` the port is parsed from the
            target (or defaults to 6379).
        timeout: Per-request timeout in seconds.
        probes: List of probes to run ("ping", "info", "config"). Defaults to
            all three.
        connector: Callable for sending/receiving TCP data (for testing).

    Returns:
        Structured result dict consumed by the formatters below.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port

    probe_list = list(probes) if probes else list(DEFAULT_PROBES)

    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "ping": None,
        "info": {},
        "config": {},
        "dangerous_findings": [],
        "accessible": False,
        "error": None,
    }

    # Run PING first
    if "ping" in probe_list:
        ping_req = _build_resp_array("PING")
        ping_data, ping_err = _send_recv(host, server_port, ping_req, timeout, connector=connector)
        if ping_err:
            results["error"] = f"ping request failed: {ping_err}"
            return results
        ping_resp, _ = _parse_resp(ping_data)
        if isinstance(ping_resp, bytes):
            results["ping"] = ping_resp.decode("utf-8", errors="replace")
        elif isinstance(ping_resp, str):
            results["ping"] = ping_resp
        else:
            results["ping"] = str(ping_resp) if ping_resp is not None else None
        if results["ping"] and "PONG" not in str(results["ping"]).upper():
            # Still consider accessible if we got a response; but PONG is normal
            pass
        results["accessible"] = True

    # Run INFO server
    if "info" in probe_list:
        info_req = _build_resp_array("INFO", "server")
        info_data, info_err = _send_recv(host, server_port, info_req, timeout, connector=connector)
        if info_err:
            results["error"] = f"info request failed: {info_err}"
            return results
        parsed_info = _parse_info(info_data)
        if not parsed_info:
            # try full INFO
            info_req2 = _build_resp_array("INFO")
            info_data2, info_err2 = _send_recv(host, server_port, info_req2, timeout, connector=connector)
            if not info_err2:
                parsed_info = _parse_info(info_data2)
        results["info"] = parsed_info
        results["accessible"] = True

    # Run CONFIG GET *
    if "config" in probe_list:
        config_req = _build_resp_array("CONFIG", "GET", "*")
        config_data, config_err = _send_recv(host, server_port, config_req, timeout, connector=connector)
        if config_err:
            results["error"] = f"config request failed: {config_err}"
            return results
        parsed_config = _parse_config(config_data)
        results["config"] = parsed_config
        findings = _assess_dangerous(parsed_config)
        results["dangerous_findings"] = findings
        results["accessible"] = True

    return results


def format_redis_report_json(data: dict[str, Any]) -> str:
    """Format Redis reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_redis_report_markdown(data: dict[str, Any]) -> str:
    """Format Redis reconnaissance results as Markdown."""
    lines = ["# ethscan Redis Reconnaissance Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Host:** {data.get('host', '')}")
    lines.append(f"- **Port:** {data.get('port', DEFAULT_PORT)}")
    lines.append(f"- **Accessible:** {'Yes' if data.get('accessible') else 'No'}")
    if data.get("error"):
        lines.append(f"- **Error:** {data.get('error')}")
    lines.append("")

    if data.get("ping"):
        lines.append("## PING")
        lines.append(f"- **Response:** {data.get('ping')}")
        lines.append("")

    info = data.get("info") or {}
    if info:
        lines.append("## Server Info")
        # Extract common fields
        for key in ["redis_version", "os", "arch_bits", "arch", "process_id", "run_id",
                    "tcp_port", "uptime_in_seconds", "role", "connected_clients",
                    "used_memory_human", "used_memory_rss", "maxmemory_human",
                    "gcc_version", "server_mode"]:
            if key in info:
                label = key.replace("_", " ").title()
                lines.append(f"- **{label}:** {info[key]}")
        lines.append("")

    config = data.get("config") or {}
    if config:
        lines.append("## Configuration (selected)")
        # show key dangerous indicators
        for key in ["bind", "requirepass", "protected-mode", "dir", "dbfilename", "port",
                    "daemonize", "timeout"]:
            if key in config:
                lines.append(f"- **{key}:** {config[key]}")
        lines.append("")

    findings = data.get("dangerous_findings") or []
    if findings:
        lines.append("## Dangerous Findings")
        for finding in findings:
            lines.append(f"- {finding}")
        lines.append("")
    else:
        lines.append("## Dangerous Findings\n- None detected\n")

    return "\n".join(lines)


def format_redis_report_csv(data: dict[str, Any]) -> str:
    """Format Redis reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "host",
        "port",
        "accessible",
        "ping",
        "redis_version",
        "os",
        "role",
        "connected_clients",
        "bind",
        "requirepass_set",
        "dangerous_findings",
        "error",
    ])

    info = data.get("info") or {}
    config = data.get("config") or {}
    findings = data.get("dangerous_findings") or []
    requirepass = config.get("requirepass", "")
    requirepass_set = "true" if requirepass else "false"

    writer.writerow([
        data.get("target", ""),
        data.get("host", ""),
        data.get("port", DEFAULT_PORT),
        "true" if data.get("accessible") else "false",
        data.get("ping") or "",
        info.get("redis_version", ""),
        info.get("os", ""),
        info.get("role", ""),
        info.get("connected_clients", ""),
        config.get("bind", ""),
        requirepass_set,
        "; ".join(findings).replace("\n", " ").replace("\r", " "),
        data.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")
