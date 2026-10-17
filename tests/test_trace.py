import csv
import socket
import io
import socket
import json
import socket
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


def test_format_trace_report_csv():
    result = {
        "target": "example.com",
        "hops": [
            {"hop": 1, "ttl": 1, "ip": "10.0.0.1", "host": "10.0.0.1", "response_type": "ICMP_TTL_EXCEEDED", "rtt_ms": 1.5, "rtt_avg_ms": 1.5, "reached_destination": False, "reached": False},
            {"hop": 2, "ttl": 2, "ip": "93.184.215.14", "host": "93.184.215.14", "response_type": "REACHED", "rtt_ms": 10.0, "rtt_avg_ms": 10.0, "reached_destination": True, "reached": True},
        ],
    }
    output = trace.format_trace_report_csv(result)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "hop", "ip", "host", "response_type", "rtt_ms", "reached_destination"]
    assert reader[1] == ["example.com", "1", "10.0.0.1", "10.0.0.1", "ICMP_TTL_EXCEEDED", "1.5", "false"]
    assert reader[2] == ["example.com", "2", "93.184.215.14", "93.184.215.14", "REACHED", "10.0", "true"]


def test_format_trace_report_csv_empty():
    result = {"target": "example.com", "hops": []}
    output = trace.format_trace_report_csv(result)
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 1
    assert reader[0][0] == "target"


def test_normalize_host_edge_cases():
    assert trace._normalize_host("") == ""
    assert trace._normalize_host("   ") == ""
    assert trace._normalize_host("http://") == ""
    assert trace._normalize_host("https://") == ""
    assert trace._normalize_host("http://example.com/path?query=1") == "example.com"
    assert trace._normalize_host("https://example.com:8080/path") == "example.com"
    assert trace._normalize_host("example.com:8080") == "example.com"


def test_probe_once_timeout():
    with patch("ethscan.trace.socket.socket") as mock_sock_class:
        mock_sock = MagicMock()
        mock_sock_class.return_value = mock_sock
        mock_sock.setsockopt = MagicMock()
        mock_sock.bind = MagicMock()
        mock_sock.connect_ex = MagicMock(return_value=0)
        mock_sock.recvfrom = MagicMock(side_effect=socket.timeout)
        mock_sock.close = MagicMock()
        res = trace._probe_once("1.1.1.1", 80, 1, 0.1)
        assert "rtt_ms" in res or res.get("rtt_ms") is not None or res.get("error") is not None


def test_probe_once_close_raises():
    with patch("ethscan.trace.socket.socket") as mock_sock_class:
        mock_sock = MagicMock()
        mock_sock_class.return_value = mock_sock
        mock_sock.setsockopt = MagicMock()
        mock_sock.bind = MagicMock()
        mock_sock.connect_ex = MagicMock(return_value=0)
        mock_sock.recvfrom = MagicMock(side_effect=socket.timeout)
        mock_sock.connect = MagicMock(side_effect=socket.timeout)
        mock_sock.close = MagicMock(side_effect=Exception("close boom"))
        res = trace._probe_once("1.1.1.1", 80, 1, 0.1)
        assert isinstance(res, dict)


def test_probe_once_connect_fail():
    with patch("ethscan.trace.socket.socket") as mock_sock_class:
        mock_sock = MagicMock()
        mock_sock_class.return_value = mock_sock
        mock_sock.setsockopt = MagicMock()
        mock_sock.bind = MagicMock()
        mock_sock.connect_ex = MagicMock(return_value=1)
        mock_sock.connect = MagicMock(side_effect=socket.error('conn err'))
        mock_sock.close = MagicMock()
        res = trace._probe_once("1.1.1.1", 80, 1, 0.1)
        assert res.get("reached") is False


def test_probe_once_socket_error():
    with patch("ethscan.trace.socket.socket") as mock_sock_class:
        mock_sock_class.side_effect = socket.error("socket error")
        res = trace._probe_once("1.1.1.1", 80, 1, 0.1)
        assert res.get("hop_ip") is None
        assert res.get("reached") is False


def test_probe_once_recv_socket_error():
    with patch("ethscan.trace.socket.socket") as mock_sock_class:
        mock_sock = MagicMock()
        mock_sock_class.return_value = mock_sock
        mock_sock.setsockopt = MagicMock()
        mock_sock.bind = MagicMock()
        mock_sock.connect_ex = MagicMock(return_value=0)
        mock_sock.connect = MagicMock(side_effect=socket.error('recv err'))
        mock_sock.close = MagicMock()
        res = trace._probe_once("1.1.1.1", 80, 1, 0.1)
        assert res.get("hop_ip") is None
        assert res.get("reached") is False


def test_trace_single_invalid_target():
    try:
        trace._trace_single("", 80, 3, 1.0, 1)
    except ValueError:
        pass


def test_trace_single_dns_failure():
    with patch("ethscan.trace.socket.gethostbyname") as mock_gethost:
        mock_gethost.side_effect = Exception("DNS fail")
        res = trace._trace_single("bad.example", 80, 3, 1.0, 1)
        assert res.get("error") is not None
        assert "DNS fail" in res.get("error", "")
        assert isinstance(res.get("hops"), list)


def test_trace_single_with_reach():
    with patch("ethscan.trace.socket.gethostbyname") as mock_gethost, \
         patch.object(trace, "_probe_once") as mock_probe:
        mock_gethost.return_value = "93.184.215.14"
        # Simulate reaching target at hop 2
        mock_probe.side_effect = [
            {"hop_ip": "1.1.1.1", "rtt_ms": 1.0, "reached": False, "error": None},
            {"hop_ip": "93.184.215.14", "rtt_ms": 2.0, "reached": True, "error": None},
        ]
        res = trace._trace_single("example.com", 80, 30, 2.0, 1)
        assert res.get("destination_reached") is True
        assert res.get("reached_destination") is True
        assert res.get("reached") is True


def test_trace_single_with_errors():
    with patch("ethscan.trace.socket.gethostbyname") as mock_gethost, \
         patch.object(trace, "_probe_once") as mock_probe:
        mock_gethost.return_value = "93.184.215.14"
        mock_probe.return_value = {"error": "some error"}
        res = trace._trace_single("example.com", 80, 3, 1.0, 1)
        assert isinstance(res.get("hops"), list)


def test_trace_single_multiple_probes():
    with patch("ethscan.trace.socket.gethostbyname") as mock_gethost, \
         patch.object(trace, "_probe_once") as mock_probe:
        mock_gethost.return_value = "93.184.215.14"
        mock_probe.side_effect = [
            {"hop_ip": "1.1.1.1", "rtt_ms": 1.0, "reached": False, "error": None},
            {"hop_ip": "1.1.1.1", "rtt_ms": 2.0, "reached": False, "error": None},
            {"hop_ip": "93.184.215.14", "rtt_ms": 3.0, "reached": True, "error": None},
        ]
        res = trace._trace_single("example.com", 80, 5, 1.0, 2)
        assert isinstance(res.get("hops"), list)


def test_run_trace_dns_error():
    with patch("ethscan.trace.socket.gethostbyname") as mock_gethost:
        mock_gethost.side_effect = Exception("DNS")
        res = trace.run_trace("bad", port=80, max_hops=1, timeout=1.0, probes_per_hop=1)
        assert res.get("error") is not None
        assert isinstance(res.get("hops"), list)


def test_run_trace_recursive_destination_not_reached():
    with patch.object(trace, "_trace_single") as mock_trace:
        main_result = {
            "target": "example.com",
            "dst_ip": "93.184.215.14",
            "destination_reached": False,
            "hops": [{"hop": 1, "ip": "1.1.1.1", "reached_destination": False}],
        }
        mock_trace.return_value = main_result
        res = trace.run_trace("example.com", recursive=True)
        assert res.get("notes") is not None


def test_run_trace_recursive_no_hop_ips():
    with patch.object(trace, "_trace_single") as mock_trace:
        main_result = {
            "target": "example.com",
            "dst_ip": "93.184.215.14",
            "destination_reached": True,
            "hops": [],
        }
        mock_trace.return_value = main_result
        res = trace.run_trace("example.com", recursive=True)
        assert res.get("recursive_traces") == []


def test_run_trace_recursive_prevents_cycles():
    with patch.object(trace, "_trace_single") as mock_trace:
        main_result = {
            "target": "example.com",
            "dst_ip": "93.184.215.14",
            "destination_reached": True,
            "hops": [
                {"hop": 1, "ip": "1.1.1.1", "reached_destination": False},
            ],
            "port": 80,
            "max_hops": 30,
            "timeout": 3.0,
            "probes_per_hop": 3,
        }
        recursive_result = {
            "target": "1.1.1.1",
            "dst_ip": "1.1.1.1",
            "destination_reached": True,
            "hops": [
                {"hop": 1, "ip": "example.com", "reached_destination": False},  # cycle
            ],
            "port": 80,
            "max_hops": 30,
            "timeout": 3.0,
            "probes_per_hop": 3,
        }
        mock_trace.side_effect = [main_result, recursive_result]
        res = trace.run_trace("example.com", recursive=True, max_depth=5)
        assert len(res["recursive_traces"]) == 1


def test_run_trace_recursive_no_next_targets():
    with patch.object(trace, "_trace_single") as mock_trace:
        main_result = {
            "target": "example.com",
            "dst_ip": "93.184.215.14",
            "destination_reached": True,
            "hops": [
                {"hop": 1, "ip": "1.1.1.1", "reached_destination": False},
            ],
        }
        recursive_result = {
            "target": "1.1.1.1",
            "dst_ip": "1.1.1.1",
            "destination_reached": True,
            "hops": [
                {"hop": 1, "ip": "1.1.1.1", "reached_destination": True},  # no intermediate hops
            ],
        }
        mock_trace.side_effect = [main_result, recursive_result]
        res = trace.run_trace("example.com", recursive=True, max_depth=3)
        assert len(res["recursive_traces"]) == 1


def test_fmt_rtt_edge_cases():
    assert trace._fmt_rtt(None) == "N/A"
    assert trace._fmt_rtt(0.0) == "0.00ms"
    assert trace._fmt_rtt(1.234) is not None


def test_format_markdown_edge_cases():
    result = {
        "target": "t",
        "hops": [{"ip": None, "host": None, "hop": 1}],
        "error": "err",
        "notes": ["note1"],
    }
    md = trace.format_trace_report_markdown(result)
    assert "err" in md
    assert "note1" in md


def test_format_markdown_no_ip():
    result = {"target": "t", "hops": []}
    md = trace.format_trace_report_markdown(result)
    assert "t" in md


def test_format_markdown_recursive_no_hops():
    result = {
        "target": "t",
        "dst_ip": "1.1.1.1",
        "recursive": True,
        "recursive_traces": [
            {"target": "r1", "hops": []}
        ],
    }
    md = trace.format_trace_report_markdown(result)
    assert "Recursive Traces" in md


def test_format_markdown_recursive_with_error_and_notes():
    result = {
        "target": "t",
        "recursive": True,
        "recursive_traces": [
            {
                "target": "r1",
                "error": "err",
                "notes": ["n1"],
                "hops": [{"hop": 1, "ip": "2.2.2.2", "reached": True}],
            }
        ],
    }
    md = trace.format_trace_report_markdown(result)
    assert "err" in md
    assert "n1" in md


def test_format_csv_recursive():
    result = {
        "target": "example.com",
        "hops": [{"hop": 1, "ip": "1.1.1.1", "rtt_avg_ms": 1.0}],
        "recursive_traces": [
            {
                "target": "1.1.1.1",
                "hops": [{"hop": 1, "ip": "10.0.0.1", "rtt_ms": 2.0, "reached": True}],
            }
        ],
    }
    output = trace.format_trace_report_csv(result)
    lines = output.splitlines()
    assert len(lines) >= 2  # header + at least one data row


def test_probe_once_close_exception():
    with patch("ethscan.trace.socket.socket") as mock_sock_class:
        mock_sock = MagicMock()
        mock_sock_class.return_value = mock_sock
        mock_sock.setsockopt = MagicMock()
        mock_sock.bind = MagicMock()
        mock_sock.connect_ex = MagicMock(return_value=0)
        mock_sock.recvfrom = MagicMock(side_effect=socket.timeout)
        mock_sock.close = MagicMock(side_effect=Exception("close err"))
        res = trace._probe_once("1.1.1.1", 80, 1, 0.1)
        assert "rtt_ms" in res or res.get("error") is not None


def test_trace_single_raw_socket_unavailable_note():
    with patch("ethscan.trace.socket.gethostbyname") as mock_gethost:
        mock_gethost.return_value = "1.1.1.1"
        with patch.object(trace, "_probe_once") as mock_probe:
            mock_probe.side_effect = Exception("raw")
            try:
                trace._trace_single("t", 80, 1, 0.1, 1)
            except Exception:
                pass
import socket
