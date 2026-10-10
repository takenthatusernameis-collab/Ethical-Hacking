"""Tests for the ethscan scanner module."""

import pytest

from ethscan.scanner import (
    COMMON_PORTS,
    FAST_PORTS,
    FULL_PORTS,
    PROFILE_DEFAULTS,
    get_common_ports,
    get_profile_defaults,
    get_profile_ports,
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


def test_get_profile_ports_fast() -> None:
    ports = get_profile_ports("fast")
    assert isinstance(ports, list)
    assert ports == FAST_PORTS


def test_get_profile_ports_normal() -> None:
    ports = get_profile_ports("normal")
    assert isinstance(ports, list)
    assert ports == COMMON_PORTS


def test_get_profile_ports_full() -> None:
    ports = get_profile_ports("full")
    assert isinstance(ports, list)
    assert ports == FULL_PORTS


def test_get_profile_ports_case_insensitive() -> None:
    assert get_profile_ports("FAST") == FAST_PORTS
    assert get_profile_ports("Normal") == COMMON_PORTS
    assert get_profile_ports("FULL") == FULL_PORTS


def test_get_profile_ports_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown profile: invalid"):
        get_profile_ports("invalid")


def test_get_profile_defaults_fast() -> None:
    defaults = get_profile_defaults("fast")
    assert defaults == {"timeout": 0.5, "workers": 200}
    assert defaults["timeout"] == 0.5
    assert defaults["workers"] == 200


def test_get_profile_defaults_normal() -> None:
    defaults = get_profile_defaults("normal")
    assert defaults == {"timeout": 1.0, "workers": 100}
    assert defaults["timeout"] == 1.0
    assert defaults["workers"] == 100


def test_get_profile_defaults_full() -> None:
    defaults = get_profile_defaults("full")
    assert defaults == {"timeout": 2.0, "workers": 50}
    assert defaults["timeout"] == 2.0
    assert defaults["workers"] == 50


def test_get_profile_defaults_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown profile: invalid"):
        get_profile_defaults("invalid")