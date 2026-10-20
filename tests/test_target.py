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
    "mysql",
    "mongodb",
    "oracle",
    "postgresql",
    "mssql",
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
    assert web._parse_url("") == ("localhost", 443, True)
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
    assert module._resolve_host(host) is None


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
)

USABLE_PATH_TARGETS = (
    "https://example.com/path",
    "https://example.com/a%20b",
    "https://example.com/?q=1",
    "https://example.com/path?query=1",
    "https://example.com/path#frag",
    "https://example.com/path?query=1#frag",
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

TRACE_ERROR_MESSAGE = "Invalid target"


def test_trace_rejects_a_target_without_a_host() -> None:
    """The traceroute reports an unusable target as an unusable target."""
    from ethscan import trace

    for target in ("", "   ", "http://", "https://", "/"):
        with pytest.raises(TargetSpecError) as excinfo:
            trace.run_trace(target)
        assert str(excinfo.value) == TRACE_ERROR_MESSAGE


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
