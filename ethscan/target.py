"""Shared target-specification types and helpers for ethscan.

Several protocol modules accept a target string that may be a bare host, a
``host:port`` pair, or a scheme URL (``redis://host:port``). When such a
string does not contain a usable host, the module raises
:class:`TargetSpecError` so the CLI layer can report the problem as a usage
error instead of letting a raw traceback escape.

:func:`url_port` does the same for a target whose port is not a number:
``urllib.parse`` raises a bare ``ValueError`` when the port of a parsed URL
cannot be turned into an integer, and that error is re-raised here as a
:class:`TargetSpecError` with its message unchanged.

:func:`check_target_host` does the same for a target whose host contains a
space or a control character: ``http.client`` refuses such a host with an
``http.client.InvalidURL``, which derives from ``HTTPException`` and not
from ``ValueError``, so it escapes the ``except ValueError`` handlers of the
library and reaches the user as a raw traceback.

:func:`check_target_path` does the same for a target whose path or query
contains a space or a control character: ``http.client`` refuses such a
request target with an ``http.client.InvalidURL`` for the same reason. The
fragment (``#...``) is not sent to the server and is therefore not
validated.

The module is intentionally free of any click import: the translation from a
library error to a click usage error happens in :mod:`ethscan.cli`.
"""
from __future__ import annotations

import re
from urllib.parse import SplitResult

# The characters that ``http.client`` refuses in a URL: the C0 control
# characters, the space and DEL.
_DISALLOWED_HOST_RE = re.compile(r"[\x00-\x20\x7f]")

_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


class TargetSpecError(ValueError):
    """Raised when a target string does not contain a usable host.

    Subclasses :class:`ValueError` so that modules which treat an
    unparsable target as a failed probe (and report it inside their own
    output) keep working unchanged, while letting the CLI layer distinguish
    an invalid target from unrelated value errors and turn it into a usage
    error.
    """


def url_port(parsed: SplitResult) -> int | None:
    """Return the port of a parsed URL, or ``None`` when it carries no port.

    ``urllib.parse`` raises a bare ``ValueError`` when the port is not an
    integer ("Port could not be cast to integer value as 'x'") or is out of
    range. The error is re-raised as a :class:`TargetSpecError` with the
    original message intact, so the CLI can report it as a usage error while
    modules that treat an unusable target as a failed probe keep the exact
    wording they report today.

    Args:
        parsed: The result of ``urllib.parse.urlparse`` (or ``urlsplit``).

    Returns:
        The port number, or ``None`` when the URL has no port.

    Raises:
        TargetSpecError: If the port is not a valid port number.
    """
    try:
        return parsed.port
    except ValueError as exc:
        raise TargetSpecError(str(exc)) from exc


def check_port(port: int | str) -> int:
    """Return the port when it is a valid port number.

    The port of a bare ``host:port`` target is parsed by hand, so it can be
    text that ``str.isdigit`` accepts but ``int`` refuses (the superscript
    digits, for example). The text is converted here, so an unusable port is
    reported as a :class:`TargetSpecError` instead of a raw ``ValueError``.

    Args:
        port: The candidate port, either as a number or as the text of a
            number as it appears in a ``host:port`` target.

    Returns:
        The port number when it is in range.

    Raises:
        TargetSpecError: If the port is not a number or is outside 0-65535.
    """
    if isinstance(port, str):
        try:
            value = int(port)
        except ValueError as exc:
            raise TargetSpecError(f"Invalid port {port!r}") from exc
    else:
        value = port
    if value < 0 or value > 65535:
        raise TargetSpecError("Port out of range 0-65535")
    return value


def _host_of(target: str) -> str:
    """Return the authority part of a raw target string.

    Args:
        target: A target string, with or without a scheme.

    Returns:
        The part of the target that stands between the scheme and the path,
        the query or the fragment. The userinfo and the port are kept,
        because they belong to the authority that ``http.client`` validates.
    """
    remainder = target.strip()
    scheme = _SCHEME_RE.match(remainder)
    if scheme is not None:
        remainder = remainder[scheme.end():]
    for delimiter in ("/", "?", "#"):
        index = remainder.find(delimiter)
        if index != -1:
            remainder = remainder[:index]
    return remainder



def _path_of(target: str) -> str:
    """Return the path+query portion of a raw target string.

    The fragment (``#...``) is not sent to the server and is therefore not
    validated here.
    """
    remainder = target.strip()
    scheme = _SCHEME_RE.match(remainder)
    if scheme is not None:
        remainder = remainder[scheme.end():]
    # Find start of path
    slash = remainder.find('/')
    if slash != -1:
        # From slash to end, excluding fragment
        fragment = remainder.find('#', slash)
        if fragment != -1:
            return remainder[slash:fragment]
        return remainder[slash:]
    query = remainder.find('?')
    if query != -1:
        fragment = remainder.find('#', query)
        if fragment != -1:
            return remainder[query:fragment]
        return remainder[query:]
    return ''


def check_target_path(target: str) -> None:
    """Reject a target whose path or query contains a space or control char."""
    path_part = _path_of(target)
    if path_part and _DISALLOWED_HOST_RE.search(path_part):
        raise TargetSpecError("Target path contains a space or control character")


def check_target_host(target: str) -> None:
    """Reject a target whose host contains a space or a control character.

    The host is read from the raw target text and not from
    ``urllib.parse``: ``urlsplit`` silently removes tab, carriage return and
    newline characters, so a parsed host can look clean while the host that
    is actually sent over the network is not.

    A host with a space or a control character is refused by
    ``http.client``, which raises an ``http.client.InvalidURL``. That error
    derives from ``HTTPException`` and not from ``ValueError``, so it
    escapes the ``except ValueError`` handlers of the library and reaches
    the user as a raw traceback.

    Args:
        target: A target string, with or without a scheme. A bare host is
            accepted as well.

    Raises:
        TargetSpecError: If the host contains a space or a control character.
    """
    if _DISALLOWED_HOST_RE.search(_host_of(target)):
        raise TargetSpecError("Target host contains a space or control character")
