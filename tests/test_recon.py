"""Tests for the ethscan recon module."""

import json
from unittest.mock import patch, MagicMock

from ethscan.recon import (
    DEFAULT_RECON_MODULES,
    _normalize_domain,
    run_recon,
    format_recon_report_json,
    format_recon_report_markdown,
)


# ---------------------------------------------------------------------------
# Domain normalization
# ---------------------------------------------------------------------------


def test_normalize_domain_bare() -> None:
    assert _normalize_domain("example.com") == "example.com"


def test_normalize_domain_uppercase() -> None:
    assert _normalize_domain("Example.COM") == "example.com"


def test_normalize_domain_https_url() -> None:
    assert _normalize_domain("https://example.com/path") == "example.com"


def test_normalize_domain_strips_whitespace() -> None:
    assert _normalize_domain("  example.com  ") == "example.com"


def test_normalize_domain_with_port() -> None:
    assert _normalize_domain("http://example.com:8080") == "example.com:8080"


# ---------------------------------------------------------------------------
# run_recon with mocked sub-modules
# ---------------------------------------------------------------------------


def test_run_recon_default_modules() -> None:
    with patch("ethscan.recon.run_subdomains") as mock_subdomains, \
         patch("ethscan.recon.run_dns") as mock_dns, \
         patch("ethscan.recon.run_whois") as mock_whois, \
         patch("ethscan.recon.run_geo") as mock_geo, \
         patch("ethscan.recon.run_trace") as mock_trace:

        mock_subdomains.return_value = {"subdomains_tested": 10, "resolved_count": 2}
        mock_dns.return_value = {"records": {"A": ["1.2.3.4"]}}
        mock_whois.return_value = {"parsed": {"registrar": "Test Registrar"}}
        mock_geo.return_value = {"geolocation": {"status": "success", "country": "US"}}
        mock_trace.return_value = {"hops": [], "destination_reached": False}

        result = run_recon("example.com")

        assert result["target"] == "example.com"
        assert result["domain"] == "example.com"
        assert set(result["modules_run"]) == set(DEFAULT_RECON_MODULES)
        assert result["subdomains"] is not None
        assert result["dns"] is not None
        assert result["whois"] is not None
        assert result["geo"] is not None
        assert result["trace"] is not None


def test_run_recon_custom_modules() -> None:
    with patch("ethscan.recon.run_subdomains") as mock_subdomains, \
         patch("ethscan.recon.run_dns") as mock_dns:

        mock_subdomains.return_value = {"subdomains_tested": 10}
        mock_dns.return_value = {"records": {}}

        result = run_recon("example.com", modules=["subdomains", "dns"])

        assert result["modules_run"] == ["subdomains", "dns"]
        mock_subdomains.assert_called_once()
        mock_dns.assert_called_once()
        # whois, geo, trace should not be called


def test_run_recon_url_target() -> None:
    with patch("ethscan.recon.run_subdomains") as mock_subdomains, \
         patch("ethscan.recon.run_dns") as mock_dns, \
         patch("ethscan.recon.run_whois") as mock_whois, \
         patch("ethscan.recon.run_geo") as mock_geo, \
         patch("ethscan.recon.run_trace") as mock_trace:

        mock_subdomains.return_value = {}
        mock_dns.return_value = {}
        mock_whois.return_value = {}
        mock_geo.return_value = {}
        mock_trace.return_value = {}

        result = run_recon("https://example.com/path")

        assert result["target"] == "https://example.com/path"
        assert result["domain"] == "example.com"


def test_run_recon_subdomains_parameters() -> None:
    with patch("ethscan.recon.run_subdomains") as mock_subdomains, \
         patch("ethscan.recon.run_dns"), \
         patch("ethscan.recon.run_whois"), \
         patch("ethscan.recon.run_geo"), \
         patch("ethscan.recon.run_trace"):

        mock_subdomains.return_value = {}

        run_recon(
            "example.com",
            modules=["subdomains"],
            subdomains_wordlist=["www", "mail"],
            timeout=3.0,
            max_workers=20,
            resolver="8.8.8.8",
        )

        mock_subdomains.assert_called_once()
        call_kwargs = mock_subdomains.call_args[1]
        assert call_kwargs["subdomains"] == ["www", "mail"]
        assert call_kwargs["timeout"] == 3.0
        assert call_kwargs["max_workers"] == 20
        assert call_kwargs["resolver"] == "8.8.8.8"


def test_run_recon_dns_parameters() -> None:
    with patch("ethscan.recon.run_subdomains"), \
         patch("ethscan.recon.run_dns") as mock_dns, \
         patch("ethscan.recon.run_whois"), \
         patch("ethscan.recon.run_geo"), \
         patch("ethscan.recon.run_trace"):

        mock_dns.return_value = {}

        run_recon(
            "example.com",
            modules=["dns"],
            dns_record_types=["A", "MX"],
            dns_server="1.1.1.1",
            timeout=2.5,
        )

        mock_dns.assert_called_once()
        call_kwargs = mock_dns.call_args[1]
        assert call_kwargs["record_types"] == ["A", "MX"]
        assert call_kwargs["server"] == "1.1.1.1"
        assert call_kwargs["timeout"] == 2.5


def test_run_recon_whois_parameters() -> None:
    with patch("ethscan.recon.run_subdomains"), \
         patch("ethscan.recon.run_dns"), \
         patch("ethscan.recon.run_whois") as mock_whois, \
         patch("ethscan.recon.run_geo"), \
         patch("ethscan.recon.run_trace"):

        mock_whois.return_value = {}

        run_recon(
            "example.com",
            modules=["whois"],
            whois_server="whois.example.com",
            whois_port=443,
            timeout=10.0,
        )

        mock_whois.assert_called_once()
        call_kwargs = mock_whois.call_args[1]
        assert call_kwargs["server"] == "whois.example.com"
        assert call_kwargs["port"] == 443
        assert call_kwargs["timeout"] == 10.0


def test_run_recon_geo_parameters() -> None:
    with patch("ethscan.recon.run_subdomains"), \
         patch("ethscan.recon.run_dns"), \
         patch("ethscan.recon.run_whois"), \
         patch("ethscan.recon.run_geo") as mock_geo, \
         patch("ethscan.recon.run_trace"):

        mock_geo.return_value = {}

        run_recon(
            "example.com",
            modules=["geo"],
            geo_use_cache=False,
            geo_offline_fallback=False,
            geo_api_url="http://custom.api/json/",
            timeout=7.0,
        )

        mock_geo.assert_called_once()
        call_kwargs = mock_geo.call_args[1]
        assert call_kwargs["use_cache"] is False
        assert call_kwargs["offline_fallback"] is False
        assert call_kwargs["api_url"] == "http://custom.api/json/"
        assert call_kwargs["timeout"] == 7.0


def test_run_recon_trace_parameters() -> None:
    with patch("ethscan.recon.run_subdomains"), \
         patch("ethscan.recon.run_dns"), \
         patch("ethscan.recon.run_whois"), \
         patch("ethscan.recon.run_geo"), \
         patch("ethscan.recon.run_trace") as mock_trace:

        mock_trace.return_value = {}

        run_recon(
            "example.com",
            modules=["trace"],
            trace_port=443,
            trace_max_hops=20,
            trace_probes_per_hop=5,
            timeout=4.0,
        )

        mock_trace.assert_called_once()
        call_kwargs = mock_trace.call_args[1]
        assert call_kwargs["port"] == 443
        assert call_kwargs["max_hops"] == 20
        assert call_kwargs["probes_per_hop"] == 5
        assert call_kwargs["timeout"] == 4.0


def test_run_recon_module_failure_handling() -> None:
    with patch("ethscan.recon.run_subdomains") as mock_subdomains, \
         patch("ethscan.recon.run_dns") as mock_dns:

        mock_subdomains.side_effect = Exception("Subdomain error")
        mock_dns.return_value = {}

        result = run_recon("example.com", modules=["subdomains", "dns"])

        # Both modules should be in modules_run even if one fails
        assert "subdomains" in result["modules_run"]
        assert "dns" in result["modules_run"]
        assert len(result["notes"]) >= 1
        assert any("subdomains module failed" in note for note in result["notes"])


def test_run_recon_offline_target() -> None:
    """Test run_recon with an unresolvable target."""
    with patch("ethscan.recon.run_subdomains") as mock_subdomains, \
         patch("ethscan.recon.run_dns") as mock_dns, \
         patch("ethscan.recon.run_whois") as mock_whois, \
         patch("ethscan.recon.run_geo") as mock_geo, \
         patch("ethscan.recon.run_trace") as mock_trace:

        mock_subdomains.return_value = {"resolved_count": 0}
        mock_dns.return_value = {"records": {"A": []}}
        mock_whois.return_value = {"parsed": {"registrar": None}}
        mock_geo.return_value = {"geolocation": None}
        mock_trace.return_value = {"hops": [], "destination_reached": False}

        result = run_recon("nonexistent.invalid.domain.tld")

        assert result["target"] == "nonexistent.invalid.domain.tld"
        assert result["domain"] == "nonexistent.invalid.domain.tld"


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def test_format_recon_report_json() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": ["subdomains", "dns"],
        "subdomains": {"resolved_count": 1},
        "dns": {"records": {"A": ["1.2.3.4"]}},
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_json(data)
    parsed = json.loads(output)
    assert parsed["target"] == "example.com"
    assert parsed["modules_run"] == ["subdomains", "dns"]


def test_format_recon_report_json_empty() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": [],
        "subdomains": None,
        "dns": None,
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_json(data)
    parsed = json.loads(output)
    assert parsed["modules_run"] == []


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------


def test_format_recon_report_markdown_basic() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": ["subdomains", "dns"],
        "subdomains": {
            "subdomains_tested": 10,
            "resolved_count": 2,
            "resolved": [
                {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"}
            ],
        },
        "dns": {
            "record_types_queried": ["A", "AAAA"],
            "records": {"A": ["1.2.3.4"], "AAAA": []},
        },
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_markdown(data)
    assert "ethscan Reconnaissance Report" in output
    assert "example.com" in output
    assert "subdomains, dns" in output
    assert "Subdomain Enumeration" in output
    assert "DNS Record Enumeration" in output


def test_format_recon_report_markdown_with_resolver() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": ["subdomains"],
        "subdomains": {
            "subdomains_tested": 5,
            "resolved_count": 1,
            "resolved": [{"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"}],
            "resolver": "8.8.8.8",
            "dnspython_available": True,
        },
        "dns": None,
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_markdown(data)
    assert "**Resolver:** 8.8.8.8 (dnspython: Yes)" in output
    assert "dnspython: Yes" in output


def test_format_recon_report_markdown_dns_records() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": ["dns"],
        "subdomains": None,
        "dns": {
            "record_types_queried": ["A", "MX", "TXT"],
            "records": {
                "A": ["1.2.3.4"],
                "MX": ["mail.example.com"],
                "TXT": ["v=spf1 -all"],
            },
        },
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_markdown(data)
    assert "A Records" in output
    assert "1.2.3.4" in output
    assert "MX Records" in output
    assert "mail.example.com" in output
    assert "TXT Records" in output
    assert "v=spf1 -all" in output


def test_format_recon_report_markdown_whois() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": ["whois"],
        "subdomains": None,
        "dns": None,
        "whois": {
            "server": "whois.iana.org",
            "port": 43,
            "parsed": {
                "registrar": "Example Registrar",
                "creation_date": "2000-01-01",
                "expiration_date": "2030-01-01",
                "registrant_org": "Example Org",
                "nameservers": ["ns1.example.com", "ns2.example.com"],
                "status_codes": ["clientTransferProhibited"],
            },
        },
        "geo": None,
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_markdown(data)
    assert "WHOIS Lookup" in output
    assert "Example Registrar" in output
    assert "2000-01-01" in output
    assert "ns1.example.com" in output
    assert "clientTransferProhibited" in output


def test_format_recon_report_markdown_geo_success() -> None:
    data = {
        "target": "8.8.8.8",
        "domain": "8.8.8.8",
        "modules_run": ["geo"],
        "subdomains": None,
        "dns": None,
        "whois": None,
        "geo": {
            "geolocation": {
                "status": "success",
                "country": "United States",
                "countryCode": "US",
                "region": "VA",
                "regionName": "Virginia",
                "city": "Ashburn",
                "lat": 39.03,
                "lon": -77.5,
                "isp": "Google LLC",
                "org": "Google LLC",
                "as": "AS15169 Google LLC",
                "reverse": "dns.google",
                "cached": False,
            }
        },
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_markdown(data)
    assert "IP Geolocation" in output
    assert "United States" in output
    assert "Google LLC" in output
    assert "AS15169" in output


def test_format_recon_report_markdown_geo_fail() -> None:
    data = {
        "target": "10.0.0.1",
        "domain": "10.0.0.1",
        "modules_run": ["geo"],
        "subdomains": None,
        "dns": None,
        "whois": None,
        "geo": {
            "geolocation": {
                "status": "fail",
                "error": "Private IP range",
            }
        },
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_markdown(data)
    assert "IP Geolocation" in output
    assert "fail" in output
    assert "Private IP range" in output


def test_format_recon_report_markdown_trace() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": ["trace"],
        "subdomains": None,
        "dns": None,
        "whois": None,
        "geo": None,
        "trace": {
            "port": 80,
            "max_hops": 30,
            "probes_per_hop": 3,
            "raw_socket_available": False,
            "destination_reached": True,
            "hops": [
                {
                    "hop": 1,
                    "ip": "192.168.1.1",
                    "host": "192.168.1.1",
                    "response_type": "TIME_EXCEEDED",
                    "rtt_ms": 1.5,
                    "rtt_avg_ms": 1.5,
                    "reached_destination": False,
                },
                {
                    "hop": 2,
                    "ip": "10.0.0.1",
                    "host": "10.0.0.1",
                    "response_type": "PORT_UNREACHABLE",
                    "rtt_ms": 5.2,
                    "rtt_avg_ms": 5.2,
                    "reached_destination": True,
                },
            ],
        },
        "notes": [],
    }
    output = format_recon_report_markdown(data)
    assert "TCP Traceroute" in output
    assert "Hop Table" in output
    assert "192.168.1.1" in output
    assert "TIME_EXCEEDED" in output
    assert "PORT_UNREACHABLE" in output


def test_format_recon_report_markdown_notes() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": ["subdomains"],
        "subdomains": {},
        "dns": None,
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": ["subdomains module failed: timeout", "geo module failed: API limit"],
    }
    output = format_recon_report_markdown(data)
    assert "Notes" in output
    assert "subdomains module failed" in output
    assert "geo module failed" in output


def test_format_recon_report_markdown_empty_modules() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": [],
        "subdomains": None,
        "dns": None,
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": [],
    }
    output = format_recon_report_markdown(data)
    assert "ethscan Reconnaissance Report" in output
    assert "**Modules Run:** None" in output