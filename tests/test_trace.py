"""Tests for the trace module."""
import json
from unittest.mock import patch, MagicMock

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


def test_extract_hop_ips():
    hops = [
        {"hop": 1, "ip": "1.1.1.1", "reached_destination": False},
        {"hop": 2, "ip": "2.2.2.2", "reached_destination": False},
        {"hop": 3, "ip": "3.3.3.3", "reached_destination": True},
    ]
    ips = trace._extract_hop_ips(hops)
    assert set(ips) == {"1.1.1.1", "2.2.2.2"}


def test_extract_hop_ips_empty():
    assert trace._extract_hop_ips([]) == []
    assert trace._extract_hop_ips([{"hop": 1, "ip": "1.1.1.1", "reached_destination": True}]) == []


def test_run_trace_recursive_disabled_by_default():
    """Test that recursive is disabled by default."""
    with patch.object(trace, "_trace_single") as mock_trace:
        mock_trace.return_value = {
            "target": "example.com",
            "dst_ip": "93.184.215.14",
            "destination_reached": True,
            "hops": [{"hop": 1, "ip": "1.1.1.1", "reached_destination": False}],
        }
        res = trace.run_trace("example.com", recursive=False)
        assert res.get("recursive") is not True


def test_run_trace_recursive_enabled():
    """Test recursive tracing with successful main trace and one hop."""
    with patch.object(trace, "_trace_single") as mock_trace:
        # Main trace result
        main_result = {
            "target": "example.com",
            "dst_ip": "93.184.215.14",
            "destination_reached": True,
            "hops": [
                {"hop": 1, "ip": "1.1.1.1", "reached_destination": False},
                {"hop": 2, "ip": "93.184.215.14", "reached_destination": True},
            ],
            "port": 80,
            "max_hops": 30,
            "timeout": 3.0,
            "probes_per_hop": 3,
        }
        # Recursive trace result for 1.1.1.1
        recursive_result = {
            "target": "1.1.1.1",
            "dst_ip": "1.1.1.1",
            "destination_reached": True,
            "hops": [
                {"hop": 1, "ip": "10.0.0.1", "reached_destination": False},
                {"hop": 2, "ip": "1.1.1.1", "reached_destination": True},
            ],
            "port": 80,
            "max_hops": 30,
            "timeout": 3.0,
            "probes_per_hop": 3,
        }
        # Second level recursive trace result for 10.0.0.1 (depth 2)
        recursive_result_2 = {
            "target": "10.0.0.1",
            "dst_ip": "10.0.0.1",
            "destination_reached": True,
            "hops": [
                {"hop": 1, "ip": "192.168.1.1", "reached_destination": False},
                {"hop": 2, "ip": "10.0.0.1", "reached_destination": True},
            ],
            "port": 80,
            "max_hops": 30,
            "timeout": 3.0,
            "probes_per_hop": 3,
        }
        mock_trace.side_effect = [main_result, recursive_result, recursive_result_2]

        res = trace.run_trace("example.com", recursive=True, max_depth=2)

        assert res.get("recursive") is True
        assert res.get("max_depth") == 2
        assert "recursive_traces" in res
        # Should have traces for 1.1.1.1 and 10.0.0.1 (2 traces total)
        assert len(res["recursive_traces"]) == 2
        assert res["recursive_traces"][0]["target"] == "1.1.1.1"
        assert res["recursive_traces"][1]["target"] == "10.0.0.1"


def test_run_trace_recursive_respects_max_depth():
    """Test that recursive tracing stops at max_depth."""
    with patch.object(trace, "_trace_single") as mock_trace:
        main_result = {
            "target": "example.com",
            "dst_ip": "93.184.215.14",
            "destination_reached": True,
            "hops": [{"hop": 1, "ip": "1.1.1.1", "reached_destination": False}],
            "port": 80,
            "max_hops": 30,
            "timeout": 3.0,
            "probes_per_hop": 3,
        }
        recursive_result = {
            "target": "1.1.1.1",
            "dst_ip": "1.1.1.1",
            "destination_reached": True,
            "hops": [{"hop": 1, "ip": "10.0.0.1", "reached_destination": False}],
            "port": 80,
            "max_hops": 30,
            "timeout": 3.0,
            "probes_per_hop": 3,
        }
        # Max depth 1 means only one level of recursion
        mock_trace.side_effect = [main_result, recursive_result]

        res = trace.run_trace("example.com", recursive=True, max_depth=1)

        # Should only trace the first hop, not the second hop's hops
        assert len(res["recursive_traces"]) == 1


def test_run_trace_recursive_stops_when_no_intermediate_hops():
    """Test recursive tracing stops when no intermediate hops found."""
    with patch.object(trace, "_trace_single") as mock_trace:
        main_result = {
            "target": "example.com",
            "dst_ip": "93.184.215.14",
            "destination_reached": True,
            "hops": [{"hop": 1, "ip": "93.184.215.14", "reached_destination": True}],  # Direct connection
            "port": 80,
            "max_hops": 30,
            "timeout": 3.0,
            "probes_per_hop": 3,
        }
        mock_trace.return_value = main_result

        res = trace.run_trace("example.com", recursive=True, max_depth=2)

        assert res.get("recursive") is True
        assert len(res.get("recursive_traces", [])) == 0


def test_format_trace_report_markdown_recursive():
    """Test markdown formatter includes recursive traces section."""
    result = {
        "target": "example.com",
        "dst_ip": "93.184.215.14",
        "port": 80,
        "max_hops": 30,
        "timeout": 3.0,
        "probes_per_hop": 3,
        "recursive": True,
        "max_depth": 2,
        "hops": [
            {"hop": 1, "ip": "1.1.1.1", "rtt_ms": 5.0, "reached_destination": False},
            {"hop": 2, "ip": "93.184.215.14", "rtt_ms": 10.0, "reached_destination": True},
        ],
        "recursive_traces": [
            {
                "target": "1.1.1.1",
                "dst_ip": "1.1.1.1",
                "port": 80,
                "max_hops": 30,
                "timeout": 3.0,
                "probes_per_hop": 3,
                "hops": [
                    {"hop": 1, "ip": "10.0.0.1", "rtt_ms": 2.0, "reached_destination": False},
                    {"hop": 2, "ip": "1.1.1.1", "rtt_ms": 3.0, "reached_destination": True},
                ],
                "destination_reached": True,
            }
        ],
        "notes": ["Recursive tracing completed"],
    }
    md = trace.format_trace_report_markdown(result)
    assert "Recursive Traces" in md
    assert "Recursive Trace 1" in md
    assert "1.1.1.1" in md
    assert "10.0.0.1" in md
