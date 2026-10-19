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

The module is intentionally free of any click import: the translation from a
library error to a click usage error happens in :mod:`ethscan.cli`.
"""
from __future__ import annotations

from urllib.parse import SplitResult


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
