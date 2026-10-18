"""LDAP reconnaissance module for ethscan.

Offline-forward LDAP reconnaissance using only the Python standard
library (``socket``, ``struct``-free BER helpers, and ``ssl`` for
LDAPS). The module performs two safe, bounded probes:

* **Anonymous bind** -- an LDAP ``BindRequest`` (RFC 4511) with no
  name and no authentication. A ``success`` result code means the
  server accepts anonymous binds; anything else (commonly 49
  ``invalidCredentials`` or 1 ``operationsError``) means it does not.
* **RootDSE search** -- a base-object search with an empty DN and the
  ``(objectClass=*)`` present filter. The RootDSE entry is the LDAP
  equivalent of a server banner: it carries the vendor name/version,
  naming contexts, supported LDAP versions, SASL mechanisms, and
  controls.

Both probes use minimal BER (ASN.1) encodings built by hand, and both
responses are parsed by a small defensive BER reader that never raises:
malformed, truncated, or non-LDAP responses are reported through the
``error`` field.

LDAPS is supported implicitly: an ``ldaps://`` URL (or port 636) wraps
the socket in TLS before sending the probe. Certificate verification is
disabled, mirroring nmap's LDAP scripts; this is a reconnaissance
probe, not a PKI validation.

All network access is confined to a single helper, ``_send_recv``, so
tests can inject a fake connector and exercise request building and
response parsing without touching the network.
"""
from __future__ import annotations

import csv
import io
import json
import socket
import ssl
from typing import Any, Optional

DEFAULT_PORT = 389
DEFAULT_LDAPS_PORT = 636
DEFAULT_TIMEOUT = 3.0
DEFAULT_LDAP_VERSION = 3

# LDAP protocol operation tags (BER context-specific, constructed).
LDAP_TAG_BIND_REQUEST = 0x60  # [APPLICATION 0]
LDAP_TAG_BIND_RESPONSE = 0x61  # [APPLICATION 1]
LDAP_TAG_SEARCH_REQUEST = 0x63  # [APPLICATION 3]
LDAP_TAG_SEARCH_RESULT_ENTRY = 0x64  # [APPLICATION 4]
LDAP_TAG_SEARCH_RESULT_DONE = 0x65  # [APPLICATION 5]
LDAP_TAG_SEARCH_RESULT_REFERENCE = 0x73  # [APPLICATION 19]
LDAP_TAG_NOTICE_OF_DISCONNECTION = 0x77  # [APPLICATION 23]

# Universal BER tags used inside LDAP messages.
TAG_BOOLEAN = 0x01
TAG_INTEGER = 0x02
TAG_OCTET_STRING = 0x04
TAG_ENUMERATED = 0x0A
TAG_SEQUENCE = 0x30
TAG_SET = 0x31

# A "present" filter (objectClass=*) is a context-specific primitive
# tag 7 whose content is the attribute description.
FILTER_TAG_PRESENT = 0x87

# Referral is [3] inside BindResponse / SearchResultDone.
TAG_REFERRAL = 0x83

# Common LDAP result codes (RFC 4511 section 4.1.10 and friends).
LDAP_RESULT_CODES: dict[int, str] = {
    0: "success",
    1: "operationsError",
    2: "protocolError",
    3: "timeLimitExceeded",
    4: "sizeLimitExceeded",
    5: "compareFalse",
    6: "compareTrue",
    7: "authMethodNotSupported",
    8: "strongAuthRequired",
    9: "partialResults",
    10: "referral",
    11: "adminLimitExceeded",
    12: "unavailableCriticalExtension",
    13: "confidentialityRequired",
    14: "saslBindInProgress",
    16: "noSuchAttribute",
    17: "undefinedAttributeType",
    18: "inappropriateMatching",
    19: "constraintViolation",
    20: "attributeOrValueExists",
    21: "invalidAttributeSyntax",
    32: "noSuchObject",
    33: "aliasProblem",
    34: "invalidDN",
    35: "aliasDereferencingProblem",
    48: "inappropriateAuthentication",
    49: "invalidCredentials",
    50: "insufficientAccessRights",
    51: "busy",
    52: "unavailable",
    53: "unwillingToPerform",
    54: "loopDetect",
    64: "namingViolation",
    65: "objectClassViolation",
    66: "notAllowedOnNonLeaf",
    67: "notAllowedOnRDN",
    68: "entryAlreadyExists",
    69: "objectClassModsProhibited",
    71: "affectsMultipleDSAs",
    80: "other",
}

_OPERATION_NAMES: dict[int, str] = {
    LDAP_TAG_BIND_RESPONSE: "bindResponse",
    LDAP_TAG_SEARCH_RESULT_ENTRY: "searchResultEntry",
    LDAP_TAG_SEARCH_RESULT_DONE: "searchResultDone",
    LDAP_TAG_SEARCH_RESULT_REFERENCE: "searchResultReference",
    LDAP_TAG_NOTICE_OF_DISCONNECTION: "noticeOfDisconnection",
}


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and integer port.

    Accepts bare hosts (``192.168.1.5``), ``host:port``, and
    ``ldap://host:port`` / ``ldaps://host:port`` URLs. ``ldaps://``
    defaults to port 636; everything else defaults to 389. IPv6
    literals may be bracketed.
    """
    normalized = (target or "").strip()
    host: Optional[str] = None
    port: Optional[int] = None
    scheme = ""

    if "://" in normalized:
        from urllib.parse import urlparse

        parsed = urlparse(normalized)
        host = (parsed.hostname or "").strip()
        port = parsed.port
        scheme = (parsed.scheme or "").lower()
    else:
        host = normalized
        # IPv6 literal in brackets, optionally followed by :port.
        if host and host.startswith("["):
            close = host.find("]")
            if close > 0:
                maybe_port = host[close + 1:]
                if maybe_port.startswith(":") and maybe_port[1:].isdigit():
                    port = port or int(maybe_port[1:])
                host = host[1:close]
        elif host and ":" in host and "]" not in host:
            base, _, rest = host.rpartition(":")
            if rest.isdigit():
                host = base
                port = port or int(rest)

    if not host:
        raise ValueError(f"Could not parse host from target {target!r}")

    default_port = DEFAULT_LDAPS_PORT if scheme == "ldaps" else DEFAULT_PORT
    return host, int(port) if port else default_port


def _is_ldaps_target(target: str) -> bool:
    """Return True when the target explicitly requests LDAPS."""
    return "://" in (target or "") and target.split("://", 1)[0].strip().lower() == "ldaps"


# ---------------------------------------------------------------------------
# BER (ASN.1) encoding helpers
# ---------------------------------------------------------------------------


def _int_bytes(value: int) -> bytes:
    """Encode a non-negative integer as a minimal BER INTEGER value."""
    if value < 0:
        raise ValueError("BER integer encoding supports non-negative values only")
    if value == 0:
        return b"\x00"
    octets: list[int] = []
    while value > 0:
        octets.append(value & 0xFF)
        value >>= 8
    octets.reverse()
    if octets[0] & 0x80:
        octets.insert(0, 0x00)  # keep the sign bit clear
    return bytes(octets)


def _ber_length(length: int) -> bytes:
    """Encode a definite-form BER length."""
    if length < 0:
        raise ValueError("negative BER length")
    if length < 0x80:
        return bytes([length])
    octets: list[int] = []
    value = length
    while value > 0:
        octets.append(value & 0xFF)
        value >>= 8
    octets.reverse()
    return bytes([0x80 | len(octets)]) + bytes(octets)


def _ber_tlv(tag: int, content: bytes) -> bytes:
    """Wrap ``content`` in a BER tag-length-value triplet."""
    return bytes([tag]) + _ber_length(len(content)) + content


# ---------------------------------------------------------------------------
# Request builders
# ---------------------------------------------------------------------------


def _build_bind_request(
    version: int = DEFAULT_LDAP_VERSION,
    message_id: int = 1,
) -> bytes:
    """Build a BER-encoded anonymous ``BindRequest``.

    Layout::

        LDAPMessage ::= SEQUENCE {
            messageID  INTEGER,
            bindRequest [APPLICATION 0] SEQUENCE {
                version INTEGER   -- name and authentication omitted
            }
        }

    Omitting ``name`` and ``authentication`` is the RFC 4511 anonymous
    bind. Version 3 is the modern default; version 2 probes legacy
    servers that predate RFC 4511.
    """
    version_tlv = _ber_tlv(TAG_INTEGER, _int_bytes(version))
    bind_request = _ber_tlv(LDAP_TAG_BIND_REQUEST, version_tlv)
    msg_id = _ber_tlv(TAG_INTEGER, _int_bytes(message_id))
    return _ber_tlv(TAG_SEQUENCE, msg_id + bind_request)


def _build_root_dse_search(message_id: int = 2) -> bytes:
    """Build a BER-encoded RootDSE ``SearchRequest``.

    The search targets the empty DN (the RootDSE) with
    ``scope=baseObject``, the ``(objectClass=*)`` present filter, and
    an empty attribute list (return all user attributes).
    """
    base_object = _ber_tlv(TAG_OCTET_STRING, b"")
    scope = _ber_tlv(TAG_ENUMERATED, b"\x00")  # baseObject
    deref_aliases = _ber_tlv(TAG_ENUMERATED, b"\x00")  # neverDerefAliases
    size_limit = _ber_tlv(TAG_INTEGER, b"\x00")
    time_limit = _ber_tlv(TAG_INTEGER, b"\x00")
    types_only = _ber_tlv(TAG_BOOLEAN, b"\x00")  # FALSE
    present_filter = _ber_tlv(FILTER_TAG_PRESENT, b"objectClass")
    attributes = _ber_tlv(TAG_SEQUENCE, b"")  # empty list -> all attributes
    search_request = _ber_tlv(
        LDAP_TAG_SEARCH_REQUEST,
        base_object
        + scope
        + deref_aliases
        + size_limit
        + time_limit
        + types_only
        + present_filter
        + attributes,
    )
    msg_id = _ber_tlv(TAG_INTEGER, _int_bytes(message_id))
    return _ber_tlv(TAG_SEQUENCE, msg_id + search_request)


# ---------------------------------------------------------------------------
# BER reader and response parser
# ---------------------------------------------------------------------------


def _read_length(data: bytes, offset: int) -> tuple[int, int]:
    """Read a definite-form BER length; return ``(length, next_offset)``."""
    if offset >= len(data):
        raise ValueError("truncated length")
    first = data[offset]
    if first < 0x80:
        return first, offset + 1
    count = first & 0x7F
    if count == 0 or count > 4:
        raise ValueError("unsupported BER length form")
    if offset + 1 + count > len(data):
        raise ValueError("truncated length")
    return int.from_bytes(data[offset + 1:offset + 1 + count], "big"), offset + 1 + count


def _read_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    """Read one TLV; return ``(tag, content, next_offset)``."""
    if offset >= len(data):
        raise ValueError("offset past end of data")
    tag = data[offset]
    length, pos = _read_length(data, offset + 1)
    end = pos + length
    if end > len(data):
        raise ValueError("truncated TLV content")
    return tag, data[pos:end], end


def _parse_result_content(content: bytes, result: dict[str, Any]) -> None:
    """Parse the shared BindResponse/SearchResultDone body.

    Body order (RFC 4511): optional version INTEGER, resultCode
    ENUMERATED, matchedDN OCTET STRING, diagnosticMessage OCTET
    STRING, optional referral [3]. Unknown elements are ignored.
    """
    offset = 0
    got_result_code = False
    got_matched_dn = False
    got_diagnostic = False
    while offset < len(content):
        tag, value, offset = _read_tlv(content, offset)
        if tag == TAG_INTEGER and result.get("version") is None and not got_result_code:
            result["version"] = int.from_bytes(value, "big") if value else 0
        elif tag == TAG_ENUMERATED:
            result["result_code"] = int.from_bytes(value, "big") if value else 0
            result["result_code_name"] = LDAP_RESULT_CODES.get(
                result["result_code"],
                f"unknown ({result['result_code']})",
            )
            got_result_code = True
        elif tag == TAG_OCTET_STRING:
            if not got_matched_dn:
                result["matched_dn"] = value.decode("utf-8", errors="replace")
                got_matched_dn = True
            elif not got_diagnostic:
                result["diagnostic_message"] = value.decode("utf-8", errors="replace")
                got_diagnostic = True
        elif tag == TAG_REFERRAL:
            result["referral"] = value.decode("utf-8", errors="replace")
        # Unknown elements (e.g. authResponse [7]) are ignored.


def _parse_attribute(content: bytes) -> dict[str, Any]:
    """Parse one RootDSE attribute: ``SEQUENCE { type, SET OF values }``."""
    type_tag, type_value, offset = _read_tlv(content, 0)
    if type_tag != TAG_OCTET_STRING:
        raise ValueError("malformed attribute description")
    values: list[str] = []
    while offset < len(content):
        set_tag, set_value, offset = _read_tlv(content, offset)
        if set_tag != TAG_SET:
            continue
        voff = 0
        while voff < len(set_value):
            vtag, vvalue, voff = _read_tlv(set_value, voff)
            if vtag == TAG_OCTET_STRING:
                values.append(vvalue.decode("utf-8", errors="replace"))
    return {"type": type_value.decode("utf-8", errors="replace"), "values": values}


def _parse_search_entry(content: bytes) -> dict[str, Any]:
    """Parse a ``SearchResultEntry``: ``{ objectName, attributes... }``."""
    entry: dict[str, Any] = {"dn": "", "attributes": {}}
    offset = 0
    dn_tag, dn_value, offset = _read_tlv(content, 0)
    if dn_tag == TAG_OCTET_STRING:
        entry["dn"] = dn_value.decode("utf-8", errors="replace")
    while offset < len(content):
        tag, value, offset = _read_tlv(content, offset)
        if tag != TAG_SEQUENCE:
            continue
        try:
            attr = _parse_attribute(value)
        except ValueError:
            continue
        entry["attributes"].setdefault(attr["type"], []).extend(attr["values"])
    return entry


def _parse_ldap_message(content: bytes, result: dict[str, Any]) -> None:
    """Parse one LDAPMessage envelope and dispatch on the protocol op."""
    msg_id_tag, msg_id_value, offset = _read_tlv(content, 0)
    if msg_id_tag != TAG_INTEGER:
        raise ValueError("missing messageID")
    result["message_id"] = int.from_bytes(msg_id_value, "big") if msg_id_value else 0
    op_tag, op_content, _ = _read_tlv(content, offset)
    result["protocol_op_tag"] = op_tag
    result["protocol_op"] = _OPERATION_NAMES.get(op_tag, f"unknown (0x{op_tag:02x})")
    if op_tag in (LDAP_TAG_BIND_RESPONSE, LDAP_TAG_SEARCH_RESULT_DONE,
                  LDAP_TAG_NOTICE_OF_DISCONNECTION):
        _parse_result_content(op_content, result)
    elif op_tag == LDAP_TAG_SEARCH_RESULT_ENTRY:
        result["entries"].append(_parse_search_entry(op_content))


def _parse_ldap_response(data: Optional[bytes]) -> dict[str, Any]:
    """Parse a raw LDAP response buffer into a structured dict.

    A buffer may hold several LDAPMessages (e.g. a search response with
    a ``searchResultEntry`` followed by ``searchResultDone``). Malformed
    or non-LDAP input is reported via the ``error`` field instead of
    raising.
    """
    result: dict[str, Any] = {
        "message_id": None,
        "protocol_op": None,
        "protocol_op_tag": None,
        "version": None,
        "result_code": None,
        "result_code_name": None,
        "matched_dn": None,
        "diagnostic_message": None,
        "referral": None,
        "entries": [],
        "raw_preview": "",
        "error": None,
    }

    if not data:
        result["error"] = "no response received"
        return result

    result["raw_preview"] = data[:48].hex()

    offset = 0
    while offset < len(data):
        try:
            tag, content, end = _read_tlv(data, offset)
        except ValueError as exc:
            result["error"] = f"malformed LDAP response: {exc}"
            return result
        if tag != TAG_SEQUENCE:
            result["error"] = "response is not an LDAP message (expected SEQUENCE)"
            return result
        try:
            _parse_ldap_message(content, result)
        except ValueError as exc:
            result["error"] = f"malformed LDAP message: {exc}"
            return result
        offset = end

    return result


# ---------------------------------------------------------------------------
# Network transport
# ---------------------------------------------------------------------------


def _send_recv(
    host: str,
    port: int,
    request: bytes,
    timeout: float,
    connector=None,
    use_tls: bool = False,
) -> tuple[Optional[bytes], Optional[str]]:
    """Send ``request`` to ``host:port`` and return ``(data, error)``.

    When ``connector`` is provided it is called as
    ``connector(host, port, request, timeout)`` and must return a
    ``(data, error)`` tuple, bypassing the network. This is what tests
    use. When ``use_tls`` is set the TCP connection is wrapped in TLS
    (certificate verification disabled, as this is a recon probe).
    """
    if connector is not None:
        return connector(host, port, request, timeout)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        if use_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=host)
        sock.sendall(request)
        data = sock.recv(65536)
        return data, None
    except socket.timeout:
        return None, "timeout"
    except OSError as exc:
        return None, str(exc)
    finally:
        try:
            sock.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _build_banner(results: dict[str, Any]) -> Optional[str]:
    """Build a short human-readable banner from the probe results."""
    if not results.get("accessible"):
        return None
    version = results.get("ldap_version", DEFAULT_LDAP_VERSION)
    bind = "anonymous bind allowed" if results.get("anonymous_bind") else "anonymous bind not allowed"
    parts = [f"LDAPv{version}", bind]
    root_dse = results.get("root_dse") or {}
    vendor = root_dse.get("vendorName") or root_dse.get("vendor")
    if vendor:
        parts.append(f"vendor={vendor[0]}")
    contexts = root_dse.get("namingContexts")
    if contexts:
        parts.append(f"namingContexts={','.join(contexts)}")
    return "; ".join(parts)


def run_ldap(
    target: str,
    port: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
    ldap_version: int = DEFAULT_LDAP_VERSION,
    connector=None,
) -> dict[str, Any]:
    """Run LDAP reconnaissance against ``target``.

    Parameters mirror the CLI: ``target`` is a host, ``host:port``, or
    ``ldap://host:port`` / ``ldaps://host:port`` URL; ``port``
    overrides the parsed/default port (389, or 636 for ``ldaps://``);
    ``timeout`` bounds each TCP exchange; ``ldap_version`` selects the
    BindRequest version (2 or 3); ``connector`` injects a fake
    transport for testing.

    Two probes are run, each on its own connection: an anonymous bind
    (anonymous-bind support detection) and a RootDSE search (server
    identity). The RootDSE probe is skipped when the bind probe fails
    at the transport layer.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port
    version = int(ldap_version)
    use_tls = _is_ldaps_target(target) or server_port == DEFAULT_LDAPS_PORT

    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "accessible": False,
        "protocol": "LDAPS" if use_tls else "LDAP",
        "ldap_version": version,
        "message_id": None,
        "bind_result_code": None,
        "bind_result": None,
        "matched_dn": None,
        "diagnostic_message": None,
        "referral": None,
        "anonymous_bind": False,
        "root_dse": {},
        "root_dse_error": None,
        "banner": None,
        "raw_preview": "",
        "notes": [],
        "error": None,
    }

    # Probe 1: anonymous bind.
    bind_request = _build_bind_request(version)
    data, err = _send_recv(host, server_port, bind_request, timeout,
                           connector=connector, use_tls=use_tls)
    if err:
        results["error"] = f"bind request failed: {err}"
        return results
    if not data:
        results["error"] = "bind request failed: no response"
        return results

    parsed = _parse_ldap_response(data)
    results["raw_preview"] = parsed.get("raw_preview", "")
    results["message_id"] = parsed.get("message_id")
    if parsed.get("error"):
        results["error"] = parsed["error"]
    results["bind_result_code"] = parsed.get("result_code")
    results["bind_result"] = parsed.get("result_code_name")
    results["matched_dn"] = parsed.get("matched_dn")
    results["diagnostic_message"] = parsed.get("diagnostic_message")
    results["referral"] = parsed.get("referral")
    results["accessible"] = True
    if parsed.get("result_code") == 0:
        results["anonymous_bind"] = True
    elif parsed.get("result_code") == 49:
        results["notes"].append(
            "anonymous bind rejected (invalidCredentials); the server may still allow anonymous searches",
        )
    elif parsed.get("result_code") == 2 and version >= 3:
        results["notes"].append(
            "protocol error; the server may require LDAPv2 (retry with --ldap-version 2)",
        )

    # Probe 2: RootDSE search (server identity / capabilities).
    search_request = _build_root_dse_search()
    search_data, search_err = _send_recv(host, server_port, search_request, timeout,
                                         connector=connector, use_tls=use_tls)
    if search_err:
        results["root_dse_error"] = f"root DSE search failed: {search_err}"
    elif not search_data:
        results["root_dse_error"] = "root DSE search failed: no response"
    else:
        parsed_search = _parse_ldap_response(search_data)
        if parsed_search.get("error"):
            results["root_dse_error"] = parsed_search["error"]
        else:
            merged: dict[str, list[str]] = {}
            for entry in parsed_search.get("entries") or []:
                for attr, values in (entry.get("attributes") or {}).items():
                    merged.setdefault(attr, []).extend(values)
            results["root_dse"] = merged
            done_code = parsed_search.get("result_code")
            if done_code is not None and done_code != 0 and not merged:
                results["root_dse_error"] = (
                    f"root DSE search returned "
                    f"{parsed_search.get('result_code_name') or done_code}"
                )

    results["banner"] = _build_banner(results)
    return results


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def format_ldap_report_json(results: dict[str, Any]) -> str:
    """Format LDAP reconnaissance results as JSON."""
    return json.dumps(results, indent=2, default=str)


def format_ldap_report_markdown(results: dict[str, Any]) -> str:
    """Format LDAP reconnaissance results as Markdown."""
    lines = ["# ethscan LDAP Reconnaissance Report", ""]
    lines.append(f"- **Target:** {results.get('target', '')}")
    lines.append(f"- **Host:** {results.get('host', '')}")
    lines.append(f"- **Port:** {results.get('port', DEFAULT_PORT)}")
    lines.append(f"- **Protocol:** {results.get('protocol') or 'LDAP'}")
    lines.append(f"- **Accessible:** {'Yes' if results.get('accessible') else 'No'}")
    if results.get("error"):
        lines.append(f"- **Error:** {results.get('error')}")
    lines.append("")

    lines.append("## Anonymous Bind")
    lines.append(f"- **LDAP Version:** {results.get('ldap_version')}")
    code = results.get("bind_result_code")
    lines.append(f"- **Result Code:** {code if code is not None else 'n/a'}")
    lines.append(f"- **Result:** {results.get('bind_result') or 'n/a'}")
    lines.append(f"- **Anonymous Bind:** {'Yes' if results.get('anonymous_bind') else 'No'}")
    if results.get("matched_dn") is not None:
        lines.append(f"- **Matched DN:** {results.get('matched_dn') or '(empty)'}")
    if results.get("diagnostic_message"):
        lines.append(f"- **Diagnostic Message:** {results.get('diagnostic_message')}")
    if results.get("referral"):
        lines.append(f"- **Referral:** {results.get('referral')}")
    lines.append("")

    root_dse = results.get("root_dse") or {}
    if root_dse:
        lines.append("## Server Identity (RootDSE)")
        shown = {
            "vendorName", "vendorVersion", "namingContexts", "supportedLDAPVersion",
            "supportedSASLMechanisms", "supportedControl", "supportedExtension",
            "subschemaSubentry", "defaultNamingContext", "rootDomainNamingContext",
            "dnsHostName", "configurationNamingContext", "schemaNamingContext",
        }
        for key in ("vendorName", "vendorVersion", "namingContexts", "supportedLDAPVersion",
                    "supportedSASLMechanisms", "supportedControl", "supportedExtension",
                    "subschemaSubentry", "defaultNamingContext", "rootDomainNamingContext",
                    "configurationNamingContext", "schemaNamingContext", "dnsHostName"):
            if key in root_dse:
                lines.append(f"- **{key}:** {', '.join(root_dse[key])}")
        others = {k: v for k, v in root_dse.items() if k not in shown}
        if others:
            lines.append("")
            lines.append("### Other RootDSE Attributes")
            for key in sorted(others):
                lines.append(f"- **{key}:** {', '.join(others[key])}")
        lines.append("")
    elif results.get("root_dse_error"):
        lines.append("## Server Identity (RootDSE)")
        lines.append(f"- **Error:** {results.get('root_dse_error')}")
        lines.append("")

    notes = results.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    raw = results.get("raw_preview")
    if raw:
        lines.append("## Response Preview")
        lines.append("```")
        lines.append(raw)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def format_ldap_report_csv(results: dict[str, Any]) -> str:
    """Format LDAP reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "host",
        "port",
        "accessible",
        "protocol",
        "ldap_version",
        "bind_result_code",
        "bind_result",
        "anonymous_bind",
        "matched_dn",
        "diagnostic_message",
        "vendor_name",
        "vendor_version",
        "naming_contexts",
        "supported_ldap_versions",
        "root_dse_attributes",
        "banner",
        "error",
    ])
    root_dse = results.get("root_dse") or {}
    writer.writerow([
        results.get("target", ""),
        results.get("host", ""),
        results.get("port", DEFAULT_PORT),
        "true" if results.get("accessible") else "false",
        results.get("protocol") or "LDAP",
        results.get("ldap_version"),
        results.get("bind_result_code"),
        results.get("bind_result") or "",
        "true" if results.get("anonymous_bind") else "false",
        results.get("matched_dn") or "",
        results.get("diagnostic_message") or "",
        "|".join(root_dse.get("vendorName", [])),
        "|".join(root_dse.get("vendorVersion", [])),
        "|".join(root_dse.get("namingContexts", [])),
        "|".join(root_dse.get("supportedLDAPVersion", [])),
        "; ".join(f"{k}={','.join(v)}" for k, v in sorted(root_dse.items())),
        results.get("banner") or "",
        results.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")


__all__ = [
    "DEFAULT_LDAPS_PORT",
    "DEFAULT_LDAP_VERSION",
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT",
    "LDAP_RESULT_CODES",
    "LDAP_TAG_BIND_REQUEST",
    "LDAP_TAG_BIND_RESPONSE",
    "LDAP_TAG_SEARCH_REQUEST",
    "LDAP_TAG_SEARCH_RESULT_DONE",
    "LDAP_TAG_SEARCH_RESULT_ENTRY",
    "_build_bind_request",
    "_build_root_dse_search",
    "_normalize_target",
    "_parse_ldap_response",
    "_read_length",
    "_read_tlv",
    "_send_recv",
    "format_ldap_report_csv",
    "format_ldap_report_json",
    "format_ldap_report_markdown",
    "run_ldap",
]
