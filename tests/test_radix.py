"""Tests for the ethscan radix module."""

import json

from ethscan.radix import (
    _common_prefix_length,
    _common_prefix_of_pair,
    _merge_networks,
    _nth_bit,
    _normalize_cidr,
    format_radix_report_json,
    format_radix_report_markdown,
    run_radix,
)

import ipaddress


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
    assert _normalize_cidr("192.168.1.5/24") == "192.168.1.0/24"


def test_normalize_cidr_strips_whitespace() -> None:
    assert _normalize_cidr("  192.168.1.0/24  ") == "192.168.1.0/24"


def test_normalize_cidr_empty_raises() -> None:
    try:
        _normalize_cidr("")
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Bit helpers
# ---------------------------------------------------------------------------


def test_nth_bit_ipv4_msb() -> None:
    addr = ipaddress.ip_address("128.0.0.0")
    assert _nth_bit(addr, 0, True) == 1


def test_nth_bit_ipv4_zero() -> None:
    addr = ipaddress.ip_address("0.0.0.0")
    assert _nth_bit(addr, 0, True) == 0


def test_nth_bit_ipv4_lsb() -> None:
    addr = ipaddress.ip_address("0.0.0.1")
    assert _nth_bit(addr, 31, True) == 1


def test_nth_bit_out_of_range() -> None:
    addr = ipaddress.ip_address("0.0.0.0")
    assert _nth_bit(addr, 32, True) == 0


def test_nth_bit_ipv6_msb() -> None:
    addr = ipaddress.ip_address("8000::1")
    assert _nth_bit(addr, 0, False) == 1


def test_common_prefix_length_single() -> None:
    net = ipaddress.ip_network("192.168.1.0/24")
    assert _common_prefix_length([net]) == 24


def test_common_prefix_length_empty() -> None:
    assert _common_prefix_length([]) == 0


def test_common_prefix_length_shared() -> None:
    nets = [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("192.168.2.0/24"),
    ]
    assert _common_prefix_length(nets) == 22


def test_common_prefix_length_adjacent() -> None:
    nets = [
        ipaddress.ip_network("192.168.0.0/24"),
        ipaddress.ip_network("192.168.1.0/24"),
    ]
    assert _common_prefix_length(nets) == 23


def test_common_prefix_length_disjoint() -> None:
    nets = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("192.168.1.0/24"),
    ]
    assert _common_prefix_length(nets) == 0


def test_common_prefix_of_pair_ipv4() -> None:
    start = ipaddress.ip_address("192.168.1.0")
    end = ipaddress.ip_address("192.168.1.255")
    assert _common_prefix_of_pair(start, end, True) == 24


def test_common_prefix_of_pair_ipv4_large() -> None:
    start = ipaddress.ip_address("192.168.0.0")
    end = ipaddress.ip_address("192.168.3.255")
    assert _common_prefix_of_pair(start, end, True) == 22


def test_common_prefix_of_pair_ipv6() -> None:
    start = ipaddress.ip_address("2001:db8::")
    end = ipaddress.ip_address("2001:db8:ffff:ffff:ffff:ffff:ffff:ffff")
    assert _common_prefix_of_pair(start, end, False) == 32


# ---------------------------------------------------------------------------
# Network merging
# ---------------------------------------------------------------------------


def test_merge_networks_empty() -> None:
    assert _merge_networks([]) == []


def test_merge_networks_single() -> None:
    nets = [ipaddress.ip_network("192.168.1.0/24")]
    merged = _merge_networks(nets)
    assert len(merged) == 1
    assert str(merged[0]) == "192.168.1.0/24"


def test_merge_networks_overlapping() -> None:
    nets = [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("192.168.1.128/25"),
    ]
    merged = _merge_networks(nets)
    assert len(merged) == 1
    assert str(merged[0]) == "192.168.1.0/24"


def test_merge_networks_adjacent_supernet() -> None:
    nets = [
        ipaddress.ip_network("192.168.0.0/24"),
        ipaddress.ip_network("192.168.1.0/24"),
    ]
    merged = _merge_networks(nets)
    assert len(merged) == 1
    assert str(merged[0]) == "192.168.0.0/23"


def test_merge_networks_disjoint() -> None:
    nets = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("192.168.1.0/24"),
    ]
    merged = _merge_networks(nets)
    assert len(merged) == 2
    assert str(merged[0]) == "10.0.0.0/8"
    assert str(merged[1]) == "192.168.1.0/24"


def test_merge_networks_sorted() -> None:
    nets = [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("10.0.0.0/8"),
    ]
    merged = _merge_networks(nets)
    assert str(merged[0]) == "10.0.0.0/8"
    assert str(merged[1]) == "192.168.1.0/24"


# ---------------------------------------------------------------------------
# run_radix
# ---------------------------------------------------------------------------


def test_run_radix_basic_ipv4() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/23"])
    assert data["network_count"] == 2
    assert data["merged_network_count"] == 2
    assert data["merge_enabled"] is True
    assert data["max_depth"] == 64
    assert "192.168.1.0/24" in data["merged"]
    assert "192.168.2.0/23" in data["merged"]


def test_run_radix_merge_disabled() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/24"], merge=False)
    assert data["merge_enabled"] is False
    assert data["merged_network_count"] == 2


def test_run_radix_overlapping_merges() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.1.128/25"])
    assert data["merged_network_count"] == 1
    assert data["merged"][0] == "192.168.1.0/24"


def test_run_radix_compression_ratio() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/24", "192.168.0.0/16"])
    assert data["network_count"] == 3
    assert data["merged_network_count"] == 1
    assert data["compression_ratio"] > 1.0


def test_run_radix_ipv6() -> None:
    data = run_radix(["2001:db8::/32", "2001:db8:1::/48"])
    assert data["network_count"] == 2
    assert "2001:db8::/32" in data["merged"]


def test_run_radix_single_network() -> None:
    data = run_radix(["10.0.0.0/8"])
    assert data["network_count"] == 1
    assert data["merged_network_count"] == 1
    assert data["radix_tree"] is not None
    assert data["radix_tree"]["prefix"] == "10.0.0.0/8"


def test_run_radix_radix_tree_structure() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/23"])
    root = data["radix_tree"]
    assert root is not None
    assert root["total_addresses"] >= 768
    assert len(root["children"]) >= 1


def test_run_radix_radix_tree_leaf() -> None:
    data = run_radix(["192.168.1.0/24"])
    root = data["radix_tree"]
    assert root is not None
    assert root["children"] == []
    assert root["networks"] == ["192.168.1.0/24"]


def test_run_radix_max_depth() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/24"], max_depth=1)
    assert data["max_depth"] == 1


def test_run_radix_empty() -> None:
    data = run_radix([])
    assert data["network_count"] == 0
    assert data["radix_tree"] is None


def test_run_radix_invalid_cidr_raises() -> None:
    try:
        run_radix(["not-a-cidr"])
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_run_radix_input_addresses() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/24"])
    assert data["total_input_addresses"] == 512
    assert data["total_merged_addresses"] == 512


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def test_format_radix_report_json_basic() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/23"])
    output = format_radix_report_json(data)
    parsed = json.loads(output)
    assert parsed["network_count"] == 2
    assert parsed["merged_network_count"] == 2
    assert parsed["radix_tree"] is not None


def test_format_radix_report_json_merge_disabled() -> None:
    data = run_radix(["192.168.1.0/24"], merge=False)
    output = format_radix_report_json(data)
    parsed = json.loads(output)
    assert parsed["merge_enabled"] is False


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------


def test_format_radix_report_markdown_basic() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/23"])
    output = format_radix_report_markdown(data)
    assert "# ethscan Radix Tree Report" in output
    assert "Networks Provided" in output
    assert "Merged Networks" in output
    assert "192.168.1.0/24" in output
    assert "Radix Tree" in output


def test_format_radix_report_markdown_single() -> None:
    data = run_radix(["10.0.0.0/8"])
    output = format_radix_report_markdown(data)
    assert "10.0.0.0/8" in output
    assert "1 net(s)" in output


def test_format_radix_report_markdown_merge_disabled() -> None:
    data = run_radix(["192.168.1.0/24"], merge=False)
    output = format_radix_report_markdown(data)
    assert "False" in output


def test_format_radix_report_markdown_pipe_escaping() -> None:
    data = run_radix(["192.168.1.0/24"])
    data["merged"] = ["192|168.1.0/24"]
    output = format_radix_report_markdown(data)
    assert "192\\|168.1.0/24" in output


def test_format_radix_report_markdown_empty_merged() -> None:
    data = run_radix(["192.168.1.0/24"])
    data["merged"] = []
    output = format_radix_report_markdown(data)
    assert "Merged Networks" in output
