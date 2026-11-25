"""Shared helpers for reading and writing files.

Every option that takes a file can point at a file whose *content* is
hostile: a wordlist with a line that is not valid UTF-8, a JSON file that is
truncated, an XML file that is not XML at all. The helpers below read such a
file without raising, so the command that uses them can report the problem in
its own output instead of leaking a traceback.
"""
from __future__ import annotations

import codecs
import csv
import json
import os
import tempfile
from pathlib import Path
from typing import IO, Any, Callable, Iterable


def read_text(path: str | Path) -> str:
    """Read a text file leniently.

    The bytes that are not valid UTF-8 are replaced instead of raising a
    ``UnicodeDecodeError``: a file with a stray byte is used as far as it can
    be read, and the command reports what it makes of the result.

    Args:
        path: Path to the file.

    Returns:
        The content of the file.
    """
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def read_lines(path: str | Path, *, skip_comments: bool = True) -> list[str]:
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


def load_json(path: str | Path) -> Any:
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
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    # Guard against inputs that nest deeper than the parser can safely handle
    # (Python's json parser may not raise RecursionError on every version).
    # Brackets that appear inside a JSON string literal do not contribute to
    # nesting depth, so the scan tracks whether it is inside a string (honouring
    # backslash escapes); without this a valid file whose string merely contains
    # many '[' or '{' characters (a regex, a banner, a data blob) would be
    # wrongly rejected as nesting too deeply.
    depth = 0
    max_depth = 0
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        elif ch in "]}":
            if depth > 0:
                depth -= 1
    if max_depth > 1000:
        raise ValueError("the file nests too deeply to be parsed as JSON")
    try:
        return json.loads(text)
    except RecursionError as exc:
        raise ValueError(
            "the file nests too deeply to be parsed as JSON"
        ) from exc


def is_utf8(path: str | Path) -> bool:
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


def _atomic_write(
    path: Path,
    write: Callable[[IO[str]], None],
    *,
    encoding: str = "utf-8",
) -> None:
    """Write to ``path`` atomically: temp file in the same directory, then rename.

    A non-atomic write opens the destination with ``"w"`` (truncating) *before*
    it writes, so a failure mid-write -- a disk full, a read-only file system,
    a parent that is a file -- leaves the user's previous content destroyed
    instead of intact. Writing to a temporary file in the same directory and
    renaming it over the destination keeps the old content until the new one
    is complete: the rename is atomic on POSIX, and the temp file is removed
    when the write fails.

    Args:
        path: The path of the file to write.
        write: A callable that receives an open text handle and writes the
            content to it.
        encoding: File encoding (defaults to utf-8).

    Raises:
        OSError: The destination cannot be written (its parent does not exist
            and cannot be created, the parent is not a directory, the path is
            a directory, the file system refuses the write, and so on). The
            original error is preserved.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
        encoding=encoding,
    )
    try:
        with tmp as handle:
            write(handle)
        os.replace(tmp.name, path)
    except BaseException:
        # A failed write must not leave a partial temp file behind.
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def write_text(path: str | Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write text to a file atomically.

    The parent directory of ``path`` is created when it does not exist, the
    same way ``config --init`` writes its sample file: a report whose
    directory was never created is a path the user meant to use, not a usage
    error. A path that still cannot be written -- a directory, a path whose
    parent is a file, a name the file system refuses -- raises ``OSError``,
    which the caller reports as a usage error instead of reaching the user as
    a raw traceback.

    The write is atomic: the content is written to a temporary file in the
    same directory and renamed over the destination, so a failure mid-write
    leaves the previous content intact.

    Args:
        path: Path to the file.
        content: Text content to write.
        encoding: File encoding (defaults to utf-8).
    """
    p = Path(path)

    def _write(handle: IO[str]) -> None:
        handle.write(content)

    _atomic_write(p, _write, encoding=encoding)


def write_json(path: str | Path, data: Any, *, indent: int = 2) -> None:
    """Write data as JSON to a file atomically.

    The parent directory of ``path`` is created when it does not exist, and the
    write is atomic: the content is written to a temporary file in the same
    directory and renamed over the destination, so a failure mid-write leaves
    the previous content intact.

    Args:
        path: Path to the file.
        data: Data to serialize as JSON.
        indent: JSON indentation (defaults to 2).
    """
    p = Path(path)

    def _write(handle: IO[str]) -> None:
        json.dump(data, handle, indent=indent)
        handle.write("\n")

    _atomic_write(p, _write)


def sanitize_csv_cell(value: Any) -> Any:
    """Neutralise CSV formula injection (CWE-1236).

    Spreadsheet applications evaluate a cell whose content begins with ``=``,
    ``+``, ``-``, ``@``, TAB or CR as a formula. A hostile value (e.g. a
    banner or DNS record) written verbatim via ``csv.writer`` can therefore
    execute when the resulting CSV is opened. This helper prefixes such string
    cells with a single quote so they are treated as text, while leaving purely
    numeric cells (including negative numbers) untouched.

    Non-string values are returned unchanged.
    """
    if not isinstance(value, str) or not value:
        return value
    if value[0] in ("=", "+", "-", "@", "\t", "\r"):
        # Keep purely numeric cells (e.g. "-1", "+2", "3.14") unsanitised.
        try:
            float(value)
            return value
        except ValueError:
            return "'" + value
    return value


class SanitizingCSVWriter:
    """A ``csv.writer`` wrapper that neutralises formula injection per cell.

    Each cell is passed through :func:`sanitize_csv_cell` before being handed
    to the underlying writer, so a hostile banner or DNS record can no longer
    execute as a spreadsheet formula when the CSV is opened. Only
    ``writerow`` is provided because that is the sole method the codebase uses.
    """

    def __init__(self, handle: IO[str], **kwargs: Any) -> None:
        self._writer = csv.writer(handle, **kwargs)

    def writerow(self, row: Iterable[Any]) -> Any:
        return self._writer.writerow([sanitize_csv_cell(cell) for cell in row])


def csv_writer(handle: IO[str], **kwargs: Any) -> SanitizingCSVWriter:
    """Return a :class:`csv.writer` that sanitizes every cell (CWE-1236).

    Drop-in replacement for ``csv.writer`` used by every ``format_*_report_csv``
    helper so formula-triggering values are prefixed with a single quote.
    """
    return SanitizingCSVWriter(handle, **kwargs)
