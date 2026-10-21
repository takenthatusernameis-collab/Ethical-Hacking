"""Shared helpers for reading the input files that the CLI accepts.

Every option that takes a file can point at a file whose *content* is
hostile: a wordlist with a line that is not valid UTF-8, a JSON file that is
truncated, an XML file that is not XML at all. The helpers below read such a
file without raising, so the command that uses them can report the problem in
its own output instead of leaking a traceback.
"""
from __future__ import annotations

import codecs
import json
from typing import Any


def read_text(path: str) -> str:
    """Read a text file leniently.

    The bytes that are not valid UTF-8 are replaced instead of raising a
    ``UnicodeDecodeError``: a file with a stray byte is used as far as it can
    be read, and the command reports what it makes of the result.

    Args:
        path: Path to the file.

    Returns:
        The content of the file.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def read_lines(path: str, *, skip_comments: bool = True) -> list[str]:
    """Read a text file into a list of stripped, non-empty lines.

    Args:
        path: Path to the file.
        skip_comments: Drop the lines whose first non-blank character is ``#``.

    Returns:
        The lines of the file, stripped, without the empty ones.
    """
    lines: list[str] = []
    for raw_line in read_text(path).split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if skip_comments and stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def load_json(path: str) -> Any:
    """Load a JSON file.

    A file whose content nests deeper than the parser can read is a file that
    cannot be used: the JSON parser raises a ``RecursionError`` for it, which
    is reported as an unusable value (a ``ValueError``) like a file that holds
    broken JSON.

    Args:
        path: Path to the file.

    Returns:
        The parsed content of the file.

    Raises:
        ValueError: The file does not hold valid JSON (``json.JSONDecodeError``
            is a ``ValueError``), or it nests too deeply to be parsed.
        OSError: The file cannot be read.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        try:
            return json.load(handle)
        except RecursionError as exc:
            raise ValueError(
                "the file nests too deeply to be parsed as JSON"
            ) from exc


def is_utf8(path: str) -> bool:
    """Return True when the file holds only bytes that are valid UTF-8.

    A credential file that is not valid UTF-8 cannot be read without changing
    the credentials it holds, so the commands that take one refuse it instead
    of hashing a mangled password.

    Args:
        path: Path to the file.

    Returns:
        True when the file can be decoded as UTF-8, False when it cannot or
        cannot be read.
    """
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
    except (UnicodeDecodeError, OSError):
        return False
    return True
