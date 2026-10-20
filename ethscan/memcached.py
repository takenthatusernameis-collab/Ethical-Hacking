"""Memcached reconnaissance module for ethscan.

Offline-first Memcached reconnaissance using only the Python standard
library (``socket``). The module performs two safe, bounded probes over
the Memcached text protocol (TCP 11211):

* **version** -- send ``version\\r\\n`` and parse the ``VERSION <x.y.z>``
  response, which identifies the server build.
* **stats** -- send ``stats\\r\\n`` and parse the ``STAT`` lines into a
  structured map (uptime, bytes, connections, command counters, hits /
  misses, evictions, etc.).

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

DEFAULT_PORT = 11211
DEFAULT_TIMEOUT = 3.0
DEFAULT_PROBES = ("version", "stats")


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and integer port.

    Accepts bare hosts (``192.168.1.5``), ``host:port``, and
    ``memcached://host:port`` URLs. Defaults to port ``DEFAULT_PORT``
    when none is supplied. IPv6 literals may be bracketed.
    """
    normalized = (target or "").strip()
    host: str | None = None
    port: int | None = None

    if "://" in normalized:
        from urllib.parse import urlparse

        parsed = urlparse(normalized)
        host = (parsed.hostname or "").strip()
        port = url_port(parsed)
        (parsed.scheme or "").lower()
    else:
        host = normalized
        # IPv6 literal in brackets, optionally followed by :port.
        if host and host.startswith("["):
            close = host.find("]")
            if close > 0:
                maybe_port = host[close + 1:]
                if maybe_port.startswith(":") and maybe_port[1:].isdigit():
                    port = port or int(maybe_port[1:])
                host = host[1:close]
        elif host and ":" in host and "]" not in host:
            base, _, rest = host.rpartition(":")
            if rest.isdigit():
                host = base
                port = port or check_port(int(rest))

    if not host:
        raise TargetSpecError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


def _build_memcached_request(command: str) -> bytes:
    """Build a Memcached text-protocol command with CRLF terminator."""
    return command.rstrip("\r\n").encode("utf-8") + b"\r\n"


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


def _parse_version_response(data: bytes | None) -> str | None:
    """Parse a ``VERSION <x.y.z>\\r\\n`` response into the version string."""
    if not data:
        return None
    text = data.decode("utf-8", errors="replace")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("VERSION "):
            return line[len("VERSION "):].strip()
        if line.startswith("VERSION\t"):
            return line[len("VERSION\t"):].strip()
        # tolerate a bare version token on its own line
        if line and line[0].isdigit():
            return line
    return None


def _parse_stats_response(data: bytes | None) -> dict[str, str]:
    """Parse a Memcached ``stats`` response into a dict of STAT lines.

    The response is a sequence of ``STAT <key> <value>`` lines terminated
    by ``END\\r\\n``. Only ``STAT`` lines are parsed; ``END`` and any
    other framing lines are ignored.
    """
    stats: dict[str, str] = {}
    if not data:
        return stats
    text = data.decode("utf-8", errors="replace")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "END":
            break
        if line.startswith("STAT "):
            body = line[len("STAT "):]
            parts = body.split(None, 1)
            if len(parts) == 2:
                stats[parts[0].strip()] = parts[1].strip()
            elif len(parts) == 1:
                stats[parts[0].strip()] = ""
        elif line.startswith("STAT\t"):
            body = line[len("STAT\t"):]
            parts = body.split(None, 1)
            if len(parts) == 2:
                stats[parts[0].strip()] = parts[1].strip()
            elif len(parts) == 1:
                stats[parts[0].strip()] = ""
    return stats


def _coerce_int(value: str) -> int | None:
    """Best-effort integer coercion for stats values."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _assess_stats(stats: dict[str, str]) -> list[str]:
    """Identify noteworthy conditions from the parsed stats map."""
    findings: list[str] = []
    if not stats:
        return findings
    if _coerce_int(stats.get("pid", "")) == 0:
        findings.append("server reports pid 0")
    if _coerce_int(stats.get("uptime", "")) == 0:
        findings.append("server uptime is 0")
    if _coerce_int(stats.get("bytes", "")) == 0:
        findings.append("server reports 0 bytes")
    if _coerce_int(stats.get("limit_maxbytes", "")) == 0:
        findings.append("limit_maxbytes is 0 (unbounded cache)")
    if _coerce_int(stats.get("accepting_conns", "")) == 0:
        findings.append("server is not currently accepting connections")
    evictions = _coerce_int(stats.get("evictions", ""))
    if evictions is not None and evictions > 0:
        findings.append("evictions are occurring (cache pressure)")
    get_hits = _coerce_int(stats.get("get_hits", ""))
    get_misses = _coerce_int(stats.get("get_misses", ""))
    if get_hits == 0 and get_misses is not None and get_misses > 0:
        findings.append("no cache hits recorded")
    return findings


def _build_banner(results: dict[str, Any]) -> str | None:
    """Build a short human-readable banner from the probe results."""
    if not results.get("accessible"):
        return None
    parts: list[str] = []
    version = results.get("version")
    if version:
        parts.append(f"memcached {version}")
    stats = results.get("stats") or {}
    if stats:
        uptime = _coerce_int(stats.get("uptime", ""))
        if uptime is not None:
            parts.append(f"uptime={uptime}s")
        bytes_val = _coerce_int(stats.get("bytes", ""))
        if bytes_val is not None:
            parts.append(f"bytes={bytes_val}")
        curr = _coerce_int(stats.get("curr_connections", ""))
        if curr is not None:
            parts.append(f"curr_connections={curr}")
    return "; ".join(parts) if parts else "memcached"


def run_memcached(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    probes: list[str] | None = None,
    connector=None,
) -> dict[str, Any]:
    """Run Memcached reconnaissance against *target*.

    Args:
        target: Hostname, ``host:port``, or ``memcached://`` URL.
        port: Explicit Memcached port; when ``None`` the port is parsed from
            the target (or defaults to 11211).
        timeout: Per-request timeout in seconds.
        probes: List of probes to run ("version", "stats"). Defaults to both.
        connector: Callable for sending/receiving TCP data (for testing).

    Returns:
        Structured result dict consumed by the formatters below.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port

    probe_list = (
        [p.strip().lower() for p in probes if p.strip()]
        if probes is not None
        else list(DEFAULT_PROBES)
    )

    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "version": None,
        "stats": {},
        "findings": [],
        "accessible": False,
        "error": None,
    }

    # Probe 1: version
    if "version" in probe_list:
        req = _build_memcached_request("version")
        data, err = _send_recv(host, server_port, req, timeout, connector=connector)
        if err:
            results["error"] = f"version request failed: {err}"
            return results
        if not data:
            results["error"] = "version request failed: no response"
            return results
        parsed_version = _parse_version_response(data)
        results["version"] = parsed_version
        results["accessible"] = True

    # Probe 2: stats
    if "stats" in probe_list:
        req = _build_memcached_request("stats")
        data, err = _send_recv(host, server_port, req, timeout, connector=connector)
        if err:
            results["error"] = f"stats request failed: {err}"
            return results
        if not data:
            results["error"] = "stats request failed: no response"
            return results
        parsed_stats = _parse_stats_response(data)
        results["stats"] = parsed_stats
        results["findings"] = _assess_stats(parsed_stats)
        results["accessible"] = True

    return results


def format_memcached_report_json(data: dict[str, Any]) -> str:
    """Format Memcached reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_memcached_report_markdown(data: dict[str, Any]) -> str:
    """Format Memcached reconnaissance results as Markdown."""
    lines = ["# ethscan Memcached Reconnaissance Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Host:** {data.get('host', '')}")
    lines.append(f"- **Port:** {data.get('port', DEFAULT_PORT)}")
    lines.append(f"- **Accessible:** {'Yes' if data.get('accessible') else 'No'}")
    if data.get("error"):
        lines.append(f"- **Error:** {data.get('error')}")
    lines.append("")

    if data.get("version"):
        lines.append("## Version")
        lines.append(f"- **Memcached Version:** {data.get('version')}")
        lines.append("")

    stats = data.get("stats") or {}
    if stats:
        lines.append("## Stats")
        # Show the most interesting fields first, then the rest.
        primary_keys = [
            "pid", "uptime", "time", "version", "bytes", "limit_maxbytes",
            "curr_connections", "total_connections", "accepting_conns",
            "cmd_get", "cmd_set", "get_hits", "get_misses", "evictions",
            "bytes_read", "bytes_written", "connection_structures",
        ]
        shown: dict[str, str] = {}
        others: dict[str, str] = {}
        for key, value in stats.items():
            if key in primary_keys:
                shown[key] = value
            else:
                others[key] = value

        if shown:
            lines.append("| Stat | Value |")
            lines.append("|------|-------|")
            for key in primary_keys:
                if key in shown:
                    lines.append(f"| {key} | {_markdown_escape(shown[key])} |")
            lines.append("")

        if others:
            lines.append("### Other Stats")
            lines.append("| Stat | Value |")
            lines.append("|------|-------|")
            for key in sorted(others):
                lines.append(f"| {key} | {_markdown_escape(others[key])} |")
            lines.append("")
    elif data.get("error") is None:
        lines.append("## Stats")
        lines.append("- No stats collected.")
        lines.append("")

    findings = data.get("findings") or []
    if findings:
        lines.append("## Findings")
        for finding in findings:
            lines.append(f"- {finding}")
        lines.append("")
    else:
        lines.append("## Findings\n- None detected\n")

    return "\n".join(lines)


def format_memcached_report_csv(data: dict[str, Any]) -> str:
    """Format Memcached reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "host",
        "port",
        "accessible",
        "version",
        "uptime",
        "bytes",
        "curr_connections",
        "cmd_get",
        "cmd_set",
        "get_hits",
        "get_misses",
        "evictions",
        "findings",
        "error",
    ])

    stats = data.get("stats") or {}
    findings = data.get("findings") or []
    writer.writerow([
        data.get("target", ""),
        data.get("host", ""),
        data.get("port", DEFAULT_PORT),
        "true" if data.get("accessible") else "false",
        data.get("version") or "",
        stats.get("uptime", ""),
        stats.get("bytes", ""),
        stats.get("curr_connections", ""),
        stats.get("cmd_get", ""),
        stats.get("cmd_set", ""),
        stats.get("get_hits", ""),
        stats.get("get_misses", ""),
        stats.get("evictions", ""),
        "; ".join(findings).replace("\n", " ").replace("\r", " "),
        data.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")


__all__ = [
    "DEFAULT_PORT",
    "DEFAULT_PROBES",
    "DEFAULT_TIMEOUT",
    "TargetSpecError",
    "_assess_stats",
    "_build_memcached_request",
    "_coerce_int",
    "_normalize_target",
    "_parse_stats_response",
    "_parse_version_response",
    "_send_recv",
    "format_memcached_report_csv",
    "format_memcached_report_json",
    "format_memcached_report_markdown",
    "run_memcached",
]