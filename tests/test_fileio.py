"""Unit tests for the shared input-file readers."""

import pytest

from ethscan.fileio import is_utf8, load_json, read_lines, read_text


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
