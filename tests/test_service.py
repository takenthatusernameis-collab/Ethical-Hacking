"""Tests for the ethscan service module."""

import pytest

from ethscan.service import (
    DEFAULT_PORTS,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    COMMON_SERVICE_PORTS,
    SERVICE_SIGNATURES,
    format_service_report_json,
    format_service_report_markdown,
    grab_banner,
    run_service,
)


def test_defaults() -> None:
    assert DEFAULT_TIMEOUT == 3.0
    assert DEFAULT_WORKERS == 50
    assert 21 in DEFAULT_PORTS
    assert 22 in DEFAULT_PORTS
    assert 80 in DEFAULT_PORTS
    assert 443 in DEFAULT_PORTS


def test_common_service_ports() -> None:
    assert COMMON_SERVICE_PORTS[21] == "ftp"
    assert COMMON_SERVICE_PORTS[22] == "ssh"
    assert COMMON_SERVICE_PORTS[80] == "http"
    assert COMMON_SERVICE_PORTS[443] == "https"
    assert COMMON_SERVICE_PORTS[3306] == "mysql"


def test_service_signatures() -> None:
    assert "ftp" in SERVICE_SIGNATURES
    assert "ssh" in SERVICE_SIGNATURES
    assert "http" in SERVICE_SIGNATURES
    assert len(SERVICE_SIGNATURES["ftp"]) > 0


def test_grab_banner_connection_refused() -> None:
    port, banner, service = grab_banner("127.0.0.1", 9999, 0.5)
    assert port == 9999
    assert banner is None
    assert service is None


def test_grab_banner_timeout() -> None:
    port, banner, service = grab_banner("10.255.255.1", 22, 0.1)
    assert port == 22
    assert banner is None
    assert service is None


def test_run_service_offline(monkeypatch) -> None:
    def mock_grab_banner(host, port, timeout):
        if port == 21:
            return port, "220 ProFTPD 1.3.5 Server ready.", "ProFTPD"
        if port == 22:
            return port, "SSH-2.0-OpenSSH_8.9", "OpenSSH"
        if port == 80:
            return port, "HTTP/1.1 200 OK\r\nServer: nginx", "nginx"
        return port, None, None

    monkeypatch.setattr("ethscan.service.grab_banner", mock_grab_banner)

    result = run_service("example.com", ports=[21, 22, 80, 9999], timeout=1.0)

    assert result["target"] == "example.com"
    assert result["host"] == "example.com"
    assert result["ports_scanned"] == 4
    assert result["services_found"] == 3
    assert len(result["results"]) == 3

    services = {r["port"]: r.get("service") for r in result["results"]}
    assert services[21] == "ProFTPD"
    assert services[22] == "OpenSSH"
    assert services[80] == "nginx"

    banners = {r["port"]: r.get("banner") for r in result["results"]}
    assert "ProFTPD" in banners[21]
    assert "OpenSSH" in banners[22]
    assert "nginx" in banners[80]


def test_run_service_target_normalization(monkeypatch) -> None:
    def mock_grab_banner(host, port, timeout):
        return port, "test banner", "TestService"

    monkeypatch.setattr("ethscan.service.grab_banner", mock_grab_banner)

    result = run_service("https://example.com/path", ports=[80], timeout=1.0)

    assert result["host"] == "example.com"


def test_run_service_custom_ports(monkeypatch) -> None:
    called_ports = []

    def mock_grab_banner(host, port, timeout):
        called_ports.append(port)
        return port, None, None

    monkeypatch.setattr("ethscan.service.grab_banner", mock_grab_banner)

    run_service("example.com", ports=[8080, 8443], timeout=1.0)

    assert called_ports == [8080, 8443]


def test_format_service_report_json() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 3,
        "services_found": 2,
        "results": [
            {"port": 21, "banner": "220 FTP Server ready", "service": "FTP"},
            {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
        ],
    }
    output = format_service_report_json(data)
    assert "example.com" in output
    assert "FTP" in output
    assert "OpenSSH" in output
    assert '"port": 21' in output


def test_format_service_report_markdown() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 3,
        "services_found": 2,
        "results": [
            {"port": 21, "banner": "220 FTP Server ready", "service": "FTP"},
            {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
        ],
    }
    output = format_service_report_markdown(data)
    assert "# ethscan Service Detection Report" in output
    assert "example.com" in output
    assert "**Ports Scanned:** 3" in output
    assert "**Services Found:** 2" in output
    assert "## Detected Services" in output
    assert "| 21 | FTP |" in output
    assert "| 22 | OpenSSH |" in output


def test_format_service_report_markdown_no_results() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 3,
        "services_found": 0,
        "results": [],
    }
    output = format_service_report_markdown(data)
    assert "*No services detected.*" in output


def test_banner_truncation_in_markdown(monkeypatch) -> None:
    long_banner = "A" * 100

    def mock_grab_banner(host, port, timeout):
        return port, long_banner, "TestService"

    monkeypatch.setattr("ethscan.service.grab_banner", mock_grab_banner)

    result = run_service("example.com", ports=[80], timeout=1.0)
    output = format_service_report_markdown(result)

    assert "..." in output
    assert len([line for line in output.split("\n") if "| 80 |" in line][0]) < 200