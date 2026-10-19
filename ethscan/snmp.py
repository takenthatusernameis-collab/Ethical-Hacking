"""SNMP reconnaissance module for ethscan.

Offline-first SNMP reconnaissance using only the Python standard library
(``socket`` + hand-rolled BER encoding/decoding). The module performs:

* SNMP GET requests for standard MIB-II OIDs (``sysDescr``,
  ``sysObjectID``, ``sysUpTime``, ``sysName``) to gather system
  information from the target device.
* Community-string probing (``public``, ``private``, ``default`` and the
  empty string) to identify valid/misconfigured community strings.
* SNMP version detection (v1/v2c) based on which message version the
  server answers.

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw UDP socket so tests can substitute a local fake server.
"""
from __future__ import annotations

import csv
import io
import json
import socket
from typing import Any

from ethscan.target import TargetSpecError

DEFAULT_PORT = 161
DEFAULT_TIMEOUT = 3.0
DEFAULT_COMMUNITIES = ("public", "private", "default", "")

# Standard MIB-II OIDs requested in every GET request.
STANDARD_OIDS: dict[str, str] = {
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysObjectID": "1.3.6.1.2.1.1.2.0",
    "sysUpTime": "1.3.6.1.2.1.1.3.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
}

_OID_TO_KEY = {
    "1.3.6.1.2.1.1.1.0": "sysDescr",
    "1.3.6.1.2.1.1.2.0": "sysObjectID",
    "1.3.6.1.2.1.1.3.0": "sysUpTime",
    "1.3.6.1.2.1.1.5.0": "sysName",
}

# BER tags.
TAG_INTEGER = 0x02
TAG_OCTET_STRING = 0x04
TAG_NULL = 0x05
TAG_OID = 0x06
TAG_IPADDRESS = 0x40
TAG_COUNTER32 = 0x41
TAG_GAUGE32 = 0x42
TAG_TIMETICKS = 0x43
TAG_OPAQUE = 0x44
TAG_COUNTER64 = 0x46
TAG_SEQUENCE = 0x30
TAG_GET_REQUEST = 0xA0
TAG_GET_NEXT_REQUEST = 0xA1
TAG_GET_RESPONSE = 0xA2

_PDU_TAGS = {
    TAG_GET_REQUEST: "get-request",
    TAG_GET_NEXT_REQUEST: "get-next-request",
    TAG_GET_RESPONSE: "get-response",
}

_VALUE_TYPE_NAMES = {
    TAG_INTEGER: "integer",
    TAG_OCTET_STRING: "octet-string",
    TAG_NULL: "null",
    TAG_OID: "oid",
    TAG_IPADDRESS: "ipaddress",
    TAG_COUNTER32: "counter32",
    TAG_GAUGE32: "gauge32",
    TAG_TIMETICKS: "timeticks",
    TAG_OPAQUE: "opaque",
    TAG_COUNTER64: "counter64",
}

# SNMPv2c exception values signalled inside a varbind.
_EXCEPTION_TAGS = {
    0x80: "endOfMibView",
    0x81: "noSuchObject",
    0x82: "noSuchInstance",
}

ERROR_STATUS_NAMES = {
    0: "noError",
    1: "tooBig",
    2: "noSuchName",
    3: "badValue",
    4: "readOnly",
    5: "genErr",
    6: "noAccess",
    7: "wrongType",
    8: "wrongLength",
    9: "wrongEncoding",
    10: "wrongValue",
    11: "noCreation",
    12: "inconsistentValue",
    13: "resourceUnavailable",
    14: "commitFailed",
    15: "undoFailed",
    16: "authorizationError",
    17: "notWritable",
    18: "inconsistentName",
}


# ---------------------------------------------------------------------------
# Target normalization
# ---------------------------------------------------------------------------


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and port.

    Accepts ``host``, ``host:port``, and ``snmp://host:port`` forms.
    Defaults to port ``DEFAULT_PORT`` when none is supplied.
    """
    normalized = target.strip()
    if "://" in normalized:
        from urllib.parse import urlparse

        parsed = urlparse(normalized)
        host = parsed.hostname or ""
        port = parsed.port
    else:
        host = normalized
        port = None
        if host and host.startswith("[") and "]:" in host:
            bracket_end = host.find("]:")
            if bracket_end > 0:
                port_part = host[bracket_end + 2:]
                if port_part.isdigit():
                    host = host[1:bracket_end]
                    port = port or int(port_part)
        elif host and ":" in host and "]" not in host:
            base, _, rest = host.rpartition(":")
            if rest.isdigit():
                host = base
                port = port or int(rest)
        elif host and host.startswith("[") and host.endswith("]"):
            host = host[1:-1]

    if not host:
        raise TargetSpecError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


# ---------------------------------------------------------------------------
# BER encoding
# ---------------------------------------------------------------------------


def _encode_length(length: int) -> bytes:
    """Encode a BER length (short or long form)."""
    if length < 0:
        raise ValueError("length must be non-negative")
    if length < 0x80:
        return bytes([length])
    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(encoded)]) + encoded


def _encode_tlv(tag: int, value: bytes) -> bytes:
    """Encode a BER tag-length-value triple."""
    return bytes([tag]) + _encode_length(len(value)) + value


def _encode_integer(value: int) -> bytes:
    """Encode a BER INTEGER with minimal two's-complement payload."""
    payload = value.to_bytes(max(1, (value.bit_length() + 8) // 8), "big", signed=True)
    return _encode_tlv(TAG_INTEGER, payload)


def _encode_octet_string(value: str) -> bytes:
    """Encode a BER OCTET STRING from a UTF-8 string."""
    return _encode_tlv(TAG_OCTET_STRING, value.encode("utf-8"))


def _encode_base128(value: int) -> bytes:
    """Encode an OID component in base-128 (high bit = continuation)."""
    if value < 0:
        raise ValueError("OID components must be non-negative")
    if value == 0:
        return b"\x00"
    groups = []
    while value > 0:
        groups.append(value & 0x7F)
        value >>= 7
    groups.reverse()
    return bytes(group | 0x80 for group in groups[:-1]) + bytes([groups[-1]])


def _encode_oid_value(oid: str) -> bytes:
    """Encode the value payload of a BER OID (without tag/length)."""
    components = [int(part) for part in oid.strip().strip(".").split(".") if part]
    if len(components) < 2:
        components.append(0)
    encoded = bytes([components[0] * 40 + components[1]])
    for component in components[2:]:
        encoded += _encode_base128(component)
    return encoded


def _encode_oid(oid: str) -> bytes:
    """Encode a full BER OID (tag + length + value)."""
    return _encode_tlv(TAG_OID, _encode_oid_value(oid))


def _encode_null() -> bytes:
    """Encode a BER NULL."""
    return _encode_tlv(TAG_NULL, b"")


def _build_get_request(version: int, community: str, oids: list[str]) -> bytes:
    """Build an SNMP GET request message (v1 or v2c).

    Args:
        version: SNMP version integer (0 = v1, 1 = v2c).
        community: Community string.
        oids: OID strings to request.
    """
    varbinds = b"".join(
        _encode_tlv(TAG_SEQUENCE, _encode_oid(oid) + _encode_null()) for oid in oids
    )
    varbind_list = _encode_tlv(TAG_SEQUENCE, varbinds)
    pdu_body = (
        _encode_integer(0)  # request-id
        + _encode_integer(0)  # error-status
        + _encode_integer(0)  # error-index
        + varbind_list
    )
    pdu = _encode_tlv(TAG_GET_REQUEST, pdu_body)
    message_body = _encode_integer(version) + _encode_octet_string(community) + pdu
    return _encode_tlv(TAG_SEQUENCE, message_body)


# ---------------------------------------------------------------------------
# BER decoding
# ---------------------------------------------------------------------------


def _parse_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    """Parse one BER TLV at *offset*, returning (tag, value, next_offset)."""
    if offset >= len(data):
        raise ValueError("truncated TLV: missing tag")
    tag = data[offset]
    offset += 1
    if offset >= len(data):
        raise ValueError("truncated TLV: missing length")
    first = data[offset]
    offset += 1
    if first & 0x80:
        num_bytes = first & 0x7F
        if num_bytes == 0:
            raise ValueError("indefinite lengths are not supported")
        if offset + num_bytes > len(data):
            raise ValueError("truncated TLV: incomplete length")
        length = int.from_bytes(data[offset:offset + num_bytes], "big")
        offset += num_bytes
    else:
        length = first
    if offset + length > len(data):
        raise ValueError("truncated TLV: incomplete value")
    return tag, data[offset:offset + length], offset + length


def _parse_oid(value: bytes) -> str:
    """Decode an OID value payload into dotted notation."""
    if not value:
        return ""
    first = value[0]
    components = [first // 40, first % 40]
    component = 0
    for byte in value[1:]:
        component = (component << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            components.append(component)
            component = 0
    return ".".join(str(part) for part in components)


def _decode_varbind_value(tag: int, value: bytes) -> Any:
    """Decode a varbind value payload based on its tag."""
    if tag in _EXCEPTION_TAGS:
        return None
    if tag == TAG_OCTET_STRING:
        return value.decode("utf-8", "replace")
    if tag == TAG_OID:
        return _parse_oid(value)
    if tag == TAG_NULL:
        return None
    if tag == TAG_IPADDRESS:
        return ".".join(str(byte) for byte in value[:4])
    if tag in (TAG_INTEGER, TAG_COUNTER32, TAG_GAUGE32, TAG_TIMETICKS, TAG_COUNTER64):
        signed = tag == TAG_INTEGER
        return int.from_bytes(value, "big", signed=signed)
    return value.hex()


def _parse_snmp_message(data: bytes) -> dict[str, Any]:
    """Parse an SNMP message (GET request or GET response) into a dict.

    Returns a dict with ``version``, ``community``, ``pdu_type``,
    ``request_id``, ``error_status``, ``error_index`` and ``varbinds``
    (a list of ``{oid, value, value_type}`` dicts). Raises ``ValueError``
    when the packet is malformed.
    """
    tag, value, offset = _parse_tlv(data, 0)
    if tag != TAG_SEQUENCE:
        raise ValueError("expected SEQUENCE at top level")
    if offset != len(data):
        raise ValueError("trailing data after top-level SEQUENCE")

    inner = value
    ptag, ver_value, poff = _parse_tlv(inner, 0)
    if ptag != TAG_INTEGER:
        raise ValueError("expected INTEGER version")
    version = int.from_bytes(ver_value, "big", signed=True)

    ptag, comm_value, poff = _parse_tlv(inner, poff)
    if ptag != TAG_OCTET_STRING:
        raise ValueError("expected OCTET STRING community")
    community = comm_value.decode("utf-8", "replace")

    ptag, pdu_value, poff = _parse_tlv(inner, poff)
    if poff != len(inner):
        raise ValueError("trailing data after PDU")
    pdu_type = _PDU_TAGS.get(ptag, f"unknown (0x{ptag:02x})")

    # PDU body: request-id, error-status, error-index, varbind-list.
    ptag, v, o = _parse_tlv(pdu_value, 0)
    if ptag != TAG_INTEGER:
        raise ValueError("expected INTEGER request-id")
    request_id = int.from_bytes(v, "big", signed=True)

    ptag, v, o = _parse_tlv(pdu_value, o)
    if ptag != TAG_INTEGER:
        raise ValueError("expected INTEGER error-status")
    error_status = int.from_bytes(v, "big", signed=True)

    ptag, v, o = _parse_tlv(pdu_value, o)
    if ptag != TAG_INTEGER:
        raise ValueError("expected INTEGER error-index")
    error_index = int.from_bytes(v, "big", signed=True)

    ptag, v, o = _parse_tlv(pdu_value, o)
    if ptag != TAG_SEQUENCE:
        raise ValueError("expected SEQUENCE varbind-list")

    varbinds: list[dict[str, Any]] = []
    vb_off = 0
    while vb_off < len(v):
        vb_tag, vb_value, vb_off = _parse_tlv(v, vb_off)
        if vb_tag != TAG_SEQUENCE:
            raise ValueError("expected SEQUENCE varbind")
        vtag, oid_value, o2 = _parse_tlv(vb_value, 0)
        if vtag != TAG_OID:
            raise ValueError("expected OID in varbind")
        vtag2, val_value, _ = _parse_tlv(vb_value, o2)
        if vtag2 in _EXCEPTION_TAGS:
            value_type = _EXCEPTION_TAGS[vtag2]
        else:
            value_type = _VALUE_TYPE_NAMES.get(
                vtag2, f"unknown (0x{vtag2:02x})"
            )
        varbinds.append({
            "oid": _parse_oid(oid_value),
            "value": _decode_varbind_value(vtag2, val_value),
            "value_type": value_type,
        })

    return {
        "version": version,
        "community": community,
        "pdu_type": pdu_type,
        "request_id": request_id,
        "error_status": error_status,
        "error_index": error_index,
        "varbinds": varbinds,
    }


# ---------------------------------------------------------------------------
# Network I/O
# ---------------------------------------------------------------------------


def _send_recv(
    host: str,
    port: int,
    request: bytes,
    timeout: float,
    connector=None,
) -> tuple[bytes | None, str | None]:
    """Send a UDP request and receive the response (injectable for tests)."""
    if connector is not None:
        return connector(host, port, request, timeout)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(request, (host, port))
        data, _ = sock.recvfrom(65536)
        return data, None
    except socket.timeout:
        return None, "timeout"
    except OSError as exc:
        return None, str(exc)
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# Reconnaissance entry point
# ---------------------------------------------------------------------------


def _assign_varbind(entry: dict[str, Any], varbind: dict[str, Any]) -> None:
    """Copy a decoded varbind into the per-community result entry."""
    key = _OID_TO_KEY.get(varbind.get("oid", ""))
    if key is None:
        return
    value = varbind.get("value")
    if varbind.get("value_type") == "timeticks" and isinstance(value, int):
        entry[key] = value * 10  # TimeTicks are hundredths of a second
    else:
        entry[key] = value


def _probe_community(
    host: str,
    port: int,
    community: str,
    timeout: float,
    connector,
) -> dict[str, Any]:
    """Probe a single community string with v2c first, then v1."""
    entry: dict[str, Any] = {
        "community": community,
        "valid": False,
        "version": None,
        "error": None,
    }
    last_error: str | None = None

    for version, version_label in ((1, "v2c"), (0, "v1")):
        request = _build_get_request(version, community, list(STANDARD_OIDS.values()))
        data, err = _send_recv(host, port, request, timeout, connector=connector)
        if err:
            last_error = f"{version_label} request failed: {err}"
            continue
        try:
            message = _parse_snmp_message(data)
        except ValueError as exc:
            last_error = f"{version_label} response parse failed: {exc}"
            continue
        error_status = message.get("error_status", 0)
        if error_status:
            status_name = ERROR_STATUS_NAMES.get(error_status, "unknown")
            last_error = f"{version_label} error status {error_status} ({status_name})"
            continue
        if message.get("pdu_type") not in ("get-response",):
            last_error = f"{version_label} unexpected PDU: {message.get('pdu_type')}"
            continue

        entry["valid"] = True
        entry["version"] = version_label
        for varbind in message.get("varbinds", []):
            _assign_varbind(entry, varbind)
        return entry

    entry["error"] = last_error
    return entry


def run_snmp(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    communities: list[str] | None = None,
    connector=None,
) -> dict[str, Any]:
    """Run SNMP reconnaissance against *target*.

    Args:
        target: Hostname, ``host:port``, or URL.
        port: Explicit SNMP port; when ``None`` the port is parsed from the
            target (or defaults to 161).
        timeout: Per-request timeout in seconds.
        communities: Community strings to probe (defaults to ``public``,
            ``private``, ``default`` and the empty string).
        connector: Callable for sending/receiving UDP packets (for testing).

    Returns:
        Structured result dict consumed by the formatters below.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port
    community_list = list(communities) if communities is not None else list(DEFAULT_COMMUNITIES)

    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "snmp_version": None,
        "communities": [],
        "valid_communities": [],
        "sysDescr": None,
        "sysObjectID": None,
        "sysUpTime": None,
        "sysName": None,
        "error": None,
    }

    first_error: str | None = None
    for community in community_list:
        entry = _probe_community(host, server_port, community, timeout, connector)
        results["communities"].append(entry)
        if entry["valid"]:
            results["valid_communities"].append(community)
            if results["snmp_version"] is None:
                results["snmp_version"] = entry.get("version")
                for key in ("sysDescr", "sysObjectID", "sysUpTime", "sysName"):
                    if results[key] is None:
                        results[key] = entry.get(key)
        elif entry.get("error") and first_error is None:
            first_error = entry["error"]

    if first_error is not None and not results["valid_communities"]:
        results["error"] = first_error

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def format_snmp_report_json(data: dict[str, Any]) -> str:
    """Format SNMP reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _escape_markdown(value: Any) -> str:
    """Escape pipe characters for Markdown tables/lists."""
    return str(value).replace("|", "\\|")


def format_snmp_report_markdown(data: dict[str, Any]) -> str:
    """Format SNMP reconnaissance results as Markdown."""
    lines = ["# ethscan SNMP Report", ""]
    lines.append(f"- **Target:** {_escape_markdown(data.get('target', ''))}")
    lines.append(f"- **Host:** {_escape_markdown(data.get('host', ''))}")
    lines.append(f"- **Port:** {data.get('port', '')}")
    if data.get("snmp_version"):
        lines.append(f"- **SNMP Version:** {data.get('snmp_version')}")

    communities = data.get("communities") or []
    if communities:
        lines.append("")
        lines.append("## Community Probes")
        lines.append("")
        lines.append("| Community | Valid | Error |")
        lines.append("| --- | --- | --- |")
        for entry in communities:
            community = entry.get("community")
            label = community if community else "(empty)"
            valid = "YES" if entry.get("valid") else "NO"
            error = _escape_markdown(entry.get("error") or "")
            lines.append(f"| {_escape_markdown(label)} | {valid} | {error} |")

    lines.append("")
    lines.append("## System Information")
    for key, label in (
        ("sysDescr", "sysDescr"),
        ("sysObjectID", "sysObjectID"),
        ("sysUpTime", "sysUpTime"),
        ("sysName", "sysName"),
    ):
        value = data.get(key)
        if value is None:
            lines.append(f"- **{label}:** N/A")
        elif key == "sysUpTime":
            lines.append(f"- **{label}:** {value} ms")
        else:
            lines.append(f"- **{label}:** {_escape_markdown(value)}")

    valid = data.get("valid_communities") or []
    if valid:
        lines.append("")
        lines.append("## Assessment")
        lines.append(
            f"- **Valid communities:** {', '.join(_escape_markdown(c) if c else '(empty)' for c in valid)}"
        )
        default_valid = [c for c in valid if c in ("public", "private", "default", "")]
        if default_valid:
            lines.append(
                "- **Misconfiguration:** default community strings are accepted "
                "(the device exposes its MIB-II tree to unauthenticated queries)"
            )
    elif not data.get("error"):
        lines.append("")
        lines.append("## Assessment")
        lines.append("- No valid community strings found.")

    if data.get("error"):
        lines.append("")
        lines.append(f"- **Error:** {_escape_markdown(data['error'])}")

    lines.append("")
    return "\n".join(lines)


def format_snmp_report_csv(data: dict[str, Any]) -> str:
    """Format SNMP reconnaissance results as CSV.

    Emits a header row plus one row per probed community (including a
    summary row). The ``record_type`` discriminator column distinguishes
    them:

    - ``summary`` row: target-level fields (system information and the
      top-level error) are populated; community fields are empty.
    - ``community`` row: the target context is repeated (so each row is
      self-contained) and per-community fields (``community``,
      ``community_valid``, ``community_version``, ``community_error``)
      are populated; system fields are empty.

    One row is emitted per entry in ``data["communities"]`` so every probed
    community--valid or invalid, whether or not it produced an error--is
    preserved. The previous single-row form collapsed all communities into a
    comma-joined ``valid_communities`` string and a semicolon-joined
    ``error`` string, dropping per-community structure, the v1/v2c version
    per community, and the valid/error association per community.

    Header: ``target,host,port,snmp_version,sys_descr,sys_object_id,sys_up_time_ms,sys_name,error,record_type,community,community_valid,community_version,community_error``.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target", "host", "port", "snmp_version",
        "sys_descr", "sys_object_id", "sys_up_time_ms", "sys_name", "error",
        "record_type", "community", "community_valid",
        "community_version", "community_error",
    ])

    # Target-level context, repeated on every row so each row is
    # self-contained for downstream CSV consumers.
    target = data.get("target", "")
    host = data.get("host", "")
    port = data.get("port", "") or ""
    snmp_version = data.get("snmp_version", "") or ""
    sys_descr = data.get("sysDescr", "") or ""
    sys_object_id = data.get("sysObjectID", "") or ""
    sys_up_time = data.get("sysUpTime", "") if data.get("sysUpTime") is not None else ""
    sys_name = data.get("sysName", "") or ""
    top_error = data.get("error") or ""

    # Summary row: target-level fields filled, community fields empty.
    writer.writerow([
        target, host, port, snmp_version,
        sys_descr, sys_object_id, sys_up_time, sys_name, top_error,
        "summary", "", "", "", "",
    ])

    # One row per probed community (valid or invalid) so per-community
    # structure, version and error are preserved rather than collapsed.
    for entry in data.get("communities") or []:
        community = entry.get("community") or ""
        valid = "true" if entry.get("valid") else "false"
        community_version = entry.get("version") or ""
        community_error = entry.get("error") or ""
        writer.writerow([
            target, host, port, snmp_version,
            "", "", "", "", "",
            "community", community, valid, community_version, community_error,
        ])

    return output.getvalue().rstrip("\r\n")
