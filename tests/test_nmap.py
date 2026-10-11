"""Unit tests for the Nmap XML parser module."""

import json
import tempfile
from pathlib import Path

import pytest

from ethscan.nmap import (
    parse_nmap_xml,
    run_nmap,
    format_nmap_report_json,
    format_nmap_report_markdown,
)


SAMPLE_NMAP_XML = """<runscanner version="1.0" scanner="nmap" args="nmap -oX - 192.168.1.1" start="1234567890" nmap_version="7.94" xmloutputversion="1.05">
<scaninfo type="syn" protocol="tcp" numservices="1000" services="1-1000"/>
<verbose level="0"/>
<debugging level="0"/>
<host starttime="1234567890" endtime="1234567891">
<status state="up" reason="syn-ack"/>
<address addr="192.168.1.1" addrtype="ipv4"/>
<hostnames>
<hostname name="router.local" type="PTR"/>
</hostnames>
<ports>
<port protocol="tcp" portid="22">
<state state="open" reason="syn-ack" reason_ttl="64"/>
<service name="ssh" product="OpenSSH" version="7.2p2" extrainfo="protocol 2.0" method="probed" conf="10"/>
</port>
<port protocol="tcp" portid="80">
<state state="open" reason="syn-ack" reason_ttl="64"/>
<service name="http" product="Apache httpd" version="2.4.41" extrainfo="(Ubuntu)" method="probed" conf="10"/>
</port>
<port protocol="tcp" portid="443">
<state state="closed" reason="reset" reason_ttl="64"/>
<service name="https" method="table" conf="3"/>
</port>
</ports>
</host>
<host starttime="1234567890" endtime="1234567891">
<status state="up" reason="syn-ack"/>
<address addr="192.168.1.2" addrtype="ipv4"/>
<hostnames>
<hostname name="server.local" type="PTR"/>
</hostnames>
<ports>
<port protocol="tcp" portid="21">
<state state="open" reason="syn-ack" reason_ttl="64"/>
<service name="ftp" product="vsftpd" version="2.3.4" method="probed" conf="10"/>
</port>
<port protocol="tcp" portid="22">
<state state="open" reason="syn-ack" reason_ttl="64"/>
<service name="ssh" product="OpenSSH" version="8.2p1" method="probed" conf="10"/>
</port>
</ports>
</host>
</runscanner>
"""

EMPTY_NMAP_XML = """<runscanner version="1.0" scanner="nmap" args="nmap -oX - 192.168.1.1" start="1234567890" nmap_version="7.94" xmloutputversion="1.05">
<scaninfo type="syn" protocol="tcp" numservices="1000" services="1-1000"/>
<host starttime="1234567890" endtime="1234567891">
<status state="up" reason="syn-ack"/>
<address addr="192.168.1.1" addrtype="ipv4"/>
<hostnames/>
<ports>
<port protocol="tcp" portid="22">
<state state="closed" reason="reset" reason_ttl="64"/>
<service name="ssh" method="table" conf="3"/>
</port>
</ports>
</host>
</runscanner>
"""

NO_HOSTS_NMAP_XML = """<runscanner version="1.0" scanner="nmap" args="nmap -oX - 192.168.1.1" start="1234567890" nmap_version="7.94" xmloutputversion="1.05">
<scaninfo type="syn" protocol="tcp" numservices="1000" services="1-1000"/>
</runscanner>
"""


def test_parse_nmap_xml_basic():
    hosts = parse_nmap_xml(SAMPLE_NMAP_XML)
    assert len(hosts) == 2

    # First host
    host1 = hosts[0]
    assert host1["address"] == "192.168.1.1"
    assert host1["hostnames"] == ["router.local"]
    assert host1["status"] == "up"
    assert len(host1["ports"]) == 3

    # Check port 22 (OpenSSH 7.2p2)
    port22 = next(p for p in host1["ports"] if p["port"] == 22)
    assert port22["state"] == "open"
    assert port22["service_name"] == "ssh"
    assert port22["product"] == "OpenSSH"
    assert port22["version"] == "7.2p2"
    assert "OpenSSH 7.2p2" in port22["banner"]

    # Check port 80 (Apache)
    port80 = next(p for p in host1["ports"] if p["port"] == 80)
    assert port80["state"] == "open"
    assert port80["service_name"] == "http"
    assert port80["product"] == "Apache httpd"
    assert port80["version"] == "2.4.41"
    assert "Apache httpd 2.4.41" in port80["banner"]

    # Check port 443 (closed)
    port443 = next(p for p in host1["ports"] if p["port"] == 443)
    assert port443["state"] == "closed"

    # Second host
    host2 = hosts[1]
    assert host2["address"] == "192.168.1.2"
    assert host2["hostnames"] == ["server.local"]
    assert len(host2["ports"]) == 2


def test_parse_nmap_xml_empty_hosts():
    hosts = parse_nmap_xml(NO_HOSTS_NMAP_XML)
    assert len(hosts) == 0


def test_parse_nmap_xml_no_open_ports():
    hosts = parse_nmap_xml(EMPTY_NMAP_XML)
    assert len(hosts) == 1
    assert len(hosts[0]["ports"]) == 1
    assert hosts[0]["ports"][0]["state"] == "closed"


def test_run_nmap_offline_target():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(SAMPLE_NMAP_XML)
        temp_path = f.name

    try:
        results = run_nmap(temp_path)

        assert results["input_file"] == temp_path
        assert results["hosts_scanned"] == 2
        assert results["total_ports_scanned"] == 5  # 3 + 2 ports
        assert results["total_open_ports"] == 4  # 2 + 2 open ports
        assert results["services_detected"] == 4  # 4 open ports with service info
        assert results["finding_count"] >= 1  # Should find at least some vulns

        # Check for specific CVE findings
        findings = results["findings"]
        cve_ids = [f["id"] for f in findings]
        # Should find OpenSSH 7.2p2 vulns (CVE-2016-6210, CVE-2018-15473)
        # CVE-2016-0777 is for version < 7.2 (exclusive), so 7.2p2 doesn't match
        assert "CVE-2016-6210" in cve_ids
        assert "CVE-2018-15473" in cve_ids
        # Should find vsftpd 2.3.4 backdoor
        assert "VSFTPD-2.3.4-BACKDOOR" in cve_ids
    finally:
        Path(temp_path).unlink()


def test_run_nmap_no_open_ports():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(EMPTY_NMAP_XML)
        temp_path = f.name

    try:
        results = run_nmap(temp_path)
        assert results["total_open_ports"] == 0
        assert results["finding_count"] == 0
        assert "No open ports found in scan" in results["notes"]
    finally:
        Path(temp_path).unlink()


def test_run_nmap_missing_file():
    with pytest.raises(FileNotFoundError):
        run_nmap("/nonexistent/file.xml")


def test_format_nmap_report_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(SAMPLE_NMAP_XML)
        temp_path = f.name

    try:
        results = run_nmap(temp_path)
        output = format_nmap_report_json(results)
        parsed = json.loads(output)
        assert parsed["input_file"] == temp_path
        assert parsed["finding_count"] == results["finding_count"]
    finally:
        Path(temp_path).unlink()


def test_format_nmap_report_markdown():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(SAMPLE_NMAP_XML)
        temp_path = f.name

    try:
        results = run_nmap(temp_path)
        output = format_nmap_report_markdown(results)
        assert "ethscan Nmap Vulnerability Report" in output
        assert "Severity Summary" in output
        assert "Detected Services" in output
        assert "Vulnerability Findings" in output
        assert "CVE-2016-6210" in output
        assert "VSFTPD-2.3.4-BACKDOOR" in output
    finally:
        Path(temp_path).unlink()


def test_format_nmap_report_markdown_no_findings():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(EMPTY_NMAP_XML)
        temp_path = f.name

    try:
        results = run_nmap(temp_path)
        output = format_nmap_report_markdown(results)
        assert "No known vulnerabilities matched" in output
    finally:
        Path(temp_path).unlink()


def test_run_nmap_banner_parsing_fallback():
    # Test that banner parsing works when product/version are missing but banner has them
    xml_with_banner_only = """<runscanner version="1.0" scanner="nmap" args="nmap -oX - 192.168.1.1" start="1234567890" nmap_version="7.94" xmloutputversion="1.05">
<scaninfo type="syn" protocol="tcp" numservices="1000" services="1-1000"/>
<host starttime="1234567890" endtime="1234567891">
<status state="up" reason="syn-ack"/>
<address addr="192.168.1.1" addrtype="ipv4"/>
<hostnames/>
<ports>
<port protocol="tcp" portid="22">
<state state="open" reason="syn-ack" reason_ttl="64"/>
<service name="ssh" product="" version="" extrainfo="OpenSSH_7.2p2 protocol 2.0" method="probed" conf="10"/>
</port>
</ports>
</host>
</runscanner>
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(xml_with_banner_only)
        temp_path = f.name

    try:
        results = run_nmap(temp_path)
        findings = results["findings"]
        cve_ids = [f["id"] for f in findings]
        # Should still find OpenSSH vulns via banner parsing
        assert "CVE-2016-6210" in cve_ids or len(findings) > 0
    finally:
        Path(temp_path).unlink()


def test_run_nmap_severity_counts():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(SAMPLE_NMAP_XML)
        temp_path = f.name

    try:
        results = run_nmap(temp_path)
        severity_counts = results["severity_counts"]
        # Should have counts for at least some severities
        total = sum(severity_counts.values())
        assert total == results["finding_count"]
        for sev in ["critical", "high", "medium", "low"]:
            assert sev in severity_counts
    finally:
        Path(temp_path).unlink()