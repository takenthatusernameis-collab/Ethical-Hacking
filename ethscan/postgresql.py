"""PostgreSQL reconnaissance module for ethscan.

Offline-first PostgreSQL reconnaissance using only the Python standard library
(``socket``). The module performs a safe, bounded probe over the PostgreSQL
wire protocol (TCP ``5432``):

* **startup** -- send a minimal SSL-interop ``StartupMessage`` (protocol 3.0)
  and parse the server's immediate response. The greeting carries
  ``ParameterStatus`` messages (including ``server_version``), an
  ``Authentication`` request (auth method/type), and ``BackendKeyData``
  (process id). No login is attempted and no password is sent.

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw TCP socket so tests can substitute a local fake server.
"""

import csv
import io
import json
import socket
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PORT = 5432
DEFAULT_TIMEOUT = 3.0
DEFAULT_PROBES = ("startup",)

# PostgreSQL protocol version 3.0 (0x00030000).
_PG_PROTOCOL_VERSION_3_0 = 196608

# Authentication type codes used in 'R' (Authentication) messages.
_AUTH_TYPE_NAMES: Dict[int, str] = {
    0: "Ok",
    1: "KerberosV5",
    2: "CleartextPassword",
    3: "MD5Password",
    4: "SCMCredential",
    5: "GSS",
    6: "GSSContinue",
    7: "GSSFinal",
    10: "SASL",
    11: "SASLContinue",
    12: "SASLFinal",
    13: "SASLexchange",
}


def _normalize_target(target: str) -> Tuple[str, int]:
    """Parse a target into a bare host and integer port.

    Accepts bare hosts, ``host:port``, and ``postgresql://`` / ``postgres://``
    URLs. Defaults to port ``DEFAULT_PORT`` when none is supplied. IPv6
    literals may be bracketed.
    """
    normalized = (target or "").strip()
    host: Optional[str] = None
    port: Optional[int] = None

    if "://" in normalized:
        from urllib.parse import urlparse

        parsed = urlparse(normalized)
        # urlparse already unwraps bracketed IPv6 and splits the port.
        host = (parsed.hostname or "").strip()
        port = parsed.port
    else:
        host = normalized
        # Only interpret host[:port] / bracketed IPv6 when no scheme was given.
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

    return host, int(port) if port else DEFAULT_PORT


def _build_startup_request(user: str = "ethscan") -> bytes:
    """Build a PostgreSQL ``StartupMessage`` (protocol 3.0).

    Wire layout (all integers big-endian / network byte order):

        Int32  messageLength   (including itself)
        Int32  protocolVersion (0x00030000 = protocol 3.0)
        name\x00 value\x00 ... \x00   (null-terminated pair list)
    """
    params = b"user\x00" + user.encode("utf-8") + b"\x00"
    params += b"\x00"  # terminate the parameter list

    # length field counts: 4 (length) + 4 (protocol) + len(params)
    message_length = 4 + 4 + len(params)
    header = (
        message_length.to_bytes(4, "big")
        + _PG_PROTOCOL_VERSION_3_0.to_bytes(4, "big")
    )
    return header + params


def _send_recv(
    host: str,
    port: int,
    request: bytes,
    timeout: float,
    connector=None,
) -> Tuple[Optional[bytes], Optional[str]]:
    """Send bytes over TCP and return received bytes.

    Tests may provide a ``connector`` callable to inject a fake transport.
    """
    if connector is not None:
        try:
            return connector(host, port, request, timeout)
        except Exception as exc:  # pragma: no cover
            return None, f"connector error: {exc}"

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            if request:
                sock.sendall(request)
            chunks: List[bytes] = []
            try:
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
            except socket.timeout:
                pass
            return b"".join(chunks) if chunks else None, None
    except socket.timeout:
        return None, "Timeout"
    except ConnectionRefusedError:
        return None, "Connection refused"
    except OSError as exc:
        return None, str(exc)


def _parse_error_fields(body: bytes) -> Dict[str, str]:
    """Parse an ErrorResponse / NoticeResponse body into a field map.

    Each field is ``<type-byte><value>\0``; the body is terminated by a final
    ``\\0``.
    """
    fields: Dict[str, str] = {}
    pos = 0
    n = len(body)
    while pos < n:
        ftype = body[pos:pos + 1]
        if ftype == b"\x00":
            break
        rest = body[pos + 1:]
        nul = rest.find(b"\x00")
        if nul == -1:
            fields[ftype.decode("ascii", errors="replace")] = rest.decode(
                "utf-8", errors="replace"
            )
            break
        fields[ftype.decode("ascii", errors="replace")] = rest[:nul].decode(
            "utf-8", errors="replace"
        )
        pos = pos + 1 + nul + 1
    return fields


def _parse_startup_response(data: bytes) -> Dict[str, Any]:
    """Parse the server greeting returned after a ``StartupMessage``.

    The response is a stream of length-prefixed messages (big-endian), each
    beginning with a one-byte message type. This parser extracts the
    ``server_version`` and other parameters from ``ParameterStatus`` ('S')
    messages, the authentication method from ``Authentication`` ('R')
    messages, and the backend process id from ``BackendKeyData`` ('K')
    messages.
    """
    result: Dict[str, Any] = {
        "server_version": None,
        "auth_type_code": None,
        "auth_type_name": None,
        "process_id": None,
        "parameters": {},
        "errors": [],
        "notices": [],
    }
    if not data:
        return result

    pos = 0
    n = len(data)
    while pos < n:
        msg_type = data[pos:pos + 1]
        if not msg_type:
            break
        # Need at least type(1) + length(4)
        if pos + 5 > n:
            break
        length = int.from_bytes(data[pos + 1:pos + 5], "big")
        if length < 4:
            break
        body_start = pos + 5
        body_end = pos + 1 + length
        if body_end > n:
            body = data[body_start:]
        else:
            body = data[body_start:body_end]

        t = msg_type[0:1]
        if t == b"S":  # ParameterStatus
            parts = body.split(b"\x00")
            if len(parts) >= 2:
                name = parts[0].decode("utf-8", errors="replace")
                value = parts[1].decode("utf-8", errors="replace")
                result["parameters"][name] = value
                if name == "server_version":
                    result["server_version"] = value
        elif t == b"R":  # Authentication
            if len(body) >= 4:
                code = int.from_bytes(body[0:4], "big")
                result["auth_type_code"] = code
                result["auth_type_name"] = _AUTH_TYPE_NAMES.get(code, f"Unknown({code})")
        elif t == b"K":  # BackendKeyData
            if len(body) >= 4:
                result["process_id"] = int.from_bytes(body[0:4], "big")
        elif t == b"E":  # ErrorResponse
            fields = _parse_error_fields(body)
            message = fields.get("M") or fields.get("C") or ""
            result["errors"].append({"message": message, "fields": fields})
        elif t == b"N":  # NoticeResponse
            fields = _parse_error_fields(body)
            message = fields.get("M") or fields.get("C") or ""
            result["notices"].append({"message": message, "fields": fields})
        # other types (e.g. 'Z' ReadyForQuery) are ignored for recon

        pos = body_end

    return result


def _assess_startup(startup: Dict[str, Any]) -> List[str]:
    """Assess startup/greeting data and return findings."""
    findings: List[str] = []
    version = startup.get("server_version")
    if version:
        findings.append(f"PostgreSQL server version: {version}")
        try:
            major = int(str(version).split(".")[0])
            if major < 10:
                findings.append(
                    f"Old PostgreSQL version detected (major {major}; may lack security features)"
                )
        except (ValueError, AttributeError):
            pass

    auth_name = startup.get("auth_type_name")
    auth_code = startup.get("auth_type_code")
    if auth_name:
        findings.append(f"Authentication method: {auth_name} (code {auth_code})")
        if auth_name == "Ok":
            findings.append(
                "Server accepted the startup without requiring credentials "
                "(authentication method 'Ok' / trust)"
            )

    if startup.get("process_id") is not None:
        findings.append(f"Backend process id: {startup['process_id']}")

    for err in startup.get("errors", []) or []:
        msg = err.get("message") if isinstance(err, dict) else str(err)
        if msg:
            findings.append(f"Server error: {msg}")

    return findings


def run_postgresql(
    target: str,
    port: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
    probes: Optional[List[str]] = None,
    connector=None,
) -> Dict[str, Any]:
    """Run PostgreSQL reconnaissance probes against *target*.

    Args:
        target: Hostname, ``host:port``, or ``postgresql://`` / ``postgres://``
            URL.
        port: Explicit PostgreSQL port; when ``None`` the port is parsed from
            the target (or defaults to 5432).
        timeout: Per-request timeout in seconds.
        probes: List of probes to run (case-insensitive). Defaults to
            ``("startup",)``.
        connector: Callable for sending/receiving TCP data (for testing).

    Returns:
        Structured result dict consumed by the formatters below.
    """
    try:
        host, parsed_port = _normalize_target(target)
    except ValueError as exc:
        return {
            "target": target,
            "host": None,
            "port": port or DEFAULT_PORT,
            "accessible": False,
            "startup": {},
            "version": None,
            "findings": [],
            "error": str(exc),
        }

    final_port = int(port) if port is not None else parsed_port
    probe_list = probes if probes is not None else list(DEFAULT_PROBES)
    if not probe_list:
        return {
            "target": target,
            "host": host,
            "port": final_port,
            "accessible": False,
            "startup": {},
            "version": None,
            "findings": [],
            "error": None,
        }

    norm_probes = [p.strip().lower() for p in probe_list if p.strip()]

    startup_data: Dict[str, Any] = {}
    version: Optional[str] = None
    accessible = False
    error: Optional[str] = None

    if "startup" in norm_probes:
        try:
            resp, err = _send_recv(
                host, final_port, _build_startup_request(), timeout, connector
            )
            if err:
                error = err
            elif resp:
                accessible = True
                startup_data = _parse_startup_response(resp)
                if startup_data.get("server_version"):
                    version = str(startup_data["server_version"])
            else:
                error = error or "No response from server"
        except Exception as exc:  # pragma: no cover
            error = str(exc)

    findings = _assess_startup(startup_data)

    return {
        "target": target,
        "host": host,
        "port": final_port,
        "accessible": bool(accessible),
        "startup": startup_data,
        "version": version,
        "findings": findings,
        "error": error,
    }


def format_postgresql_report_json(data: Dict[str, Any]) -> str:
    """Format PostgreSQL reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_postgresql_report_markdown(data: Dict[str, Any]) -> str:
    """Format PostgreSQL reconnaissance results as Markdown."""
    lines: List[str] = []
    lines.append("# PostgreSQL Reconnaissance Report")
    lines.append("")
    lines.append(f"**Target:** {data.get('target', '')}")
    lines.append(f"**Host:** {data.get('host') or 'N/A'}")
    lines.append(f"**Port:** {data.get('port', DEFAULT_PORT)}")
    lines.append(f"**Accessible:** {'Yes' if data.get('accessible') else 'No'}")
    lines.append("")

    if data.get("version"):
        lines.append(f"**Server Version:** {data['version']}")
        lines.append("")

    startup = data.get("startup") or {}
    if startup:
        lines.append("## Server Greeting")
        lines.append("")
        for key in [
            "server_version",
            "auth_type_name",
            "auth_type_code",
            "process_id",
        ]:
            if key in startup and startup[key] is not None:
                lines.append(f"- **{key}:** {_markdown_escape(startup[key])}")
        parameters = startup.get("parameters") or {}
        if parameters:
            lines.append("")
            lines.append("## Server Parameters")
            lines.append("")
            lines.append("| Parameter | Value |")
            lines.append("|-----------|-------|")
            for key in sorted(parameters):
                lines.append(f"| {key} | {_markdown_escape(parameters[key])} |")
            lines.append("")
        lines.append("")

    findings = data.get("findings") or []
    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings:
            lines.append(f"- {f}")
        lines.append("")
    else:
        lines.append("## Findings\n- No notable findings\n")

    if data.get("error"):
        lines.append("## Error")
        lines.append("")
        lines.append(f"**Error:** {data['error']}")
        lines.append("")

    return "\n".join(lines).rstrip("\n")


def format_postgresql_report_csv(data: Dict[str, Any]) -> str:
    """Format PostgreSQL reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "host",
        "port",
        "accessible",
        "version",
        "auth_type",
        "process_id",
        "findings",
        "error",
    ])

    startup = data.get("startup") or {}
    findings = data.get("findings") or []
    writer.writerow([
        data.get("target", ""),
        data.get("host", ""),
        data.get("port", DEFAULT_PORT),
        "true" if data.get("accessible") else "false",
        data.get("version") or "",
        startup.get("auth_type_name") or "",
        startup.get("process_id") or "",
        "; ".join(findings).replace("\n", " ").replace("\r", " "),
        data.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")


__all__ = [
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT",
    "DEFAULT_PROBES",
    "_normalize_target",
    "_build_startup_request",
    "_send_recv",
    "_parse_error_fields",
    "_parse_startup_response",
    "_assess_startup",
    "run_postgresql",
    "format_postgresql_report_csv",
    "format_postgresql_report_json",
    "format_postgresql_report_markdown",
]
