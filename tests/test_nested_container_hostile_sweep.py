"""Permanent sweep test: hostile nested response containers never raise.

The protocol-recon formatters (mongodb, mssql, mysql, ntp, postgresql, redis)
each render a nested response container (``buildInfo``, ``prelogin``,
``handshake``, ``time_response`` / ``monlist_response``, ``startup``,
``info`` / ``config``). A hostile or malformed answer can put any shape in
that slot; the formatters must treat a non-dict as empty rather than raising.

Covers both public output formats for every module against non-dict scalars,
lists, and strings, plus a well-formed regression for each container.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan import mongodb, mssql, mysql, ntp, postgresql, redis

FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    mongodb.format_mongodb_report_markdown,
    mongodb.format_mongodb_report_csv,
    mssql.format_mssql_report_markdown,
    mssql.format_mssql_report_csv,
    mysql.format_mysql_report_markdown,
    mysql.format_mysql_report_csv,
    ntp.format_ntp_report_markdown,
    ntp.format_ntp_report_csv,
    postgresql.format_postgresql_report_markdown,
    postgresql.format_postgresql_report_csv,
    redis.format_redis_report_markdown,
    redis.format_redis_report_csv,
]

# One representative nested container key per formatter, in the same order as
# FORMATTERS above.
CONTAINER_KEYS: list[str] = [
    "buildInfo",
    "buildInfo",
    "prelogin",
    "prelogin",
    "handshake",
    "handshake",
    "time_response",
    "time_response",
    "startup",
    "startup",
    "info",
    "info",
]

# A second container key per formatter where the module renders more than one.
SECONDARY_KEYS: list[str | None] = [
    None,
    None,
    None,
    None,
    None,
    None,
    "monlist_response",
    "monlist_response",
    None,
    None,
    "config",
    "config",
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


HOSTILE_CONTAINERS: list[object] = [
    None,
    0,
    1,
    True,
    3.14,
    "str",
    "error",
    "version",
    [],
    [None],
    ["a"],
    [{"nested": True}],
]


@pytest.mark.parametrize("formatter", FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("container", HOSTILE_CONTAINERS)
def test_formatters_tolerate_hostile_container(
    formatter: Callable[[dict[str, Any]], str], container: object
) -> None:
    key = CONTAINER_KEYS[FORMATTERS.index(formatter)]
    output = formatter({key: container})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("container", HOSTILE_CONTAINERS)
def test_formatters_tolerate_hostile_secondary_container(
    formatter: Callable[[dict[str, Any]], str], container: object
) -> None:
    key = SECONDARY_KEYS[FORMATTERS.index(formatter)]
    if key is None:
        pytest.skip("formatter has no secondary container")
    output = formatter({key: container})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", FORMATTERS, ids=_formatter_id)
def test_formatters_tolerate_both_containers_hostile(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    key = CONTAINER_KEYS[FORMATTERS.index(formatter)]
    secondary = SECONDARY_KEYS[FORMATTERS.index(formatter)]
    data: dict[str, Any] = {key: 1}
    if secondary is not None:
        data[secondary] = ["x"]
    output = formatter(data)
    assert isinstance(output, str)


WELL_FORMED: dict[str, dict[str, Any]] = {
    "format_mongodb_report_markdown": {
        "buildInfo": {"version": "5.0.0", "sysInfo": "Linux", "modules": "ssl"}
    },
    "format_mongodb_report_csv": {
        "buildInfo": {"version": "5.0.0", "sysInfo": "Linux", "modules": "ssl"}
    },
    "format_mssql_report_markdown": {
        "prelogin": {
            "version": "v1",
            "encryption": "on",
            "instance_name": "i",
            "thread_id": 3,
        }
    },
    "format_mssql_report_csv": {
        "prelogin": {
            "version": "v1",
            "encryption": "on",
            "instance_name": "i",
            "thread_id": 3,
        }
    },
    "format_mysql_report_markdown": {
        "handshake": {
            "protocol_version": 10,
            "thread_id": 7,
            "capabilities": "c",
            "charset": 8,
            "status": 2,
            "auth_plugin_name": "mysql_native_password",
        }
    },
    "format_mysql_report_csv": {
        "handshake": {
            "protocol_version": 10,
            "thread_id": 7,
            "capabilities": "c",
            "charset": 8,
            "status": 2,
            "auth_plugin_name": "mysql_native_password",
        }
    },
    "format_ntp_report_markdown": {
        "time_response": {"version": 4, "stratum": 2},
        "monlist_response": {"peer_count": 1},
    },
    "format_ntp_report_csv": {
        "time_response": {"version": 4, "stratum": 2},
        "monlist_response": {"peer_count": 1},
    },
    "format_postgresql_report_markdown": {
        "startup": {
            "server_version": "16.0",
            "auth_type_name": "MD5Password",
            "auth_type_code": 3,
            "process_id": 42,
            "parameters": {"server_version": "16.0", "client_encoding": "UTF8"},
        }
    },
    "format_postgresql_report_csv": {
        "startup": {
            "server_version": "16.0",
            "auth_type_name": "MD5Password",
            "auth_type_code": 3,
            "process_id": 42,
        }
    },
    "format_redis_report_markdown": {
        "info": {"redis_version": "7.0.0", "os": "Linux", "role": "master"},
        "config": {"bind": "*", "requirepass": "secret"},
    },
    "format_redis_report_csv": {
        "info": {"redis_version": "7.0.0", "os": "Linux", "role": "master"},
        "config": {"bind": "*", "requirepass": "secret"},
    },
}


@pytest.mark.parametrize("formatter", FORMATTERS, ids=_formatter_id)
def test_formatters_render_well_formed_containers(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter(WELL_FORMED[formatter.__name__])
    assert isinstance(output, str)
    assert output.strip()


def test_postgresql_parameters_mixed_key_types_do_not_raise() -> None:
    output = postgresql.format_postgresql_report_markdown(
        {"startup": {"parameters": {1: "a", "b": 2}}}
    )
    assert isinstance(output, str)
    assert "## Server Parameters" in output