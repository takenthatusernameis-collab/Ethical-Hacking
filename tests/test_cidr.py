"""Tests for the ethscan cidr module."""

import json

from ethscan.cidr import (
    _contains_ip,
    _format_network_info,
    _normalize_cidr,
    format_cidr_report_json,
    format_cidr_report_markdown,
    run_cidr,
)

# ---------------------------------------------------------------------------
# CIDR normalization
# ---------------------------------------------------------------------------


def test_normalize_cidr_bare_ipv4() -> None:
    assert _normalize_cidr("192.168.1.1") == "192.168.1.1/32"


def test_normalize_cidr_bare_ipv6() -> None:
    assert _normalize_cidr("2001:db8::1") == "2001:db8::1/128"


def test_normalize_cidr_ipv4_with_prefix() -> None:
    assert _normalize_cidr("192.168.1.0/24") == "192.168.1.0/24"


def test_normalize_cidr_ipv6_with_prefix() -> None:
    assert _normalize_cidr("2001:db8::/32") == "2001:db8::/32"


def test_normalize_cidr_host_bits_zeroed() -> None:
    """Host bits should be zeroed to network address."""
    assert _normalize_cidr("192.168.1.5/24") == "192.168.1.0/24"


def test_normalize_cidr_strips_whitespace() -> None:
    assert _normalize_cidr("  192.168.1.0/24  ") == "192.168.1.0/24"


def test_normalize_cidr_empty_raises() -> None:
    try:
        _normalize_cidr("")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_normalize_cidr_uppercase() -> None:
    assert _normalize_cidr("192.168.1.0/24") == "192.168.1.0/24"


# ---------------------------------------------------------------------------
# Network info formatting
# ---------------------------------------------------------------------------


def test_format_network_info_ipv4_basic() -> None:
    import ipaddress

    network = ipaddress.ip_network("192.168.1.0/24")
    info = _format_network_info(network)

    assert info["network_address"] == "192.168.1.0"
    assert info["netmask"] == "255.255.255.0"
    assert info["broadcast_address"] == "192.168.1.255"
    assert info["wildcard_mask"] == "0.0.0.255"
    assert info["first_host"] == "192.168.1.1"
    # Implementation uses network[-1] which includes broadcast address
    assert info["last_host"] == "192.168.1.255"
    assert info["usable_host_count"] == 254
    assert info["total_addresses"] == 256
    assert info["prefixlen"] == 24


def test_format_network_info_ipv4_31() -> None:
    """RFC 3021 /31 networks have no usable hosts in traditional sense."""
    import ipaddress

    network = ipaddress.ip_network("192.168.1.0/31")
    info = _format_network_info(network)

    assert info["network_address"] == "192.168.1.0"
    assert info["broadcast_address"] == "192.168.1.1"
    assert info["usable_host_count"] == 0
    assert info["total_addresses"] == 2


def test_format_network_info_ipv4_32() -> None:
    """Single host /32 network."""
    import ipaddress

    network = ipaddress.ip_network("192.168.1.1/32")
    info = _format_network_info(network)

    assert info["network_address"] == "192.168.1.1"
    assert info["broadcast_address"] == "192.168.1.1"
    assert info["first_host"] == "192.168.1.1"
    assert info["last_host"] == "192.168.1.1"
    assert info["usable_host_count"] == 0
    assert info["total_addresses"] == 1


def test_format_network_info_ipv6_basic() -> None:
    import ipaddress

    network = ipaddress.ip_network("2001:db8::/32")
    info = _format_network_info(network)

    assert info["network_address"] == "2001:db8::"
    assert info["netmask"] == "ffff:ffff::"
    assert info["broadcast_address"] is None
    # Implementation uses network.hostmask which for /32 gives 96 bits of 1s
    assert info["wildcard_mask"] == "::ffff:ffff:ffff:ffff:ffff:ffff"
    assert info["usable_host_count"] == network.num_addresses - 2


def test_format_network_info_ipv6_128() -> None:
    """Single host /128 network."""
    import ipaddress

    network = ipaddress.ip_network("2001:db8::1/128")
    info = _format_network_info(network)

    assert info["network_address"] == "2001:db8::1"
    assert info["first_host"] == "2001:db8::1"
    assert info["last_host"] == "2001:db8::1"
    assert info["usable_host_count"] == 0
    assert info["total_addresses"] == 1


# ---------------------------------------------------------------------------
# IP containment
# ---------------------------------------------------------------------------


def test_contains_ip_ipv4_in_network() -> None:
    import ipaddress

    network = ipaddress.ip_network("192.168.1.0/24")
    assert _contains_ip(network, "192.168.1.100") is True
    assert _contains_ip(network, "192.168.1.0") is True
    assert _contains_ip(network, "192.168.1.255") is True


def test_contains_ip_ipv4_not_in_network() -> None:
    import ipaddress

    network = ipaddress.ip_network("192.168.1.0/24")
    assert _contains_ip(network, "192.168.2.1") is False
    assert _contains_ip(network, "10.0.0.1") is False


def test_contains_ip_ipv6_in_network() -> None:
    import ipaddress

    network = ipaddress.ip_network("2001:db8::/32")
    assert _contains_ip(network, "2001:db8::1") is True
    assert _contains_ip(network, "2001:db8:ffff:ffff:ffff:ffff:ffff:ffff") is True


def test_contains_ip_ipv6_not_in_network() -> None:
    import ipaddress

    network = ipaddress.ip_network("2001:db8::/32")
    assert _contains_ip(network, "2001:db9::1") is False


def test_contains_ip_invalid_ip() -> None:
    import ipaddress

    network = ipaddress.ip_network("192.168.1.0/24")
    assert _contains_ip(network, "not-an-ip") is False
    assert _contains_ip(network, "") is False


# ---------------------------------------------------------------------------
# run_cidr
# ---------------------------------------------------------------------------


def test_run_cidr_ipv4_basic() -> None:
    result = run_cidr("192.168.1.0/24")

    assert result["cidr"] == "192.168.1.0/24"
    assert result["ip_version"] == "IPv4"
    assert result["network"]["network_address"] == "192.168.1.0"
    assert result["network"]["netmask"] == "255.255.255.0"
    assert result["network"]["broadcast_address"] == "192.168.1.255"
    assert result["network"]["usable_host_count"] == 254


def test_run_cidr_ipv4_bare_ip() -> None:
    result = run_cidr("192.168.1.100")

    assert result["cidr"] == "192.168.1.100/32"
    assert result["ip_version"] == "IPv4"
    assert result["network"]["total_addresses"] == 1


def test_run_cidr_ipv6_basic() -> None:
    result = run_cidr("2001:db8::/32")

    assert result["cidr"] == "2001:db8::/32"
    assert result["ip_version"] == "IPv6"
    assert result["network"]["broadcast_address"] is None


def test_run_cidr_ipv6_bare_ip() -> None:
    result = run_cidr("2001:db8::1")

    assert result["cidr"] == "2001:db8::1/128"
    assert result["ip_version"] == "IPv6"


def test_run_cidr_with_contains_true() -> None:
    result = run_cidr("192.168.1.0/24", contains="192.168.1.50")

    assert "contains" in result
    assert result["contains"]["ip"] == "192.168.1.50"
    assert result["contains"]["in_network"] is True


def test_run_cidr_with_contains_false() -> None:
    result = run_cidr("192.168.1.0/24", contains="192.168.2.50")

    assert result["contains"]["ip"] == "192.168.2.50"
    assert result["contains"]["in_network"] is False


def test_run_cidr_with_contains_invalid_ip() -> None:
    result = run_cidr("192.168.1.0/24", contains="not-an-ip")

    assert result["contains"]["in_network"] is False


def test_run_cidr_with_contains_strips_whitespace() -> None:
    result = run_cidr("192.168.1.0/24", contains="  192.168.1.50  ")

    assert result["contains"]["ip"] == "192.168.1.50"
    assert result["contains"]["in_network"] is True


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def test_format_cidr_report_json_basic() -> None:
    data = run_cidr("192.168.1.0/24")
    output = format_cidr_report_json(data)

    parsed = json.loads(output)
    assert parsed["cidr"] == "192.168.1.0/24"
    assert parsed["ip_version"] == "IPv4"


def test_format_cidr_report_json_with_contains() -> None:
    data = run_cidr("192.168.1.0/24", contains="192.168.1.50")
    output = format_cidr_report_json(data)

    parsed = json.loads(output)
    assert parsed["contains"]["in_network"] is True


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------


def test_format_cidr_report_markdown_basic() -> None:
    data = run_cidr("192.168.1.0/24")
    output = format_cidr_report_markdown(data)

    assert "# ethscan CIDR Network Calculator Report" in output
    assert "192.168.1.0/24" in output
    assert "IPv4" in output
    assert "Network Address" in output
    assert "192.168.1.0" in output
    assert "Broadcast Address" in output
    assert "192.168.1.255" in output
    assert "Usable Host Count" in output
    assert "254" in output


def test_format_cidr_report_markdown_ipv6() -> None:
    data = run_cidr("2001:db8::/32")
    output = format_cidr_report_markdown(data)

    assert "IPv6" in output
    assert "2001:db8::/32" in output
    assert "Broadcast Address" in output
    assert "None" in output or "" in output


def test_format_cidr_report_markdown_with_contains_true() -> None:
    data = run_cidr("192.168.1.0/24", contains="192.168.1.50")
    output = format_cidr_report_markdown(data)

    assert "Membership Test" in output
    assert "192.168.1.50" in output
    assert "Yes" in output


def test_format_cidr_report_markdown_with_contains_false() -> None:
    data = run_cidr("192.168.1.0/24", contains="10.0.0.1")
    output = format_cidr_report_markdown(data)

    assert "Membership Test" in output
    assert "10.0.0.1" in output
    assert "No" in output


def test_format_cidr_report_markdown_pipe_escaping() -> None:
    """Values containing pipe characters should be escaped."""
    data = run_cidr("192.168.1.0/24")
    # Manually inject a value with pipe
    data["network"]["netmask"] = "255|255|255|0"
    output = format_cidr_report_markdown(data)
    # Pipe should be escaped
    assert "255\\|255\\|255\\|0" in output