"""Bare (unbracketed) IPv6 targets are hosts, not ``host:port`` pairs.

The protocol modules share a small ``_normalize_target`` helper that strips
an optional ``:port`` suffix from a bare target. A regex-free port split must
not treat the numeric tail of an unbracketed IPv6 literal as a port: ``::1``
used to be read as host ``":"`` on port ``1`` (and ``2001:db8::1`` as host
``"2001:db8:"`` on port ``1``), so the probe contacted the wrong endpoint.
An IPv6 literal may only carry a port when it is bracketed.
"""

from types import ModuleType

import pytest

from ethscan import (
    ftp,
    ldap,
    memcached,
    mongodb,
    mssql,
    mysql,
    netbios,
    ntp,
    oracle,
    postgresql,
    redis,
    smb,
    smtp,
    snmp,
)

TARGET_MODULES: list[tuple[ModuleType, int]] = [
    (ftp, 21),
    (ldap, 389),
    (memcached, 11211),
    (mongodb, 27017),
    (mssql, 1433),
    (mysql, 3306),
    (netbios, 137),
    (ntp, 123),
    (oracle, 1521),
    (postgresql, 5432),
    (redis, 6379),
    (smb, 445),
    (smtp, 25),
    (snmp, 161),
]

_MODULE_IDS = [module.__name__.rsplit(".", 1)[-1] for module, _ in TARGET_MODULES]


@pytest.mark.parametrize(
    "module, default_port", TARGET_MODULES, ids=_MODULE_IDS
)
def test_bare_ipv6_literal_is_kept_whole(
    module: ModuleType, default_port: int
) -> None:
    for target in ("::1", "2001:db8::1", "fe80::1", "::ffff:192.0.2.1"):
        host, port = module._normalize_target(target)
        assert host == target
        assert port == default_port


@pytest.mark.parametrize(
    "module, default_port", TARGET_MODULES, ids=_MODULE_IDS
)
def test_host_port_and_bare_ipv4_still_split(
    module: ModuleType, default_port: int
) -> None:
    assert module._normalize_target("example.com:1234") == ("example.com", 1234)
    assert module._normalize_target("192.0.2.1") == ("192.0.2.1", default_port)


@pytest.mark.parametrize(
    "module, default_port", TARGET_MODULES, ids=_MODULE_IDS
)
def test_bracketed_ipv6_still_parses(
    module: ModuleType, default_port: int
) -> None:
    assert module._normalize_target("[2001:db8::1]:9999") == ("2001:db8::1", 9999)
    assert module._normalize_target("[2001:db8::1]") == ("2001:db8::1", default_port)


def test_ntp_probe_uses_bare_ipv6_host() -> None:
    """The probe must dial the IPv6 literal itself, not host ``:`` port 1."""
    seen: list[tuple[str, int]] = []

    def connector(host: str, port: int, request: bytes, timeout: float):
        seen.append((host, port))
        return None, "timeout"

    result = ntp.run_ntp("::1", connector=connector)

    assert seen == [("::1", 123)]
    assert result["host"] == "::1"
    assert result["port"] == 123
