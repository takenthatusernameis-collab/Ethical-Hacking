from unittest.mock import patch

import ethscan.trace as trace
from ethscan.trace import format_trace_report_markdown, run_trace


def test_fmt_rtt_branch_gaps():
    # bool is subclass of int; bool branch (line 42) must be taken before int/float
    assert trace._fmt_rtt(True) == "N/A"
    assert trace._fmt_rtt(False) == "N/A"
    # string convertible to float
    assert trace._fmt_rtt("12.5") == "12.50ms"
    # string not convertible -> suppress path + fallback
    assert trace._fmt_rtt("not-a-float") == "N/A"
    # unsupported type falls through to final N/A
    assert trace._fmt_rtt(object()) == "N/A"


def test_trace_single_reached_with_none_rtt_covers_170_172():
    # Force a "reached" probe that carries no RTT so the 170->172 false branch is taken.
    def fake_probe_once(dst_ip, port, ttl, timeout):
        return {"hop_ip": "1.2.3.4", "rtt_ms": None, "reached": True, "error": None}

    with patch("ethscan.trace.socket.gethostbyname", return_value="1.2.3.4"), \
         patch("ethscan.trace._probe_once", side_effect=fake_probe_once):
        res = trace._trace_single("example.com", port=80, max_hops=2, timeout=1.0, probes_per_hop=1)

    assert res["destination_reached"] is True
    assert res["hops"][0]["reached_destination"] is True
    assert res["hops"][0]["rtt_ms"] is None


def test_recursive_trace_destination_not_reached_covers_270_263():
    # Main trace reaches destination with an intermediate hop so recursive tracing runs.
    # Recursive child trace does NOT reach destination -> 270 condition false, loop continues (270->263).
    def fake_trace_single(target, port, max_hops, timeout, probes_per_hop):
        if target == "main.test":
            return {
                "target": "main.test",
                "destination_reached": True,
                "hops": [
                    {"hop": 1, "ip": "10.0.0.1", "reached_destination": False},
                    {"hop": 2, "ip": "10.0.0.2", "reached_destination": True},
                ],
            }
        return {
            "target": target,
            "destination_reached": False,
            "hops": [{"hop": 1, "ip": None, "reached_destination": False}],
        }

    with patch("ethscan.trace._trace_single", side_effect=fake_trace_single):
        res = run_trace("main.test", recursive=True, max_depth=2)

    assert res["recursive"] is True
    assert len(res["recursive_traces"]) == 1
    assert res["recursive_traces"][0]["target"] == "10.0.0.1"
    assert res["recursive_traces"][0]["destination_reached"] is False


def test_format_markdown_empty_or_noniterable_notes_covers_310_313_and_364_367():
    # Empty lists: outer/inner loops over notes take 310->313 and 364->367 false paths.
    result = {
        "target": "t",
        "notes": [],
        "hops": [],
        "recursive_traces": [
            {"target": "child", "notes": [], "hops": []},
        ],
    }
    md = format_trace_report_markdown(result)
    assert "# TCP Traceroute Report" in md
    assert "Recursive Trace 1: child" in md
    assert "**Note:**" not in md

    # Non-list truthy notes: isinstance check false -> 364->367 branch taken.
    result2 = {
        "target": "t",
        "hops": [],
        "recursive_traces": [
            {"target": "child2", "notes": "not-a-list", "hops": []},
        ],
    }
    md2 = format_trace_report_markdown(result2)
    assert "Recursive Trace 1: child2" in md2
    assert "**Note:**" not in md2
