"""TCP traceroute using TTL-incremented probes (stdlib-only)."""
from __future__ import annotations

import json
import socket
import time
from typing import Any, Dict, List, Optional

DEFAULT_PORT = 80
DEFAULT_MAX_HOPS = 30
DEFAULT_TIMEOUT = 2.0
DEFAULT_PROBES_PER_HOP = 3

__all__ = [
    "run_trace",
    "format_trace_report_json",
    "format_trace_report_markdown",
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


def _fmt_rtt(rtt_ms: Optional[float]) -> str:
    if rtt_ms is None:
        return "N/A"
    return f"{rtt_ms:.2f}ms"


def _probe_once(dst_ip: str, port: int, ttl: int, timeout: float) -> Dict[str, Any]:
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
    except socket.error:
        return {"hop_ip": None, "rtt_ms": None, "reached": False, "error": None}
    finally:
        try:
            sock.close()
        except Exception:
            pass


def run_trace(
    target: str,
    port: int = DEFAULT_PORT,
    max_hops: int = DEFAULT_MAX_HOPS,
    timeout: float = DEFAULT_TIMEOUT,
    probes_per_hop: int = DEFAULT_PROBES_PER_HOP,
    raw_socket=None,
) -> Dict[str, Any]:
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

    hops: List[Dict[str, Any]] = []
    reached = False
    for ttl in range(1, max_hops + 1):
        rtt_list: List[float] = []
        hop_ip = None
        reached_hop = False
        probes_done = 0
        probe_results = []
        for _ in range(max(1, probes_per_hop)):
            probes_done += 1
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


def format_trace_report_json(result: Dict[str, Any]) -> str:
    return json.dumps(result, indent=2)


def format_trace_report_markdown(result: Dict[str, Any]) -> str:
    lines: List[str] = []
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
    return "\n".join(lines)
