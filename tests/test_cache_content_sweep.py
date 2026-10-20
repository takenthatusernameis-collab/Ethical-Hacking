"""Permanent sweep test: every cache file that the toolkit writes survives hostile content.

The file-option sweep (``tests/test_file_option_sweep.py``) checks the *path*
of a file option, the file-content sweep (``tests/test_file_content_sweep.py``)
checks the *content* of an input file and the config-value sweep
(``tests/test_config_value_sweep.py``) checks the values of the config file.
This sweep checks the fourth source of hostile input: the *cache files* that
the ``geo``, ``cert``, ``mac`` and ``cve`` commands write in
``~/.cache/ethscan``.

The cache is written by the toolkit itself, so a cache file that cannot be
used is never an error: it is an empty cache. A cache file that is not valid
UTF-8, that is not a JSON object, that holds an entry that is not a mapping,
or that holds a timestamp that is not a finite number used to leak a
traceback (``UnicodeDecodeError`` and ``TypeError``). Every one of them must
now be read without raising, and the command must never leak a traceback.

The per-invocation timeout is enforced with ``signal.SIGALRM``, the same
mechanism the other sweeps use. The network is closed (``urlopen`` raises), so
the commands take the path that a broken cache file takes: the cache is read
first, and the API is only asked when the cache cannot answer.
"""
from __future__ import annotations

import inspect
import json
import signal
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ethscan import cert, cli, cve, geo, mac


class _Timeout(BaseException):
    """Raised by the alarm to abort a single invocation."""


def _alarm(signum: int, frame: Any) -> None:
    raise _Timeout()


@dataclass(frozen=True)
class _CacheUser:
    """A command that reads a cache file, and the key it is written under."""

    name: str
    module: Any
    key: str
    # The arguments that make the command run. The cve command reads its
    # cache only after a product and a version are known, so it is covered by
    # the library level of the sweep and not by the command line level.
    cli_args: tuple[str, ...] | None


CACHE_USERS = (
    _CacheUser("geo", geo, "127.0.0.1", ("geo", "--target", "127.0.0.1")),
    _CacheUser("cert", cert, "localhost", ("cert", "--target", "localhost")),
    _CacheUser("mac", mac, "00:1a:2b:3c:4d:5e", ("mac", "--target", "00:1a:2b:3c:4d:5e")),
    _CacheUser("cve", cve, "CVE-2021-44228", None),
)

# The content of a cache file that is hostile for every cache. ``{key}`` is
# the key that the cache is written under.
HOSTILE_TEMPLATES = {
    "not json": "not valid json",
    "a json list": '["not", "a", "dict"]',
    "a json number": "123",
    "json null": "null",
    "an entry that is a number": '{"{key}": 5}',
    "an entry that is a list": '{"{key}": [1, 2]}',
    "an entry that is a string": '{"{key}": "text"}',
    "an entry that is null": '{"{key}": null}',
    "a timestamp that is a string": '{"{key}": {"timestamp": "soon"}}',
    "a timestamp that is null": '{"{key}": {"timestamp": null}}',
    "a timestamp that is a mapping": '{"{key}": {"timestamp": {"a": 1}}}',
    "a timestamp that is a list": '{"{key}": {"timestamp": [1]}}',
    "a timestamp that is not finite": '{"{key}": {"timestamp": 1e999}}',
}

# A cache file that is not valid UTF-8 at all.
NOT_UTF8 = b"\xff\xfe not utf-8"

# What a hostile cache file is worth to the command that reads it:
#   "empty" - the cache holds nothing for the key, so the command reports the
#              lookup it could not do;
#   "stale" - the cache holds an entry that cannot be fresh, so the command
#              falls back to it and says that the data is stale.
EXPECT_EMPTY = "empty"
EXPECT_STALE = "stale"

EXPECTATIONS = {
    "not utf-8": EXPECT_EMPTY,
    "not json": EXPECT_EMPTY,
    "a json list": EXPECT_EMPTY,
    "a json number": EXPECT_EMPTY,
    "json null": EXPECT_EMPTY,
    "an entry that is a number": EXPECT_EMPTY,
    "an entry that is a list": EXPECT_EMPTY,
    "an entry that is a string": EXPECT_EMPTY,
    "an entry that is null": EXPECT_EMPTY,
    "a timestamp that is a string": EXPECT_STALE,
    "a timestamp that is null": EXPECT_STALE,
    "a timestamp that is a mapping": EXPECT_STALE,
    "a timestamp that is a list": EXPECT_STALE,
    "a timestamp that is not finite": EXPECT_STALE,
}

# Per-invocation timeout, in seconds.
PER_INVOCATION_TIMEOUT = 5


def _hostile_contents(key: str) -> list[tuple[str, bytes]]:
    """Return the hostile cache files, with the key of the cache in them."""
    contents = [("not utf-8", NOT_UTF8)]
    for label, template in HOSTILE_TEMPLATES.items():
        contents.append((label, template.replace("{key}", key).encode("utf-8")))
    return contents


def _cached_or_fetch(user: _CacheUser) -> dict[str, object]:
    """Ask a command for the data of its key with the network closed."""
    func = user.module._get_cached_or_fetch
    kwargs: dict[str, Any] = {}
    if "api_url" in inspect.signature(func).parameters:
        kwargs["api_url"] = None
    with patch("urllib.request.urlopen", side_effect=OSError("network is closed")):
        return func(user.key, 0.001, True, True, **kwargs)


@pytest.mark.parametrize("user", CACHE_USERS, ids=lambda u: u.name)
def test_a_hostile_cache_file_is_an_empty_cache(user: _CacheUser, tmp_path) -> None:
    """A cache file that cannot be used is read as an empty cache."""
    for label, content in _hostile_contents(user.key):
        cache_file = tmp_path / f"{user.name}-cache.json"
        cache_file.write_bytes(content)
        with patch.object(user.module, "CACHE_FILE", cache_file):
            loaded = user.module._load_cache()
        assert isinstance(loaded, dict), f"{user.name} {label}: {loaded!r}"
        for key, entry in loaded.items():
            assert isinstance(entry, dict), (
                f"{user.name} {label}: the entry {key!r} is not a mapping: {entry!r}"
            )


@pytest.mark.parametrize("user", CACHE_USERS, ids=lambda u: u.name)
def test_a_hostile_cache_entry_is_never_fresh(user: _CacheUser, tmp_path) -> None:
    """A cache entry that cannot be checked is never served as fresh."""
    for label, content in _hostile_contents(user.key):
        cache_file = tmp_path / f"{user.name}-cache.json"
        cache_file.write_bytes(content)
        with patch.object(user.module, "CACHE_FILE", cache_file):
            loaded = user.module._load_cache()
        for entry in loaded.values():
            assert user.module._is_cache_valid(entry) is False, (
                f"{user.name} {label}: the entry {entry!r} is fresh"
            )


@pytest.mark.parametrize("user", CACHE_USERS, ids=lambda u: u.name)
def test_a_hostile_cache_file_never_leaks_a_traceback(user: _CacheUser, tmp_path) -> None:
    """A hostile cache file is answered with a result, not with a traceback."""
    for label, content in _hostile_contents(user.key):
        cache_file = tmp_path / f"{user.name}-cache.json"
        cache_file.write_bytes(content)
        with patch.object(user.module, "CACHE_FILE", cache_file):
            result = _cached_or_fetch(user)
        assert isinstance(result, dict), f"{user.name} {label}: {result!r}"
        expected = EXPECTATIONS[label]
        if expected == EXPECT_EMPTY:
            assert result.get("cached") is False, (
                f"{user.name} {label}: the cache was used: {result!r}"
            )
            assert result.get("error"), f"{user.name} {label}: {result!r}"
        else:
            assert result.get("offline_fallback") is True, (
                f"{user.name} {label}: the stale entry was not marked as stale: {result!r}"
            )


@pytest.mark.parametrize(
    "user", [u for u in CACHE_USERS if u.cli_args], ids=lambda u: u.name
)
def test_a_hostile_cache_file_never_leaks_a_traceback_on_the_command_line(
    user: _CacheUser, tmp_path
) -> None:
    """The command line reads a hostile cache file without leaking a traceback."""
    signal.signal(signal.SIGALRM, _alarm)
    runner = CliRunner()
    try:
        for label, content in _hostile_contents(user.key):
            cache_file = tmp_path / f"{user.name}-cache.json"
            cache_file.write_bytes(content)
            with (
                patch.object(user.module, "CACHE_FILE", cache_file),
                patch.object(user.module, "CACHE_DIR", tmp_path),
                patch("urllib.request.urlopen", side_effect=OSError("network is closed")),
            ):
                signal.setitimer(signal.ITIMER_REAL, PER_INVOCATION_TIMEOUT)
                try:
                    result = runner.invoke(cli.cli, list(user.cli_args))
                except _Timeout:
                    pytest.fail(
                        f"{user.name} {label} timed out after {PER_INVOCATION_TIMEOUT}s"
                    )
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
            exc = result.exception
            if exc is not None and not isinstance(exc, SystemExit):
                pytest.fail(
                    f"{user.name} {label} leaked a traceback: "
                    f"{type(exc).__name__}: {exc}"
                )
            assert result.exit_code == 0, (
                f"{user.name} {label} exited with {result.exit_code}\n{result.output}"
            )
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


@pytest.mark.parametrize("user", CACHE_USERS, ids=lambda u: u.name)
def test_a_valid_cache_entry_is_still_served(user: _CacheUser, tmp_path) -> None:
    """A cache file that the toolkit wrote is still served from the cache."""
    entry = {"status": "success", "timestamp": time.time()}
    cache_file = tmp_path / f"{user.name}-cache.json"
    cache_file.write_text(json.dumps({user.key: entry}), encoding="utf-8")
    with (
        patch.object(user.module, "CACHE_FILE", cache_file),
        patch.object(user.module, "CACHE_DIR", tmp_path),
    ):
        result = _cached_or_fetch(user)
    assert result.get("cached") is True, result
    assert "offline_fallback" not in result, result
    assert result.get("timestamp") == entry["timestamp"], result
