"""Tests for the shared target-specification error type.

The protocol modules raise :class:`TargetSpecError` when a target string
does not contain a usable host. The CLI turns that into a usage error, but
the modules that report a failed probe inside their own output keep
catching it as an ordinary :class:`ValueError`.

A target whose *port* is not a number is the same kind of problem:
``urllib.parse`` raises a bare ``ValueError`` for it, which
:func:`url_port` re-raises as a :class:`TargetSpecError`.

A target whose *host* contains a space or a control character is the same
kind of problem too: ``http.client`` refuses such a host with an
``http.client.InvalidURL``, which derives from ``HTTPException`` and not
from ``ValueError``, so :func:`check_target_host` reports it as a
:class:`TargetSpecError` before the request is made.
"""

import importlib
from urllib.parse import urlparse

import pytest

from ethscan.target import TargetSpecError, check_target_host, url_port

TARGET_MODULES = (
    "redis",
    "memcached",
    "ntp",
    "snmp",
    "ftp",
    "ldap",
    "netbios",
    "smb",
    "smtp",
    "mysql",
    "mongodb",
    "oracle",
    "postgresql",
    "mssql",
)

# The modules that treat an unparsable target as a failed probe and report
# it inside their own output instead of failing the whole run.
PROBE_FAILURE_MODULES = (
    "mysql",
    "mongodb",
    "oracle",
    "postgresql",
    "mssql",
)

UNUSABLE_TARGETS = ("", "   ", "://no-host", "redis://", ":6379")


def test_target_spec_error_is_a_value_error() -> None:
    """The error type must stay a ValueError subclass."""
    assert issubclass(TargetSpecError, ValueError)


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_unusable_target_raises_target_spec_error(module_name: str) -> None:
    """Every protocol module raises the dedicated error type."""
    module = importlib.import_module(f"ethscan.{module_name}")
    for target in UNUSABLE_TARGETS:
        with pytest.raises(TargetSpecError):
            module._normalize_target(target)


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_unusable_target_is_still_caught_as_a_value_error(module_name: str) -> None:
    """Existing ``except ValueError`` handlers keep working."""
    module = importlib.import_module(f"ethscan.{module_name}")
    with pytest.raises(ValueError):
        module._normalize_target("")


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_usable_target_is_not_an_error(module_name: str) -> None:
    """Valid targets are unaffected by the error type change."""
    module = importlib.import_module(f"ethscan.{module_name}")
    assert module._normalize_target("127.0.0.1:1234") == ("127.0.0.1", 1234)
    assert module._normalize_target("127.0.0.1")[0] == "127.0.0.1"


@pytest.mark.parametrize("module_name", PROBE_FAILURE_MODULES)
def test_probe_failure_modules_still_report_the_error_in_their_output(
    module_name: str,
) -> None:
    """A module that reports a failed probe keeps its contract."""
    module = importlib.import_module(f"ethscan.{module_name}")
    run = getattr(module, f"run_{module_name}")
    results = run("")
    assert results["accessible"] is False
    assert results["error"] == "Could not parse host from target ''"


def test_the_error_type_is_raised_by_every_module_that_reports_a_host() -> None:
    """The dedicated type is used consistently, not just for empty targets."""
    module = importlib.import_module("ethscan.redis")
    with pytest.raises(TargetSpecError) as excinfo:
        module._normalize_target("   ")
    assert str(excinfo.value) == "Could not parse host from target '   '"


# --- A target whose port is not a number -----------------------------------

NON_NUMERIC_PORT_MESSAGE = "Port could not be cast to integer value as 'notaport'"


def test_url_port_returns_the_port_of_a_parsed_url() -> None:
    """A valid port is returned unchanged."""
    assert url_port(urlparse("redis://host:6379")) == 6379
    assert url_port(urlparse("redis://host:0")) == 0


def test_url_port_returns_none_when_the_url_has_no_port() -> None:
    """A URL without a port keeps reporting ``None``."""
    assert url_port(urlparse("redis://host")) is None


def test_url_port_raises_target_spec_error_for_a_non_numeric_port() -> None:
    """A port that is not a number is reported as an unusable target."""
    with pytest.raises(TargetSpecError) as excinfo:
        url_port(urlparse("redis://host:notaport"))
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE


def test_url_port_raises_target_spec_error_for_an_out_of_range_port() -> None:
    """A port outside the valid range is reported as an unusable target."""
    with pytest.raises(TargetSpecError) as excinfo:
        url_port(urlparse("redis://host:99999"))
    assert str(excinfo.value) == "Port out of range 0-65535"


def test_url_port_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    with pytest.raises(ValueError):
        url_port(urlparse("redis://host:notaport"))


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_non_numeric_port_raises_target_spec_error(module_name: str) -> None:
    """Every protocol module rejects a URL whose port is not a number."""
    module = importlib.import_module(f"ethscan.{module_name}")
    with pytest.raises(TargetSpecError) as excinfo:
        module._normalize_target("redis://host:notaport")
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_valid_port_is_still_parsed(module_name: str) -> None:
    """A URL with a real port keeps being parsed as before."""
    module = importlib.import_module(f"ethscan.{module_name}")
    assert module._normalize_target("redis://host:6379") == ("host", 6379)


@pytest.mark.parametrize("module_name", PROBE_FAILURE_MODULES)
def test_probe_failure_modules_report_a_non_numeric_port_unchanged(
    module_name: str,
) -> None:
    """A module that reports a failed probe keeps its wording."""
    module = importlib.import_module(f"ethscan.{module_name}")
    run = getattr(module, f"run_{module_name}")
    results = run("mysql://host:notaport")
    assert results["accessible"] is False
    assert results["error"] == NON_NUMERIC_PORT_MESSAGE


def test_web_and_ssh_report_a_non_numeric_port_as_a_target_error() -> None:
    """The URL-based modules reject a port that is not a number."""
    from ethscan import ssh, web

    with pytest.raises(TargetSpecError) as excinfo:
        web._parse_url("https://host:notaport")
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE

    with pytest.raises(TargetSpecError) as excinfo:
        ssh._extract_port("host:notaport")
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE


def test_web_and_ssh_still_parse_a_valid_port() -> None:
    """A valid port keeps being parsed exactly as before."""
    from ethscan import ssh, web

    assert web._parse_url("https://example.com:8443") == ("example.com", 8443, True)
    assert web._parse_url("http://example.com:8080") == ("example.com", 8080, False)
    assert web._parse_url("example.com") == ("example.com", 443, True)
    assert ssh._extract_port("ssh://example.com:2222") == 2222
    assert ssh._extract_port("example.com") == 22


# --- A target whose host contains a space or a control character ------------

HOST_ERROR_MESSAGE = "Target host contains a space or control character"

HOSTILE_HOST_TARGETS = (
    "host name",
    "host\tname",
    "host\nname",
    "ho\x00st",
    "host\x7fname",
    "https://host name",
    "http://host name",
    "https://host\tname",
    "host name:8443",
    "https://host name:8443",
)

USABLE_HOST_TARGETS = (
    "host",
    "host:443",
    "http://host",
    "https://host:8443",
    "[::1]:443",
    "example.com/path",
    "https://example.com/path?query=1",
)


def test_check_target_host_rejects_a_host_with_a_space() -> None:
    """A host with a space is reported as an unusable target."""
    with pytest.raises(TargetSpecError) as excinfo:
        check_target_host("host name")
    assert str(excinfo.value) == HOST_ERROR_MESSAGE


def test_check_target_host_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    with pytest.raises(ValueError):
        check_target_host("host name")


@pytest.mark.parametrize("target", HOSTILE_HOST_TARGETS)
def test_check_target_host_rejects_every_hostile_host(target: str) -> None:
    """A space or a control character in the host is always rejected."""
    with pytest.raises(TargetSpecError) as excinfo:
        check_target_host(target)
    assert str(excinfo.value) == HOST_ERROR_MESSAGE


@pytest.mark.parametrize("target", USABLE_HOST_TARGETS)
def test_check_target_host_accepts_a_usable_host(target: str) -> None:
    """A host that ``http.client`` accepts is not an error."""
    check_target_host(target)


def test_a_control_character_is_found_although_urlsplit_removes_it() -> None:
    """The check reads the raw target, not the parsed one.

    ``urllib.parse`` silently drops tab, carriage return and newline
    characters, so a parsed host can look clean while the host that is
    actually sent over the network is not.
    """
    assert urlparse("https://host\tname").hostname == "hostname"
    with pytest.raises(TargetSpecError):
        check_target_host("https://host\tname")


def test_the_url_modules_reject_a_hostile_host() -> None:
    """web, fuzz and s3 refuse a target with an unusable host."""
    from ethscan import fuzz, s3, web

    parsers = (web._parse_url, fuzz._normalize_base_url, s3._normalize_target)
    for parser in parsers:
        for target in HOSTILE_HOST_TARGETS:
            with pytest.raises(TargetSpecError) as excinfo:
                parser(target)
            assert str(excinfo.value) == HOST_ERROR_MESSAGE


def test_the_url_modules_still_accept_the_valid_target_forms() -> None:
    """The working target forms keep behaving exactly as before."""
    from ethscan import fuzz, s3, web

    assert web._parse_url("example.com") == ("example.com", 443, True)
    assert web._parse_url("http://example.com:8080") == ("example.com", 8080, False)
    assert web._parse_url("https://example.com:8443") == ("example.com", 8443, True)
    assert web._parse_url("https://[::1]:443") == ("::1", 443, True)
    assert web._parse_url("") == ("localhost", 443, True)
    assert fuzz._normalize_base_url("example.com") == "https://example.com"
    assert fuzz._normalize_base_url("http://example.com") == "http://example.com"
    assert fuzz._normalize_base_url("https://example.com:8443") == (
        "https://example.com:8443"
    )
    assert s3._normalize_target("Example.com") == "example.com"
    assert s3._normalize_target("https://Example.com/path") == "example.com"
    assert s3._normalize_target("127.0.0.1:8443") == "127.0.0.1"


def test_fuzz_reports_a_non_numeric_port_like_the_other_commands() -> None:
    """fuzz hands the URL to ``http.client``, so a bad port is rejected."""
    from ethscan import fuzz

    with pytest.raises(TargetSpecError) as excinfo:
        fuzz._normalize_base_url("https://host:notaport")
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE


# --- A target whose path or query contains a space or a control character --

PATH_ERROR_MESSAGE = "Target path contains a space or control character"

HOSTILE_PATH_TARGETS = (
    "https://example.com/a b",
    "https://example.com/a\tb",
    "https://example.com/a\nb",
    "https://example.com/ho\x00st",
    "https://example.com/path\x7f",
    "https://example.com/?q=a b",
    "https://example.com/?q=a\tb",
    "http://example.com/a b",
    "example.com/a b",
)

USABLE_PATH_TARGETS = (
    "https://example.com/path",
    "https://example.com/a%20b",
    "https://example.com/?q=1",
    "https://example.com/path?query=1",
    "https://example.com/path#frag",
    "https://example.com/path?query=1#frag",
    "example.com",
    "https://example.com",
)


def test_check_target_path_rejects_a_path_with_a_space() -> None:
    """A path with a space is reported as an unusable target."""
    from ethscan.target import check_target_path

    with pytest.raises(TargetSpecError) as excinfo:
        check_target_path("https://example.com/a b")
    assert str(excinfo.value) == PATH_ERROR_MESSAGE


def test_check_target_path_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    from ethscan.target import check_target_path

    with pytest.raises(ValueError):
        check_target_path("https://example.com/a b")


@pytest.mark.parametrize("target", HOSTILE_PATH_TARGETS)
def test_check_target_path_rejects_every_hostile_path(target: str) -> None:
    """A space or a control character in the path or query is always rejected."""
    from ethscan.target import check_target_path

    with pytest.raises(TargetSpecError) as excinfo:
        check_target_path(target)
    assert str(excinfo.value) == PATH_ERROR_MESSAGE


@pytest.mark.parametrize("target", USABLE_PATH_TARGETS)
def test_check_target_path_accepts_a_usable_path(target: str) -> None:
    """A path that ``http.client`` accepts is not an error."""
    from ethscan.target import check_target_path

    check_target_path(target)


def test_check_target_path_does_not_reject_a_fragment() -> None:
    """The fragment is never sent to the server and must not be rejected."""
    from ethscan.target import check_target_path

    check_target_path("https://example.com/path#has space")
    check_target_path("https://example.com/path#tab\there")


def test_check_target_path_does_not_reject_a_percent_encoded_path() -> None:
    """A percent-encoded path keeps working."""
    from ethscan.target import check_target_path

    check_target_path("https://example.com/a%20b")
    check_target_path("https://example.com/%00encoded")


def test_check_target_path_is_a_noop_for_a_bare_host() -> None:
    """A target with no path has nothing to reject."""
    from ethscan.target import check_target_path

    check_target_path("example.com")
    check_target_path("https://example.com")
    check_target_path("")


def test_the_url_modules_reject_a_hostile_path() -> None:
    """web, headers and urlcheck refuse a target with an unusable path."""
    from ethscan import web

    for target in HOSTILE_PATH_TARGETS:
        with pytest.raises(TargetSpecError) as excinfo:
            web._parse_url(target)
        assert str(excinfo.value) == PATH_ERROR_MESSAGE


def test_the_url_modules_still_accept_the_valid_path_forms() -> None:
    """The working target forms keep behaving exactly as before."""
    from ethscan import web

    assert web._parse_url("https://example.com/path") == ("example.com", 443, True)
    assert web._parse_url("https://example.com/a%20b") == ("example.com", 443, True)
    assert web._parse_url("https://example.com/?q=1") == ("example.com", 443, True)
    assert web._parse_url("https://example.com/path#frag") == ("example.com", 443, True)

