"""Focused branch-coverage tests for ethscan/nmap.py edge cases."""


from ethscan.nmap import parse_nmap_xml, run_nmap


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
