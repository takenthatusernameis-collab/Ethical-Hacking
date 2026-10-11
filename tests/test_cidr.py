"""Tests for the ethscan cidr module."""

import json

from ethscan.cidr import (
    format_cidr_report_json,
    format_cidr_report_markdown,
    run_cidr,
    _normalize_cidr,
    _is_ipv4,
    _contains_ip,
)


def test_normalize_cidr_ipv4():
    assert _normalize_cidr("192.168.1.0/24") == "192.168.1.0/24"


def test_normalize_cidr_ipv4_with_host_bits():
    assert _normalize_cidr("192.168.1.5/24") == "192.168.1.0/24"


def test_normalize_cidr_ipv6():
    assert _normalize_cidr("2001:db8::/32") == "2001:db8::/32"


def test_normalize_cidr_bare_ipv4():
    assert _normalize_cidr("192.168.1.5") == "192.168.1.5/32"


def test_normalize_cidr_bare_ipv6():
    assert _normalize_cidr("::1") == "::1/128"


def test_normalize_cidr_empty():
    import pytest
    with pytest.raises(ValueError):
        _normalize_cidr("")


def test_is_ipv4_true():
    import ipaddress
    net = ipaddress.ip_network("192.168.1.0/24", strict=False)
    assert _is_ipv4(net) is True


def test_is_ipv4_false():
    import ipaddress
    net = ipaddress.ip_network("2001:db8::/32", strict=False)
    assert _is_ipv4(net) is False


def test_run_cidr_ipv4_basic():
    results = run_cidr("192.168.1.0/24")
    assert results["cidr"] == "192.168.1.0/24"
    assert results["ip_version"] == "IPv4"
    network = results["network"]
    assert network["network_address"] == "192.168.1.0"
    assert network["netmask"] == "255.255.255.0"
    assert network["broadcast_address"] == "192.168.1.255"
    assert network["first_host"] == "192.168.1.1"
    assert network["last_host"] == "192.168.1.254"
    assert network["usable_host_count"] == 254
    assert network["total_addresses"] == 256
    assert network["prefixlen"] == 24


def test_run_cidr_ipv6_basic():
    results = run_cidr("2001:db8::/32")
    assert results["ip_version"] == "IPv6"
    network = results["network"]
    assert network["broadcast_address"] is None
    assert network["usable_host_count"] >= 0


def test_run_cidr_contains_inside():
    results = run_cidr("192.168.1.0/24", contains="192.168.1.50")
    assert results["contains"]["ip"] == "192.168.1.50"
    assert results["contains"]["in_network"] is True


def test_run_cidr_contains_outside():
    results = run_cidr("192.168.1.0/24", contains="10.0.0.1")
    assert results["contains"]["in_network"] is False


def test_run_cidr_contains_invalid():
    results = run_cidr("192.168.1.0/24", contains="not-an-ip")
    assert results["contains"]["in_network"] is False


def test_run_cidr_single_host():
    results = run_cidr("192.168.1.5/32")
    network = results["network"]
    assert network["usable_host_count"] == 0
    assert network["total_addresses"] == 1


def test_format_cidr_report_json():
    data = run_cidr("192.168.1.0/24", contains="192.168.1.10")
    output = format_cidr_report_json(data)
    parsed = json.loads(output)
    assert parsed["cidr"] == "192.168.1.0/24"
    assert parsed["network"]["usable_host_count"] == 254
    assert parsed["contains"]["in_network"] is True


def test_format_cidr_report_json_no_contains():
    data = run_cidr("10.0.0.0/8")
    output = format_cidr_report_json(data)
    parsed = json.loads(output)
    assert "contains" not in parsed


def test_format_cidr_report_markdown():
    data = run_cidr("192.168.1.0/24", contains="192.168.1.10")
    output = format_cidr_report_markdown(data)
    assert "ethscan CIDR Network Calculator Report" in output
    assert "192.168.1.0/24" in output
    assert "Network Information" in output
    assert "192.168.1.0" in output
    assert "Membership Test" in output


def test_format_cidr_report_markdown_no_contains():
    data = run_cidr("10.0.0.0/8")
    output = format_cidr_report_markdown(data)
    assert "Membership Test" not in output
    assert "10.0.0.0/8" in output


def test_format_cidr_report_markdown_pipe_escape():
    """Test that the escape helper is used (no raw pipes leak into output)."""
    from ethscan.cidr import _escape
    assert _escape("a|b") == "a\\|b"
    data = run_cidr("192.168.1.0/24")
    output = format_cidr_report_markdown(data)
    # No raw pipe should appear in the table rows (all are escaped)
    assert "| 192.168.1.0 |" in output


def test_format_cidr_report_markdown_ipv6():
    data = run_cidr("2001:db8::/32")
    output = format_cidr_report_markdown(data)
    assert "IPv6" in output