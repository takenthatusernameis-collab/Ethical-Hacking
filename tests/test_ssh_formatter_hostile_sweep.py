"""Permanent sweep test: hostile SSH formatter inputs are rendered, never raised.

Covers ``format_ssh_report_markdown``, ``format_ssh_report_csv`` and
``format_ssh_report_json`` against hostile top-level shapes, the four
algorithm sections (``kex_algorithms``, ``host_key_algorithms``,
``encryption_algorithms``, ``mac_algorithms``), ``host_key`` and
``findings``. Every shape yields a string and never raises; the algorithm
sections stringify elements so ``set()``/``sorted()`` never blow up on a
malformed or hostile answer.
"""
from __future__ import annotations

from typing import Any, Callable, cast

import pytest

from ethscan.ssh import (
    format_ssh_report_csv,
    format_ssh_report_json,
    format_ssh_report_markdown,
)

SSH_FORMATTERS: list[Callable[[Any], str]] = [
    format_ssh_report_markdown,
    format_ssh_report_csv,
    format_ssh_report_json,
]

ALGO_KEYS = [
    "kex_algorithms",
    "host_key_algorithms",
    "encryption_algorithms",
    "mac_algorithms",
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_ALGO_VALUES: list[object] = [
    # Non-iterable scalars: ``or []`` no longer hides these, so set()/sorted()
    # must be guarded by _normalize_algo_list.
    1,
    0,
    3.14,
    True,
    None,
    "supported",
    # Lists are accepted; their elements are stringified.
    ["a", "b"],
    [1, 2],
    [["nested"]],
    # Hostile dicts.
    {"supported": 1},
    {"weak": 1},
    {"strong": 3.14},
    {"weak": [["nested"]]},
    {"supported": ["a", 1]},
    {"supported": ["x", None, 2.5]},
    {"weak": {"a": 1}},
    {"supported": None, "weak": None, "strong": None},
    {"key": "value"},
]

NON_ITERABLE_FINDINGS: list[object] = [None, 1, 0, True, "finding", {"x": 1}, 3.14]

HOSTILE_FINDING_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
    ["not-a-dict", {"severity": "high", "description": "d"}],
    [{"severity": None, "description": 1}],
    [{"type": "kex", "algorithm": None, "severity": 2, "description": ["x"]}],
]

NON_DICT_HOST_KEY: list[object] = [None, 1, "x", [1, 2]]

HOSTILE_HOST_KEY_DICTS: list[dict[str, object]] = [
    {"key_type": None},
    {"fingerprint": 1},
    {"key_bits": "not-a-number"},
    {"key_type": {"nested": True}},
    {"key_type": "ssh-ed25519", "fingerprint": None, "key_bits": None},
]

WELL_FORMED = {
    "target": "127.0.0.1",
    "host": "127.0.0.1",
    "port": 22,
    "banner": "SSH-2.0-OpenSSH_9.0",
    "kex_algorithms": {
        "supported": ["curve25519-sha256", "diffie-hellman-group14-sha256"],
        "weak": ["diffie-hellman-group14-sha256"],
        "strong": ["curve25519-sha256"],
    },
    "host_key_algorithms": {
        "supported": ["ssh-ed25519"],
        "weak": [],
        "strong": ["ssh-ed25519"],
    },
    "encryption_algorithms": {
        "supported": ["aes128-ctr"],
        "weak": ["aes128-ctr"],
        "strong": [],
    },
    "mac_algorithms": {
        "supported": ["hmac-sha2-256"],
        "weak": [],
        "strong": ["hmac-sha2-256"],
    },
    "host_key": {
        "key_type": "ssh-ed25519",
        "fingerprint": "ab:cd:ef",
        "key_bits": 256,
    },
    "findings": [
        {
            "type": "kex",
            "algorithm": "diffie-hellman-group14-sha256",
            "severity": "medium",
            "description": "weak key exchange",
        }
    ],
}


# ---------------------------------------------------------------------------
# Non-Mapping top-level data.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", SSH_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_ssh_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_ssh_report_json:
        assert output == "{}"


# ---------------------------------------------------------------------------
# Hostile algorithm sections (markdown iterates supported/weak/strong;
# CSV/JSON only render findings, but must still not raise).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", SSH_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("algo_key", ALGO_KEYS)
@pytest.mark.parametrize("algo_value", HOSTILE_ALGO_VALUES)
def test_ssh_formatters_tolerate_hostile_algorithm_sections(
    formatter: Callable[[Any], str], algo_key: str, algo_value: object
) -> None:
    output = formatter({algo_key: algo_value})
    assert isinstance(output, str)
    # A hostile section must never crash; markdown still emits the section
    # header even when the payload normalizes to empty.
    if formatter is format_ssh_report_markdown and isinstance(algo_value, dict):
        assert "## " in output


@pytest.mark.parametrize("formatter", SSH_FORMATTERS, ids=_formatter_id)
def test_ssh_formatters_still_render_well_formed_algorithms(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_ssh_report_markdown:
        assert "Key Exchange Algorithms" in output
        assert "curve25519-sha256" in output
        assert "weak/deprecated" in output


# ---------------------------------------------------------------------------
# Hostile ``host_key`` values.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", SSH_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("host_key", NON_DICT_HOST_KEY)
def test_ssh_formatters_tolerate_non_dict_host_key(
    formatter: Callable[[Any], str], host_key: object
) -> None:
    output = formatter({"host_key": host_key})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", SSH_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("host_key", HOSTILE_HOST_KEY_DICTS)
def test_ssh_formatters_render_hostile_host_key_dicts(
    formatter: Callable[[Any], str], host_key: dict[str, object]
) -> None:
    output = formatter({"host_key": host_key})
    assert isinstance(output, str)


# ---------------------------------------------------------------------------
# Hostile ``findings`` values (iterated by markdown and CSV).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", SSH_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_ssh_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[Any], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    if formatter is format_ssh_report_markdown:
        assert "No weak algorithms detected" in output


@pytest.mark.parametrize("formatter", SSH_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_ssh_formatters_render_hostile_findings_lists(
    formatter: Callable[[Any], str], findings: list[object]
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    # Well-formed dict findings are rendered by markdown/CSV; non-dict entries
    # are skipped rather than crashing.
    if formatter is format_ssh_report_markdown:
        assert "Security Findings" in output


@pytest.mark.parametrize("formatter", SSH_FORMATTERS, ids=_formatter_id)
def test_ssh_formatters_still_render_well_formed_findings(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_ssh_report_markdown:
        assert "weak key exchange" in output
        assert "MEDIUM" in output
    elif formatter is format_ssh_report_csv:
        assert "weak key exchange" in output
        assert "diffie-hellman-group14-sha256" in output


# ---------------------------------------------------------------------------
# Regression: exact crash shapes reproduced before the fix.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"kex_algorithms": {"weak": 1}},
        {"kex_algorithms": {"supported": 1}},
        {"kex_algorithms": {"weak": [["nested"]]}},
        {"kex_algorithms": {"supported": ["a", 1]}},
        {"mac_algorithms": {"strong": 3.14}},
    ],
)
def test_ssh_markdown_regression_formerly_crashed(payload: dict[str, object]) -> None:
    # Before the fix these raised TypeError from set()/sorted().
    assert isinstance(format_ssh_report_markdown(payload), str)