"""TCP traceroute using TTL-incremented probes (stdlib-only)."""
from __future__ import annotations

import contextlib
import csv
import io
import json
import socket
import time
from typing import Any

DEFAULT_PORT = 80
DEFAULT_MAX_HOPS = 30
DEFAULT_TIMEOUT = 2.0
DEFAULT_PROBES_PER_HOP = 3
DEFAULT_MAX_DEPTH = 2

__all__ = [
    "format_trace_report_json",
    "format_trace_report_markdown",
    "run_trace",
]


def _normalize_host(target: str) -> str:
    t = (target or "").strip()
    if t.startswith("http://"):
        t = t[7:]
    elif t.startswith("https://"):
        t = t[8:]
    if "/" in t:
        t = t.split("/", 1)[0]
    if ":" in t and not t.startswith("["):
        parts = t.rsplit(":", 1)
        if parts[0] and parts[1].isdigit():
            t = parts[0]
    return t


def _fmt_rtt(rtt_ms: float | None) -> str:
    if rtt_ms is None:
        return "N/A"
    return f"{rtt_ms:.2f}ms"


def _probe_once(dst_ip: str, port: int, ttl: int, timeout: float) -> dict[str, Any]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except Exception as e:
        return {"hop_ip": None, "rtt_ms": None, "reached": False, "error": str(e)}

    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        sock.settimeout(timeout)
        start = time.time()
        sock.connect((dst_ip, port))
        end = time.time()
        rtt_ms = (end - start) * 1000.0
        return {"hop_ip": dst_ip, "rtt_ms": rtt_ms, "reached": True, "error": None}
    except socket.timeout:
        return {"hop_ip": None, "rtt_ms": None, "reached": False, "error": None}
    except OSError:
        return {"hop_ip": None, "rtt_ms": None, "reached": False, "error": None}
    finally:
        with contextlib.suppress(Exception):
            sock.close()


def _trace_single(
    target: str,
    port: int,
    max_hops: int,
    timeout: float,
    probes_per_hop: int,
) -> dict[str, Any]:
    """Trace a single target and return the result."""
    host = _normalize_host(target)
    if not host:
        raise ValueError("Invalid target")

    try:
        dst_ip = socket.gethostbyname(host)
    except Exception as e:
        return {
            "target": host,
            "host": host,
            "ip": None,
            "dst_ip": None,
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "reached_destination": False,
            "reached": False,
            "error": str(e),
            "notes": ["Raw ICMP socket unavailable; connect-only fallback mode"],
        }

    hops: list[dict[str, Any]] = []
    reached = False
    for ttl in range(1, max_hops + 1):
        rtt_list: list[float] = []
        hop_ip = None
        reached_hop = False
        probes_done = 0
        probe_results = []
        for probes_done in range(1, max(1, probes_per_hop) + 1):
            res = _probe_once(dst_ip, port, ttl, timeout)
            if res.get("error"):
                hop_obj = {
                    "hop": ttl,
                    "ttl": ttl,
                    "ip": None,
                    "host": "*",
                    "response_type": "ERROR",
                    "rtt_ms": None,
                    "rtt_avg_ms": None,
                    "probes": probe_results,
                    "reached_destination": False,
                    "reached": False,
                    "error_code": res.get("error"),
                }
                hops.append(hop_obj)
                return {
                    "target": host,
                    "host": host,
                    "ip": dst_ip,
                    "dst_ip": dst_ip,
                    "port": port,
                    "max_hops": max_hops,
                    "timeout": timeout,
                    "probes_per_hop": probes_per_hop,
                    "raw_socket_available": False,
                    "hops": hops,
                    "hop_count": len(hops),
                    "destination_reached": False,
                    "reached_destination": False,
                    "reached": False,
                    "error": res.get("error"),
                    "notes": ["Raw ICMP socket unavailable; connect-only fallback mode"],
                }
            probe_rtt = res["rtt_ms"]
            probe_ip = res["hop_ip"]
            probe_results.append({
                "hop": ttl,
                "ttl": ttl,
                "ip": probe_ip,
                "host": probe_ip or "*",
                "response_type": "ICMP_TTL_EXCEEDED" if not res["reached"] else "REACHED",
                "rtt_ms": round(probe_rtt, 2) if probe_rtt is not None else None,
                "reached_destination": bool(res["reached"]),
                "error_code": None,
            })
            if res["reached"]:
                hop_ip = res["hop_ip"]
                if res["rtt_ms"] is not None:
                    rtt_list.append(res["rtt_ms"])
                reached_hop = True
                break
            if res["hop_ip"]:
                hop_ip = res["hop_ip"]
            if res["rtt_ms"] is not None:
                rtt_list.append(res["rtt_ms"])
        rtt_avg = sum(rtt_list) / len(rtt_list) if rtt_list else None
        hop_obj = {
            "hop": ttl,
            "ttl": ttl,
            "ip": hop_ip,
            "host": hop_ip or "*",
            "response_type": "REACHED" if reached_hop else ("NO-RESPONSE" if not rtt_list else "ICMP_TTL_EXCEEDED"),
            "rtt_ms": round(rtt_avg, 2) if rtt_avg is not None else None,
            "rtt_avg_ms": round(rtt_avg, 2) if rtt_avg is not None else None,
            "probes": probe_results,
            "reached_destination": reached_hop,
            "reached": reached_hop,
            "error_code": None,
        }
        hops.append(hop_obj)
        if reached_hop:
            reached = True
            break

    return {
        "target": host,
        "host": host,
        "ip": dst_ip,
        "dst_ip": dst_ip,
        "port": port,
        "max_hops": max_hops,
        "timeout": timeout,
        "probes_per_hop": probes_per_hop,
        "raw_socket_available": False,
        "hops": hops,
        "hop_count": len(hops),
        "destination_reached": reached,
        "reached_destination": reached,
        "reached": reached,
        "notes": ["Raw ICMP socket unavailable; connect-only fallback mode"],
    }


def _extract_hop_ips(hops: list[dict[str, Any]]) -> list[str]:
    """Extract unique hop IPs from trace results (excluding the destination)."""
    ips: set[str] = set()
    for hop in hops:
        ip = hop.get("ip")
        if ip and not hop.get("reached_destination", False):
            ips.add(ip)
    return list(ips)


def run_trace(
    target: str,
    port: int = DEFAULT_PORT,
    max_hops: int = DEFAULT_MAX_HOPS,
    timeout: float = DEFAULT_TIMEOUT,
    probes_per_hop: int = DEFAULT_PROBES_PER_HOP,
    raw_socket=None,
    recursive: bool = False,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> dict[str, Any]:
    """Run TCP traceroute, optionally recursively tracing intermediate hops."""
    # First, trace the main target
    main_result = _trace_single(target, port, max_hops, timeout, probes_per_hop)

    # If not recursive or destination not reached, return the main result
    if not recursive or not main_result.get("destination_reached", False):
        if recursive:
            main_result.setdefault("notes", []).append("Recursive tracing enabled but destination not reached")
        return main_result

    # Extract intermediate hop IPs
    hop_ips = _extract_hop_ips(main_result.get("hops", []))
    if not hop_ips:
        main_result.setdefault("notes", []).append("Recursive tracing enabled but no intermediate hops found")
        main_result["recursive"] = True
        main_result["max_depth"] = max_depth
        main_result["recursive_traces"] = []
        return main_result

    # Recursively trace each hop IP up to max_depth
    recursive_results: list[dict[str, Any]] = []
    seen_targets: set[str] = {main_result.get("target", "").lower()}

    def _recursive_trace(targets: list[str], depth: int) -> None:
        if depth > max_depth or not targets:
            return
        next_targets: list[str] = []
        for t in targets:
            t_lower = t.lower()
            if t_lower in seen_targets:
                continue
            seen_targets.add(t_lower)
            res = _trace_single(t, port, max_hops, timeout, probes_per_hop)
            recursive_results.append(res)
            if res.get("destination_reached", False):
                next_targets.extend(_extract_hop_ips(res.get("hops", [])))
        if next_targets:
            _recursive_trace(next_targets, depth + 1)

    _recursive_trace(hop_ips, 1)

    # Combine results
    main_result["recursive"] = True
    main_result["max_depth"] = max_depth
    main_result["recursive_traces"] = recursive_results
    main_result.setdefault("notes", []).append(f"Recursive tracing completed for {len(recursive_results)} intermediate hops (max depth: {max_depth})")

    return main_result


def format_trace_report_json(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2)


def format_trace_report_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# TCP Traceroute Report")
    lines.append("")
    lines.append(f"**Target:** {result.get('target', result.get('host', 'N/A'))}")
    ip = result.get('dst_ip') or result.get('ip')
    if ip:
        lines.append(f"**Destination IP:** {ip}")
    lines.append(f"**Port:** {result.get('port', DEFAULT_PORT)}")
    lines.append(f"**Max Hops:** {result.get('max_hops', DEFAULT_MAX_HOPS)}")
    lines.append(f"**Timeout:** {result.get('timeout', DEFAULT_TIMEOUT)}s")
    lines.append(f"**Probes per Hop:** {result.get('probes_per_hop', DEFAULT_PROBES_PER_HOP)}")
    if result.get("recursive"):
        lines.append(f"**Recursive:** Yes (max depth: {result.get('max_depth', DEFAULT_MAX_DEPTH)})")
    if result.get("error"):
        lines.append(f"**Error:** {result.get('error')}")
    if result.get("notes"):
        for n in result.get("notes"):
            lines.append(f"**Note:** {n}")
    lines.append("")

    hops = result.get("hops", []) or []
    if hops:
        lines.append("## Hop Table")
        lines.append("")
        lines.append("| Hop | IP | Host | Response | RTT (avg) | Reached |")
        lines.append("|---|-----|------|----------|-----------|---------|")
        for h in hops:
            hop_no = h.get("hop", h.get("ttl", "?"))
            ip = h.get("ip") or "*"
            host = h.get("host") or ip or "*"
            resp = h.get("response_type") or ("REACHED" if h.get("reached") else "NO-RESPONSE")
            rtt = _fmt_rtt(h.get("rtt_avg_ms") or h.get("rtt_ms"))
            reached = "Yes" if (h.get("reached_destination") or h.get("reached")) else "No"
            lines.append(f"| {hop_no} | {ip} | {host} | {resp} | {rtt} | {reached} |")
    else:
        lines.append("No hops recorded.")
    lines.append("")
    reached = result.get("destination_reached") or result.get("reached_destination") or result.get("reached")
    lines.append(f"**Reached target:** {'Yes' if reached else 'No'}")

    # Add recursive trace sections
    recursive_traces = result.get("recursive_traces", [])
    if recursive_traces:
        lines.append("")
        lines.append("## Recursive Traces")
        lines.append("")
        for i, trace_res in enumerate(recursive_traces):
            lines.append(f"### Recursive Trace {i + 1}: {trace_res.get('target', 'N/A')}")
            lines.append("")
            trace_ip = trace_res.get('dst_ip') or trace_res.get('ip')
            if trace_ip:
                lines.append(f"**Destination IP:** {trace_ip}")
            lines.append(f"**Port:** {trace_res.get('port', DEFAULT_PORT)}")
            lines.append(f"**Max Hops:** {trace_res.get('max_hops', DEFAULT_MAX_HOPS)}")
            lines.append(f"**Timeout:** {trace_res.get('timeout', DEFAULT_TIMEOUT)}s")
            lines.append(f"**Probes per Hop:** {trace_res.get('probes_per_hop', DEFAULT_PROBES_PER_HOP)}")
            if trace_res.get("error"):
                lines.append(f"**Error:** {trace_res.get('error')}")
            if trace_res.get("notes"):
                for n in trace_res.get("notes"):
                    lines.append(f"**Note:** {n}")
            lines.append("")
            trace_hops = trace_res.get("hops", []) or []
            if trace_hops:
                lines.append("#### Hop Table")
                lines.append("")
                lines.append("| Hop | IP | Host | Response | RTT (avg) | Reached |")
                lines.append("|---|-----|------|----------|-----------|---------|")
                for h in trace_hops:
                    hop_no = h.get("hop", h.get("ttl", "?"))
                    ip = h.get("ip") or "*"
                    host = h.get("host") or ip or "*"
                    resp = h.get("response_type") or ("REACHED" if h.get("reached") else "NO-RESPONSE")
                    rtt = _fmt_rtt(h.get("rtt_avg_ms") or h.get("rtt_ms"))
                    reached = "Yes" if (h.get("reached_destination") or h.get("reached")) else "No"
                    lines.append(f"| {hop_no} | {ip} | {host} | {resp} | {rtt} | {reached} |")
            else:
                lines.append("No hops recorded.")
            lines.append("")
            trace_reached = trace_res.get("destination_reached") or trace_res.get("reached_destination") or trace_res.get("reached")
            lines.append(f"**Reached target:** {'Yes' if trace_reached else 'No'}")
            lines.append("")

    return "\n".join(lines)


def format_trace_report_csv(result: dict[str, Any]) -> str:
    """Format trace results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "hop",
        "ip",
        "host",
        "response_type",
        "rtt_ms",
        "reached_destination",
    ])

    def _write_hops(target: Any, hops: list[dict[str, Any]]) -> None:
        for hop in hops:
            hop_no = hop.get("hop", hop.get("ttl", ""))
            rtt = hop.get("rtt_avg_ms")
            if rtt is None:
                rtt = hop.get("rtt_ms")
            writer.writerow([
                target,
                hop_no,
                hop.get("ip") or "",
                hop.get("host") or "",
                hop.get("response_type") or "",
                rtt if rtt is not None else "",
                "true" if (hop.get("reached_destination") or hop.get("reached")) else "false",
            ])

    _write_hops(result.get("target", ""), result.get("hops") or [])
    for trace_res in result.get("recursive_traces", []) or []:
        _write_hops(trace_res.get("target", ""), trace_res.get("hops") or [])
    return output.getvalue().rstrip("\r\n")
