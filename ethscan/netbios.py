"""NetBIOS Name Service (NBNS) reconnaissance module for ethscan.

Offline-first NetBIOS reconnaissance using only the Python standard library
(``socket`` + raw packet encoding for RFC 1001/1002 NBNS). The module
performs:

* A NBNS NODE STATUS request (UDP port 137, QTYPE NBSTAT / 0x0021) for a
  target NetBIOS name (default ``"*"`` wildcard to enumerate all names).
* Parsing of the NBSTAT response: the MAC address (``Unit ID``), and the
  name table with per-name service suffix, name flags (group/unique,
  permanent/active, owner node type, conflict/deregister) and a heuristic
  service-type mapping.
* Heuristics such as ``is_server`` (a ``<20>`` File server service name is
  present, indicating SMB/resource sharing) and ``hostname`` (the unique
  ``<00>`` Workstation service name).

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw UDP socket so tests can substitute a local fake server.
"""
from __future__ import annotations

import csv
import io
import json
import socket
import struct
from typing import Any

DEFAULT_PORT = 137
DEFAULT_TIMEOUT = 3.0
DEFAULT_NAME = "*"
DEFAULT_SUFFIX = 0x00

# Question/answer record types (RFC 1002).
RR_TYPE_NB = 0x0020
RR_TYPE_NBSTAT = 0x0021
RR_CLASS_IN = 0x0001

# DNS-style name compression pointer marker.
DNS_POINTER_MASK = 0xC0

# NODE NAME_FLAGS bits (RFC 1002 section 4.2.18), read as a big-endian
# 16-bit value. See also dpkt's NS_NAME_* constants.
NAME_FLAGS_GROUP = 0x8000  # G  - bit 15: 1 = group name, 0 = unique name
NAME_FLAGS_ONT = 0x6000  # bits 14-13: Owner Node Type
NAME_FLAGS_DRG = 0x1000  # bit 12: Deregister flag
NAME_FLAGS_CNF = 0x0800  # bit 11: Conflict flag
NAME_FLAGS_ACT = 0x0400  # bit 10: Active name flag
NAME_FLAGS_PRM = 0x0200  # bit 9: Permanent name flag
NAME_FLAGS_RESERVED = 0x01FF  # bits 8-0: reserved

_OWNER_NODE_TYPES = {
    0: "B-node",
    1: "P-node",
    2: "M-node",
    3: "reserved",
}

# NBNS RCODE values (RFC 1002).
RCODE_NAMES = {
    0: "No error",
    1: "Format error",
    2: "Server failure",
    3: "Name error",
    4: "Unsupported option",
    5: "Refused",
    6: "Name in conflict",
    7: "DNS server (name in use)",
    8: "DNIND (duplicate name)",
    15: "Transaction rejected",
}

# NetBIOS suffix byte -> human-readable service type. The suffix is the
# 16th byte of a 16-byte NetBIOS name and identifies the registered service.
SUFFIX_SERVICE_TYPES = {
    0x00: "Workstation service",
    0x01: "Messenger service",
    0x02: "Reserved",
    0x03: "Messenger service (alias)",
    0x04: "Reserved",
    0x05: "Reserved",
    0x06: "Reserved",
    0x07: "Remote Access Service",
    0x08: "Reservoir",
    0x09: "Reservoir",
    0x0A: "Reservoir",
    0x0B: "RAS service",
    0x17: "RAS service",
    0x1B: "Domain master browser",
    0x1C: "Domain controllers",
    0x1D: "Master browser",
    0x1E: "Browser service elections",
    0x20: "File server service",
    0x2B: "Remote Access Service",
    0x2C: "Remote Access Service",
    0x2D: "Remote Access Service",
    0x2E: "Remote Access Service",
    0x2F: "Remote Access Service",
    0x33: "Default name",
    0x34: "SMB server",
}

# Suffixes that identify a real machine / server role for heuristics.
_SUFFIX_WORKSTATION = 0x00
_SUFFIX_FILE_SERVER = 0x20


# ---------------------------------------------------------------------------
# Target normalization
# ---------------------------------------------------------------------------


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and port.

    Accepts ``host``, ``host:port``, and ``netbios://host:port`` forms.
    Defaults to port ``DEFAULT_PORT`` (137) when none is supplied.
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
        raise ValueError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


# ---------------------------------------------------------------------------
# NetBIOS name encoding / decoding (RFC 1001 section 14.1 first-level encoding)
# ---------------------------------------------------------------------------


def _encode_name_chars(name: str, suffix: int) -> bytes:
    """Encode a 15-char name + 1-byte suffix into the 32-char first-level form.

    Each of the 16 source bytes is split into high and low nibbles, each
    mapped to an ASCII letter ``A``-``P`` (``0x41 + nibble``), yielding 32
    bytes. The name is upper-cased and space-padded to 15 characters.
    """
    padded = name.upper().encode("ascii", "replace").ljust(15, b" ")[:15]
    raw = padded + bytes([suffix & 0xFF])
    chars = bytearray()
    for byte in raw:
        chars.append((byte >> 4) + 0x41)
        chars.append((byte & 0x0F) + 0x41)
    return bytes(chars)


def _encode_qname(name: str, suffix: int = DEFAULT_SUFFIX) -> bytes:
    """Encode a NetBIOS name as a DNS-style question name (length + chars + 0x00)."""
    chars = _encode_name_chars(name, suffix)
    return bytes([len(chars)]) + chars + b"\x00"


def _decode_name_chars(chars: bytes) -> tuple[str, int]:
    """Decode 32 first-level-encoded chars back into (name, suffix).

    Each pair of chars is a byte ``(ord(c) - 0x41)`` for each nibble.
    """
    if len(chars) % 2 != 0:
        raise ValueError("first-level name must have an even length")
    raw = bytearray()
    for i in range(0, len(chars), 2):
        high = chars[i] - 0x41
        low = chars[i + 1] - 0x41
        if not (0 <= high <= 0x0F) or not (0 <= low <= 0x0F):
            raise ValueError("invalid first-level encoded name character")
        raw.append((high << 4) | low)
    name = raw[:15].rstrip(b" ").rstrip(b"\x00").decode("ascii", "replace")
    suffix = raw[15]
    return name, suffix


# ---------------------------------------------------------------------------
# Request building
# ---------------------------------------------------------------------------


def _build_nbns_query(
    name: str = DEFAULT_NAME,
    suffix: int = DEFAULT_SUFFIX,
    transaction_id: int = 0,
) -> bytes:
    """Build an NBNS NODE STATUS request (QTYPE NBSTAT) for *name*.

    Args:
        name: NetBIOS name to query (default ``"*"`` to enumerate all names).
        suffix: Service suffix byte (default 0x00).
        transaction_id: 16-bit transaction id.
    """
    question_name = _encode_qname(name, suffix)
    header = struct.pack(
        "!HHHHHH",
        transaction_id & 0xFFFF,
        0x0000,  # flags: standard query
        1,  # QDCOUNT
        0,  # ANCOUNT
        0,  # NSCOUNT
        0,  # ARCOUNT
    )
    question = question_name + struct.pack("!HH", RR_TYPE_NBSTAT, RR_CLASS_IN)
    return header + question


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_dns_name(data: bytes, offset: int) -> tuple[str, int]:
    """Parse a DNS-style (possibly compressed) name starting at *offset*.

    Returns ``(name, next_offset)``. Handles first-level encoded NetBIOS
    labels and DNS compression pointers (``0xC0``).
    """
    labels: list[bytes] = []
    next_offset = offset
    jumped = False
    jumps = 0

    while offset < len(data):
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if (length & DNS_POINTER_MASK) == DNS_POINTER_MASK:
            if offset + 1 >= len(data):
                raise ValueError("truncated DNS compression pointer")
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                next_offset = offset + 2
            offset = pointer
            jumped = True
            jumps += 1
            if jumps > 16:
                raise ValueError("too many DNS compression pointers")
            continue
        offset += 1
        if offset + length > len(data):
            raise ValueError("truncated DNS label")
        labels.append(data[offset:offset + length])
        offset += length

    if not jumped:
        next_offset = offset

    raw = b"".join(labels)
    if raw:
        try:
            name, _ = _decode_name_chars(raw)
            return name, next_offset
        except ValueError:
            return raw.decode("latin-1", "replace"), next_offset
    return "", next_offset


def _parse_name_flags(flags: int) -> dict[str, Any]:
    """Decode the 16-bit NODE_NAME_FLAGS field of an NBSTAT name entry."""
    return {
        "group": bool(flags & NAME_FLAGS_GROUP),
        "unique": not bool(flags & NAME_FLAGS_GROUP),
        "owner_node_type": _OWNER_NODE_TYPES.get(
            (flags & NAME_FLAGS_ONT) >> 13, "reserved"
        ),
        "permanent": bool(flags & NAME_FLAGS_PRM),
        "transient": not bool(flags & NAME_FLAGS_PRM),
        "active": bool(flags & NAME_FLAGS_ACT),
        "conflict": bool(flags & NAME_FLAGS_CNF),
        "deregister": bool(flags & NAME_FLAGS_DRG),
        "raw": flags,
    }


def _parse_nbtstat_rdata(rdata: bytes) -> dict[str, Any]:
    """Parse the RDATA of an NBSTAT (node status) resource record.

    Layout (RFC 1002 section 4.2.18): ``NUM_NAMES(1)`` followed by that many
    18-byte name entries (``15-byte name`` + ``1-byte suffix`` +
    ``2-byte NAME_FLAGS``), then the ``STATISTICS`` block whose first field is
    the 6-byte ``Unit ID`` (MAC address).
    """
    if not rdata:
        raise ValueError("empty NBSTAT RDATA")

    num_names = rdata[0]
    offset = 1
    names: list[dict[str, Any]] = []

    for _ in range(num_names):
        if offset + 18 > len(rdata):
            raise ValueError("truncated NBNS name entry")
        raw_name = rdata[offset:offset + 15]
        suffix = rdata[offset + 15]
        flags = struct.unpack("!H", rdata[offset + 16:offset + 18])[0]
        offset += 18

        name = raw_name.rstrip(b" ").rstrip(b"\x00").decode("ascii", "replace")
        names.append({
            "name": name,
            "suffix": suffix,
            "suffix_hex": f"0x{suffix:02x}",
            "service_type": SUFFIX_SERVICE_TYPES.get(
                suffix, f"unknown (0x{suffix:02x})"
            ),
            "flags": _parse_name_flags(flags),
        })

    mac = None
    if offset + 6 <= len(rdata):
        mac_bytes = rdata[offset:offset + 6]
        mac = ":".join(f"{b:02x}" for b in mac_bytes)

    return {"num_names": num_names, "names": names, "mac": mac}


def _skip_question(data: bytes, offset: int, qdcount: int) -> int:
    """Skip *qdcount* DNS question records, returning the new offset."""
    for _ in range(qdcount):
        _, offset = _parse_dns_name(data, offset)
        if offset + 4 > len(data):
            raise ValueError("truncated question record")
        offset += 4  # QUESTION_TYPE (2) + QUESTION_CLASS (2)
    return offset


def _parse_nbns_response(data: bytes) -> dict[str, Any]:
    """Parse an NBNS message (response expected) into a dict.

    Returns a dict with ``transaction_id``, ``flags`` (``is_response``,
    ``opcode``, ``rcode``, ``rcode_name``), ``question_count``,
    ``answer_count`` and ``answers`` (list of resource records). For NBSTAT
    answers, ``mac`` and ``names`` are extracted. Raises ``ValueError`` on
    malformed/truncated packets.
    """
    if len(data) < 12:
        raise ValueError("truncated NBNS header (need 12 bytes)")

    transaction_id = struct.unpack("!H", data[0:2])[0]
    flags_raw = struct.unpack("!H", data[2:4])[0]
    qdcount = struct.unpack("!H", data[4:6])[0]
    ancount = struct.unpack("!H", data[6:8])[0]
    nscount = struct.unpack("!H", data[8:10])[0]
    arcount = struct.unpack("!H", data[10:12])[0]

    is_response = bool(flags_raw & 0x8000)
    opcode = (flags_raw >> 11) & 0x0F
    rcode = flags_raw & 0x000F

    offset = 12
    if qdcount:
        offset = _skip_question(data, offset, qdcount)

    answers: list[dict[str, Any]] = []
    mac: str | None = None
    names: list[dict[str, Any]] = []

    for _ in range(ancount):
        if offset >= len(data):
            raise ValueError("truncated answer record")
        _, offset = _parse_dns_name(data, offset)
        if offset + 10 > len(data):
            raise ValueError("truncated resource record header")
        rr_type = struct.unpack("!H", data[offset:offset + 2])[0]
        rr_class = struct.unpack("!H", data[offset + 2:offset + 4])[0]
        ttl = struct.unpack("!I", data[offset + 4:offset + 8])[0]
        rdlength = struct.unpack("!H", data[offset + 8:offset + 10])[0]
        offset += 10
        if offset + rdlength > len(data):
            raise ValueError("truncated resource record RDATA")
        rdata = data[offset:offset + rdlength]
        offset += rdlength

        answer: dict[str, Any] = {
            "type": rr_type,
            "class": rr_class,
            "ttl": ttl,
            "rdata_length": rdlength,
        }
        if rr_type == RR_TYPE_NBSTAT:
            parsed = _parse_nbtstat_rdata(rdata)
            answer["type_name"] = "nbstat"
            answer["mac"] = parsed["mac"]
            answer["names"] = parsed["names"]
            answer["num_names"] = parsed["num_names"]
            if parsed["mac"]:
                mac = parsed["mac"]
            if parsed["names"]:
                names = parsed["names"]
        elif rr_type == RR_TYPE_NB:
            answer["type_name"] = "nb"
            answer["address"] = (
                ".".join(str(b) for b in rdata[:4]) if len(rdata) >= 4 else None
            )
        else:
            answer["type_name"] = f"0x{rr_type:04x}"

        answers.append(answer)

    return {
        "transaction_id": transaction_id,
        "flags": {
            "raw": flags_raw,
            "is_response": is_response,
            "opcode": opcode,
            "rcode": rcode,
            "rcode_name": RCODE_NAMES.get(rcode, f"unknown ({rcode})"),
        },
        "question_count": qdcount,
        "answer_count": ancount,
        "authority_count": nscount,
        "additional_count": arcount,
        "answers": answers,
        "mac": mac,
        "names": names,
        "num_names": len(names),
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
    """Send a UDP NBNS request and receive the response (injectable for tests)."""
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


def _derive_assessment(names: list[dict[str, Any]]) -> dict[str, Any]:
    """Build heuristic signals from a parsed name table."""
    is_server = False
    hostname: str | None = None
    is_domain_member = False

    for entry in names:
        flags = entry.get("flags", {})
        suffix = entry.get("suffix")
        if suffix == _SUFFIX_FILE_SERVER:
            is_server = True
        if suffix == _SUFFIX_WORKSTATION and not flags.get("group") and hostname is None:
            hostname = entry.get("name")
        if suffix == _SUFFIX_WORKSTATION and flags.get("group"):
            is_domain_member = True

    return {
        "is_server": is_server,
        "hostname": hostname,
        "is_domain_member": is_domain_member,
    }


def run_netbios(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    name: str = DEFAULT_NAME,
    suffix: int = DEFAULT_SUFFIX,
    connector=None,
) -> dict[str, Any]:
    """Run NetBIOS (NBNS) NODE STATUS reconnaissance against *target*.

    Args:
        target: Hostname, ``host:port``, or URL.
        port: Explicit NBNS port; when ``None`` the port is parsed from the
            target (or defaults to 137).
        timeout: Per-request timeout in seconds.
        name: NetBIOS name to query (default ``"*"`` to enumerate all names).
        suffix: Service suffix byte for the queried name (default 0x00).
        connector: Callable for sending/receiving UDP packets (for testing).

    Returns:
        Structured result dict consumed by the formatters below.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port

    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "queried_name": name,
        "queried_suffix": suffix,
        "mac": None,
        "names": [],
        "num_names": 0,
        "is_server": False,
        "hostname": None,
        "is_domain_member": False,
        "transaction_id": 0,
        "error": None,
    }

    request = _build_nbns_query(name=name, suffix=suffix, transaction_id=0)
    data, err = _send_recv(host, server_port, request, timeout, connector=connector)
    if err:
        results["error"] = f"node status request failed: {err}"
        return results

    try:
        message = _parse_nbns_response(data)
    except ValueError as exc:
        results["error"] = f"response parse failed: {exc}"
        return results

    rcode = message["flags"]["rcode"]
    if rcode != 0:
        results["transaction_id"] = message["transaction_id"]
        results["error"] = (
            f"response rcode {rcode} ({message['flags']['rcode_name']})"
        )
        return results

    if not message["flags"]["is_response"]:
        results["transaction_id"] = message["transaction_id"]
        results["error"] = "unexpected response: not a response packet"
        return results

    names = message.get("names", [])
    results["transaction_id"] = message["transaction_id"]
    results["mac"] = message.get("mac")
    results["names"] = names
    results["num_names"] = message.get("num_names", len(names))

    assessment = _derive_assessment(names)
    results["is_server"] = assessment["is_server"]
    results["hostname"] = assessment["hostname"]
    results["is_domain_member"] = assessment["is_domain_member"]

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def format_netbios_report_json(data: dict[str, Any]) -> str:
    """Format NetBIOS reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _escape_markdown(value: Any) -> str:
    """Escape pipe characters for Markdown tables/lists."""
    return str(value).replace("|", "\\|")


def format_netbios_report_markdown(data: dict[str, Any]) -> str:
    """Format NetBIOS reconnaissance results as Markdown."""
    lines = ["# ethscan NetBIOS Report", ""]
    lines.append(f"- **Target:** {_escape_markdown(data.get('target', ''))}")
    lines.append(f"- **Host:** {_escape_markdown(data.get('host', ''))}")
    lines.append(f"- **Port:** {data.get('port', '')}")
    lines.append(f"- **Queried Name:** {_escape_markdown(data.get('queried_name', ''))}")
    if data.get("mac"):
        lines.append(f"- **MAC:** {_escape_markdown(data.get('mac'))}")
    lines.append(f"- **Names Found:** {data.get('num_names', 0)}")

    names = data.get("names") or []
    if names:
        lines.append("")
        lines.append("## Names")
        lines.append("")
        lines.append("| Name | Suffix | Service | Type | Flags |")
        lines.append("| --- | --- | --- | --- | --- |")
        for entry in names:
            name = _escape_markdown(entry.get("name", ""))
            if not name:
                name = "(empty)"
            flags = entry.get("flags", {})
            rtype = "group" if flags.get("group") else "unique"
            flag_str = ", ".join(
                f"{k}={v}"
                for k, v in (
                    ("permanent", flags.get("permanent")),
                    ("active", flags.get("active")),
                    ("conflict", flags.get("conflict")),
                )
                if v
            ) or "none"
            lines.append(
                f"| {name} | {entry.get('suffix_hex', '')} | "
                f"{_escape_markdown(entry.get('service_type', ''))} | "
                f"{rtype} | {_escape_markdown(flag_str)} |"
            )

    lines.append("")
    lines.append("## Assessment")
    if data.get("is_server"):
        lines.append(
            "- **Server:** YES - a `<20>` File server service name was found "
            "(the host exposes SMB/resource shares)"
        )
    else:
        lines.append("- **Server:** NO - no `<20>` File server service name found")
    if data.get("hostname"):
        lines.append(f"- **Hostname:** {_escape_markdown(data['hostname'])}")
    if data.get("is_domain_member"):
        lines.append("- **Domain member:** YES - a group `<00>` Domain name was found")

    if data.get("error"):
        lines.append("")
        lines.append(f"- **Error:** {_escape_markdown(data['error'])}")

    lines.append("")
    return "\n".join(lines)


def format_netbios_report_csv(data: dict[str, Any]) -> str:
    """Format NetBIOS reconnaissance results as CSV.

    Emits a header row plus one row per NetBIOS name entry (including a
    summary row). The Markdown formatter renders a per-name ``Names`` table
    (Name | Suffix | Service | Type | Flags); this CSV previously collapsed
    that table into a single ``names`` column with ``"; "``-joined
    ``name<suffix>`` strings, losing every per-name attribute (service type,
    group/unique, owner node type, permanent/active, conflict/deregister) and
    the association between a name and its flags.

    Header (25 columns)::

        target,host,port,mac,queried_name,queried_suffix,num_names,
        record_type,name,suffix,suffix_hex,service_type,group,unique,
        owner_node_type,permanent,transient,active,conflict,deregister,
        raw,is_server,hostname,is_domain_member,error

    - Summary row: ``record_type=summary``; target context + query + ``num_names``
      + the table-level assessment (``is_server``/``hostname``/
      ``is_domain_member``) + top-level ``error``; per-name fields empty.
    - Name rows: ``record_type=name``; target context repeated (self-contained
      rows) + one row per entry in ``data["names"]`` carrying ``name``,
      ``suffix``, ``suffix_hex``, ``service_type`` and every decoded flag;
      assessment fields empty (they are aggregate signals, not per-name).
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Unified header with record_type discriminator.
    writer.writerow([
        "target", "host", "port", "mac", "queried_name", "queried_suffix",
        "num_names", "record_type", "name", "suffix", "suffix_hex",
        "service_type", "group", "unique", "owner_node_type", "permanent",
        "transient", "active", "conflict", "deregister", "raw",
        "is_server", "hostname", "is_domain_member", "error",
    ])

    names = data.get("names") or []
    num_names = data.get("num_names", len(names))

    def _name_fields(entry: dict[str, Any]) -> list[Any]:
        flags = entry.get("flags") or {}
        return [
            entry.get("name", ""),
            entry.get("suffix", ""),
            entry.get("suffix_hex", ""),
            entry.get("service_type", ""),
            "true" if flags.get("group") else "false",
            "true" if flags.get("unique") else "false",
            flags.get("owner_node_type", ""),
            "true" if flags.get("permanent") else "false",
            "true" if flags.get("transient") else "false",
            "true" if flags.get("active") else "false",
            "true" if flags.get("conflict") else "false",
            "true" if flags.get("deregister") else "false",
            flags.get("raw", ""),
        ]

    # Summary row: target context + query + aggregate signals; name fields empty.
    writer.writerow([
        data.get("target", ""),
        data.get("host", ""),
        data.get("port", ""),
        data.get("mac", "") or "",
        data.get("queried_name", ""),
        data.get("queried_suffix", ""),
        num_names,
        "summary",  # record_type
        "",  # name
        "",  # suffix
        "",  # suffix_hex
        "",  # service_type
        "",  # group
        "",  # unique
        "",  # owner_node_type
        "",  # permanent
        "",  # transient
        "",  # active
        "",  # conflict
        "",  # deregister
        "",  # raw
        "true" if data.get("is_server") else "false",
        data.get("hostname", "") or "",
        "true" if data.get("is_domain_member") else "false",
        data.get("error", "") or "",
    ])

    # Name rows: one per NetBIOS name entry, target context repeated.
    for entry in names:
        writer.writerow([
            data.get("target", ""),
            data.get("host", ""),
            data.get("port", ""),
            data.get("mac", "") or "",
            data.get("queried_name", ""),
            data.get("queried_suffix", ""),
            num_names,
            "name",  # record_type
            *_name_fields(entry),
            "", "", "", "",  # assessment fields empty on name rows
        ])

    return output.getvalue().rstrip("\r\n")
