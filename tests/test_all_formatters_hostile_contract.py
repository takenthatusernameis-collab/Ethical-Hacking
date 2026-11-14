"""Repo-wide contract test for ``ethscan`` report formatters.

Discovers every ``format_*_report_{json,markdown,csv}`` callable that is
*defined* in an ``ethscan.*`` module (re-exports such as those in
``ethscan.cli`` are ignored via ``__module__``) and asserts that each
single-argument formatter:

* returns ``str`` for a hostile top-level matrix (``None``, scalars,
  containers, ``bytes`` and a hostile field dict), and
* never raises, and
* emits parseable JSON when the formatter is a ``*_report_json`` variant, and
* does not mutate its input and renders the same input identically twice.

Formatters with non-standard signatures are tracked in an explicit allowlist
(``ethscan.passwords.format_audit_report_*``) rather than blanket-skipped, and
a dedicated test keeps that allowlist honest so future signature changes cannot
silently drop coverage.
"""
from __future__ import annotations

import copy
import importlib
import inspect
import json
import pkgutil
from typing import Any, Callable

import pytest

import ethscan

Formatter = Callable[[Any], str]

# Formatters intentionally excluded from the single-argument sweep because they
# take a richer, non-Mapping signature. Keep this list exact: the allowlist
# accuracy test fails if a new non-standard formatter appears or one disappears.
NON_STANDARD_ALLOWLIST: frozenset[str] = frozenset(
    {
        "ethscan.passwords.format_audit_report_json",
        "ethscan.passwords.format_audit_report_markdown",
        "ethscan.passwords.format_audit_report_csv",
    }
)

HOSTILE_FIELD_DICT: dict[str, Any] = {
    "target": [],
    "port": "x",
    "hops": [None, {"rtt_avg_ms": "x"}],
    "notes": [None, {}],
    "recursive_traces": [None, {"hops": "x"}],
}

# A dict whose every common report field holds a hostile value.
ALL_HOSTILE_FIELDS: dict[str, Any] = {
    "target": None,
    "port": "x",
    "hops": [None, {}],
    "notes": [1, {}],
    "recursive_traces": [{"hops": "x"}, []],
    "cves": [None, {}],
    "certificates": [None, {}],
    "results": [None, {}],
    "findings": [None, {}],
    "services": [None, {}],
    "records": [None, {}],
    "entries": [None, {}],
    "items": [None, {}],
    "data": [None, {}],
    "error": [None, {}],
}

# (id, value) pairs exercised against every discovered formatter.
HOSTILE_MATRIX: list[tuple[str, Any]] = [
    ("none", None),
    ("int", 1),
    ("str", "x"),
    ("list", []),
    ("bytes", b"bytes"),
    ("empty_dict", {}),
    ("hostile_fields", HOSTILE_FIELD_DICT),
    ("nan", float("nan")),
    ("inf", float("inf")),
    ("neg_inf", float("-inf")),
    ("deeply_nested_list", [[[[{"a": [1, {"b": [None]}]}]]]]),
    ("list_of_hostile_dicts", [{"rtt_avg_ms": "x"}, None]),
    ("all_hostile_fields", ALL_HOSTILE_FIELDS),
]

# A minimal valid report exercising the common fields formatters read. Used to
# inject a single hostile field into an otherwise-valid report, exercising
# code paths that only activate when some fields are valid (complementary to
# the "all-fields-hostile" top-level sweep in HOSTILE_MATRIX).
_VALID_REPORT: dict[str, Any] = {
    "target": "example.com",
    "port": 443,
    "hops": [],
    "notes": [],
    "recursive_traces": [],
    "cves": [],
    "certificates": [],
    "results": [],
    "findings": [],
    "services": [],
    "records": {},
    "entries": [],
    "items": [],
    "data": {},
    "error": None,
}

# Hostile values most likely to expose type-assumption crashes in formatters.
_HOSTILE_FIELD_VALUES: list[Any] = [None, 1, "x", [], {}, b"bytes", float("nan")]


def _is_report_formatter(attr: str, obj: object) -> bool:
    return (
        attr.startswith("format_")
        and "_report_" in attr
        and inspect.isfunction(obj)
    )


def _iter_module_formatters() -> list[tuple[str, str, Any]]:
    """Yield ``(module, attr, func)`` for formatters defined in each module."""
    discovered: list[tuple[str, str, Any]] = []
    for module_info in pkgutil.iter_modules(ethscan.__path__):
        module_name = f"ethscan.{module_info.name}"
        module = importlib.import_module(module_name)
        for attr, obj in inspect.getmembers(module, inspect.isfunction):
            if not _is_report_formatter(attr, obj):
                continue
            # Only test the canonical definition, not re-exports (e.g. cli).
            if getattr(obj, "__module__", None) != module_name:
                continue
            discovered.append((module_name, attr, obj))
    return discovered


def _param_count(func: Any) -> int | None:
    try:
        return len(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return None


def _single_arg_formatters() -> list[Formatter]:
    formatters: list[Formatter] = []
    for _module, _attr, func in _iter_module_formatters():
        if _param_count(func) == 1:
            formatters.append(func)
    return formatters


def _non_standard_formatters() -> set[str]:
    found: set[str] = set()
    for module, attr, func in _iter_module_formatters():
        if _param_count(func) != 1:
            found.add(f"{module}.{attr}")
    return found


SINGLE_ARG_FORMATTERS: list[Formatter] = _single_arg_formatters()


def _formatter_id(func: Formatter) -> str:
    return f"{func.__module__}.{func.__qualname__}"


@pytest.mark.parametrize(
    "formatter",
    SINGLE_ARG_FORMATTERS,
    ids=[_formatter_id(f) for f in SINGLE_ARG_FORMATTERS],
)
@pytest.mark.parametrize(
    "value",
    [value for _value_id, value in HOSTILE_MATRIX],
    ids=[value_id for value_id, _ in HOSTILE_MATRIX],
)
def test_formatter_survives_hostile_input(formatter: Formatter, value: Any) -> None:
    result = formatter(value)
    assert isinstance(result, str), (
        f"{_formatter_id(formatter)} returned {type(result).__name__}, not str"
    )
    if formatter.__name__.endswith("_report_json"):
        # A hostile non-mapping input is rendered as a JSON string; the contract
        # only requires that the output is parseable JSON.
        json.loads(result)


@pytest.mark.parametrize(
    "formatter",
    SINGLE_ARG_FORMATTERS,
    ids=[_formatter_id(f) for f in SINGLE_ARG_FORMATTERS],
)
def test_formatter_is_pure_and_deterministic(formatter: Formatter) -> None:
    """A formatter must not mutate its input and must render it the same twice.

    The report formatters are called once per command, but a formatter that
    pops or sorts its input would corrupt a caller that reuses the parsed
    result, and one that depends on dict/set iteration order would produce
    unstable reports.
    """
    value = copy.deepcopy(HOSTILE_FIELD_DICT)
    snapshot = copy.deepcopy(value)
    first = formatter(value)
    assert value == snapshot, f"{_formatter_id(formatter)} mutated its input"
    second = formatter(value)
    assert first == second, f"{_formatter_id(formatter)} is not deterministic"


@pytest.mark.parametrize(
    "formatter",
    SINGLE_ARG_FORMATTERS,
    ids=[_formatter_id(f) for f in SINGLE_ARG_FORMATTERS],
)
@pytest.mark.parametrize("field", sorted(_VALID_REPORT), ids=lambda f: f"field={f}")
@pytest.mark.parametrize(
    "hostile",
    _HOSTILE_FIELD_VALUES,
    ids=lambda h: f"hostile={type(h).__name__}",
)
def test_formatter_survives_hostile_report_field(
    formatter: Formatter, field: str, hostile: Any
) -> None:
    """A formatter must not crash or return non-str when one report field is hostile.

    Complements ``test_formatter_survives_hostile_input``: that test passes the
    hostile value as the *entire* argument (so formatters often short-circuit on
    a non-dict or all-hostile dict). Here a single field of an otherwise-valid
    report is hostile, exercising code paths that only activate once the
    formatter has decided to render a real report.
    """
    data = dict(_VALID_REPORT)
    data[field] = hostile
    result = formatter(data)
    assert isinstance(result, str), (
        f"{_formatter_id(formatter)} returned {type(result).__name__}, not str "
        f"for field {field!r}={hostile!r}"
    )
    if formatter.__name__.endswith("_report_json"):
        json.loads(result)


def test_discovery_finds_expected_formatter_modules() -> None:
    modules = {module for module, _attr, _func in _iter_module_formatters()}
    # Every command module that renders reports must be represented, plus the
    # generic report/scanner helpers.
    expected = {
        "ethscan.trace",
        "ethscan.wifi",
        "ethscan.config",
        "ethscan.report",
        "ethscan.scanner",
    }
    assert expected <= modules, f"missing formatter modules: {expected - modules}"
    assert len(SINGLE_ARG_FORMATTERS) >= 150, (
        "expected a broad sweep; discovery may have regressed: "
        f"found {len(SINGLE_ARG_FORMATTERS)}"
    )


def test_non_standard_allowlist_is_accurate() -> None:
    actual = _non_standard_formatters()
    assert actual == set(NON_STANDARD_ALLOWLIST), (
        "non-standard formatter signatures changed; update the allowlist "
        f"intentionally (added: {actual - set(NON_STANDARD_ALLOWLIST)}, "
        f"removed: {set(NON_STANDARD_ALLOWLIST) - actual})"
    )