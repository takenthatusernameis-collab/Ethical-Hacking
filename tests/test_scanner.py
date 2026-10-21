"""Tests for the ethscan scanner module."""

import pytest

from ethscan.scanner import (
    COMMON_PORTS,
    FAST_PORTS,
    FULL_PORTS,
    PortSpecError,
    format_scan_report_csv,
    format_scan_report_json,
    format_scan_report_markdown,
    get_all_ports,
    get_common_ports,
    get_profile_defaults,
    get_profile_ports,
    parse_port_range,
    resolve_port_list,
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


def test_parse_port_range_out_of_range_high() -> None:
    """A port above 65535 must be rejected, not silently scanned."""
    with pytest.raises(ValueError):
        parse_port_range("70000")


def test_parse_port_range_out_of_range_negative() -> None:
    """A negative port must be rejected, not silently scanned."""
    with pytest.raises(ValueError):
        parse_port_range("-1")


def test_parse_port_range_inverted_range() -> None:
    """An inverted range (start > end) must be rejected, not silently empty."""
    with pytest.raises(ValueError):
        parse_port_range("100-50")


def test_parse_port_range_non_numeric() -> None:
    """A non-numeric token must be rejected with a clear error."""
    with pytest.raises(ValueError):
        parse_port_range("abc")


def test_parse_port_range_missing_range_end() -> None:
    """A range missing its end (e.g. ``80-``) must be rejected."""
    with pytest.raises(ValueError):
        parse_port_range("80-")


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


def test_scan_port_transport_failure_is_reported(monkeypatch) -> None:
    """A transport failure of an unnamed type is reported as a closed port."""
    from ethscan import scanner as scanner_mod

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.scanner.socket.create_connection", boom)

    assert scanner_mod.scan_port("127.0.0.1", 80) == (80, False)


def test_scan_ports_transport_failure_is_reported(monkeypatch) -> None:
    """A failing transport does not escape the concurrent scan either."""
    from ethscan import scanner as scanner_mod

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.scanner.socket.create_connection", boom)

    assert scanner_mod.scan_ports("127.0.0.1", [80, 443]) == [(80, False), (443, False)]


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


def test_resolve_port_list_common_keyword() -> None:
    assert resolve_port_list("common") == get_common_ports()


def test_resolve_port_list_all_keyword() -> None:
    assert resolve_port_list("all") == get_all_ports()


def test_resolve_port_list_keywords_are_case_insensitive() -> None:
    assert resolve_port_list("COMMON") == COMMON_PORTS
    assert resolve_port_list("Common") == COMMON_PORTS
    assert resolve_port_list("ALL") == list(range(1, 65536))
    assert resolve_port_list("All") == list(range(1, 65536))


def test_resolve_port_list_ranges_still_work() -> None:
    assert resolve_port_list("80,443,8000-9000") == [80, 443] + list(range(8000, 9001))


def test_resolve_port_list_common_with_profile_uses_profile_ports() -> None:
    assert resolve_port_list("common", profile="fast") == FAST_PORTS
    assert resolve_port_list("common", profile="normal") == COMMON_PORTS
    assert resolve_port_list("common", profile="full") == FULL_PORTS


def test_resolve_port_list_all_with_profile_uses_all_ports() -> None:
    assert resolve_port_list("all", profile="fast") == list(range(1, 65536))


def test_resolve_port_list_explicit_range_with_profile() -> None:
    assert resolve_port_list("22,80", profile="fast") == [22, 80]


def test_resolve_port_list_invalid_keyword_rejected() -> None:
    with pytest.raises(ValueError):
        resolve_port_list("abc")


def test_format_scan_report_json() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 3,
        "open_ports": [22, 80],
        "details": [
            {"port": 22, "open": True},
            {"port": 80, "open": True},
            {"port": 443, "open": False},
        ],
    }
    output = format_scan_report_json(data)
    assert '"target": "127.0.0.1"' in output
    assert "22" in output and "80" in output  # open_ports contains 22 and 80
    assert '"port": 22' in output
    assert '"open": true' in output


def test_format_scan_report_json_empty() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 0,
        "open_ports": [],
        "details": [],
    }
    output = format_scan_report_json(data)
    assert '"open_ports": []' in output
    assert '"details": []' in output


def test_format_scan_report_markdown() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 3,
        "open_ports": [22, 80],
        "details": [
            {"port": 22, "open": True},
            {"port": 80, "open": True},
            {"port": 443, "open": False},
        ],
    }
    output = format_scan_report_markdown(data)
    assert "# ethscan Port Scan Report" in output
    assert "**Target:** 127.0.0.1" in output
    assert "**Open Ports:** 22, 80" in output
    assert "## Port Details" in output
    assert "| Port | Status |" in output
    assert "| 22 | Open |" in output
    assert "| 443 | Closed |" in output


def test_format_scan_report_markdown_no_open_ports() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 3,
        "open_ports": [],
        "details": [
            {"port": 22, "open": False},
            {"port": 80, "open": False},
            {"port": 443, "open": False},
        ],
    }
    output = format_scan_report_markdown(data)
    assert "**Open Ports:** None" in output


def test_format_scan_report_markdown_no_ports_scanned() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 0,
        "open_ports": [],
        "details": [],
    }
    output = format_scan_report_markdown(data)
    assert "*No ports scanned.*" in output


def test_format_scan_report_csv() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 3,
        "open_ports": [22, 80],
        "details": [
            {"port": 22, "open": True},
            {"port": 80, "open": True},
            {"port": 443, "open": False},
        ],
    }
    output = format_scan_report_csv(data)
    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "port,open"
    assert "22,true" in lines
    assert "80,true" in lines
    assert "443,false" in lines


def test_format_scan_report_csv_empty() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 0,
        "open_ports": [],
        "details": [],
    }
    output = format_scan_report_csv(data)
    assert output.strip() == "port,open"

def test_port_spec_error_is_a_value_error() -> None:
    """PortSpecError must stay catchable as a ValueError.

    The CLI layer relies on the dedicated type to tell an invalid port
    specification apart from unrelated value errors, but existing callers
    that catch ValueError must keep working.
    """
    assert issubclass(PortSpecError, ValueError)


def test_parse_port_range_raises_port_spec_error() -> None:
    """An invalid specification must raise the dedicated error type."""
    with pytest.raises(PortSpecError):
        parse_port_range("bogus")


def test_parse_port_range_errors_are_value_errors() -> None:
    """The dedicated error type must not break plain ValueError handling."""
    with pytest.raises(ValueError):
        parse_port_range("70000")


def test_resolve_port_list_raises_port_spec_error() -> None:
    """resolve_port_list must surface the dedicated error type as well."""
    with pytest.raises(PortSpecError):
        resolve_port_list("bogus")


def test_resolve_port_list_with_profile_raises_port_spec_error() -> None:
    """The profile branch must surface the dedicated error type as well."""
    with pytest.raises(PortSpecError):
        resolve_port_list("bogus", profile="fast")
