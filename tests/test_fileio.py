"""Unit tests for the shared input-file readers and writers."""

import json

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


def test_write_text_raises_oserror_for_unwritable_parent(tmp_path) -> None:
    """An unwritable parent directory surfaces as OSError."""
    parent = tmp_path / "readonly"
    parent.mkdir()
    parent.chmod(0o555)
    try:
        with pytest.raises(OSError):
            write_text(parent / "file.txt", "hello\n")
    finally:
        parent.chmod(0o755)


def test_write_text_raises_oserror_when_target_is_directory(tmp_path) -> None:
    path = tmp_path / "adir"
    path.mkdir()
    with pytest.raises(OSError):
        write_text(path, "hello\n")


def test_write_text_raises_oserror_when_parent_is_a_file(tmp_path) -> None:
    """A parent path that is a file surfaces as OSError."""
    bogus_parent = tmp_path / "notadir"
    bogus_parent.write_text("i am a file")
    with pytest.raises(OSError):
        write_text(bogus_parent / "file.txt", "hello\n")


def test_write_json_raises_oserror_for_unwritable_parent(tmp_path) -> None:
    parent = tmp_path / "readonly"
    parent.mkdir()
    parent.chmod(0o555)
    try:
        with pytest.raises(OSError):
            write_json(parent / "file.json", {"a": 1})
    finally:
        parent.chmod(0o755)


def test_write_json_raises_oserror_when_target_is_directory(tmp_path) -> None:
    path = tmp_path / "adir"
    path.mkdir()
    with pytest.raises(OSError):
        write_json(path, {"a": 1})


def test_write_json_raises_oserror_when_parent_is_a_file(tmp_path) -> None:
    bogus_parent = tmp_path / "notadir"
    bogus_parent.write_text("i am a file")
    with pytest.raises(OSError):
        write_json(bogus_parent / "file.json", {"a": 1})


def test_write_text_atomicity_on_failure(tmp_path, monkeypatch) -> None:
    """A failed mid-write leaves the destination intact and removes the temp file."""
    path = tmp_path / "file.txt"
    path.write_text("original\n")

    import ethscan.fileio as fileio

    def boom(handle):
        handle.write("partial")
        raise RuntimeError("boom")

    # Patch the inner write via _atomic_write by calling it directly with a
    # failing writer, mirroring write_text's usage.
    with pytest.raises(RuntimeError):
        fileio._atomic_write(path, boom)

    assert path.read_text() == "original\n"
    # No leftover temp files in the directory.
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith("file.txt.")]
    assert leftovers == []


def test_write_json_atomicity_on_failure(tmp_path) -> None:
    path = tmp_path / "file.json"
    path.write_text('{"old": true}\n')

    import ethscan.fileio as fileio

    def boom(handle):
        handle.write("partial")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        fileio._atomic_write(path, boom)

    assert path.read_text() == '{"old": true}\n'
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith("file.json.")]
    assert leftovers == []


def test_load_json_tracks_the_shallowest_opening_bracket(tmp_path) -> None:
    """A bracket that opens at or below the deepest level is still counted.

    The depth guard walks every character and only bumps ``max_depth`` when a
    bracket opens deeper than any seen so far; a bracket that opens at the
    current depth must not be skipped.
    """
    path = tmp_path / "file.json"
    path.write_text('[[1], [2]]')
    assert load_json(str(path)) == [[1], [2]]


def test_load_json_accepts_a_bracket_heavy_string(tmp_path) -> None:
    """A string that contains many brackets is not "too deep" nesting.

    The depth guard must ignore brackets inside JSON string literals: a valid
    file whose string value is a long run of ``[``/``{`` (a regex, a banner, a
    data blob) is shallow and must load, not be rejected as nesting too deeply.
    """
    path = tmp_path / "file.json"
    payload = {"pattern": "[" * 1500 + "{" * 1500}
    path.write_text(json.dumps(payload))
    assert load_json(str(path)) == payload


def test_load_json_accepts_escaped_quotes_around_brackets(tmp_path) -> None:
    """Escaped quotes inside a string do not end the string early.

    A bracket-heavy string that also contains escaped quotes (``\\"``) must
    still be treated as a single string, so its brackets do not count toward
    nesting depth.
    """
    path = tmp_path / "file.json"
    payload = {"pattern": '\\"' + "[" * 1500 + '\\"'}
    path.write_text(json.dumps(payload))
    assert load_json(str(path)) == payload


def test_load_json_ignores_a_closing_bracket_that_overflows_depth(tmp_path) -> None:
    """A stray closing bracket at depth zero is ignored by the guard.

    The guard only decrements depth when it is positive, so an unbalanced
    closer does not drive depth negative; the file is then rejected by the
    JSON parser as unusable.
    """
    path = tmp_path / "file.json"
    path.write_text("]")
    with pytest.raises(ValueError):
        load_json(str(path))


def test_load_json_converts_a_parser_recursion_error_to_value_error(tmp_path, monkeypatch) -> None:
    """A RecursionError from the JSON parser is reported as an unusable value,
    like broken JSON, instead of leaking a traceback."""
    import ethscan.fileio as fileio

    path = tmp_path / "file.json"
    path.write_text("{}")

    def raising_loads(text):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(fileio.json, "loads", raising_loads)

    with pytest.raises(ValueError, match="nests too deeply"):
        load_json(str(path))


def test_atomic_write_cleanup_swallows_unlink_error(tmp_path, monkeypatch) -> None:
    """A failed write re-raises the original error even when removing the temp
    file itself fails with OSError."""
    path = tmp_path / "file.txt"
    path.write_text("original\n")

    import ethscan.fileio as fileio

    def boom(handle):
        handle.write("partial")
        raise RuntimeError("boom")

    def unlink_raises(name, *args, **kwargs):
        raise OSError("unlink failed")

    monkeypatch.setattr(fileio.os, "unlink", unlink_raises)

    with pytest.raises(RuntimeError, match="boom"):
        fileio._atomic_write(path, boom)

    assert path.read_text() == "original\n"


def test_sanitize_csv_cell_prefixes_formula_triggers() -> None:
    from ethscan.fileio import sanitize_csv_cell

    assert sanitize_csv_cell("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert sanitize_csv_cell("=HYPERLINK(\"http://x\")") == "'=HYPERLINK(\"http://x\")"
    assert sanitize_csv_cell("@SUM(A1:A2)") == "'@SUM(A1:A2)"
    assert sanitize_csv_cell("+cmd") == "'+cmd"
    assert sanitize_csv_cell("\tfoo") == "'\tfoo"
    assert sanitize_csv_cell("\rfoo") == "'\rfoo"


def test_sanitize_csv_cell_keeps_numeric_and_safe_values() -> None:
    from ethscan.fileio import sanitize_csv_cell

    assert sanitize_csv_cell("-1") == "-1"
    assert sanitize_csv_cell("+2") == "+2"
    assert sanitize_csv_cell(42) == 42
    assert sanitize_csv_cell(None) is None
    assert sanitize_csv_cell("") == ""
    assert sanitize_csv_cell("plain text") == "plain text"


def test_sanitize_csv_cell_numeric_vs_formula_property() -> None:
    """Property test: for strings starting with formula triggers, sanitize_csv_cell
    must match Python's float() oracle. If float() parses it, it's a pure number
    and passes through; otherwise it gets a leading quote.

    Strings not starting with triggers pass through unchanged regardless of
    float()-parseability (they are not formula-injection vectors per the spec).
    """
    import random
    import string
    from ethscan.fileio import sanitize_csv_cell

    TRIGGERS = ("=", "+", "-", "@", "\t", "\r")

    def is_float_parseable(s: str) -> bool:
        try:
            float(s)
            return True
        except ValueError:
            return False

    rng = random.Random(20261126)

    # Test 1: Random strings starting with triggers - must match float() oracle
    for _ in range(2000):
        trigger = rng.choice(TRIGGERS)
        # Generate rest of string from various character classes
        rest_len = rng.randint(0, 50)
        chars = string.ascii_letters + string.digits + string.punctuation + " \t\r\n"
        rest = "".join(rng.choice(chars) for _ in range(rest_len))
        s = trigger + rest

        result = sanitize_csv_cell(s)
        float_ok = is_float_parseable(s)

        if float_ok:
            assert result == s, f"float-parseable {s!r} should pass through, got {result!r}"
        else:
            assert result == "'" + s, f"non-float {s!r} should be quoted, got {result!r}"

    # Test 2: Strings NOT starting with triggers pass through unchanged
    non_triggers = tuple(c for c in (string.ascii_letters + string.digits + " ") if c not in TRIGGERS)
    for _ in range(1000):
        first = rng.choice(non_triggers)
        rest_len = rng.randint(0, 50)
        chars = string.ascii_letters + string.digits + string.punctuation + " \t\r\n"
        rest = "".join(rng.choice(chars) for _ in range(rest_len))
        s = first + rest

        result = sanitize_csv_cell(s)
        assert result == s, f"non-trigger {s!r} should pass through unchanged, got {result!r}"

    # Test 3: Empty string and non-strings pass through unchanged
    assert sanitize_csv_cell("") == ""
    assert sanitize_csv_cell(None) is None
    assert sanitize_csv_cell(42) == 42
    assert sanitize_csv_cell([]) == []
    assert sanitize_csv_cell({}) == {}
