"""Tests for the shared target-specification error type.

The protocol modules raise :class:`TargetSpecError` when a target string
does not contain a usable host. The CLI turns that into a usage error, but
the modules that report a failed probe inside their own output keep
catching it as an ordinary :class:`ValueError`.

A target whose *port* is not a number is the same kind of problem:
``urllib.parse`` raises a bare ``ValueError`` for it, which
:func:`url_port` re-raises as a :class:`TargetSpecError`.
"""

import importlib
from urllib.parse import urlparse

import pytest

from ethscan.target import TargetSpecError, url_port

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

