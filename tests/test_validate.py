"""Tests for the ethscan validate module."""

import ipaddress
import json

from ethscan.validate import (
    MAX_EXPANDED_IPS,
    _format_network_info,
    _ports_to_ranges,
    _validate_cidr,
    _validate_port_spec,
    format_validate_report_json,
    format_validate_report_markdown,
    run_validate,
)


# ---------------------------------------------------------------------------
# _validate_port_spec
# ---------------------------------------------------------------------------


def test_validate_port_single() -> None:
    result = _validate_port_spec("80")
    assert result["valid"] is True
    assert result["ports"] == [80]
    assert result["count"] == 1
    assert result["error"] is None


def test_validate_port_multiple() -> None:
    result = _validate_port_spec("80,443")
    assert result["valid"] is True
    assert result["ports"] == [80, 443]
    assert result["count"] == 2


def test_validate_port_range() -> None:
    result = _validate_port_spec("8000-8003")
    assert result["valid"] is True
    assert result["ports"] == [8000, 8001, 8002, 8003]
    assert result["count"] == 4


def test_validate_port_mixed() -> None:
    result = _validate_port_spec("22,80,443,8000-8002")
    assert result["valid"] is True
    assert result["ports"] == [22, 80, 443, 8000, 8001, 8002]
    assert result["count"] == 6


def test_validate_port_dedup() -> None:
    result = _validate_port_spec("80,80,443,443")
    assert result["valid"] is True
    assert result["ports"] == [80, 443]
    assert result["count"] == 2


def test_validate_port_strips_whitespace() -> None:
    result = _validate_port_spec("  80 , 443  ")
    assert result["valid"] is True
    assert result["ports"] == [80, 443]


def test_validate_port_empty() -> None:
    result = _validate_port_spec("")
    assert result["valid"] is False
    assert result["ports"] == []
    assert result["count"] == 0
    assert result["error"] is not None


def test_validate_port_only_whitespace() -> None:
    result = _validate_port_spec("   ")
    assert result["valid"] is False
    assert result["error"] is not None


def test_validate_port_invalid_non_numeric() -> None:
    result = _validate_port_spec("abc")
    assert result["valid"] is False
    assert result["error"] is not None


def test_validate_port_out_of_range_high() -> None:
    result = _validate_port_spec("70000")
    assert result["valid"] is False
    assert "range" in result["error"].lower() or "out" in result["error"].lower()


def test_validate_port_out_of_range_negative() -> None:
    result = _validate_port_spec("-1")
    assert result["valid"] is False


def test_validate_port_range_reversed() -> None:
    result = _validate_port_spec("100-50")
    assert result["valid"] is False
    assert "start" in result["error"].lower() or ">" in result["error"]


def test_validate_port_range_missing_end() -> None:
    result = _validate_port_spec("80-")
    assert result["valid"] is False
    assert result["error"] is not None


def test_validate_port_range_missing_start() -> None:
    result = _validate_port_spec("-80")
    assert result["valid"] is False
    assert result["error"] is not None


def test_validate_port_zero() -> None:
    result = _validate_port_spec("0")
    assert result["valid"] is True
    assert result["ports"] == [0]


def test_validate_port_max() -> None:
    result = _validate_port_spec("65535")
    assert result["valid"] is True
    assert result["ports"] == [65535]


def test_validate_port_range_partial_invalid() -> None:
    result = _validate_port_spec("80,abc,443")
    assert result["valid"] is False
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# _validate_cidr
# ---------------------------------------------------------------------------


def test_validate_cidr_ipv4_basic() -> None:
    result = _validate_cidr("192.168.1.0/24")
    assert result["valid"] is True
    assert result["canonical"] == "192.168.1.0/24"
    assert result["network"]["network_address"] == "192.168.1.0"
    assert result["error"] is None


def test_validate_cidr_bare_ipv4() -> None:
    result = _validate_cidr("192.168.1.100")
    assert result["valid"] is True
    assert result["canonical"] == "192.168.1.100/32"
    assert result["network"]["total_addresses"] == 1


def test_validate_cidr_ipv6_basic() -> None:
    result = _validate_cidr("2001:db8::/32")
    assert result["valid"] is True
    assert result["canonical"] == "2001:db8::/32"
    assert result["network"]["network_address"] == "2001:db8::"


def test_validate_cidr_bare_ipv6() -> None:
    result = _validate_cidr("2001:db8::1")
    assert result["valid"] is True
    assert result["canonical"] == "2001:db8::1/128"


def test_validate_cidr_host_bits_zeroed() -> None:
    result = _validate_cidr("192.168.1.5/24")
    assert result["valid"] is True
    assert result["canonical"] == "192.168.1.0/24"


def test_validate_cidr_strips_whitespace() -> None:
    result = _validate_cidr("  192.168.1.0/24  ")
    assert result["valid"] is True
    assert result["canonical"] == "192.168.1.0/24"


def test_validate_cidr_empty() -> None:
    result = _validate_cidr("")
    assert result["valid"] is False
    assert result["canonical"] is None
    assert result["network"] is None
    assert result["error"] is not None


def test_validate_cidr_invalid() -> None:
    result = _validate_cidr("not-an-ip")
    assert result["valid"] is False
    assert result["canonical"] is None
    assert result["network"] is None
    assert result["error"] is not None


def test_validate_cidr_32() -> None:
    result = _validate_cidr("10.0.0.5/32")
    assert result["valid"] is True
    assert result["canonical"] == "10.0.0.5/32"
    assert result["network"]["total_addresses"] == 1


def test_validate_cidr_includes_expanded_addresses_small() -> None:
    network = ipaddress.ip_network("192.168.1.0/30")
    info = _format_network_info(network)
    assert info["addresses"] is not None
    assert info["addresses"] == ["192.168.1.0", "192.168.1.1", "192.168.1.2", "192.168.1.3"]


def test_validate_cidr_excludes_large_expanded_addresses() -> None:
    network = ipaddress.ip_network("10.0.0.0/8")
    info = _format_network_info(network)
    assert info["addresses"] is None


# ---------------------------------------------------------------------------
# _format_network_info
# ---------------------------------------------------------------------------


def test_format_network_info_ipv4_basic() -> None:
    network = ipaddress.ip_network("192.168.1.0/24")
    info = _format_network_info(network)
    assert info["network_address"] == "192.168.1.0"
    assert info["netmask"] == "255.255.255.0"
    assert info["broadcast_address"] == "192.168.1.255"
    assert info["total_addresses"] == 256
    assert info["prefixlen"] == 24
    assert info["first_host"] == "192.168.1.1"
    assert info["last_host"] == "192.168.1.254"


def test_format_network_info_ipv4_32() -> None:
    network = ipaddress.ip_network("192.168.1.1/32")
    info = _format_network_info(network)
    assert info["total_addresses"] == 1
    assert info["broadcast_address"] == "192.168.1.1"
    assert info["first_host"] == "192.168.1.1"
    assert info["last_host"] == "192.168.1.1"


def test_format_network_info_ipv6_no_broadcast() -> None:
    network = ipaddress.ip_network("2001:db8::/32")
    info = _format_network_info(network)
    assert info["broadcast_address"] is None
    assert info["network_address"] == "2001:db8::"


# ---------------------------------------------------------------------------
# _ports_to_ranges
# ---------------------------------------------------------------------------


def test_ports_to_ranges_single() -> None:
    assert _ports_to_ranges([80]) == "80"


def test_ports_to_ranges_multiple_single() -> None:
    assert _ports_to_ranges([80, 443]) == "80, 443"


def test_ports_to_ranges_contiguous() -> None:
    assert _ports_to_ranges([8000, 8001, 8002]) == "8000-8002"


def test_ports_to_ranges_mixed() -> None:
    assert _ports_to_ranges([22, 80, 443, 8000, 8001, 8002]) == "22, 80, 443, 8000-8002"


def test_ports_to_ranges_empty() -> None:
    assert _ports_to_ranges([]) == ""


def test_ports_to_ranges_sorted_input() -> None:
    assert _ports_to_ranges([8000, 8001, 8002, 80]) == "80, 8000-8002"


# ---------------------------------------------------------------------------
# run_validate
# ---------------------------------------------------------------------------


def test_run_validate_no_specs() -> None:
    result = run_validate()
    assert result["ports"] == []
    assert result["cidrs"] == []
    assert result["summary"]["ports_specified"] == 0
    assert result["summary"]["cidrs_specified"] == 0
    assert result["summary"]["ports_total"] == 0
    assert result["summary"]["all_valid"] is False
    assert any("nothing to validate" in n.lower() for n in result["notes"])


def test_run_validate_ports_only() -> None:
    result = run_validate(ports="80,443,8000-8002")
    assert len(result["ports"]) == 1  # entire string is one spec
    assert result["summary"]["ports_specified"] == 1
    assert result["summary"]["ports_valid"] == 1
    assert result["summary"]["ports_total"] == 5
    assert result["summary"]["all_valid"] is True


def test_run_validate_cidrs_only() -> None:
    result = run_validate(cidrs="192.168.1.0/24,10.0.0.0/8")
    assert len(result["cidrs"]) == 2
    assert result["summary"]["cidrs_specified"] == 2
    assert result["summary"]["cidrs_valid"] == 2
    assert result["summary"]["all_valid"] is True


def test_run_validate_both_ports_and_cidrs() -> None:
    result = run_validate(ports="80,443", cidrs="192.168.1.0/24")
    assert len(result["ports"]) == 1
    assert len(result["cidrs"]) == 1
    assert result["summary"]["ports_specified"] == 1
    assert result["summary"]["cidrs_specified"] == 1
    assert result["summary"]["all_valid"] is True


def test_run_validate_mixed_valid_invalid() -> None:
    result = run_validate(ports="80,abc", cidrs="192.168.1.0/24,not-an-ip")
    assert result["summary"]["ports_valid"] == 0
    assert result["summary"]["ports_specified"] == 1
    assert result["summary"]["cidrs_valid"] == 1
    assert result["summary"]["cidrs_specified"] == 2
    assert result["summary"]["all_valid"] is False


def test_run_validate_summary_ports_total() -> None:
    result = run_validate(ports="80,443")
    assert result["summary"]["ports_total"] == 2


def test_run_validate_notes_added() -> None:
    result = run_validate(ports="80,443")
    assert len(result["notes"]) > 0
    assert any("port" in n.lower() for n in result["notes"])


# ---------------------------------------------------------------------------
# format_validate_report_json
# ---------------------------------------------------------------------------


def test_format_validate_report_json_basic() -> None:
    data = run_validate(ports="80,443", cidrs="192.168.1.0/24")
    output = format_validate_report_json(data)
    parsed = json.loads(output)
    assert "ports" in parsed
    assert "cidrs" in parsed
    assert "summary" in parsed
    assert "notes" in parsed


def test_format_validate_report_json_no_specs() -> None:
    data = run_validate()
    output = format_validate_report_json(data)
    parsed = json.loads(output)
    assert parsed["ports"] == []
    assert parsed["cidrs"] == []


def test_format_validate_report_json_includes_errors() -> None:
    data = run_validate(ports="abc")
    output = format_validate_report_json(data)
    parsed = json.loads(output)
    assert parsed["ports"][0]["valid"] is False
    assert parsed["ports"][0]["error"] is not None


# ---------------------------------------------------------------------------
# format_validate_report_markdown
# ---------------------------------------------------------------------------


def test_format_validate_report_markdown_basic() -> None:
    data = run_validate(ports="80,443", cidrs="192.168.1.0/24")
    output = format_validate_report_markdown(data)
    assert "# ethscan Validate Report" in output
    assert "## Summary" in output
    assert "## Port Specifications" in output
    assert "## CIDR / Network Specifications" in output


def test_format_validate_report_markdown_no_specs() -> None:
    data = run_validate()
    output = format_validate_report_markdown(data)
    assert "# ethscan Validate Report" in output
    assert "## Summary" in output
    assert "All Valid" in output


def test_format_validate_report_markdown_summary_fields() -> None:
    data = run_validate(ports="80,443", cidrs="192.168.1.0/24")
    output = format_validate_report_markdown(data)
    assert "Port Specs Provided" in output
    assert "Port Specs Valid" in output
    assert "Total Ports Expanded" in output
    assert "CIDR Specs Provided" in output
    assert "CIDR Specs Valid" in output


def test_format_validate_report_markdown_ports_table() -> None:
    data = run_validate(ports="80,443,8000-8002")
    output = format_validate_report_markdown(data)
    assert "80, 443, 8000-8002" in output
    assert "## Port Specifications" in output


def test_format_validate_report_markdown_invalid_port() -> None:
    data = run_validate(ports="abc")
    output = format_validate_report_markdown(data)
    assert "No" in output  # valid column shows No
    assert "Invalid port number" in output or "error" in output.lower()


def test_format_validate_report_markdown_invalid_cidr() -> None:
    data = run_validate(cidrs="not-an-ip")
    output = format_validate_report_markdown(data)
    assert "No" in output
    assert "not-an-ip" in output


def test_format_validate_report_markdown_pipe_escaping() -> None:
    data = run_validate(ports="80|443")
    output = format_validate_report_markdown(data)
    assert "80\\|443" in output


def test_format_validate_report_markdown_notes() -> None:
    data = run_validate(ports="80,443")
    output = format_validate_report_markdown(data)
    assert "## Notes" in output
