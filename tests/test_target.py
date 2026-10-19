"""Tests for the shared target-specification error type.

The protocol modules raise :class:`TargetSpecError` when a target string
does not contain a usable host. The CLI turns that into a usage error, but
the modules that report a failed probe inside their own output keep
catching it as an ordinary :class:`ValueError`.
"""

import importlib

import pytest

from ethscan.target import TargetSpecError

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
