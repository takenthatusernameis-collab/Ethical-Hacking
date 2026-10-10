"""Tests for the ethscan scanner module."""

import pytest

from ethscan.scanner import (
    COMMON_PORTS,
    get_common_ports,
    parse_port_range,
    scan_port,
    scan_ports,
)


def test_parse_port_range_single() -> None:
    assert parse_port_range("80") == [80]


def test_parse_port_range_multiple() -> None:
    assert parse_port_range("80,443,8080") == [80, 443, 8080]


def test_parse_port_range_range() -> None:
    assert parse_port_range("1-5") == [1, 2, 3, 4, 5]


def test_parse_port_range_mixed() -> None:
    assert parse_port_range("80,100-102,443") == [80, 100, 101, 102, 443]


def test_parse_port_range_whitespace() -> None:
    assert parse_port_range(" 80 , 443 , 8080 ") == [80, 443, 8080]


def test_parse_port_range_duplicates() -> None:
    assert parse_port_range("80,80,443") == [80, 443]


def test_get_common_ports() -> None:
    ports = get_common_ports()
    assert isinstance(ports, list)
    assert len(ports) > 0
    assert ports == COMMON_PORTS


def test_scan_port_localhost_closed() -> None:
    # Port 1 is typically closed on localhost
    port, is_open = scan_port("127.0.0.1", 1, timeout=0.1)
    assert port == 1
    assert is_open is False


def test_scan_ports_localhost() -> None:
    results = scan_ports("127.0.0.1", [1, 2, 3], timeout=0.1, max_workers=10)
    assert len(results) == 3
    for port, is_open in results:
        assert port in [1, 2, 3]
        assert isinstance(is_open, bool)