"""Focused branch-coverage tests for ethscan/nmap.py edge cases."""

from typing import cast

from ethscan.nmap import (
    NmapResult,
    format_nmap_report_markdown,
    parse_nmap_xml,
    run_nmap,
)


def _host_xml(inner: str) -> str:
    return (
        '<?xml version="1.0"?>'
        '<nmaprun scanner="nmap">'
        f"<host>{inner}</host>"
        "</nmaprun>"
    )


# --- 138->157: port element without a service child ---


def test_parse_port_without_service_element_uses_empty_banner():
    """<port> with only <state>: service_elem is None, banner stays empty."""
    xml = _host_xml(
        '<address addr="10.0.0.1" addrtype="ipv4"/>'
        '<ports><port portid="22" protocol="tcp">'
        '<state state="open" reason="syn-ack"/></port></ports>'
    )
    hosts = parse_nmap_xml(xml)
    assert len(hosts) == 1
    port = hosts[0]["ports"][0]
    assert port["port"] == 22
    assert port["service_name"] == ""
    assert port["product"] == ""
    assert port["banner"] == ""


# --- 186->184: hostname with an empty name ---


def test_parse_host_hostname_with_empty_name_is_skipped():
    """<hostname name="">: the false branch of ``if name:`` skips the append."""
    xml = _host_xml(
        '<address addr="10.0.0.1" addrtype="ipv4"/>'
        '<hostnames><hostname name="" type="PTR"/><hostname name="box" type="PTR"/></hostnames>'
        '<ports></ports>'
    )
    hosts = parse_nmap_xml(xml)
    assert hosts[0]["hostnames"] == ["box"]


# --- 194->200: host element without a ports child ---


def test_parse_host_without_ports_element():
    """<host> with no <ports>: ports_elem is None, ports defaults to []."""
    xml = _host_xml(
        '<address addr="10.0.0.1" addrtype="ipv4"/>'
        '<status state="up" reason="arp-response"/>'
    )
    hosts = parse_nmap_xml(xml)
    assert len(hosts) == 1
    assert hosts[0]["ports"] == []


# --- run_nmap integration: the three parser branches through a file ---


def test_run_nmap_exercises_parser_branch_gaps(tmp_path):
    xml = (
        '<?xml version="1.0"?>'
        '<nmaprun scanner="nmap">'
        '<host>'
        '<address addr="10.0.0.1" addrtype="ipv4"/>'
        '<hostnames><hostname name="" type="PTR"/><hostname name="box" type="PTR"/></hostnames>'
        '<status state="up" reason="arp-response"/>'
        '<ports>'
        '<port portid="22" protocol="tcp"><state state="open" reason="syn-ack"/></port>'
        '<port portid="80" protocol="tcp"><state state="open" reason="syn-ack"/>'
        '<service name="http" product="nginx" version="1.2.3"/></port>'
        '</ports>'
        '</host>'
        '</nmaprun>'
    )
    path = tmp_path / "scan.xml"
    path.write_text(xml)
    results = run_nmap(str(path))
    assert results["hosts_scanned"] == 1
    assert results["total_open_ports"] == 2
    assert results["services"][0]["service_name"] == ""
    assert results["services"][0]["banner"] == ""
    assert results["services"][1]["product"] == "nginx"
    assert results["severity_counts"] == {"critical": 0, "high": 0, "medium": 0, "low": 0}


# --- 359->361 / 362->364: service finding with port and host in markdown detail ---


def test_nmap_markdown_detail_renders_port_and_host():
    """A service-kind finding with port and host takes the true branches
    (359->360 and 362->363)."""
    findings = [
        {
            "kind": "service",
            "id": "test-svc",
            "severity": "medium",
            "title": "Test service",
            "description": "d",
            "product": "nginx",
            "version": "1.2.3",
            "port": 80,
            "host": "10.0.0.1",
        }
    ]
    data: NmapResult = cast(
        NmapResult,
        {
            "input_file": "scan.xml",
            "hosts_scanned": 1,
            "total_ports_scanned": 1,
            "total_open_ports": 1,
            "services_detected": 1,
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "services": [],
            "findings": findings,
            "notes": [],
        },
    )
    md = format_nmap_report_markdown(data)
    assert "(port 80)" in md
    assert "[10.0.0.1]" in md


def test_nmap_markdown_detail_missing_port_and_host():
    """A service-kind finding with a None port and a missing host takes the
    false branches (359->361 and 362->364)."""
    findings = [
        {"kind": "service", "id": "no-port", "port": None, "host": "10.0.0.1"},
        {"kind": "service", "id": "no-host", "port": 80, "host": None},
    ]
    data: NmapResult = cast(
        NmapResult,
        {
            "input_file": "scan.xml",
            "hosts_scanned": 1,
            "total_ports_scanned": 2,
            "total_open_ports": 2,
            "services_detected": 2,
            "finding_count": 2,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "services": [],
            "findings": findings,
            "notes": [],
        },
    )
    md = format_nmap_report_markdown(data)
    assert "no-port" in md
    assert "no-host" in md
