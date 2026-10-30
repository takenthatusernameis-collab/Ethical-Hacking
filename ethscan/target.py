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
library and reaches the user as a raw traceback. The host is checked after
its percent escapes are decoded as well, because ``urllib.request`` decodes
them before the host is used.

:func:`strip_userinfo` removes the userinfo part of the authority of a URL:
``urllib.request`` keeps it in the host it connects to, and ``http.client``
then reads the text after the last colon of that host as the port.

:func:`check_target_path` does the same for a target whose path or query
contains a space or a control character: ``http.client`` refuses such a
request target with an ``http.client.InvalidURL`` for the same reason. The
fragment (``#...``) is not sent to the server and is therefore not
validated.

:func:`parse_url` parses a URL and reports a URL that ``urllib.parse``
refuses (an unmatched bracket in the authority) as a
:class:`TargetSpecError` instead of a bare ``ValueError``.

The module is intentionally free of any click import: the translation from a
library error to a click usage error happens in :mod:`ethscan.cli`.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import ParseResult, SplitResult, unquote, urlparse

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


def _bracket_ipv6_netloc(parsed: ParseResult) -> ParseResult:
    """Bracket an unbracketed IPv6 literal in the authority of ``parsed``.

    ``urllib.parse.urlparse`` reads the authority of a URL that carries an
    unbracketed IPv6 literal as ``host:port``: it takes the text after the
    first colon as the port, so ``https://2001:db8::1`` parses with
    ``hostname == "2001"`` and ``port == "db8::1"``. The literal is only valid
    in the authority when it is bracketed (``https://[2001:db8::1]``), so the
    toolkit brackets it before the host is read, the way a URL that the user
    typed correctly would have parsed it.

    A literal is detected with :mod:`ipaddress`. The port of the authority is
    the last colon-separated part when it is all digits; the literal is the
    rest. The literal-with-a-port form is tried first, because an IPv6 literal
    with a port is the common case and because the whole netloc can itself be
    a valid IPv6 literal (for example ``2001:db8::1:6379`` is one), which would
    swallow the port if it were tried first. When the literal-with-a-port form
    does not hold a literal, the whole netloc is tried as a bare literal, so a
    target such as ``redis://2001:db8::1`` is bracketed too. A netloc that is
    already bracketed, that holds no IPv6 literal, or that carries a userinfo
    is left unchanged, because bracketing it would change the host the user
    gave.

    Args:
        parsed: The result of ``urllib.parse.urlparse``.

    Returns:
        ``parsed`` with its netloc bracketed when it holds an unbracketed
        IPv6 literal, ``parsed`` unchanged otherwise.
    """
    netloc = parsed.netloc
    if not netloc or "[" in netloc:
        return parsed
    # A literal with an optional port. The port is the last colon-separated
    # part when it is all digits; the literal is the rest. The literal is
    # tried first, because an IPv6 literal with a port is the common case and
    # because the whole netloc can itself be a valid IPv6 literal (for example
    # ``2001:db8::1:6379`` is one), which would swallow the port if it were
    # tried first.
    port_part: str | None = None
    host_part = netloc
    if ":" in netloc:
        head, _, tail = netloc.rpartition(":")
        if tail and tail.isdigit():
            port_part = tail
            host_part = head
    # The literal-with-a-port form is tried first: an IPv6 literal with a port
    # is the common case, and the whole netloc can itself be a valid IPv6
    # literal (for example ``2001:db8::1:6379`` is one), which would swallow
    # the port if it were tried first. When that form does not hold a literal,
    # the whole netloc is tried as a bare literal, so a target such as
    # ``redis://2001:db8::1`` is bracketed too.
    candidates = [host_part, netloc]
    for candidate in candidates:
        try:
            ip = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        # Only bracket IPv6 literals, not IPv4
        if isinstance(ip, ipaddress.IPv4Address):
            continue
        if candidate == netloc:
            new_netloc = "[" + candidate + "]"
        else:
            new_netloc = "[" + candidate + "]:" + port_part
        return parsed._replace(netloc=new_netloc)
    return parsed


def parse_url(url: str) -> ParseResult:
    """Parse a URL, raising :class:`TargetSpecError` when urllib refuses it.

    ``urllib.parse.urlparse`` raises a bare ``ValueError`` ("Invalid IPv6
    URL") for a URL whose authority holds an unmatched bracket, e.g.
    ``http://[::1`` or ``http://example.com]``. The error is re-raised as a
    :class:`TargetSpecError` with the original message intact, so the CLI can
    report it as a usage error while modules that treat an unusable target as
    a failed probe keep working unchanged.

    An authority that holds an unbracketed IPv6 literal is bracketed before
    the host is read: ``urllib.parse`` otherwise reads the text after the
    first colon as the port and returns a truncated host, so a target such as
    ``https://2001:db8::1`` would be probed as the host ``2001``.

    Args:
        url: The URL to parse.

    Returns:
        The parsed URL, exactly as ``urllib.parse.urlparse`` returns it when
        the authority carries no unbracketed IPv6 literal.

    Raises:
        TargetSpecError: If the URL cannot be parsed.
    """
    try:
        parsed = _bracket_ipv6_netloc(urlparse(url))
    except ValueError as exc:
        raise TargetSpecError(str(exc)) from exc
    return parsed


def url_port(parsed: SplitResult | ParseResult) -> int | None:
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


def strip_userinfo(url: str) -> str:
    """Return ``url`` without the userinfo part of its authority.

    ``urllib.request`` keeps the userinfo in the host it connects to, and
    ``http.client`` then reads the text after the last colon of that host as
    the port: the target ``http://user:pass@example.com`` is refused with
    "InvalidURL: nonnumeric port: 'pass@example.com'". The credentials are
    of no use to the toolkit, so they are dropped and the host is used, the
    way the whois, mongodb and ssh modules already do it.

    Only the userinfo is removed: the scheme, the host, the port, the path,
    the query and the fragment are kept exactly as they are.

    Args:
        url: A URL, with or without a scheme.

    Returns:
        The URL without its userinfo, unchanged when it carries none.
    """
    scheme, separator, remainder = url.partition("://")
    if not separator:
        scheme, remainder = "", url
    end = len(remainder)
    for delimiter in ("/", "?", "#"):
        index = remainder.find(delimiter)
        if index != -1 and index < end:
            end = index
    authority = remainder[:end]
    if "@" not in authority:
        return url
    host = authority.rsplit("@", 1)[1]
    return f"{scheme}{separator}{host}{remainder[end:]}"



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

    The percent escapes of the host are decoded before the host is checked,
    because ``urllib.request`` decodes them as well: a host that looks
    harmless in its raw form (``%00``) carries a control character once it
    is decoded, and ``http.client`` refuses such a host.

    A host with a space or a control character is refused by
    ``http.client``, which raises an ``http.client.InvalidURL``. That error
    derives from ``HTTPException`` and not from ``ValueError``, so it
    escapes the ``except ValueError`` handlers of the library and reaches
    the user as a raw traceback.

    Args:
        target: A target string, with or without a scheme. A bare host is
            accepted as well.

    Raises:
        TargetSpecError: If the host contains a space or a control
            character, also when they only appear once the percent escapes
            of the host are decoded.
    """
    authority = _host_of(target)
    if _DISALLOWED_HOST_RE.search(authority):
        raise TargetSpecError("Target host contains a space or control character")
    if _DISALLOWED_HOST_RE.search(unquote(authority)):
        raise TargetSpecError("Target host contains a space or control character")
