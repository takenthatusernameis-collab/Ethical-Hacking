"""Tests for the ethscan wifi module."""

import json
import platform
import tempfile
from unittest.mock import patch, MagicMock

from ethscan.wifi import (
    _is_linux,
    _parse_proc_net_wireless,
    _run_iwlist_scan,
    _run_iw_scan,
    _scan_interface,
    run_wifi,
    format_wifi_report_json,
    format_wifi_report_markdown,
)


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------


def test_is_linux() -> None:
    assert isinstance(_is_linux(), bool)


# ---------------------------------------------------------------------------
# /proc/net/wireless parsing
# ---------------------------------------------------------------------------


def test_parse_proc_net_wireless_missing_file(tmp_path) -> None:
    result = _parse_proc_net_wireless("/nonexistent/path")
    assert result == []


def test_parse_proc_net_wireless_empty(tmp_path) -> None:
    content = "Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE\n face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22\n"
    f = tmp_path / "wireless"
    f.write_text(content)
    result = _parse_proc_net_wireless(str(f))
    assert result == []


def test_parse_proc_net_wireless_valid(tmp_path) -> None:
    content = """Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
 wlan0: 0000  45.  -45.  -256    0      0   0   0   0        0
 wlan1: 0000  30.  -60.  -200    0      0   0   0   0        0
"""
    f = tmp_path / "wireless"
    f.write_text(content)
    result = _parse_proc_net_wireless(str(f))
    assert len(result) == 2
    assert result[0]["interface"] == "wlan0"
    assert result[0]["status"] == 0
    assert result[0]["link_quality"] == 45.0
    assert result[0]["signal_level"] == -45.0
    assert result[0]["noise_level"] == -256.0
    assert result[1]["interface"] == "wlan1"


def test_parse_proc_net_wireless_malformed_lines(tmp_path) -> None:
    content = """Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
 wlan0: 0000  45.  -45.  -256    0      0   0   0   0        0
 invalid line
 wlan1: not numbers
"""
    f = tmp_path / "wireless"
    f.write_text(content)
    result = _parse_proc_net_wireless(str(f))
    assert len(result) == 1
    assert result[0]["interface"] == "wlan0"


# ---------------------------------------------------------------------------
# iwlist scan parsing
# ---------------------------------------------------------------------------


def test_run_iwlist_scan_not_found() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _run_iwlist_scan("wlan0")
        assert result == []


def test_run_iwlist_scan_error() -> None:
    mock_result = MagicMock(returncode=1, stdout="", stderr="error")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iwlist_scan("wlan0")
        assert result == []


def test_run_iwlist_scan_valid() -> None:
    output = """wlan0     Scan completed :
          Cell 01 - Address: 00:11:22:33:44:55
                    ESSID:"TestNetwork"
                    Protocol:IEEE 802.11bgn
                    Mode:Master
                    Frequency:2.412 GHz (Channel 1)
                    Encryption key:on
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s
                    Quality=45/70  Signal level=-65 dBm
                    Extra:tsf=0000000000000000
          Cell 02 - Address: AA:BB:CC:DD:EE:FF
                    ESSID:"OpenNetwork"
                    Protocol:IEEE 802.11bgn
                    Mode:Master
                    Frequency:2.437 GHz (Channel 6)
                    Encryption key:off
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s
                    Quality=30/70  Signal level=-80 dBm
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iwlist_scan("wlan0")
        assert len(result) == 2
        assert result[0]["bssid"] == "00:11:22:33:44:55"
        assert result[0]["ssid"] == "TestNetwork"
        assert result[0]["channel"] == 1
        assert result[0]["frequency"] == 2.412
        assert result[0]["encryption"] == "wep"
        assert result[0]["signal_dbm"] == -65
        assert result[0]["quality"] == "45/70"
        assert result[1]["bssid"] == "AA:BB:CC:DD:EE:FF"
        assert result[1]["ssid"] == "OpenNetwork"
        assert result[1]["encryption"] == "open"


def test_run_iwlist_scan_wpa() -> None:
    output = """wlan0     Scan completed :
          Cell 01 - Address: 00:11:22:33:44:55
                    ESSID:"WPANetwork"
                    Protocol:IEEE 802.11bgn
                    Mode:Master
                    Frequency:2.412 GHz (Channel 1)
                    Encryption key:on
                    Quality=45/70  Signal level=-65 dBm
                    IE: WPA Version 1
                    IE: WPA Version 2
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iwlist_scan("wlan0")
        assert len(result) == 1
        assert result[0]["encryption"] == "wpa2"  # WPA2 takes precedence


def test_run_iwlist_scan_wpa3() -> None:
    output = """wlan0     Scan completed :
          Cell 01 - Address: 00:11:22:33:44:55
                    ESSID:"WPA3Network"
                    Protocol:IEEE 802.11bgn
                    Mode:Master
                    Frequency:2.412 GHz (Channel 1)
                    Encryption key:on
                    Quality=45/70  Signal level=-65 dBm
                    IE: WPA Version 3
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iwlist_scan("wlan0")
        assert len(result) == 1
        assert result[0]["encryption"] == "wpa3"


# ---------------------------------------------------------------------------
# iw scan parsing
# ---------------------------------------------------------------------------


def test_run_iw_scan_not_found() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _run_iw_scan("wlan0")
        assert result == []


def test_run_iw_scan_error() -> None:
    mock_result = MagicMock(returncode=1, stdout="", stderr="error")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iw_scan("wlan0")
        assert result == []


def test_run_iw_scan_valid() -> None:
    output = """BSS 00:11:22:33:44:55(on wlan0)
        TSF: 123456789
        freq: 2412
        beacon interval: 100
        capability: ESS Privacy ShortSlotTime (0x0411)
        signal: -65.00 dBm
        SSID: TestNetwork
        Supported rates: 1.0* 2.0* 5.5* 11.0*
        DS Parameter set: channel 1
        RSN:     * Version: 1
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iw_scan("wlan0")
        assert len(result) == 1
        assert result[0]["bssid"] == "00:11:22:33:44:55"
        assert result[0]["ssid"] == "TestNetwork"
        assert result[0]["channel"] == 1
        assert result[0]["frequency"] == 2.412
        assert result[0]["signal_dbm"] == -65.0
        assert result[0]["encryption"] == "wpa2"  # RSN indicates WPA2


def test_run_iw_scan_wpa() -> None:
    output = """BSS 00:11:22:33:44:55(on wlan0)
        freq: 2412
        signal: -65.00 dBm
        SSID: WPANetwork
        DS Parameter set: channel 1
        WPA:     * Version: 1
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iw_scan("wlan0")
        assert len(result) == 1
        assert result[0]["encryption"] == "wpa"


# ---------------------------------------------------------------------------
# _scan_interface - tries iw first, then iwlist
# ---------------------------------------------------------------------------


def test_scan_interface_iw_success() -> None:
    with patch("ethscan.wifi._run_iw_scan", return_value=[{"bssid": "AA:BB:CC:DD:EE:FF", "ssid": "IWNetwork"}]) as mock_iw:
        with patch("ethscan.wifi._run_iwlist_scan") as mock_iwlist:
            result = _scan_interface("wlan0")
            assert len(result) == 1
            assert result[0]["ssid"] == "IWNetwork"
            mock_iw.assert_called_once()
            mock_iwlist.assert_not_called()


def test_scan_interface_iw_fails_iwlist_success() -> None:
    with patch("ethscan.wifi._run_iw_scan", return_value=[]):
        with patch("ethscan.wifi._run_iwlist_scan", return_value=[{"bssid": "00:11:22:33:44:55", "ssid": "IWListNetwork"}]) as mock_iwlist:
            result = _scan_interface("wlan0")
            assert len(result) == 1
            assert result[0]["ssid"] == "IWListNetwork"
            mock_iwlist.assert_called_once()


def test_scan_interface_both_fail() -> None:
    with patch("ethscan.wifi._run_iw_scan", return_value=[]):
        with patch("ethscan.wifi._run_iwlist_scan", return_value=[]):
            result = _scan_interface("wlan0")
            assert result == []


# ---------------------------------------------------------------------------
# run_wifi
# ---------------------------------------------------------------------------


def test_run_wifi_non_linux() -> None:
    with patch("platform.system", return_value="Windows"):
        result = run_wifi()
        assert result["platform"] == "Windows"
        assert result["platform_supported"] is False
        assert "not supported" in result["notes"][0].lower()


def test_run_wifi_linux_no_interfaces() -> None:
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=[]):
        with patch("platform.system", return_value="Linux"):
            result = run_wifi()
            assert result["platform_supported"] is True
            assert result["interfaces"] == []
            assert result["access_points"] == []
            assert "no wireless interfaces" in result["notes"][0].lower()


def test_run_wifi_linux_with_interfaces_no_scan_results() -> None:
    ifaces = [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}]
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=ifaces):
        with patch("ethscan.wifi._scan_interface", return_value=[]):
            with patch("platform.system", return_value="Linux"):
                result = run_wifi()
                assert len(result["interfaces"]) == 1
                assert result["access_points"] == []
                assert "no scan results" in result["notes"][0].lower()


def test_run_wifi_linux_with_scan_results() -> None:
    ifaces = [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}]
    aps = [
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"},
        {"bssid": "AA:BB:CC:DD:EE:FF", "ssid": "Network2", "channel": 6, "frequency": 2.437, "encryption": "open", "signal_dbm": -80, "quality": "30/70"},
    ]
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=ifaces):
        with patch("ethscan.wifi._scan_interface", return_value=aps):
            with patch("platform.system", return_value="Linux"):
                result = run_wifi()
                assert len(result["interfaces"]) == 1
                assert len(result["access_points"]) == 2
                for ap in result["access_points"]:
                    assert ap["interface"] == "wlan0"


def test_run_wifi_specific_interface() -> None:
    ifaces = [
        {"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0},
        {"interface": "wlan1", "status": 0, "link_quality": 30.0, "signal_level": -60.0, "noise_level": -200.0},
    ]
    aps = [{"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"}]
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=ifaces):
        with patch("ethscan.wifi._scan_interface", return_value=aps) as mock_scan:
            with patch("platform.system", return_value="Linux"):
                result = run_wifi(interface="wlan0")
                assert len(result["interfaces"]) == 2
                mock_scan.assert_called_once_with("wlan0")


def test_run_wifi_specific_interface_not_found() -> None:
    ifaces = [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}]
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=ifaces):
        with patch("platform.system", return_value="Linux"):
            result = run_wifi(interface="wlan99")
            assert "not found" in result["notes"][0].lower()


def test_run_wifi_deduplication_by_bssid() -> None:
    ifaces = [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}]
    aps = [
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"},
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -50, "quality": "60/70"},  # Stronger
    ]
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=ifaces):
        with patch("ethscan.wifi._scan_interface", return_value=aps):
            with patch("platform.system", return_value="Linux"):
                result = run_wifi()
                assert len(result["access_points"]) == 1
                assert result["access_points"][0]["signal_dbm"] == -50  # Keeps stronger


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def test_format_wifi_report_json() -> None:
    results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}],
        "access_points": [{"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "Test", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"}],
        "notes": [],
    }
    output = format_wifi_report_json(results)
    parsed = json.loads(output)
    assert parsed["platform"] == "Linux"
    assert len(parsed["access_points"]) == 1


def test_format_wifi_report_markdown_full() -> None:
    results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}],
        "access_points": [{"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "Test", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"}],
        "notes": ["Test note"],
    }
    output = format_wifi_report_markdown(results)
    assert "# Wi-Fi Reconnaissance Report" in output
    assert "## Platform" in output
    assert "Linux" in output
    assert "## Wireless Interfaces" in output
    assert "wlan0" in output
    assert "## Access Points" in output
    assert "00:11:22:33:44:55" in output
    assert "Test" in output
    assert "wpa2" in output
    assert "## Notes" in output
    assert "Test note" in output


def test_format_wifi_report_markdown_no_aps() -> None:
    results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}],
        "access_points": [],
        "notes": ["No APs found"],
    }
    output = format_wifi_report_markdown(results)
    assert "*No access points discovered.*" in output


def test_format_wifi_report_markdown_no_interfaces() -> None:
    results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [],
        "access_points": [],
        "notes": [],
    }
    output = format_wifi_report_markdown(results)
    assert "*No wireless interfaces found.*" in output


def test_format_wifi_report_markdown_hidden_ssid() -> None:
    results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}],
        "access_points": [{"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"}],
        "notes": [],
    }
    output = format_wifi_report_markdown(results)
    assert "<hidden>" in output


def test_format_wifi_report_markdown_missing_optional_fields() -> None:
    results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}],
        "access_points": [{"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "Test", "channel": None, "frequency": None, "encryption": "wpa2", "signal_dbm": None, "quality": None}],
        "notes": [],
    }
    output = format_wifi_report_markdown(results)
    assert "N/A" in output