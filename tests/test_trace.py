"""Tests for the trace module."""
import json

from ethscan import trace


def test_normalize_host():
    assert trace._normalize_host("example.com") == "example.com"
    assert trace._normalize_host("https://example.com") == "example.com"
    assert trace._normalize_host("http://example.com/") == "example.com"
    assert trace._normalize_host("example.com:80") == "example.com"


def test_formatters():
    result = {
        "target": "example.com",
        "dst_ip": "93.184.215.14",
        "port": 80,
        "max_hops": 30,
        "timeout": 2.0,
        "probes_per_hop": 3,
        "hops": [
            {"hop": 1, "ip": "1.1.1.1", "rtt_ms": 5.0, "reached": False},
            {"hop": 2, "ip": "93.184.215.14", "rtt_ms": 10.0, "reached": True},
        ],
        "reached": True,
    }
    js = trace.format_trace_report_json(result)
    assert json.loads(js)["target"] == "example.com"
    md = trace.format_trace_report_markdown(result)
    assert "example.com" in md
    assert "Hop" in md


def test_run_trace_localhost():
    res = trace.run_trace("127.0.0.1", port=80, max_hops=3, timeout=1.0, probes_per_hop=1)
    assert res["target"] == "127.0.0.1"
    assert isinstance(res["hops"], list)
