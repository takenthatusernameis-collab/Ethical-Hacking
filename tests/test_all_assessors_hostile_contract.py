"""Repo-wide contract test for ``ethscan`` assessor functions.

Discovers every ``_assess_*`` callable that is *defined* in an ``ethscan.*`` module
and asserts that each assessor:

* returns ``list[str]`` (or ``list[dict[str, Any]]`` for SSH) for a hostile
  input matrix, and
* never raises, and
* does not mutate its input and renders the same input identically twice.

Assessors are categorized by their expected input type:
- Dict-input assessors: take a dict with structured fields
- Str-input assessors: take a string banner/header or None
- List-input assessors: take a list of strings or None (LDAP)

Assessors with non-standard signatures are tracked in an explicit allowlist
rather than blanket-skipped, and a dedicated test keeps that allowlist honest so
future signature changes cannot silently drop coverage.

Note: ``_parse_*`` functions are intentionally excluded --- they are internal
parsers that may raise ``ValueError`` on malformed input as a documented guard.
Only the public-facing ``_assess_*`` assessors are covered here.
"""
from __future__ import annotations

import copy
import importlib
import inspect
import pkgutil
from typing import Any, Callable

import pytest

import ethscan

Assessor = Callable[[Any], list[Any]]

# Assessors intentionally excluded from the sweep because they take a richer,
# non-standard signature or are not meant to be called with arbitrary hostile
# inputs. Keep this list exact: the allowlist accuracy test fails if a new
# non-standard assessor appears or one disappears.
NON_STANDARD_ALLOWLIST: frozenset[str] = frozenset()

# Hostile values most likely to expose type-assumption crashes.
HOSTILE_VALUES: list[Any] = [
    None,
    1,
    1.5,
    True,
    False,
    b"bytes",
    [],
    {},
    float("nan"),
    float("inf"),
    float("-inf"),
    [[[[{"a": [1, {"b": [None]}]}]]]],
]

# Hostile string values for str-input assessors.
HOSTILE_STRINGS: list[str | None] = [
    None,
    "",
    "x",
    "not a version",
    "1.2.3",
    "a" * 1000,
    "\x00\x01\x02",
]

# A minimal valid dict input for dict-input assessors.
VALID_DICT_INPUT: dict[str, Any] = {
    "version": "5.7.0",
    "server_version": "10.5.10-MariaDB",
    "redis_version": "7.0.0",
    "sysInfo": "Linux",
    "modules": "none",
    "capabilities": 0,
    "auth_type_name": "MD5",
    "auth_type_code": 5,
    "process_id": 12345,
    "errors": [],
    "encryption": "REQUIRED",
    "instance_name": "SQLEXPRESS",
    "thread_id": 42,
    "error": None,
    "bind": "127.0.0.1",
    "requirepass": "secret",
    "dir": "/data",
    "dbfilename": "dump.rdb",
    "uptime": "3600",
    "bytes": "1024",
    "limit_maxbytes": "1000000",
    "accepting_conns": "1",
    "evictions": "0",
    "get_hits": "100",
    "get_misses": "10",
    "vendor_versions": ["OpenLDAP: 2.6.3"],
}

VALID_STR_INPUT: str = "OpenSSH_9.3p1"
VALID_LIST_INPUT: list[str] = ["OpenLDAP: 2.6.3"]


def _is_assessor(attr: str, obj: object) -> bool:
    return attr.startswith("_assess_") and inspect.isfunction(obj)


def _iter_module_assessors() -> list[tuple[str, str, Any]]:
    """Yield ``(module, attr, func)`` for assessors defined in each module."""
    discovered: list[tuple[str, str, Any]] = []
    for module_info in pkgutil.iter_modules(ethscan.__path__):
        module_name = f"ethscan.{module_info.name}"
        module = importlib.import_module(module_name)
        for attr, obj in inspect.getmembers(module, inspect.isfunction):
            if not _is_assessor(attr, obj):
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


def _single_arg_assessors() -> list[Assessor]:
    assessors: list[Assessor] = []
    for _module, _attr, func in _iter_module_assessors():
        if _param_count(func) == 1:
            assessors.append(func)
    return assessors


def _non_standard_assessors() -> set[str]:
    found: set[str] = set()
    for module, attr, func in _iter_module_assessors():
        if _param_count(func) != 1:
            found.add(f"{module}.{attr}")
    return found


def _categorize_assessor(func: Assessor) -> str:
    """Return the input category: 'dict', 'str', 'list', or 'ssh'."""
    qualname = func.__qualname__
    module = func.__module__
    full = f"{module}.{qualname}"

    # SSH assessor takes str banner, returns list[dict]
    if qualname == "_assess_ssh_banner":
        return "ssh"

    # Dict-input assessors
    dict_assessors = {
        "ethscan.mysql._assess_handshake",
        "ethscan.mongodb._assess_buildinfo",
        "ethscan.postgresql._assess_startup",
        "ethscan.mssql._assess_prelogin",
        "ethscan.redis._assess_dangerous",
        "ethscan.redis._assess_redis",
        "ethscan.oracle._assess_version",
        "ethscan.memcached._assess_stats",
        "ethscan.ntp._assess_ntp_version",
    }
    if full in dict_assessors:
        return "dict"

    # List-input assessors
    list_assessors = {
        "ethscan.ldap._assess_ldap_version",
    }
    if full in list_assessors:
        return "list"

    # Str-input assessors (the rest)
    return "str"


SINGLE_ARG_ASSESSORS: list[Assessor] = _single_arg_assessors()

# Categorize all discovered assessors
ASSESSORS_BY_CATEGORY: dict[str, list[Assessor]] = {"dict": [], "str": [], "list": [], "ssh": []}
for assessor in SINGLE_ARG_ASSESSORS:
    cat = _categorize_assessor(assessor)
    ASSESSORS_BY_CATEGORY[cat].append(assessor)


def _assessor_id(func: Assessor) -> str:
    return f"{func.__module__}.{func.__qualname__}"


def _is_ssh_assessor(func: Assessor) -> bool:
    return _categorize_assessor(func) == "ssh"


@pytest.mark.parametrize(
    "assessor",
    ASSESSORS_BY_CATEGORY["str"],
    ids=[_assessor_id(a) for a in ASSESSORS_BY_CATEGORY["str"]],
)
@pytest.mark.parametrize(
    "value",
    HOSTILE_STRINGS,
    ids=lambda v: f"hostile={type(v).__name__}{'' if v is None else f'_{v[:20]}'}",
)
def test_str_assessor_survives_hostile_input(assessor: Assessor, value: str | None) -> None:
    """Str-input assessors must not crash on hostile string input and must return list[str]."""
    result = assessor(value)
    assert isinstance(result, list), (
        f"{_assessor_id(assessor)} returned {type(result).__name__}, not list"
    )
    for item in result:
        assert isinstance(item, str), (
            f"{_assessor_id(assessor)} returned list with non-str element"
        )


@pytest.mark.parametrize(
    "assessor",
    ASSESSORS_BY_CATEGORY["list"],
    ids=[_assessor_id(a) for a in ASSESSORS_BY_CATEGORY["list"]],
)
@pytest.mark.parametrize(
    "value",
    [None, [], [1, 2], ["valid"], [None, {}]],
    ids=lambda v: f"hostile={type(v).__name__}",
)
def test_list_assessor_survives_hostile_input(assessor: Assessor, value: Any) -> None:
    """List-input assessors must not crash on hostile input and must return list[str]."""
    result = assessor(value)
    assert isinstance(result, list), (
        f"{_assessor_id(assessor)} returned {type(result).__name__}, not list"
    )
    for item in result:
        assert isinstance(item, str), (
            f"{_assessor_id(assessor)} returned list with non-str element"
        )


@pytest.mark.parametrize(
    "assessor",
    ASSESSORS_BY_CATEGORY["ssh"],
    ids=[_assessor_id(a) for a in ASSESSORS_BY_CATEGORY["ssh"]],
)
@pytest.mark.parametrize(
    "value",
    [None, "OpenSSH_9.3p1", "not a version"],
    ids=lambda v: f"hostile={type(v).__name__}",
)
def test_ssh_assessor_survives_hostile_input(assessor: Assessor, value: Any) -> None:
    """SSH assessor must not crash on hostile input and must return list[dict]."""
    result = assessor(value)
    assert isinstance(result, list), (
        f"{_assessor_id(assessor)} returned {type(result).__name__}, not list"
    )
    for item in result:
        assert isinstance(item, dict), (
            f"{_assessor_id(assessor)} returned list with non-dict element"
        )


# =============================================================================
# Purity and determinism tests
# =============================================================================

@pytest.mark.parametrize(
    "assessor",
    ASSESSORS_BY_CATEGORY["dict"],
    ids=[_assessor_id(a) for a in ASSESSORS_BY_CATEGORY["dict"]],
)
def test_dict_assessor_is_pure_and_deterministic(assessor: Assessor) -> None:
    """Dict-input assessors must not mutate input and must be deterministic."""
    value = copy.deepcopy(VALID_DICT_INPUT)
    snapshot = copy.deepcopy(value)
    first = assessor(value)
    assert value == snapshot, f"{_assessor_id(assessor)} mutated its input"
    second = assessor(value)
    assert first == second, f"{_assessor_id(assessor)} is not deterministic"


@pytest.mark.parametrize(
    "assessor",
    ASSESSORS_BY_CATEGORY["str"],
    ids=[_assessor_id(a) for a in ASSESSORS_BY_CATEGORY["str"]],
)
def test_str_assessor_is_pure_and_deterministic(assessor: Assessor) -> None:
    """Str-input assessors must not mutate input and must be deterministic."""
    value = VALID_STR_INPUT
    first = assessor(value)
    second = assessor(value)
    assert first == second, f"{_assessor_id(assessor)} is not deterministic"


@pytest.mark.parametrize(
    "assessor",
    ASSESSORS_BY_CATEGORY["list"],
    ids=[_assessor_id(a) for a in ASSESSORS_BY_CATEGORY["list"]],
)
def test_list_assessor_is_pure_and_deterministic(assessor: Assessor) -> None:
    """List-input assessors must not mutate input and must be deterministic."""
    value = copy.deepcopy(VALID_LIST_INPUT)
    snapshot = copy.deepcopy(value)
    first = assessor(value)
    assert value == snapshot, f"{_assessor_id(assessor)} mutated its input"
    second = assessor(value)
    assert first == second, f"{_assessor_id(assessor)} is not deterministic"


@pytest.mark.parametrize(
    "assessor",
    ASSESSORS_BY_CATEGORY["ssh"],
    ids=[_assessor_id(a) for a in ASSESSORS_BY_CATEGORY["ssh"]],
)
def test_ssh_assessor_is_pure_and_deterministic(assessor: Assessor) -> None:
    """SSH assessor must not mutate input and must be deterministic."""
    value = VALID_STR_INPUT
    first = assessor(value)
    second = assessor(value)
    assert first == second, f"{_assessor_id(assessor)} is not deterministic"


# =============================================================================
# Hostile field tests (dict-input assessors only)
# =============================================================================

# Fields that dict-input assessors actually read
DICT_ASSESSOR_FIELDS: dict[str, list[str]] = {
    "ethscan.mysql._assess_handshake": ["server_version", "capabilities"],
    "ethscan.mongodb._assess_buildinfo": ["version", "sysInfo", "modules"],
    "ethscan.postgresql._assess_startup": ["server_version", "auth_type_name", "auth_type_code", "process_id", "errors"],
    "ethscan.mssql._assess_prelogin": ["version", "encryption", "instance_name", "thread_id", "error"],
    "ethscan.redis._assess_dangerous": ["bind", "requirepass", "dir", "dbfilename"],
    "ethscan.redis._assess_redis": ["redis_version"],
    "ethscan.oracle._assess_version": ["version", "error"],
    "ethscan.memcached._assess_stats": ["pid", "uptime", "bytes", "limit_maxbytes", "accepting_conns", "evictions", "get_hits", "get_misses"],
    "ethscan.ntp._assess_ntp_version": ["version", "error"],
}

# Pre-compute test parameters for dict assessor hostile field tests
_DICT_ASSESSOR_FIELD_HOSTILE_PARAMS: list[tuple[Assessor, str, Any]] = []
for assessor in ASSESSORS_BY_CATEGORY["dict"]:
    aid = _assessor_id(assessor)
    fields = DICT_ASSESSOR_FIELDS.get(aid, [])
    for field in fields:
        for hostile in HOSTILE_VALUES:
            _DICT_ASSESSOR_FIELD_HOSTILE_PARAMS.append((assessor, field, hostile))


@pytest.mark.parametrize(
    "assessor,field,hostile",
    _DICT_ASSESSOR_FIELD_HOSTILE_PARAMS,
    ids=[f"{_assessor_id(a)}:field={f}:hostile={type(h).__name__}" for a, f, h in _DICT_ASSESSOR_FIELD_HOSTILE_PARAMS],
)
def test_dict_assessor_survives_hostile_field(assessor: Assessor, field: str, hostile: Any) -> None:
    """Dict-input assessors must not crash when one field is hostile."""
    data = dict(VALID_DICT_INPUT)
    data[field] = hostile
    result = assessor(data)
    assert isinstance(result, list), (
        f"{_assessor_id(assessor)} returned {type(result).__name__}, not list "
        f"for field {field!r}={hostile!r}"
    )
    for item in result:
        assert isinstance(item, str), (
            f"{_assessor_id(assessor)} returned list with non-str element "
            f"for field {field!r}={hostile!r}"
        )


# =============================================================================
# Discovery and allowlist tests
# =============================================================================

def test_discovery_finds_expected_assessor_modules() -> None:
    modules = {module for module, _attr, _func in _iter_module_assessors()}
    expected = {
        "ethscan.ftp",
        "ethscan.postgresql",
        "ethscan.mssql",
        "ethscan.mysql",
        "ethscan.snmp",
        "ethscan.redis",
        "ethscan.oracle",
        "ethscan.web",
        "ethscan.smtp",
        "ethscan.memcached",
        "ethscan.ntp",
        "ethscan.ldap",
        "ethscan.ssh",
        "ethscan.mongodb",
    }
    assert expected <= modules, f"missing assessor modules: {expected - modules}"
    assert len(SINGLE_ARG_ASSESSORS) >= 14, (
        "expected a broad sweep; discovery may have regressed: "
        f"found {len(SINGLE_ARG_ASSESSORS)}"
    )


def test_assessor_categories_cover_all() -> None:
    """Every discovered single-arg assessor must be categorized."""
    total_categorized = sum(len(v) for v in ASSESSORS_BY_CATEGORY.values())
    assert total_categorized == len(SINGLE_ARG_ASSESSORS), (
        f"categorization missed {len(SINGLE_ARG_ASSESSORS) - total_categorized} assessors"
    )
    # Each category should have at least one assessor
    for cat, assessors in ASSESSORS_BY_CATEGORY.items():
        assert assessors, f"category {cat} has no assessors"


def test_non_standard_allowlist_is_accurate() -> None:
    actual = _non_standard_assessors()
    assert actual == set(NON_STANDARD_ALLOWLIST), (
        "non-standard assessor signatures changed; update the allowlist "
        f"intentionally (added: {actual - set(NON_STANDARD_ALLOWLIST)}, "
        f"removed: {set(NON_STANDARD_ALLOWLIST) - actual})"
    )