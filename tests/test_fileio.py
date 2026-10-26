"""Unit tests for the shared input-file readers and writers."""

import pytest

from ethscan.fileio import (
    is_utf8,
    load_json,
    read_lines,
    read_text,
    write_json,
    write_text,
)


def test_read_text_reads_the_whole_file(tmp_path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("hello\nworld\n")
    assert read_text(str(path)) == "hello\nworld\n"


def test_read_text_replaces_the_bytes_that_are_not_utf8(tmp_path) -> None:
    """A file with a stray byte is read, not refused."""
    path = tmp_path / "file.txt"
    path.write_bytes(b"caf\xe9\n")
    assert read_text(str(path)) == "caf\ufffd\n"


def test_read_lines_strips_the_lines_and_drops_the_empty_ones(tmp_path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("  first  \n\nsecond\n")
    assert read_lines(str(path)) == ["first", "second"]


def test_read_lines_skips_the_comments(tmp_path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("# comment\nfirst\n  # indented comment\nsecond\n")
    assert read_lines(str(path)) == ["first", "second"]


def test_read_lines_keeps_the_comments_when_asked(tmp_path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("# comment\nfirst\n")
    assert read_lines(str(path), skip_comments=False) == ["# comment", "first"]


def test_read_lines_replaces_the_bytes_that_are_not_utf8(tmp_path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"caf\xe9\nsecond\n")
    assert read_lines(str(path)) == ["caf\ufffd", "second"]


def test_read_lines_splits_on_every_line_ending(tmp_path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"first\r\nsecond\rthird\n")
    assert read_lines(str(path)) == ["first", "second", "third"]


def test_load_json_reads_an_object(tmp_path) -> None:
    path = tmp_path / "file.json"
    path.write_text('{"port": 80}')
    assert load_json(str(path)) == {"port": 80}


def test_load_json_raises_on_a_file_that_is_not_json(tmp_path) -> None:
    path = tmp_path / "file.json"
    path.write_text("not json at all")
    with pytest.raises(ValueError):
        load_json(str(path))


def test_load_json_raises_on_a_file_that_nests_too_deeply(tmp_path) -> None:
    """A file whose JSON nests deeper than the parser can read is unusable.

    The JSON parser raises a ``RecursionError`` for such a file, which is
    neither a ``json.JSONDecodeError`` nor an ``OSError``: it is reported as
    an unusable value, like a file that holds broken JSON.
    """
    path = tmp_path / "file.json"
    path.write_text("[" * 20000 + "]" * 20000)
    with pytest.raises(ValueError):
        load_json(str(path))


def test_is_utf8_accepts_a_text_file(tmp_path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("café\n")
    assert is_utf8(str(path)) is True


def test_is_utf8_refuses_a_file_with_a_stray_byte(tmp_path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"caf\xe9\n")
    assert is_utf8(str(path)) is False


def test_is_utf8_refuses_a_file_that_cannot_be_read(tmp_path) -> None:
    assert is_utf8(str(tmp_path / "missing.txt")) is False


def test_is_utf8_accepts_a_character_that_straddles_two_blocks(tmp_path) -> None:
    """A multi-byte character that sits on a block boundary stays valid."""
    path = tmp_path / "file.txt"
    path.write_bytes(b"a" * 65535 + "é".encode())
    assert is_utf8(str(path)) is True


def test_write_text_writes_the_content(tmp_path) -> None:
    path = tmp_path / "file.txt"
    write_text(path, "hello\nworld\n")
    assert path.read_text() == "hello\nworld\n"


def test_write_text_creates_missing_parent_dirs(tmp_path) -> None:
    """write_text creates the parent directories when they do not exist."""
    path = tmp_path / "deep" / "nested" / "file.txt"
    write_text(path, "hello\n")
    assert path.read_text() == "hello\n"
    assert path.parent.is_dir()


def test_write_text_refuses_a_directory(tmp_path) -> None:
    """Writing to an existing directory is refused, not turned into a file."""
    path = tmp_path / "adir"
    path.mkdir()
    with pytest.raises(OSError):
        write_text(path, "hello\n")


def test_write_text_uses_the_given_encoding(tmp_path) -> None:
    path = tmp_path / "file.txt"
    write_text(path, "café", encoding="utf-16")
    assert path.read_bytes().decode("utf-16") == "café"


def test_write_json_writes_the_data(tmp_path) -> None:
    path = tmp_path / "file.json"
    write_json(path, {"port": 80, "host": "127.0.0.1"})
    assert load_json(path) == {"port": 80, "host": "127.0.0.1"}


def test_write_json_creates_missing_parent_dirs(tmp_path) -> None:
    """write_json creates the parent directories when they do not exist."""
    path = tmp_path / "deep" / "nested" / "file.json"
    write_json(path, {"a": 1})
    assert load_json(path) == {"a": 1}
    assert path.parent.is_dir()


def test_write_json_ends_with_a_newline(tmp_path) -> None:
    path = tmp_path / "file.json"
    write_json(path, {"a": 1})
    assert path.read_bytes().endswith(b"\n")


def test_write_json_writes_a_path_object(tmp_path) -> None:
    path = tmp_path / "file.json"
    write_json(tmp_path / "file.json", {"a": 1})
    assert load_json(path) == {"a": 1}
