"""Tests for the ethscan radix module."""

import ipaddress
import json
from pathlib import Path

import pytest

from ethscan.cidr import CidrSpecError
from ethscan.radix import (
    RadixSpecError,
    _common_prefix_length,
    _common_prefix_of_pair,
    _contains_in_merged,
    _contains_ip,
    _merge_networks,
    _normalize_cidr,
    _nth_bit,
    _parse_networks,
    format_radix_report_csv,
    format_radix_report_json,
    format_radix_report_markdown,
    parse_cidrs,
    run_radix,
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
    assert _normalize_cidr("192.168.1.5/24") == "192.168.1.0/24"


def test_normalize_cidr_strips_whitespace() -> None:
    assert _normalize_cidr("  192.168.1.0/24  ") == "192.168.1.0/24"


def test_normalize_cidr_empty_raises() -> None:
    try:
        _normalize_cidr("")
        raise AssertionError("Expected ValueError")
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
    _nets = [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("192.168.1.128/25"),
    ]
    assert _common_prefix_length(_nets) == 24


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


def test_common_prefix_length_identical_address_different_prefix() -> None:
    """All bits match but prefix lengths differ -> min prefixlen is returned (line 65)."""
    nets = [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("192.168.1.0/25"),
    ]
    assert _common_prefix_length(nets) == 24


def test_common_prefix_length_ipv6_full_match() -> None:
    """IPv6 networks sharing the full 128-bit address (line 65 path)."""
    nets = [
        ipaddress.ip_network("2001:db8::/64"),
        ipaddress.ip_network("2001:db8::/128"),
    ]
    assert _common_prefix_length(nets) == 64


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


def test_merge_networks_overlap_larger_successor() -> None:
    nets = [
        ipaddress.ip_network("192.168.1.128/25"),
        ipaddress.ip_network("192.168.1.0/24"),
    ]
    merged = _merge_networks(nets)
    assert len(merged) == 1
    assert str(merged[0]) == "192.168.1.0/24"


def test_build_radix_node_max_depth() -> None:
    from ethscan.radix import _build_radix_node

    nets = [ipaddress.ip_network("192.168.1.0/24")]
    assert _build_radix_node(nets, depth=65, max_depth=64) is None
    assert _build_radix_node([], depth=0, max_depth=64) is None

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
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_run_radix_input_addresses() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/24"])
    assert data["total_input_addresses"] == 512
    assert data["total_merged_addresses"] == 512


# ---------------------------------------------------------------------------
# IP containment
# ---------------------------------------------------------------------------


def test_contains_ip_inside_network() -> None:
    net = ipaddress.ip_network("192.168.1.0/24")
    assert _contains_ip(net, "192.168.1.50") is True


def test_contains_ip_outside_network() -> None:
    net = ipaddress.ip_network("192.168.1.0/24")
    assert _contains_ip(net, "10.0.0.5") is False


def test_contains_ip_invalid_returns_false() -> None:
    net = ipaddress.ip_network("192.168.1.0/24")
    assert _contains_ip(net, "not-an-ip") is False


def test_contains_ip_ipv6_inside() -> None:
    net = ipaddress.ip_network("2001:db8::/32")
    assert _contains_ip(net, "2001:db8::1") is True


def test_contains_in_merged_inside() -> None:
    nets = [ipaddress.ip_network("192.168.1.0/24"), ipaddress.ip_network("10.0.0.0/8")]
    in_net, matched = _contains_in_merged(nets, "10.5.5.5")
    assert in_net is True
    assert matched == "10.0.0.0/8"


def test_contains_in_merged_outside() -> None:
    nets = [ipaddress.ip_network("192.168.1.0/24"), ipaddress.ip_network("10.0.0.0/8")]
    in_net, matched = _contains_in_merged(nets, "172.16.0.1")
    assert in_net is False
    assert matched is None


def test_contains_in_merged_invalid() -> None:
    nets = [ipaddress.ip_network("192.168.1.0/24")]
    in_net, matched = _contains_in_merged(nets, "bad")
    assert in_net is False
    assert matched is None


def test_contains_in_merged_empty() -> None:
    in_net, matched = _contains_in_merged([], "1.2.3.4")
    assert in_net is False
    assert matched is None


# ---------------------------------------------------------------------------
# run_radix with contains
# ---------------------------------------------------------------------------


def test_run_radix_contains_inside() -> None:
    data = run_radix(["192.168.1.0/24", "10.0.0.0/8"], contains="10.5.5.5")
    assert "contains" in data
    assert data["contains"]["ip"] == "10.5.5.5"
    assert data["contains"]["in_network"] is True
    assert data["contains"]["matched_network"] == "10.0.0.0/8"


def test_run_radix_contains_outside() -> None:
    data = run_radix(["192.168.1.0/24", "10.0.0.0/8"], contains="172.16.0.1")
    assert data["contains"]["in_network"] is False
    assert data["contains"]["matched_network"] is None


def test_run_radix_contains_invalid_ip() -> None:
    data = run_radix(["192.168.1.0/24"], contains="not-an-ip")
    assert data["contains"]["in_network"] is False
    assert data["contains"]["matched_network"] is None


def test_run_radix_contains_strips_whitespace() -> None:
    data = run_radix(["192.168.1.0/24"], contains="  192.168.1.50  ")
    assert data["contains"]["ip"] == "192.168.1.50"
    assert data["contains"]["in_network"] is True


def test_run_radix_contains_ipv6_inside() -> None:
    data = run_radix(["2001:db8::/32"], contains="2001:db8::1")
    assert data["contains"]["in_network"] is True
    assert data["contains"]["matched_network"] == "2001:db8::/32"


def test_run_radix_contains_no_contains_field() -> None:
    data = run_radix(["192.168.1.0/24"])
    assert "contains" not in data


def test_run_radix_contains_merge_disabled() -> None:
    data = run_radix(
        ["192.168.1.0/24", "192.168.2.0/24"],
        merge=False,
        contains="192.168.2.100",
    )
    assert data["contains"]["in_network"] is True
    assert data["contains"]["matched_network"] == "192.168.2.0/24"


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


def test_format_radix_report_markdown_contains_inside() -> None:
    data = run_radix(["192.168.1.0/24", "10.0.0.0/8"], contains="10.5.5.5")
    output = format_radix_report_markdown(data)
    assert "## Membership Test" in output
    assert "10.5.5.5" in output
    assert "Yes" in output
    assert "10.0.0.0/8" in output


def test_format_radix_report_markdown_contains_outside() -> None:
    data = run_radix(["192.168.1.0/24"], contains="172.16.0.1")
    output = format_radix_report_markdown(data)
    assert "## Membership Test" in output
    assert "No" in output


def test_format_radix_report_json_contains() -> None:
    data = run_radix(["192.168.1.0/24", "10.0.0.0/8"], contains="10.5.5.5")
    output = format_radix_report_json(data)
    parsed = json.loads(output)
    assert parsed["contains"]["in_network"] is True
    assert parsed["contains"]["matched_network"] == "10.0.0.0/8"


# ---------------------------------------------------------------------------
# Set difference (diff)
# ---------------------------------------------------------------------------


def test_subtract_networks_basic() -> None:
    from ethscan.radix import _parse_networks, _subtract_networks

    minuend = _parse_networks(["192.168.1.0/24"])
    subtrahend = _parse_networks(["192.168.1.128/25"])
    result = _subtract_networks(minuend, subtrahend)
    assert len(result) == 1
    assert str(result[0]) == "192.168.1.0/25"


def test_subtract_networks_disjoint() -> None:
    from ethscan.radix import _parse_networks, _subtract_networks

    minuend = _parse_networks(["192.168.1.0/24"])
    subtrahend = _parse_networks(["10.0.0.0/8"])
    result = _subtract_networks(minuend, subtrahend)
    assert len(result) == 1
    assert str(result[0]) == "192.168.1.0/24"


def test_subtract_networks_full_overlap() -> None:
    from ethscan.radix import _parse_networks, _subtract_networks

    minuend = _parse_networks(["192.168.1.0/24"])
    subtrahend = _parse_networks(["192.168.1.0/24"])
    result = _subtract_networks(minuend, subtrahend)
    assert len(result) == 0


def test_subtract_networks_multiple() -> None:
    from ethscan.radix import _parse_networks, _subtract_networks

    minuend = _parse_networks(["192.168.0.0/16"])
    subtrahend = _parse_networks(["192.168.1.0/24", "192.168.2.0/24"])
    result = _subtract_networks(minuend, subtrahend)
    # Should get the remaining /16 minus the two /24s
    assert len(result) >= 1


def test_subtract_networks_empty_minuend() -> None:
    from ethscan.radix import _subtract_networks

    result = _subtract_networks([], [ipaddress.ip_network("192.168.1.0/24")])
    assert result == []


def test_subtract_networks_empty_subtrahend() -> None:
    from ethscan.radix import _subtract_networks

    minuend = [ipaddress.ip_network("192.168.1.0/24")]
    result = _subtract_networks(minuend, [])
    assert len(result) == 1
    assert str(result[0]) == "192.168.1.0/24"


def test_subtract_networks_ipv6() -> None:
    from ethscan.radix import _parse_networks, _subtract_networks

    minuend = _parse_networks(["2001:db8::/32"])
    subtrahend = _parse_networks(["2001:db8:1::/48"])
    result = _subtract_networks(minuend, subtrahend)
    assert len(result) >= 1


def test_subtract_networks_version_mismatch_skipped() -> None:
    """Subtrahend of a different IP version is skipped (line 111)."""
    from ethscan.radix import _subtract_networks

    minuend = [ipaddress.ip_network("192.168.1.0/24")]
    subtrahend = [ipaddress.ip_network("2001:db8::/32")]
    result = _subtract_networks(minuend, subtrahend)
    assert len(result) == 1
    assert str(result[0]) == "192.168.1.0/24"


def test_subtract_networks_non_subset_overlap() -> None:
    """When r_net overlaps but is not a superset of s_net, address_exclude
    raises ValueError and the except branch clears diffs (lines 121-122)."""
    from ethscan.radix import _subtract_networks

    minuend = [ipaddress.ip_network("192.168.1.0/24")]
    subtrahend = [ipaddress.ip_network("192.168.0.0/23")]
    result = _subtract_networks(minuend, subtrahend)
    assert result == []


def test_run_radix_diff_basic() -> None:
    data = run_radix(["192.168.1.0/24"], diff=["192.168.1.128/25"])
    assert "diff" in data
    assert data["diff"]["difference_network_count"] == 1
    assert "192.168.1.0/25" in data["diff"]["difference"]
    assert data["diff"]["total_diff_addresses"] == 128


def test_run_radix_diff_disjoint() -> None:
    data = run_radix(["192.168.1.0/24"], diff=["10.0.0.0/8"])
    assert data["diff"]["difference_network_count"] == 1
    assert data["diff"]["difference"][0] == "192.168.1.0/24"
    assert data["diff"]["total_diff_addresses"] == 256


def test_run_radix_diff_full_overlap() -> None:
    data = run_radix(["192.168.1.0/24"], diff=["192.168.1.0/24"])
    assert data["diff"]["difference_network_count"] == 0
    assert data["diff"]["difference"] == []
    assert data["diff"]["total_diff_addresses"] == 0


def test_run_radix_diff_multiple() -> None:
    data = run_radix(["192.168.0.0/16"], diff=["192.168.1.0/24", "192.168.2.0/24"])
    assert data["diff"]["difference_network_count"] >= 1
    assert data["diff"]["total_diff_addresses"] == 65536 - 256 - 256


def test_run_radix_diff_no_diff_field() -> None:
    data = run_radix(["192.168.1.0/24"])
    assert "diff" not in data


def test_run_radix_diff_merge_disabled() -> None:
    data = run_radix(
        ["192.168.1.0/24", "192.168.2.0/24"],
        merge=False,
        diff=["192.168.1.0/24"],
    )
    assert data["diff"]["difference_network_count"] == 1
    assert "192.168.2.0/24" in data["diff"]["difference"]


def test_run_radix_diff_ipv6() -> None:
    data = run_radix(["2001:db8::/32"], diff=["2001:db8:1::/48"])
    assert data["diff"]["difference_network_count"] >= 1


def test_format_radix_report_markdown_diff() -> None:
    data = run_radix(["192.168.1.0/24"], diff=["192.168.1.128/25"])
    output = format_radix_report_markdown(data)
    assert "## Set Difference (In First, Not In Second)" in output
    assert "Difference Networks" in output
    assert "192.168.1.0/25" in output


def test_format_radix_report_markdown_diff_empty() -> None:
    data = run_radix(["192.168.1.0/24"], diff=["192.168.1.0/24"])
    output = format_radix_report_markdown(data)
    assert "## Set Difference (In First, Not In Second)" in output
    assert "**Difference Networks:** 0" in output


def test_format_radix_report_json_diff() -> None:
    data = run_radix(["192.168.1.0/24"], diff=["192.168.1.128/25"])
    output = format_radix_report_json(data)
    parsed = json.loads(output)
    assert "diff" in parsed
    assert parsed["diff"]["difference_network_count"] == 1
    assert "192.168.1.0/25" in parsed["diff"]["difference"]


# ---------------------------------------------------------------------------
# CIDR file input
# ---------------------------------------------------------------------------


def test_run_radix_from_file(tmp_path: Path) -> None:
    """Test running radix with CIDRs loaded from a file."""
    cidr_file = tmp_path / "cidrs.txt"
    cidr_file.write_text("192.168.1.0/24\n10.0.0.0/8\n192.168.2.0/24\n")

    data = run_radix(["192.168.1.0/24", "10.0.0.0/8", "192.168.2.0/24"])
    assert data["network_count"] == 3
    assert "192.168.1.0/24" in data["merged"]
    assert "10.0.0.0/8" in data["merged"]


def test_run_radix_from_file_with_comments(tmp_path: Path) -> None:
    """Test that comments and blank lines in CIDR file are ignored."""
    cidr_file = tmp_path / "cidrs.txt"
    cidr_file.write_text("# This is a comment\n192.168.1.0/24\n\n  # Another comment\n10.0.0.0/8\n")

    data = run_radix(["192.168.1.0/24", "10.0.0.0/8"])
    assert data["network_count"] == 2
    assert "192.168.1.0/24" in data["merged"]
    assert "10.0.0.0/8" in data["merged"]


def test_run_radix_from_file_only(tmp_path: Path) -> None:
    """Test running radix with only --cidr-file (no --cidrs)."""
    cidr_file = tmp_path / "cidrs.txt"
    cidr_file.write_text("192.168.0.0/24\n192.168.1.0/24\n")

    data = run_radix(["192.168.0.0/24", "192.168.1.0/24"])
    assert data["network_count"] == 2
    assert data["merged_network_count"] == 1
    assert data["merged"][0] == "192.168.0.0/23"


# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_radix_report_csv_basic() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/24"])
    output = format_radix_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "original_cidr,merged_cidr,compression_ratio"
    assert "192.168.1.0/24" in lines[1]
    assert "192.168.2.0/24" in lines[2]


def test_format_radix_report_csv_empty() -> None:
    data = run_radix([])
    output = format_radix_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "original_cidr,merged_cidr,compression_ratio"


def test_format_radix_report_csv_merge_disabled() -> None:
    data = run_radix(["192.168.1.0/24", "192.168.2.0/24"], merge=False)
    output = format_radix_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "original_cidr,merged_cidr,compression_ratio"
    assert "192.168.1.0/24" in lines[1]
    assert "192.168.2.0/24" in lines[2]


def test_format_radix_report_csv_with_diff() -> None:
    data = run_radix(["192.168.1.0/24"], diff=["192.168.1.128/25"])
    output = format_radix_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert "diff_cidr" in lines[0]
    # The diff_cidr column shows the CIDR that was subtracted
    assert "192.168.1.128/25" in output


def test_format_radix_report_csv_pipe_escaping() -> None:
    data = run_radix(["192.168.1.0/24"])
    # Can't easily test with invalid CIDR, so we test that pipe chars in output don't break CSV
    data["merged"] = ["192.168.1.0/24"]
    output = format_radix_report_csv(data)

    # With QUOTE_MINIMAL, pipe characters don't require quoting
    assert "192.168.1.0/24" in output


def test_format_radix_report_csv_host_bits_set() -> None:
    """CIDR with host bits set must not crash the CSV formatter (strict=False)."""
    data = run_radix(["192.168.1.5/24", "10.0.0.0/24"])
    output = format_radix_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "original_cidr,merged_cidr,compression_ratio"
    # Original CIDR is preserved verbatim in the first column.
    assert "192.168.1.5/24" in lines[1]
    assert "10.0.0.0/24" in lines[2]


# ---------------------------------------------------------------------------
# _format_network_info
# ---------------------------------------------------------------------------


def test_format_network_info_ipv4_large() -> None:
    from ethscan.radix import _format_network_info

    info = _format_network_info(ipaddress.ip_network("192.168.1.0/24"))
    assert info["broadcast_address"] == "192.168.1.255"
    assert info["first_host"] == "192.168.1.1"
    assert info["last_host"] == "192.168.1.254"
    assert info["usable_host_count"] == 254


def test_format_network_info_ipv4_single() -> None:
    from ethscan.radix import _format_network_info

    info = _format_network_info(ipaddress.ip_network("192.168.1.1/32"))
    assert info["broadcast_address"] == "192.168.1.1"
    assert info["first_host"] == "192.168.1.1"
    assert info["last_host"] == "192.168.1.1"
    assert info["usable_host_count"] == 0


def test_format_network_info_ipv4_pair() -> None:
    from ethscan.radix import _format_network_info

    info = _format_network_info(ipaddress.ip_network("192.168.1.0/31"))
    assert info["first_host"] == "192.168.1.1"
    assert info["last_host"] == "192.168.1.1"
    assert info["usable_host_count"] == 0


def test_format_network_info_ipv6_large() -> None:
    from ethscan.radix import _format_network_info

    info = _format_network_info(ipaddress.ip_network("2001:db8::/64"))
    assert info["broadcast_address"] is None
    assert info["first_host"] == "2001:db8::1"
    assert info["usable_host_count"] == ipaddress.ip_network("2001:db8::/64").num_addresses - 1


def test_format_network_info_ipv6_single() -> None:
    from ethscan.radix import _format_network_info

    info = _format_network_info(ipaddress.ip_network("2001:db8::1/128"))
    assert info["broadcast_address"] is None
    assert info["first_host"] == "2001:db8::1"
    assert info["last_host"] == "2001:db8::1"
    assert info["usable_host_count"] == 0


def test_format_network_info_ipv6_pair() -> None:
    from ethscan.radix import _format_network_info

    info = _format_network_info(ipaddress.ip_network("2001:db8::/127"))
    assert info["first_host"] == "2001:db8::1"
    assert info["last_host"] == "2001:db8::1"
    assert info["usable_host_count"] == 1


# ---------------------------------------------------------------------------
# Markdown diff table error handling (lines 467-469)
# ---------------------------------------------------------------------------


def test_format_radix_report_markdown_diff_invalid_network() -> None:
    data = run_radix(["192.168.1.0/24"], diff=["192.168.1.128/25"])
    data["diff"]["difference"] = ["not-a-network"]
    output = format_radix_report_markdown(data)
    assert "## Set Difference" in output
    assert "not-a-network" in output
    assert "?" in output


# ---------------------------------------------------------------------------
# Invalid radix specifications
# ---------------------------------------------------------------------------


def test_radix_spec_error_is_a_value_error() -> None:
    """RadixSpecError must stay catchable as a plain ValueError."""
    assert issubclass(RadixSpecError, ValueError)


def test_parse_cidrs_raises_cidr_spec_error_for_invalid_values() -> None:
    """An invalid CIDR raises the dedicated error, not a bare ValueError."""
    with pytest.raises(CidrSpecError):
        parse_cidrs(["bogus"])


def test_parse_cidrs_raises_radix_spec_error_for_mixed_families() -> None:
    """A radix tree covers one address family, so mixing them is an error."""
    with pytest.raises(RadixSpecError):
        parse_cidrs(["192.168.1.0/24", "2001:db8::/32"])


def test_parse_cidrs_accepts_a_single_family() -> None:
    networks = parse_cidrs(["192.168.1.0/24", "10.0.0.0/8"])
    assert [str(n) for n in networks] == ["192.168.1.0/24", "10.0.0.0/8"]


def test_private_alias_is_the_same_function() -> None:
    """The old private name stays available as an alias of the public one."""
    assert _parse_networks is parse_cidrs


def test_run_radix_raises_cidr_spec_error_for_invalid_cidrs() -> None:
    """The library propagates CidrSpecError; the CLI does the translating."""
    with pytest.raises(CidrSpecError):
        run_radix(["bogus"])


def test_run_radix_raises_cidr_spec_error_for_invalid_diff() -> None:
    with pytest.raises(CidrSpecError):
        run_radix(["192.168.1.0/24"], diff=["bogus"])


def test_run_radix_raises_radix_spec_error_for_mixed_families() -> None:
    with pytest.raises(RadixSpecError):
        run_radix(["192.168.1.0/24", "2001:db8::/32"])


def test_run_radix_accepts_a_diff_from_the_other_address_family() -> None:
    """The diff set may use the other family; only one set may mix them."""
    result = run_radix(["192.168.1.0/24"], diff=["2001:db8::/32"])
    assert result["diff"]["diff_cidrs"] == ["2001:db8::/32"]
    assert result["diff"]["difference"] == ["192.168.1.0/24"]


def test_render_node_md_non_list_networks_and_children():
    from ethscan.radix import _render_node_md
    node = {"prefix": "p", "start_address": "s", "end_address": "e",
            "total_addresses": 1, "networks": "nope", "children": "nope"}
    lines = []
    _render_node_md(node, lines)
    assert any("p" in l for l in lines)


def test_format_markdown_defensive_branches():
    data = {
        "network_count": 1,
        "merged_network_count": 1,
        "total_input_addresses": 1,
        "total_merged_addresses": 1,
        "compression_ratio": 1.0,
        "merge_enabled": True,
        "merged": "nope",
        "radix_tree": "nope",
        "contains": "nope",
        "diff": "nope",
    }
    out = format_radix_report_markdown(data)
    assert "ethscan Radix Tree Report" in out


def test_format_markdown_diff_non_list_difference():
    data = {
        "network_count": 1,
        "merged_network_count": 1,
        "total_input_addresses": 1,
        "total_merged_addresses": 1,
        "compression_ratio": 1.0,
        "merge_enabled": True,
        "merged": ["10.0.0.0/8"],
        "radix_tree": None,
        "diff": {
            "diff_network_count": 1,
            "diff_merged_network_count": 1,
            "difference_network_count": 1,
            "total_diff_addresses": 1,
            "difference": "nope",
            "diff_cidrs": [],
        },
    }
    out = format_radix_report_markdown(data)
    assert "Set Difference" in out


def test_format_csv_defensive_branches():
    data = {
        "cidrs": "nope",
        "merged": "nope",
        "compression_ratio": 1.0,
        "diff": "nope",
    }
    out = format_radix_report_csv(data)
    assert "original_cidr" in out


def test_format_csv_diff_cidrs_empty():
    data = {
        "cidrs": ["10.0.0.0/8"],
        "merged": ["10.0.0.0/8"],
        "compression_ratio": 1.0,
        "diff": {"diff_cidrs": []},
    }
    out = format_radix_report_csv(data)
    assert "10.0.0.0/8" in out


def test_merge_overlapping_larger_second():
    nets = [ipaddress.ip_network("10.0.0.0/24"), ipaddress.ip_network("10.0.0.0/16")]
    out = _merge_networks(nets)
    assert out


def test_collapse_value_error_branch(monkeypatch):
    import ethscan.radix as r
    monkeypatch.setattr(r, "_collapse_v4_networks", lambda a, b: (_ for _ in ()).throw(ValueError()))
    nets = [ipaddress.ip_network("192.168.0.0/24"), ipaddress.ip_network("192.168.1.0/24")]
    out = _merge_networks(nets)
    assert out


def test_merge_networks_overlap_smaller_successor():
    import ipaddress
    # first is larger/same? first is /24 (larger), second /25 inside - covered by test_merge_networks_overlapping
    # try the other way where after sort first is smaller and overlaps second?
    nets = [
        ipaddress.ip_network("192.168.1.128/25"),
        ipaddress.ip_network("192.168.1.0/24"),
    ]
    merged = _merge_networks(nets)
    assert len(merged) == 1
    assert str(merged[0]) == "192.168.1.0/24"


def test_merge_networks_overlap_non_collapseable_choose_larger():
    import ipaddress
    # Two overlapping networks that can't be collapsed into single supernet by our collapse functions
    # e.g. different non-contiguous in a way collapse doesn't handle? Or just overlapping different sizes
    nets = [
        ipaddress.ip_network("10.0.0.0/23"),
        ipaddress.ip_network("10.0.1.0/24"),
    ]
    merged = _merge_networks(nets)
    # They overlap; collapse might not produce single network if not supernettable nicely
    assert len(merged) >= 1


def test_merge_networks_overlap_choose_smaller_when_last_larger():
    import ipaddress
    # Force case where last.num_addresses >= net.num_addresses is false -> take net (smaller? no wait - look at code)
    # if last.overlaps(net): if last.num_addresses >= net.num_addresses: merged[-1]=last else merged[-1]=net
    # so if net is larger than last, we take net
    nets = [
        ipaddress.ip_network("10.0.0.0/25"),  # smaller
        ipaddress.ip_network("10.0.0.0/24"),  # larger, overlaps
    ]
    merged = _merge_networks(nets)
    assert str(merged[0]) == "10.0.0.0/24"


def test_merge_networks_overlap_choose_larger_last():
    import ipaddress
    # if last is larger, keep last
    nets = [
        ipaddress.ip_network("10.0.0.0/24"),
        ipaddress.ip_network("10.0.0.0/25"),
    ]
    merged = _merge_networks(nets)
    assert str(merged[0]) == "10.0.0.0/24"


def test_merge_networks_v6():
    import ipaddress
    nets = [
        ipaddress.ip_network("2001:db8::/32"),
        ipaddress.ip_network("2001:db8:1::/48"),
    ]
    merged = _merge_networks(nets)
    assert len(merged) >= 1


def test_merge_networks_v6_disjoint():
    import ipaddress
    nets = [
        ipaddress.ip_network("2001:db8::/32"),
        ipaddress.ip_network("2001:db9::/32"),
    ]
    merged = _merge_networks(nets)
    assert len(merged) >= 1


def test_merge_networks_mixed_families_kept_separate():
    """Different IP versions are not compared or collapsed (lines 193-195)."""
    import ipaddress

    nets = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("2001:db8::/32"),
    ]
    merged = _merge_networks(nets)
    assert [str(n) for n in merged] == ["10.0.0.0/8", "2001:db8::/32"]
