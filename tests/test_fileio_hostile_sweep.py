"""Hostile-shape sweep for the shared file helpers of :mod:`ethscan.fileio`.

Every option that takes a file can point at a file whose *content* is hostile:
a wordlist with a line that is not valid UTF-8, a JSON file that is truncated,
a JSON file that nests deeper than the parser can read, a file that cannot be
read at all. The helpers below read such a file without leaking a traceback so
the command that uses them can report the problem in its own output.

The helpers also write files: the parent directory is created when missing and
the write is atomic, so a path whose directory was never created is a path the
user meant to use, not a usage error.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from ethscan.fileio import (
    is_utf8,
    load_json,
    read_lines,
    read_text,
    write_json,
    write_text,
)

NON_UTF8 = b"\xff\xfe not utf-8\n"
TRUNCATED_JSON = b"{ not json\n"
DEEPLY_NESTED = b"[" * 20000 + b"]" * 20000


def _write(path, content: bytes) -> None:
    path.write_bytes(content)


def test_read_text_replaces_invalid_utf8_instead_of_raising(tmp_path) -> None:
    path = tmp_path / "hostile.txt"
    _write(path, NON_UTF8)
    text = read_text(path)
    assert "\ufffd" in text
    assert "not utf-8" in text


def test_read_text_reads_a_clean_file(tmp_path) -> None:
    path = tmp_path / "clean.txt"
    _write(path, b"line one\nline two\n")
    assert read_text(path) == "line one\nline two\n"


def test_read_text_on_an_unreadable_file_raises_oserror(tmp_path) -> None:
    path = tmp_path / "unreadable.txt"
    _write(path, b"secret\n")
    path.chmod(0o000)
    try:
        with pytest.raises(OSError):
            read_text(path)
    finally:
        path.chmod(0o600)


def test_read_lines_drops_blank_comment_and_hostile_lines(tmp_path) -> None:
    # \xff\xfe is not valid UTF-8: read_text replaces each bad byte with the
    # replacement character, so the resulting line is non-empty and kept.
    path = tmp_path / "words.txt"
    _write(path, b"# comment\n\n  \nvalid\n\xff\xfe byte\n")
    assert read_lines(path) == ["valid", "\ufffd\ufffd byte"]


def test_read_lines_skips_comments_when_disabled(tmp_path) -> None:
    path = tmp_path / "words.txt"
    _write(path, b"# comment\nvalid\n")
    assert read_lines(path, skip_comments=False) == ["# comment", "valid"]


def test_load_json_parses_valid_json(tmp_path) -> None:
    path = tmp_path / "data.json"
    _write(path, b'{"key": [1, 2, 3]}\n')
    assert load_json(path) == {"key": [1, 2, 3]}


def test_load_json_rejects_broken_json(tmp_path) -> None:
    path = tmp_path / "broken.json"
    _write(path, TRUNCATED_JSON)
    with pytest.raises(ValueError, match="Expecting"):
        load_json(path)


def test_load_json_rejects_too_deep_nesting(tmp_path) -> None:
    path = tmp_path / "deep.json"
    _write(path, DEEPLY_NESTED)
    with pytest.raises(ValueError, match="nests too deeply"):
        load_json(path)


def test_load_json_on_an_unreadable_file_raises_oserror(tmp_path) -> None:
    path = tmp_path / "unreadable.json"
    _write(path, b"{}\n")
    path.chmod(0o000)
    try:
        with pytest.raises(OSError):
            load_json(path)
    finally:
        path.chmod(0o600)


def test_is_utf8_accepts_valid_utf8(tmp_path) -> None:
    path = tmp_path / "valid.txt"
    _write(path, b"valid utf-8\n")
    assert is_utf8(path) is True


def test_is_utf8_rejects_invalid_utf8(tmp_path) -> None:
    path = tmp_path / "invalid.txt"
    _write(path, NON_UTF8)
    assert is_utf8(path) is False


def test_is_utf8_rejects_an_unreadable_file(tmp_path) -> None:
    path = tmp_path / "unreadable.txt"
    _write(path, b"x\n")
    path.chmod(0o000)
    try:
        assert is_utf8(path) is False
    finally:
        path.chmod(0o600)


def test_write_text_creates_parent_and_writes_atomically(tmp_path) -> None:
    path = tmp_path / "nested" / "dir" / "out.txt"
    write_text(path, "hello\n")
    assert path.read_text() == "hello\n"


def test_write_text_overwrites_existing_content(tmp_path) -> None:
    path = tmp_path / "out.txt"
    path.write_text("old\n")
    write_text(path, "new\n")
    assert path.read_text() == "new\n"


def test_write_text_on_an_unwritable_parent_raises_oserror(tmp_path) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o500)
    path = blocked / "out.txt"
    try:
        with pytest.raises(OSError):
            write_text(path, "x\n")
    finally:
        blocked.chmod(0o700)


def test_write_json_serializes_and_writes(tmp_path) -> None:
    path = tmp_path / "nested" / "out.json"
    data: dict[str, Any] = {"key": [1, 2, {"three": 3}]}
    write_json(path, data)
    assert json.loads(path.read_text()) == data


def test_write_json_on_an_unwritable_parent_raises_oserror(tmp_path) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o500)
    path = blocked / "out.json"
    try:
        with pytest.raises(OSError):
            write_json(path, {})
    finally:
        blocked.chmod(0o700)
