"""Unit tests for the stale DNS detection module."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from ethscan.stale import (
    _normalize_domain,
    check_ip_reachable,
    check_tcp_connect,
    format_stale_report_csv,
    format_stale_report_json,
    format_stale_report_markdown,
    load_domains_from_file,
    resolve_a_records,
    resolve_aaaa_records,
    resolve_cname,
    resolve_domain_all,
    run_stale,
)


class TestNormalizeDomain:
    def test_bare_domain(self):
        assert _normalize_domain("example.com") == "example.com"

    def test_url_with_scheme(self):
        assert _normalize_domain("https://example.com/path") == "example.com"

    def test_url_without_scheme(self):
        assert _normalize_domain("example.com/path") == "example.com"

    def test_case_insensitive(self):
        assert _normalize_domain("EXAMPLE.COM") == "example.com"

    def test_whitespace(self):
        assert _normalize_domain("  example.com  ") == "example.com"


class TestLoadDomainsFromFile:
    def test_basic(self, tmp_path):
        f = tmp_path / "domains.txt"
        f.write_text("example.com\ngoogle.com\n")
        result = load_domains_from_file(str(f))
        assert result == ["example.com", "google.com"]

    def test_strips_whitespace(self, tmp_path):
        f = tmp_path / "domains.txt"
        f.write_text("  example.com  \n  google.com  \n")
        result = load_domains_from_file(str(f))
        assert result == ["example.com", "google.com"]

    def test_skips_empty_lines(self, tmp_path):
        f = tmp_path / "domains.txt"
        f.write_text("example.com\n\n\ngoogle.com\n")
        result = load_domains_from_file(str(f))
        assert result == ["example.com", "google.com"]

    def test_skips_comments(self, tmp_path):
        f = tmp_path / "domains.txt"
        f.write_text("example.com\n# comment\ngoogle.com\n")
        result = load_domains_from_file(str(f))
        assert result == ["example.com", "google.com"]

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_domains_from_file("/nonexistent/file.txt")


class TestResolveARecords:
    @patch("socket.getaddrinfo")
    def test_success(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, 0, 0, "", ("192.168.1.1", 0)),
            (socket.AF_INET, 0, 0, "", ("192.168.1.2", 0)),
        ]
        result = resolve_a_records("example.com", timeout=1.0)
        assert result == ["192.168.1.1", "192.168.1.2"]

    @patch("socket.getaddrinfo")
    def test_deduplicates(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, 0, 0, "", ("192.168.1.1", 0)),
            (socket.AF_INET, 0, 0, "", ("192.168.1.1", 0)),
        ]
        result = resolve_a_records("example.com", timeout=1.0)
        assert result == ["192.168.1.1"]

    @patch("socket.getaddrinfo", side_effect=socket.gaierror("fail"))
    def test_failure(self, mock_getaddrinfo):
        result = resolve_a_records("example.com", timeout=1.0)
        assert result == []


class TestResolveAAAARecords:
    @patch("socket.getaddrinfo")
    def test_success(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET6, 0, 0, "", ("2001:db8::1", 0, 0, 0)),
        ]
        result = resolve_aaaa_records("example.com", timeout=1.0)
        assert result == ["2001:db8::1"]

    @patch("socket.getaddrinfo", side_effect=socket.gaierror("fail"))
    def test_failure(self, mock_getaddrinfo):
        result = resolve_aaaa_records("example.com", timeout=1.0)
        assert result == []


class TestResolveCNAME:
    @patch("socket.getaddrinfo")
    def test_cname_found(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, 0, 0, "real.example.com", ("192.168.1.1", 0)),
        ]
        result = resolve_cname("alias.example.com", timeout=1.0)
        assert result == "real.example.com"

    @patch("socket.getaddrinfo")
    def test_no_cname(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, 0, 0, "", ("192.168.1.1", 0)),
        ]
        result = resolve_cname("example.com", timeout=1.0)
        assert result is None

    @patch("socket.getaddrinfo", side_effect=socket.gaierror("fail"))
    def test_failure(self, mock_getaddrinfo):
        result = resolve_cname("example.com", timeout=1.0)
        assert result is None


class TestCheckTCPConnect:
    @patch("socket.socket")
    def test_success(self, mock_socket):
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        result = check_tcp_connect("192.168.1.1", 80, 1.0)
        assert result is True
        mock_sock.connect.assert_called_once_with(("192.168.1.1", 80))
        mock_sock.close.assert_called_once()

    @patch("socket.socket", side_effect=ConnectionRefusedError)
    def test_refused(self, mock_socket):
        result = check_tcp_connect("192.168.1.1", 80, 1.0)
        assert result is False

    @patch("socket.socket", side_effect=socket.timeout)
    def test_timeout(self, mock_socket):
        result = check_tcp_connect("192.168.1.1", 80, 1.0)
        assert result is False


class TestCheckIPReachable:
    @patch("ethscan.stale.check_tcp_connect")
    def test_reachable_on_port_80(self, mock_check):
        mock_check.return_value = True
        result = check_ip_reachable("192.168.1.1", 1.0)
        assert result is True
        mock_check.assert_called_with("192.168.1.1", 80, 1.0)

    @patch("ethscan.stale.check_tcp_connect")
    def test_reachable_on_port_443(self, mock_check):
        mock_check.side_effect = [False, True, False]
        result = check_ip_reachable("192.168.1.1", 1.0)
        assert result is True

    @patch("ethscan.stale.check_tcp_connect")
    def test_unreachable(self, mock_check):
        mock_check.return_value = False
        result = check_ip_reachable("192.168.1.1", 1.0)
        assert result is False


class TestResolveDomainAll:
    @patch("ethscan.stale.resolve_a_records")
    @patch("ethscan.stale.resolve_aaaa_records")
    @patch("ethscan.stale.resolve_cname")
    @patch("ethscan.stale.check_ip_reachable")
    def test_all_records_present(self, mock_check_ip, mock_cname, mock_aaaa, mock_a):
        mock_a.return_value = ["192.168.1.1"]
        mock_aaaa.return_value = ["2001:db8::1"]
        mock_cname.return_value = "real.example.com"
        mock_check_ip.return_value = True

        result = resolve_domain_all("example.com", 1.0)

        assert result["domain"] == "example.com"
        assert result["A"] == ["192.168.1.1"]
        assert result["AAAA"] == ["2001:db8::1"]
        assert result["CNAME"] == "real.example.com"
        assert result["stale"] is False
        assert result["stale_reasons"] == []

    @patch("ethscan.stale.resolve_a_records", return_value=[])
    @patch("ethscan.stale.resolve_aaaa_records", return_value=[])
    @patch("ethscan.stale.resolve_cname", return_value=None)
    @patch("ethscan.stale.check_ip_reachable", return_value=False)
    def test_no_records_stale(self, mock_check_ip, mock_cname, mock_aaaa, mock_a):
        result = resolve_domain_all("example.com", 1.0)
        assert result["stale"] is True
        assert "No DNS records resolved" in result["stale_reasons"][0]

    @patch("ethscan.stale.resolve_a_records", return_value=["192.168.1.1"])
    @patch("ethscan.stale.resolve_aaaa_records", return_value=[])
    @patch("ethscan.stale.resolve_cname", return_value=None)
    @patch("ethscan.stale.check_ip_reachable", return_value=False)
    def test_ip_unreachable_stale(self, mock_check_ip, mock_cname, mock_aaaa, mock_a):
        result = resolve_domain_all("example.com", 1.0)
        assert result["stale"] is True
        assert "IP 192.168.1.1 unreachable" in result["stale_reasons"][0]

    @patch("ethscan.stale.resolve_a_records", return_value=[])
    @patch("ethscan.stale.resolve_aaaa_records", return_value=[])
    @patch("ethscan.stale.resolve_cname", return_value="cname.example.com")
    @patch("ethscan.stale.resolve_a_records", return_value=[])
    @patch("ethscan.stale.resolve_aaaa_records", return_value=[])
    def test_cname_target_unresolvable(self, mock_aaaa2, mock_a2, mock_cname, mock_aaaa1, mock_a1):
        result = resolve_domain_all("example.com", 1.0)
        assert result["stale"] is True
        assert "CNAME target cname.example.com does not resolve" in result["stale_reasons"][0]


class TestRunStale:
    @patch("ethscan.stale.resolve_domain_all")
    def test_multiple_domains(self, mock_resolve):
        mock_resolve.side_effect = [
            {"domain": "a.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []},
            {"domain": "b.com", "A": [], "AAAA": [], "CNAME": None, "stale": True, "stale_reasons": ["No DNS records resolved"]},
        ]

        results = run_stale(["a.com", "b.com"], timeout=1.0, max_workers=2)

        assert results["total_checked"] == 2
        assert results["stale_count"] == 1
        assert results["fresh_count"] == 1
        assert len(results["results"]) == 2
        assert len(results["stale_results"]) == 1

    @patch("ethscan.stale.resolve_domain_all")
    def test_deduplicates_targets(self, mock_resolve):
        mock_resolve.return_value = {"domain": "a.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}

        results = run_stale(["a.com", "a.com", "A.COM"], timeout=1.0, max_workers=2)

        assert results["total_checked"] == 1
        assert mock_resolve.call_count == 1


class TestFormatters:
    def test_json_format(self):
        data = {"total_checked": 1, "stale_count": 0, "fresh_count": 1, "results": []}
        output = format_stale_report_json(data)
        assert "total_checked" in output
        assert "1" in output

    def test_markdown_format(self):
        data = {
            "total_checked": 1,
            "stale_count": 1,
            "fresh_count": 0,
            "stale_results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale_reasons": ["IP unreachable"]}
            ],
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": True}
            ],
        }
        output = format_stale_report_markdown(data)
        assert "Stale DNS Record Detection Report" in output
        assert "example.com" in output
        assert "IP unreachable" in output

    def test_markdown_no_stale(self):
        data = {
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "stale_results": [],
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False}
            ],
        }
        output = format_stale_report_markdown(data)
        assert "**Stale Records:** 0" in output
        assert "**Fresh Records:** 1" in output


class TestCSVFormatter:
    def test_csv_format_basic(self):
        data = {
            "results": [
                {
                    "domain": "example.com",
                    "A": ["192.168.1.1"],
                    "AAAA": ["2001:db8::1"],
                    "CNAME": "real.example.com",
                    "stale": True,
                    "stale_reasons": ["IP 192.168.1.1 unreachable on common ports"],
                }
            ]
        }
        output = format_stale_report_csv(data)
        lines = output.strip().splitlines()
        assert lines[0] == "domain,A_records,AAAA_records,CNAME,stale,stale_reasons"
        assert "example.com" in lines[1]
        assert "192.168.1.1" in lines[1]
        assert "2001:db8::1" in lines[1]
        assert "real.example.com" in lines[1]
        assert "true" in lines[1]
        assert "IP 192.168.1.1 unreachable on common ports" in lines[1]

    def test_csv_format_empty(self):
        data = {"results": []}
        output = format_stale_report_csv(data)
        assert output == "domain,A_records,AAAA_records,CNAME,stale,stale_reasons"

    def test_csv_format_missing_fields(self):
        data = {
            "results": [
                {
                    "domain": "example.com",
                    "A": None,
                    "AAAA": None,
                    "CNAME": None,
                    "stale": False,
                    "stale_reasons": None,
                }
            ]
        }
        output = format_stale_report_csv(data)
        lines = output.strip().splitlines()
        assert lines[0] == "domain,A_records,AAAA_records,CNAME,stale,stale_reasons"
        assert lines[1] == "example.com,,,,false,"

    def test_csv_format_pipe_escaping(self):
        data = {
            "results": [
                {
                    "domain": "example|com",
                    "A": ["1.1.1|1"],
                    "AAAA": [],
                    "CNAME": "cname|example.com",
                    "stale": True,
                    "stale_reasons": ["reason|1", "reason|2"],
                }
            ]
        }
        output = format_stale_report_csv(data)
        lines = output.strip().splitlines()
        assert "example|com" in lines[1]
        assert "1.1.1|1" in lines[1]
        assert "cname|example.com" in lines[1]
        assert "reason|1; reason|2" in lines[1]