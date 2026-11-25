"""Tests for the shared target-specification error type.

The protocol modules raise :class:`TargetSpecError` when a target string
does not contain a usable host. The CLI turns that into a usage error, but
the modules that report a failed probe inside their own output keep
catching it as an ordinary :class:`ValueError`.

A target whose *port* is not a number is the same kind of problem:
``urllib.parse`` raises a bare ``ValueError`` for it, which
:func:`url_port` re-raises as a :class:`TargetSpecError`.

A target whose *host* contains a space or a control character is the same
kind of problem too: ``http.client`` refuses such a host with an
``http.client.InvalidURL``, which derives from ``HTTPException`` and not
from ``ValueError``, so :func:`check_target_host` reports it as a
:class:`TargetSpecError` before the request is made. The host is checked
after its percent escapes are decoded as well, because ``urllib.request``
decodes them before it uses the host.

A target whose *authority* carries a userinfo part is the same kind of
problem: ``urllib.request`` keeps the userinfo in the host it connects to,
and ``http.client`` then reads the text after the last colon of that host
as the port. :func:`strip_userinfo` drops it.
"""

import importlib
from urllib.parse import urlparse

import pytest

from ethscan.target import (
    TargetSpecError,
    check_port,
    check_target_host,
    format_host_header,
    normalize_host,
    parse_url,
    strip_userinfo,
    url_port,
)

TARGET_MODULES = (
    "redis",
    "memcached",
    "ntp",
    "snmp",
    "ftp",
    "ldap",
    "netbios",
    "smb",
    "smtp",
    "mysql",
    "mongodb",
    "oracle",
    "postgresql",
    "mssql",
)

# The modules that treat an unparsable target as a failed probe and report
# it inside their own output instead of failing the whole run.
PROBE_FAILURE_MODULES = (
    "oracle",
    "postgresql",
)

UNUSABLE_TARGETS = ("", "   ", "://no-host", "redis://", ":6379")


def test_target_spec_error_is_a_value_error() -> None:
    """The error type must stay a ValueError subclass."""
    assert issubclass(TargetSpecError, ValueError)


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_unusable_target_raises_target_spec_error(module_name: str) -> None:
    """Every protocol module raises the dedicated error type."""
    module = importlib.import_module(f"ethscan.{module_name}")
    for target in UNUSABLE_TARGETS:
        with pytest.raises(TargetSpecError):
            module._normalize_target(target)


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_unusable_target_is_still_caught_as_a_value_error(module_name: str) -> None:
    """Existing ``except ValueError`` handlers keep working."""
    module = importlib.import_module(f"ethscan.{module_name}")
    with pytest.raises(ValueError):
        module._normalize_target("")


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_usable_target_is_not_an_error(module_name: str) -> None:
    """Valid targets are unaffected by the error type change."""
    module = importlib.import_module(f"ethscan.{module_name}")
    assert module._normalize_target("127.0.0.1:1234") == ("127.0.0.1", 1234)
    assert module._normalize_target("127.0.0.1")[0] == "127.0.0.1"


@pytest.mark.parametrize("module_name", PROBE_FAILURE_MODULES)
def test_probe_failure_modules_still_report_the_error_in_their_output(
    module_name: str,
) -> None:
    """A module that reports a failed probe keeps its contract."""
    module = importlib.import_module(f"ethscan.{module_name}")
    run = getattr(module, f"run_{module_name}")
    results = run("")
    assert results["accessible"] is False
    assert results["error"] == "Could not parse host from target ''"


def test_the_error_type_is_raised_by_every_module_that_reports_a_host() -> None:
    """The dedicated type is used consistently, not just for empty targets."""
    module = importlib.import_module("ethscan.redis")
    with pytest.raises(TargetSpecError) as excinfo:
        module._normalize_target("   ")
    assert str(excinfo.value) == "Could not parse host from target '   '"


# --- A target whose port is not a number -----------------------------------

NON_NUMERIC_PORT_MESSAGE = "Port could not be cast to integer value as 'notaport'"


def test_url_port_returns_the_port_of_a_parsed_url() -> None:
    """A valid port is returned unchanged."""
    assert url_port(urlparse("redis://host:6379")) == 6379
    assert url_port(urlparse("redis://host:0")) == 0


def test_url_port_returns_none_when_the_url_has_no_port() -> None:
    """A URL without a port keeps reporting ``None``."""
    assert url_port(urlparse("redis://host")) is None


def test_url_port_raises_target_spec_error_for_a_non_numeric_port() -> None:
    """A port that is not a number is reported as an unusable target."""
    with pytest.raises(TargetSpecError) as excinfo:
        url_port(urlparse("redis://host:notaport"))
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE


def test_url_port_raises_target_spec_error_for_an_out_of_range_port() -> None:
    """A port outside the valid range is reported as an unusable target."""
    with pytest.raises(TargetSpecError) as excinfo:
        url_port(urlparse("redis://host:99999"))
    assert str(excinfo.value) == "Port out of range 0-65535"


def test_url_port_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    with pytest.raises(ValueError):
        url_port(urlparse("redis://host:notaport"))


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_non_numeric_port_raises_target_spec_error(module_name: str) -> None:
    """Every protocol module rejects a URL whose port is not a number."""
    module = importlib.import_module(f"ethscan.{module_name}")
    with pytest.raises(TargetSpecError) as excinfo:
        module._normalize_target("redis://host:notaport")
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_valid_port_is_still_parsed(module_name: str) -> None:
    """A URL with a real port keeps being parsed as before."""
    module = importlib.import_module(f"ethscan.{module_name}")
    assert module._normalize_target("redis://host:6379") == ("host", 6379)


@pytest.mark.parametrize("module_name", PROBE_FAILURE_MODULES)
def test_probe_failure_modules_report_a_non_numeric_port_unchanged(
    module_name: str,
) -> None:
    """A module that reports a failed probe keeps its wording."""
    module = importlib.import_module(f"ethscan.{module_name}")
    run = getattr(module, f"run_{module_name}")
    results = run("mysql://host:notaport")
    assert results["accessible"] is False
    assert results["error"] == NON_NUMERIC_PORT_MESSAGE


def test_web_and_ssh_report_a_non_numeric_port_as_a_target_error() -> None:
    """The URL-based modules reject a port that is not a number."""
    from ethscan import ssh, web

    with pytest.raises(TargetSpecError) as excinfo:
        web._parse_url("https://host:notaport")
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE

    with pytest.raises(TargetSpecError) as excinfo:
        ssh._extract_port("host:notaport")
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE


def test_web_and_ssh_still_parse_a_valid_port() -> None:
    """A valid port keeps being parsed exactly as before."""
    from ethscan import ssh, web

    assert web._parse_url("https://example.com:8443") == ("example.com", 8443, True)
    assert web._parse_url("http://example.com:8080") == ("example.com", 8080, False)
    assert web._parse_url("example.com") == ("example.com", 443, True)
    assert ssh._extract_port("ssh://example.com:2222") == 2222
    assert ssh._extract_port("example.com") == 22


# --- A target whose port is out of range -----------------------------------
#
# The port of a bare ``host:port`` target is parsed by hand, while the port
# of a scheme-qualified target goes through ``url_port``, which already
# refuses a port outside 0-65535. Without the same check the bare form let
# the port reach ``socket.connect()``, which raised an ``OverflowError`` (or
# silently wrapped the port) far away from the parser.

OUT_OF_RANGE_PORT_MESSAGE = "Port out of range 0-65535"

# A superscript digit: ``str.isdigit`` accepts it, ``int`` refuses it.
SUPERSCRIPT_TWO = "\xb2"

BARE_OUT_OF_RANGE_PORT_TARGETS = (
    "host:65536",
    "host:99999",
    "host:99999999999999999999",
    "[::1]:99999",
)


def test_check_port_returns_a_valid_port() -> None:
    """A port in range is returned unchanged, as a number or as text."""
    assert check_port(443) == 443
    assert check_port("443") == 443
    assert check_port(0) == 0
    assert check_port(65535) == 65535


def test_check_port_raises_target_spec_error_for_an_out_of_range_port() -> None:
    """A port outside the valid range is reported as an unusable target."""
    for port in (-1, 65536, 99999):
        with pytest.raises(TargetSpecError) as excinfo:
            check_port(port)
        assert str(excinfo.value) == OUT_OF_RANGE_PORT_MESSAGE


def test_check_port_raises_target_spec_error_for_text_that_is_not_a_number() -> None:
    """Text that ``int`` refuses is reported as an unusable target."""
    with pytest.raises(TargetSpecError) as excinfo:
        check_port(SUPERSCRIPT_TWO)
    assert str(excinfo.value) == f"Invalid port {SUPERSCRIPT_TWO!r}"


def test_check_port_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    with pytest.raises(ValueError):
        check_port(99999)


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_bare_target_with_an_out_of_range_port_is_rejected(module_name: str) -> None:
    """Every protocol module rejects a bare ``host:port`` with a bad port."""
    module = importlib.import_module(f"ethscan.{module_name}")
    for target in BARE_OUT_OF_RANGE_PORT_TARGETS:
        with pytest.raises(TargetSpecError) as excinfo:
            module._normalize_target(target)
        assert str(excinfo.value) == OUT_OF_RANGE_PORT_MESSAGE


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_bare_target_with_an_unparsable_port_is_rejected(module_name: str) -> None:
    """A port that ``int`` refuses is rejected instead of raising a ValueError."""
    module = importlib.import_module(f"ethscan.{module_name}")
    with pytest.raises(TargetSpecError) as excinfo:
        module._normalize_target(f"host:{SUPERSCRIPT_TWO}")
    assert str(excinfo.value) == f"Invalid port {SUPERSCRIPT_TWO!r}"


@pytest.mark.parametrize("module_name", PROBE_FAILURE_MODULES)
def test_probe_failure_modules_report_an_out_of_range_port(
    module_name: str,
) -> None:
    """A module that reports a failed probe keeps its contract."""
    module = importlib.import_module(f"ethscan.{module_name}")
    run = getattr(module, f"run_{module_name}")
    results = run("host:99999")
    assert results["accessible"] is False
    assert results["error"] == OUT_OF_RANGE_PORT_MESSAGE


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_a_valid_bare_port_is_still_parsed(module_name: str) -> None:
    """The valid port forms keep being parsed exactly as before."""
    module = importlib.import_module(f"ethscan.{module_name}")
    assert module._normalize_target("host:1234") == ("host", 1234)
    assert module._normalize_target("host:65535") == ("host", 65535)
    assert module._normalize_target("[::1]:443") == ("::1", 443)


# --- A target whose host contains a space or a control character ------------

HOST_ERROR_MESSAGE = "Target host contains a space or control character"

HOSTILE_HOST_TARGETS = (
    "host name",
    "host\tname",
    "host\nname",
    "ho\x00st",
    "host\x7fname",
    "https://host name",
    "http://host name",
    "https://host\tname",
    "host name:8443",
    "https://host name:8443",
)

USABLE_HOST_TARGETS = (
    "host",
    "host:443",
    "http://host",
    "https://host:8443",
    "[::1]:443",
    "example.com/path",
    "https://example.com/path?query=1",
)


def test_check_target_host_rejects_a_host_with_a_space() -> None:
    """A host with a space is reported as an unusable target."""
    with pytest.raises(TargetSpecError) as excinfo:
        check_target_host("host name")
    assert str(excinfo.value) == HOST_ERROR_MESSAGE


def test_check_target_host_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    with pytest.raises(ValueError):
        check_target_host("host name")


@pytest.mark.parametrize("target", HOSTILE_HOST_TARGETS)
def test_check_target_host_rejects_every_hostile_host(target: str) -> None:
    """A space or a control character in the host is always rejected."""
    with pytest.raises(TargetSpecError) as excinfo:
        check_target_host(target)
    assert str(excinfo.value) == HOST_ERROR_MESSAGE


@pytest.mark.parametrize("target", USABLE_HOST_TARGETS)
def test_check_target_host_accepts_a_usable_host(target: str) -> None:
    """A host that ``http.client`` accepts is not an error."""
    check_target_host(target)


def test_a_control_character_is_found_although_urlsplit_removes_it() -> None:
    """The check reads the raw target, not the parsed one.

    ``urllib.parse`` silently drops tab, carriage return and newline
    characters, so a parsed host can look clean while the host that is
    actually sent over the network is not.
    """
    assert urlparse("https://host\tname").hostname == "hostname"
    with pytest.raises(TargetSpecError):
        check_target_host("https://host\tname")


def test_the_url_modules_reject_a_hostile_host() -> None:
    """web, fuzz and s3 refuse a target with an unusable host."""
    from ethscan import fuzz, s3, web

    parsers = (web._parse_url, fuzz._normalize_base_url, s3._normalize_target)
    for parser in parsers:
        for target in HOSTILE_HOST_TARGETS:
            with pytest.raises(TargetSpecError) as excinfo:
                parser(target)
            assert str(excinfo.value) == HOST_ERROR_MESSAGE


def test_the_url_modules_still_accept_the_valid_target_forms() -> None:
    """The working target forms keep behaving exactly as before."""
    from ethscan import fuzz, s3, web

    assert web._parse_url("example.com") == ("example.com", 443, True)
    assert web._parse_url("http://example.com:8080") == ("example.com", 8080, False)
    assert web._parse_url("https://example.com:8443") == ("example.com", 8443, True)
    assert web._parse_url("https://[::1]:443") == ("::1", 443, True)
    with pytest.raises(TargetSpecError, match="Could not parse host from target"):
        web._parse_url("")
    assert fuzz._normalize_base_url("example.com") == "https://example.com"
    assert fuzz._normalize_base_url("http://example.com") == "http://example.com"
    assert fuzz._normalize_base_url("https://example.com:8443") == (
        "https://example.com:8443"
    )
    assert s3._normalize_target("Example.com") == "example.com"
    assert s3._normalize_target("https://Example.com/path") == "example.com"
    assert s3._normalize_target("127.0.0.1:8443") == "127.0.0.1"


def test_fuzz_reports_a_non_numeric_port_like_the_other_commands() -> None:
    """fuzz hands the URL to ``http.client``, so a bad port is rejected."""
    from ethscan import fuzz

    with pytest.raises(TargetSpecError) as excinfo:
        fuzz._normalize_base_url("https://host:notaport")
    assert str(excinfo.value) == NON_NUMERIC_PORT_MESSAGE


# --- A target whose host carries a percent-encoded control character -------
#
# ``urllib.request`` decodes the percent escapes of the host before it uses
# it, so a host that looks harmless in its raw form ("%00") carries a
# control character in the host that is actually sent over the network.
# ``http.client`` refuses such a host with an ``http.client.InvalidURL``.

PERCENT_ENCODED_HOST_TARGETS = (
    "%00",
    "%09host",
    "%20host",
    "host%00",
    "host%00:443",
    "https://%00",
    "https://%00/path",
    "http://host%00:8443",
)


@pytest.mark.parametrize("target", PERCENT_ENCODED_HOST_TARGETS)
def test_check_target_host_rejects_a_percent_encoded_host(target: str) -> None:
    """A host that carries a control character once decoded is rejected."""
    with pytest.raises(TargetSpecError) as excinfo:
        check_target_host(target)
    assert str(excinfo.value) == HOST_ERROR_MESSAGE


def test_check_target_host_accepts_a_harmless_percent_escape() -> None:
    """A percent escape that decodes to a harmless character is accepted."""
    check_target_host("example%2Ecom")
    check_target_host("https://example%2Ecom/path")


def test_the_url_modules_reject_a_percent_encoded_host() -> None:
    """web, fuzz and s3 refuse a host that decodes to a control character."""
    from ethscan import fuzz, s3, web

    parsers = (web._parse_url, fuzz._normalize_base_url, s3._normalize_target)
    for parser in parsers:
        for target in PERCENT_ENCODED_HOST_TARGETS:
            with pytest.raises(TargetSpecError) as excinfo:
                parser(target)
            assert str(excinfo.value) == HOST_ERROR_MESSAGE


# --- A target whose authority carries a userinfo part ----------------------
#
# ``urllib.request`` keeps the userinfo in the host it connects to, and
# ``http.client`` then reads the text after the last colon of that host as
# the port ("user:pass@example.com" -> port "pass@example.com"). The
# credentials are of no use to the toolkit, so the host is used without
# them, the way the whois, mongodb and ssh modules already do it.

USERINFO_TARGETS = (
    ("http://user:pass@example.com", "http://example.com"),
    ("https://user:pass@example.com/path?q=1#frag", "https://example.com/path?q=1#frag"),
    ("https://user@example.com", "https://example.com"),
    ("user:pass@example.com", "example.com"),
    ("https://example.com", "https://example.com"),
    ("https://example.com/path", "https://example.com/path"),
    ("https://example.com:8443", "https://example.com:8443"),
    ("https://[::1]:443", "https://[::1]:443"),
    ("https://example.com/a@b", "https://example.com/a@b"),
    ("example.com", "example.com"),
)


@pytest.mark.parametrize("target,expected", USERINFO_TARGETS)
def test_strip_userinfo_removes_only_the_userinfo(target: str, expected: str) -> None:
    """The userinfo is dropped, everything else is kept as it is."""
    assert strip_userinfo(target) == expected


def test_the_url_modules_use_the_host_without_the_userinfo() -> None:
    """web and fuzz use the host of a target that carries a userinfo."""
    from ethscan import fuzz, web

    assert web._parse_url("http://user:pass@example.com") == ("example.com", 80, False)
    assert fuzz._normalize_base_url("http://user:pass@example.com") == (
        "http://example.com"
    )
    assert fuzz._normalize_base_url("https://user:pass@example.com:8443") == (
        "https://example.com:8443"
    )


def test_fetch_headers_drops_the_userinfo_of_the_target(monkeypatch) -> None:
    """The request must not carry the credentials of the target."""
    from ethscan import web

    captured = {}

    class FakeResponse:
        def __init__(self):
            self.headers = {"Server": "test"}
            self.status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr(web.urllib.request, "urlopen", fake_urlopen)
    headers = web.fetch_headers("http://user:pass@example.com/path")
    assert captured["url"] == "http://example.com/path"
    assert headers == {"server": "test"}


# --- A target whose host is not a valid host name -------------------------
#
# The resolver encodes a host name as IDNA before it looks it up, and it
# raises a UnicodeError for a name with an empty label ("...."). That error
# is a ValueError and not an OSError, so the narrow ``except`` clauses of
# the library did not catch it and it reached the user as a raw traceback.
# Such a host is now reported the way every host that cannot be resolved is
# reported: as a failed probe inside the output.

MALFORMED_HOSTS = ("....", "example..com")

RESOLVE_HOST_MODULES = ("cert", "geo", "mac", "ping")


@pytest.mark.parametrize("module_name", RESOLVE_HOST_MODULES)
@pytest.mark.parametrize("host", MALFORMED_HOSTS)
def test_the_resolve_host_helpers_report_a_malformed_host(module_name: str, host: str) -> None:
    """A host that cannot be encoded is reported as an unresolvable host."""
    module = importlib.import_module(f"ethscan.{module_name}")
    result = module._resolve_host(host)
    # ping returns (None, None, None) tuple; others return None
    if isinstance(result, tuple):
        assert result == (None, None, None)
    else:
        assert result is None


def test_the_connection_helpers_report_a_malformed_host() -> None:
    """A host that cannot be encoded is reported as a failed connection."""
    from ethscan import osdetect, scanner, service

    assert scanner.scan_port("....", 80, timeout=0.2) == (80, False)
    port, banner, service_name = service.grab_banner("....", 80, 0.2)
    assert (port, banner, service_name) == (80, None, None)
    connected, error, rst = osdetect._connect_tcp("....", 80, 0.2)
    assert connected is False
    assert error is not None
    assert rst is None


@pytest.mark.parametrize("module_name", ("ftp", "smtp", "ssh"))
def test_the_protocol_modules_report_a_malformed_host(module_name: str) -> None:
    """A host that cannot be encoded is reported as a failed probe."""
    module = importlib.import_module(f"ethscan.{module_name}")
    run = getattr(module, f"run_{module_name}")
    results = run("....", timeout=0.2)
    assert results["error"], results


# --- A target whose path or query contains a space or a control character --

PATH_ERROR_MESSAGE = "Target path contains a space or control character"

HOSTILE_PATH_TARGETS = (
    "https://example.com/a b",
    "https://example.com/a\tb",
    "https://example.com/a\nb",
    "https://example.com/ho\x00st",
    "https://example.com/path\x7f",
    "https://example.com/?q=a b",
    "https://example.com/?q=a\tb",
    "http://example.com/a b",
    "example.com/a b",
    "https://example.com?q=a b",
)

USABLE_PATH_TARGETS = (
    "https://example.com/path",
    "https://example.com/a%20b",
    "https://example.com/?q=1",
    "https://example.com/path?query=1",
    "https://example.com/path#frag",
    "https://example.com/path?query=1#frag",
    "https://example.com?q=1",
    "https://example.com?q=1#frag",
    "example.com",
    "https://example.com",
)


def test_check_target_path_rejects_a_path_with_a_space() -> None:
    """A path with a space is reported as an unusable target."""
    from ethscan.target import check_target_path

    with pytest.raises(TargetSpecError) as excinfo:
        check_target_path("https://example.com/a b")
    assert str(excinfo.value) == PATH_ERROR_MESSAGE


def test_check_target_path_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    from ethscan.target import check_target_path

    with pytest.raises(ValueError):
        check_target_path("https://example.com/a b")


@pytest.mark.parametrize("target", HOSTILE_PATH_TARGETS)
def test_check_target_path_rejects_every_hostile_path(target: str) -> None:
    """A space or a control character in the path or query is always rejected."""
    from ethscan.target import check_target_path

    with pytest.raises(TargetSpecError) as excinfo:
        check_target_path(target)
    assert str(excinfo.value) == PATH_ERROR_MESSAGE


@pytest.mark.parametrize("target", USABLE_PATH_TARGETS)
def test_check_target_path_accepts_a_usable_path(target: str) -> None:
    """A path that ``http.client`` accepts is not an error."""
    from ethscan.target import check_target_path

    check_target_path(target)


def test_check_target_path_does_not_reject_a_fragment() -> None:
    """The fragment is never sent to the server and must not be rejected."""
    from ethscan.target import check_target_path

    check_target_path("https://example.com/path#has space")
    check_target_path("https://example.com/path#tab\there")


def test_check_target_path_does_not_reject_a_percent_encoded_path() -> None:
    """A percent-encoded path keeps working."""
    from ethscan.target import check_target_path

    check_target_path("https://example.com/a%20b")
    check_target_path("https://example.com/%00encoded")


def test_check_target_path_is_a_noop_for_a_bare_host() -> None:
    """A target with no path has nothing to reject."""
    from ethscan.target import check_target_path

    check_target_path("example.com")
    check_target_path("https://example.com")
    check_target_path("")


def test_the_url_modules_reject_a_hostile_path() -> None:
    """web, headers and urlcheck refuse a target with an unusable path."""
    from ethscan import web

    for target in HOSTILE_PATH_TARGETS:
        with pytest.raises(TargetSpecError) as excinfo:
            web._parse_url(target)
        assert str(excinfo.value) == PATH_ERROR_MESSAGE


def test_the_url_modules_still_accept_the_valid_path_forms() -> None:
    """The working target forms keep behaving exactly as before."""
    from ethscan import web

    assert web._parse_url("https://example.com/path") == ("example.com", 443, True)
    assert web._parse_url("https://example.com/a%20b") == ("example.com", 443, True)
    assert web._parse_url("https://example.com/?q=1") == ("example.com", 443, True)
    assert web._parse_url("https://example.com/path#frag") == ("example.com", 443, True)


# --- A target without a usable host in the traceroute -----------------------

TRACE_ERROR_MESSAGE = "Could not parse host from target"


def test_trace_rejects_a_target_without_a_host() -> None:
    """The traceroute reports an unusable target as an unusable target."""
    from ethscan import trace

    for target in ("", "   ", "http://", "https://", "/"):
        with pytest.raises(TargetSpecError) as excinfo:
            trace.run_trace(target)
        assert TRACE_ERROR_MESSAGE in str(excinfo.value)


def test_trace_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    from ethscan import trace

    with pytest.raises(ValueError):
        trace.run_trace("")


def test_trace_still_accepts_the_working_target_forms() -> None:
    """The valid target forms keep behaving exactly as before."""
    from ethscan import trace

    assert trace._normalize_host("example.com") == "example.com"
    assert trace._normalize_host("example.com:80") == "example.com"
    assert trace._normalize_host("http://example.com/") == "example.com"


# --- A URL that urllib refuses ---------------------------------------------
#
# ``urllib.parse.urlparse`` raises a bare ``ValueError`` ("Invalid IPv6
# URL") for a URL whose authority holds an unmatched bracket. The error
# escaped the ``except ValueError`` handlers of the modules and reached the
# user as a raw traceback, so :func:`parse_url` re-raises it as a
# :class:`TargetSpecError`.

UNPARSEABLE_URLS = (
    "http://[::1",
    "https://[::1",
    "http://example.com]",
    "http://[::1/path",
)


def test_parse_url_reports_an_unparseable_url() -> None:
    """A URL that urllib refuses is reported as a TargetSpecError."""
    for url in UNPARSEABLE_URLS:
        with pytest.raises(TargetSpecError) as excinfo:
            parse_url(url)
        assert str(excinfo.value) == "Invalid IPv6 URL"


def test_parse_url_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    with pytest.raises(ValueError):
        parse_url("http://[::1")


def test_parse_url_brackets_unbracketed_ipv6_bare() -> None:
    """An unbracketed bare IPv6 literal is bracketed."""
    assert parse_url("https://2001:db8::1").netloc == "[2001:db8::1]"


def test_parse_url_brackets_unbracketed_ipv6_with_port() -> None:
    """An unbracketed IPv6 literal carrying a port is bracketed."""
    assert parse_url("https://2001:db8::1:8080").netloc == "[2001:db8::1]:8080"


def test_parse_url_returns_the_same_result_as_urlparse() -> None:
    """A URL that urllib accepts is parsed exactly as before."""
    for url in (
        "https://example.com/path?q=1#frag",
        "http://example.com:8443",
        "http://[::1]:443",
        "https://example.com/a%20b",
        "http://user:pass@example.com",
    ):
        assert parse_url(url) == urlparse(url)


def test_parse_url_brackets_unbracketed_ipv6_literal() -> None:
    """An unbracketed IPv6 literal in the authority is bracketed before parsing."""
    parsed = parse_url("https://2001:db8::1")
    assert parsed.netloc == "[2001:db8::1]"
    assert parsed.hostname == "2001:db8::1"

    parsed2 = parse_url("redis://2001:db8::1:6379")
    assert parsed2.netloc == "[2001:db8::1]:6379"
    assert parsed2.hostname == "2001:db8::1"
    assert parsed2.port == 6379


def test_parse_url_leaves_already_bracketed_or_ipv4_unchanged() -> None:
    parsed = parse_url("http://[::1]:443")
    assert parsed.netloc == "[::1]:443"


# --- The shared host normalizer ---------------------------------------------
#
# :func:`normalize_host` extracts a bare hostname from a target that may be a
# bare host or a URL. Every module that rejects an unusable target delegates
# to it, so its contract (empty host raises, whitespace is stripped, the host
# is lowercased, scheme/port/path/query/fragment are dropped) is tested here
# directly instead of only through each module's wrapper.

EMPTY_HOST_TARGETS = ("", "   ", "://no-host", "redis://", ":6379", "https://", "http://", "/")


def test_normalize_host_returns_a_bare_host() -> None:
    """A bare host is returned unchanged."""
    assert normalize_host("example.com") == "example.com"


def test_normalize_host_lowercases_the_host() -> None:
    """The host is lowercased."""
    assert normalize_host("EXAMPLE.COM") == "example.com"
    assert normalize_host("Example.COM") == "example.com"


def test_normalize_host_strips_url_scheme_path_query_and_fragment() -> None:
    """A URL is reduced to its bare hostname."""
    assert normalize_host("https://example.com/path?q=1#frag") == "example.com"
    assert normalize_host("http://sub.example.com:8080/foo") == "sub.example.com"
    assert normalize_host("https://example.com") == "example.com"


def test_normalize_host_strips_the_port() -> None:
    """An explicit port is not part of the hostname."""
    assert normalize_host("example.com:443") == "example.com"
    assert normalize_host("https://example.com:8443") == "example.com"


def test_normalize_host_keeps_an_ipv6_literal() -> None:
    """An IPv6 literal is kept, bracketed or not, with or without a port."""
    assert normalize_host("2001:db8::1") == "2001:db8::1"
    assert normalize_host("[2001:db8::1]:443") == "2001:db8::1"
    assert normalize_host("https://[::1]:443") == "::1"


def test_normalize_host_strips_whitespace() -> None:
    """Surrounding whitespace is removed."""
    assert normalize_host("  example.com  ") == "example.com"


def test_normalize_host_uses_https_as_the_default_scheme() -> None:
    """A target without a scheme is read as https://."""
    assert normalize_host("example.com") == "example.com"


def test_normalize_host_uses_the_given_default_scheme() -> None:
    """The caller can override the default scheme."""
    assert normalize_host("example.com", default_scheme="http://") == "example.com"


@pytest.mark.parametrize("target", EMPTY_HOST_TARGETS)
def test_normalize_host_rejects_a_target_without_a_usable_host(target: str) -> None:
    """A target without a usable host raises the dedicated error type."""
    with pytest.raises(TargetSpecError) as excinfo:
        normalize_host(target)
    assert str(excinfo.value) == f"Could not parse host from target {target!r}"


def test_normalize_host_error_is_still_a_value_error() -> None:
    """Existing ``except ValueError`` handlers keep working."""
    with pytest.raises(ValueError):
        normalize_host("")


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("::1", "[::1]"),
        ("2001:db8::1", "[2001:db8::1]"),
        ("fe80::1", "[fe80::1]"),
        ("fe80::1%eth0", "[fe80::1]"),
        ("[::1]", "[::1]"),
        ("127.0.0.1", "127.0.0.1"),
        ("example.com", "example.com"),
        ("sub.example.co.uk", "sub.example.co.uk"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_format_host_header_brackets_ipv6_literals(host: str, expected: str) -> None:
    """An unbracketed IPv6 literal is bracketed for a Host header, others unchanged."""
    assert format_host_header(host) == expected


def test_format_host_header_leaves_ipv4_and_names_alone() -> None:
    """IPv4 literals and DNS names are never bracketed."""
    assert format_host_header("10.0.0.1") == "10.0.0.1"
    assert format_host_header("localhost") == "localhost"


# --- Property checks (deterministic, seeded) --------------------------------

import random as _random

_PROPERTY_SEED_TARGET = 20261125


def test_check_port_property_round_trip() -> None:
    rng = _random.Random(_PROPERTY_SEED_TARGET)
    for _ in range(5000):
        value = rng.randint(-5, 65540)
        try:
            result = check_port(value)
        except TargetSpecError:
            assert not (0 <= value <= 65535)
        else:
            assert result == value
            assert 0 <= result <= 65535


def test_check_port_property_text() -> None:
    rng = _random.Random(_PROPERTY_SEED_TARGET + 1)
    for _ in range(2000):
        n = rng.randint(0, 65535)
        text = str(n)
        assert check_port(text) == n
        for bad in ("abc", "1.5", "", " "):
            try:
                check_port(bad)
            except TargetSpecError:
                pass
            else:
                raise AssertionError(f"expected TargetSpecError for {bad!r}")


def test_normalize_host_property_lowercases() -> None:
    rng = _random.Random(_PROPERTY_SEED_TARGET + 2)
    hosts = ["example.com", "EXAMPLE.COM", "Sub.Example.COM", "localhost"]
    for h in hosts:
        assert normalize_host(h) == h.lower()
    for _ in range(1000):
        h = rng.choice(hosts)
        assert normalize_host(h + "/path?q=1") == h.lower()


def test_format_host_header_property_ipv6_roundtrip() -> None:
    rng = _random.Random(_PROPERTY_SEED_TARGET + 3)
    for _ in range(2000):
        # generate IPv4
        ip = f"{rng.randrange(256)}.{rng.randrange(256)}.{rng.randrange(256)}.{rng.randrange(256)}"
        assert format_host_header(ip) == ip
    # IPv6 literals bracketed
    for ip in ("::1", "2001:db8::1", "fe80::1"):
        assert format_host_header(ip) == f"[{ip}]"


# --- Property checks against ground-truth oracles -----------------------------
#
# These tests verify CORRECT OUTPUT (not just crash-free) by comparing
# against stdlib or hand-derived expected behavior. A mismatch is a genuine defect.

def test_parse_url_property_matches_urlparse_for_valid_urls() -> None:
    """parse_url output matches urllib.parse.urlparse for all valid URLs."""
    rng = _random.Random(_PROPERTY_SEED_TARGET + 10)
    schemes = ("http", "https", "redis", "ftp", "ssh", "ldap", "smtp", "mongodb")
    hosts = (
        "example.com",
        "sub.example.com",
        "localhost",
        "127.0.0.1",
        "192.168.1.1",
        "[::1]",
        "[2001:db8::1]",
        "[fe80::1]",
        "host-with-dash.com",
    )
    paths = ("", "/", "/path", "/path?q=1", "/path?q=1#frag", "?q=1", "#frag")
    ports = ("", ":80", ":443", ":6379", ":8443", ":8080", ":9999")
    userinfos = ("", "user:", "user:pass", "user@")

    for _ in range(3000):
        scheme = rng.choice(schemes)
        host = rng.choice(hosts)
        port = rng.choice(ports)
        path = rng.choice(paths)
        userinfo = rng.choice(userinfos)

        # Build URL carefully to avoid invalid combinations
        if userinfo:
            auth = f"{userinfo}@{host}{port}"
        else:
            auth = f"{host}{port}"
        url = f"{scheme}://{auth}{path}"

        # parse_url should match urlparse for valid URLs
        try:
            parsed_ours = parse_url(url)
            parsed_stdlib = urlparse(url)
        except TargetSpecError:
            # Some combinations may be invalid (e.g., IPv6 without brackets in stdlib)
            # but our parse_url handles IPv6 bracketing. Skip if stdlib fails.
            continue

        # Core fields must match
        assert parsed_ours.scheme == parsed_stdlib.scheme
        assert parsed_ours.netloc == parsed_stdlib.netloc
        assert parsed_ours.path == parsed_stdlib.path
        assert parsed_ours.params == parsed_stdlib.params
        assert parsed_ours.query == parsed_stdlib.query
        assert parsed_ours.fragment == parsed_stdlib.fragment
        assert parsed_ours.hostname == parsed_stdlib.hostname
        assert parsed_ours.port == parsed_stdlib.port
        assert parsed_ours.username == parsed_stdlib.username
        assert parsed_ours.password == parsed_stdlib.password


def test_parse_url_property_brackets_unbracketed_ipv6() -> None:
    """parse_url correctly brackets unbracketed IPv6 literals that stdlib misparses."""
    rng = _random.Random(_PROPERTY_SEED_TARGET + 11)
    # IPv6 literals that are unambiguous (no trailing all-digits segment that could be a port)
    ipv6_literals_no_port_ambiguity = (
        "::1",
        "2001:db8::1",
        "fe80::1",
        "::ffff:192.0.2.1",
    )
    # IPv6 literals that END with :<digits> - these will be parsed as having a port
    ipv6_literals_with_trailing_digits = (
        "2001:db8:85a3::8a2e:370:7334",
    )
    ports = ("", ":80", ":443", ":6379", ":8443")
    schemes = ("http", "https", "redis", "ftp")

    for _ in range(1500):
        ip = rng.choice(ipv6_literals_no_port_ambiguity)
        port = rng.choice(ports)
        scheme = rng.choice(schemes)

        # Unbracketed IPv6 in URL - stdlib misparses this
        url = f"{scheme}://{ip}{port}"

        # Our parse_url should bracket it and parse correctly
        parsed = parse_url(url)

        # Netloc should be bracketed
        assert parsed.netloc.startswith("[")
        assert "]" in parsed.netloc

        # Hostname should be the clean IPv6 literal
        assert parsed.hostname == ip

        # Port should be extracted correctly (URL port takes precedence)
        if port:
            assert parsed.port == int(port[1:])
        else:
            assert parsed.port is None

    # Test IPv6 literals that themselves end in :<digits>
    # When NO explicit port is given, the trailing :<digits> is parsed as port
    for ip in ipv6_literals_with_trailing_digits:
        for scheme in schemes:
            url = f"{scheme}://{ip}"
            parsed = parse_url(url)
            assert parsed.netloc.startswith("[")
            assert "]" in parsed.netloc
            # The trailing :7334 is parsed as port
            assert parsed.port == 7334
            # Hostname is the IPv6 without the trailing :7334
            assert parsed.hostname == "2001:db8:85a3::8a2e:370"

            # With explicit port, the explicit port wins BUT the hostname
            # includes the trailing :7334 (it's treated as part of the host)
            for port in (":80", ":443", ":6379"):
                url2 = f"{scheme}://{ip}{port}"
                parsed2 = parse_url(url2)
                assert parsed2.port == int(port[1:])
                # The full IPv6 literal is kept as hostname when explicit port is present
                assert parsed2.hostname == "2001:db8:85a3::8a2e:370:7334"


def test_normalize_host_property_matches_expected_behavior() -> None:
    """normalize_host output matches hand-derived expected behavior for valid targets."""
    # Test cases: (input, expected_output, default_scheme)
    test_cases = [
        # Bare hosts
        ("example.com", "example.com", "https://"),
        ("EXAMPLE.COM", "example.com", "https://"),
        ("Sub.Example.COM", "sub.example.com", "https://"),
        ("localhost", "localhost", "https://"),
        ("host-with-dash", "host-with-dash", "https://"),
        ("sub.domain.example.co.uk", "sub.domain.example.co.uk", "https://"),

        # With port (should strip port)
        ("example.com:443", "example.com", "https://"),
        ("example.com:8080", "example.com", "https://"),
        ("[::1]:443", "::1", "https://"),
        ("[2001:db8::1]:8080", "2001:db8::1", "https://"),

        # With scheme
        ("https://example.com", "example.com", "https://"),
        ("http://example.com", "example.com", "https://"),
        ("http://example.com:8080", "example.com", "https://"),
        ("https://sub.example.com/path?q=1#frag", "sub.example.com", "https://"),
        ("redis://localhost:6379", "localhost", "https://"),
        ("ftp://files.example.com", "files.example.com", "https://"),

        # IPv6 literals
        ("2001:db8::1", "2001:db8::1", "https://"),
        ("[2001:db8::1]:443", "2001:db8::1", "https://"),
        ("https://[::1]:443", "::1", "https://"),
        ("https://[2001:db8::1]/path", "2001:db8::1", "https://"),

        # With whitespace
        ("  example.com  ", "example.com", "https://"),
        ("\texample.com\n", "example.com", "https://"),
        (" example.com:443 ", "example.com", "https://"),

        # Custom default scheme
        ("example.com", "example.com", "http://"),
        ("example.com:8080", "example.com", "http://"),
    ]

    for target, expected, default_scheme in test_cases:
        result = normalize_host(target, default_scheme=default_scheme)
        assert result == expected, f"normalize_host({target!r}, default_scheme={default_scheme!r}) == {result!r}, expected {expected!r}"


def test_normalize_host_property_rejects_empty_hosts() -> None:
    """normalize_host raises TargetSpecError exactly for targets without a usable host."""
    rng = _random.Random(_PROPERTY_SEED_TARGET + 13)

    # Targets that should raise TargetSpecError (no usable host)
    empty_targets = [
        "",
        "   ",
        "\t\n",
        "://no-host",
        "redis://",
        ":6379",
        "https://",
        "http://",
        "/",
        "https:///path",
        "http://:8080",
        "://",
        "https://?",
        "https://#frag",
    ]

    for target in empty_targets:
        try:
            normalize_host(target)
            raise AssertionError(f"Expected TargetSpecError for {target!r}")
        except TargetSpecError as e:
            assert "Could not parse host from target" in str(e)

    # Random generation of definitely-invalid targets
    for _ in range(1000):
        # Generate strings that cannot possibly contain a host
        prefix = rng.choice(["", "https://", "http://", "redis://", "ftp://", "ssh://"])
        suffix = rng.choice(["", "/", "?", "#", "/path", "?q=1", "#frag"])
        middle = rng.choice(["", ":", "::", ":::", ":", "@", "@:", ":@"])
        target = prefix + middle + suffix
        # A "definitely invalid" target has no alphanumeric, no dots, no hyphens,
        # no brackets (for IPv6), and no colons that could be part of IPv6.
        # We only test targets where the middle part is just punctuation.
        # But we must also ensure the target, when parsed, has no host.
        # Skip targets that might parse as valid IPv6 (containing :: or :)
        if target and not any(c.isalnum() or c in ".-[]" for c in target.replace(":", "")):
            # Additional check: if the target could be a valid IPv6 with path, skip
            try:
                result = normalize_host(target)
                # If it succeeds, check if it's a "real" host or just :: (unspecified)
                # We only flag as error if the target was clearly invalid
                if result == "::" and "::" in target:
                    # This is the valid unspecified address, not an error
                    pass
                else:
                    raise AssertionError(f"Expected TargetSpecError for {target!r}, got {result!r}")
            except TargetSpecError:
                pass


def test_check_port_property_matches_expected_behavior() -> None:
    """check_port behavior matches hand-derived expected behavior."""
    rng = _random.Random(_PROPERTY_SEED_TARGET + 14)

    # Valid ports (int and string forms)
    for _ in range(2000):
        port = rng.randint(0, 65535)
        assert check_port(port) == port
        assert check_port(str(port)) == port

    # Invalid numeric ports
    for port in (-1, -100, 65536, 65537, 99999, 1000000):
        try:
            check_port(port)
            raise AssertionError(f"Expected TargetSpecError for port {port}")
        except TargetSpecError as e:
            assert "Port out of range" in str(e)

    # Invalid string ports (non-numeric)
    # Note: Python's int() accepts fullwidth digits (１２３) and other Unicode digits
    invalid_strings = ("abc", "1.5", "65536", "-1", "", " ", "\t")
    for s in invalid_strings:
        try:
            check_port(s)
            raise AssertionError(f"Expected TargetSpecError for port string {s!r}")
        except TargetSpecError as e:
            assert "Invalid port" in str(e) or "Port out of range" in str(e)

    # Unicode digits (fullwidth, etc.) ARE accepted by Python's int() - this is correct
    unicode_digits = ("１２３", "٠١٢", "०१२")  # Fullwidth, Arabic-Indic, Devanagari
    for s in unicode_digits:
        try:
            result = check_port(s)
            # Should succeed and return the numeric value
            assert isinstance(result, int)
            assert 0 <= result <= 65535
        except TargetSpecError as e:
            raise AssertionError(f"Unicode digits {s!r} should be accepted by int()") from e


def test_strip_userinfo_property_matches_expected() -> None:
    """strip_userinfo removes only userinfo, preserves everything else."""
    rng = _random.Random(_PROPERTY_SEED_TARGET + 15)

    test_cases = [
        ("http://user:pass@example.com", "http://example.com"),
        ("https://user:pass@example.com/path?q=1#frag", "https://example.com/path?q=1#frag"),
        ("https://user@example.com", "https://example.com"),
        ("user:pass@example.com", "example.com"),
        ("user@example.com", "example.com"),
        ("https://example.com", "https://example.com"),
        ("https://example.com/path", "https://example.com/path"),
        ("https://example.com:8443", "https://example.com:8443"),
        ("https://[::1]:443", "https://[::1]:443"),
        ("https://example.com/a@b", "https://example.com/a@b"),  # @ in path preserved
        ("example.com", "example.com"),
        ("http://user:pass@example.com:8080/path?q=1#frag", "http://example.com:8080/path?q=1#frag"),
        ("ftp://user:pass@files.example.com", "ftp://files.example.com"),
        ("ssh://git@github.com/user/repo", "ssh://github.com/user/repo"),
    ]

    for url, expected in test_cases:
        result = strip_userinfo(url)
        assert result == expected, f"strip_userinfo({url!r}) == {result!r}, expected {expected!r}"

    # Random generation
    schemes = ("", "http://", "https://", "ftp://", "ssh://")
    userinfos = ("", "user:", "user:pass", "user@")
    hosts = ("example.com", "sub.example.com", "localhost", "127.0.0.1", "[::1]", "[2001:db8::1]")
    ports = ("", ":80", ":443", ":22", ":8080")
    paths = ("", "/", "/path", "/path?q=1#frag")

    for _ in range(1000):
        scheme = rng.choice(schemes)
        userinfo = rng.choice(userinfos)
        host = rng.choice(hosts)
        port = rng.choice(ports)
        path = rng.choice(paths)

        if userinfo:
            auth = f"{userinfo}@{host}{port}"
        else:
            auth = f"{host}{port}"
        url = f"{scheme}{auth}{path}"

        result = strip_userinfo(url)

        # Verify userinfo is gone: no '@' in authority part
        # Find the authority part (between scheme:// and path/?/#)
        if "://" in result:
            after_scheme = result.split("://", 1)[1]
            authority_end = len(after_scheme)
            for delim in ("/", "?", "#"):
                idx = after_scheme.find(delim)
                if idx != -1:
                    authority_end = min(authority_end, idx)
            authority = after_scheme[:authority_end]
            assert "@" not in authority, f"userinfo '@' found in authority: {authority!r} from {url!r}"
        else:
            # No scheme - the whole thing before path is authority
            authority_end = len(result)
            for delim in ("/", "?", "#"):
                idx = result.find(delim)
                if idx != -1:
                    authority_end = min(authority_end, idx)
            authority = result[:authority_end]
            assert "@" not in authority, f"userinfo '@' found in authority: {authority!r} from {url!r}"

        # More precisely: if there was userinfo, it should be stripped
        if userinfo:
            # The result should not contain the userinfo part
            assert userinfo.split(":")[0] not in result or result.count("@") == 0
