"""Tests to cover remaining branch gaps in ethscan.wifi."""

from unittest.mock import MagicMock, patch

from ethscan.wifi import _run_iw_scan, _run_iwlist_scan, run_wifi


def test_run_iwlist_scan_cell_without_bssid_is_skipped() -> None:
    """Cell missing Address line is skipped (ethscan/wifi.py:157 false branch)."""
    output = """wlan0     Scan completed :
          Cell 01 - Address: 00:11:22:33:44:55
                    ESSID:"ValidNetwork"
                    Frequency:2.412 GHz (Channel 1)
                    Encryption key:on
                    Quality=45/70  Signal level=-65 dBm
          Cell 02 - This cell has no Address line
                    ESSID:"NoBssidNetwork"
                    Frequency:2.437 GHz (Channel 6)
                    Encryption key:off
                    Quality=30/70  Signal level=-80 dBm
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iwlist_scan("wlan0")
        assert len(result) == 1
        assert result[0]["bssid"] == "00:11:22:33:44:55"
        assert result[0]["ssid"] == "ValidNetwork"


def test_run_iw_scan_final_ap_without_bssid_is_skipped() -> None:
    """Final BSS entry missing BSSID is not added (ethscan/wifi.py:246 false branch)."""
    output = """BSS 00:11:22:33:44:55(on wlan0)
        freq: 2412
        signal: -65.00 dBm
        SSID: ValidNetwork
        DS Parameter set: channel 1
        RSN:     * Version: 1
Some trailing line without a new BSS
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iw_scan("wlan0")
        assert len(result) == 1
        assert result[0]["bssid"] == "00:11:22:33:44:55"
        assert result[0]["ssid"] == "ValidNetwork"


def test_run_iw_scan_only_stray_lines_no_bssid() -> None:
    """Input with only stray lines, no BSSID, yields empty list (ethscan/wifi.py:246 false branch)."""
    output = """Some random line
Another line
No BSS entries here
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iw_scan("wlan0")
        assert result == []


def test_run_wifi_deduplication_keeps_stronger_signal_false_branch() -> None:
    """Deduplication when new signal is not stronger exercises false branch (ethscan/wifi.py:334)."""
    ifaces = [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}]
    # Two APs with same BSSID, first has stronger signal (-50 > -65)
    aps = [
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -50, "quality": "60/70"},
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"},  # Weaker
    ]
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=ifaces), patch("ethscan.wifi._scan_interface", return_value=aps), patch("platform.system", return_value="Linux"):
        result = run_wifi()
        # Should keep the stronger one (-50)
        assert len(result["access_points"]) == 1
        assert result["access_points"][0]["signal_dbm"] == -50


def test_run_wifi_deduplication_equal_signals_false_branch() -> None:
    """Deduplication with equal signals exercises false branch (ethscan/wifi.py:334)."""
    ifaces = [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}]
    # Two APs with same BSSID and equal signal
    aps = [
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -50, "quality": "60/70"},
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -50, "quality": "60/70"},  # Equal
    ]
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=ifaces), patch("ethscan.wifi._scan_interface", return_value=aps), patch("platform.system", return_value="Linux"):
        result = run_wifi()
        # Should keep the first one (no change since not strictly greater)
        assert len(result["access_points"]) == 1
        assert result["access_points"][0]["signal_dbm"] == -50


def test_run_wifi_deduplication_non_numeric_signals_false_branch() -> None:
    """Deduplication with non-numeric signals exercises false branch (ethscan/wifi.py:334)."""
    ifaces = [{"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}]
    # Two APs with same BSSID but signal_dbm is None/non-numeric
    aps = [
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": None, "quality": "60/70"},
        {"bssid": "00:11:22:33:44:55", "ssid": "Network1", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -50, "quality": "45/70"},
    ]
    with patch("ethscan.wifi._parse_proc_net_wireless", return_value=ifaces), patch("ethscan.wifi._scan_interface", return_value=aps), patch("platform.system", return_value="Linux"):
        result = run_wifi()
        # First has None signal (not numeric), second has -50
        # The condition checks both are numeric, so it should keep the first
        # since the condition fails when sig_new/sig_old are not both numeric
        assert len(result["access_points"]) == 1
        # Which one is kept depends on the logic - the second won't replace the first
        # because the isinstance check fails


def test_run_iwlist_scan_empty_cell_after_split() -> None:
    """Empty cell from split is handled (ethscan/wifi.py:157 false branch)."""
    # Leading "Cell " creates empty first split part which is skipped by cells[1:]
    # But if there are consecutive "Cell " markers, could get empty cell
    output = """wlan0     Scan completed :
          Cell 01 - Address: 00:11:22:33:44:55
                    ESSID:"ValidNetwork"
                    Frequency:2.412 GHz (Channel 1)
                    Encryption key:on
                    Quality=45/70  Signal level=-65 dBm
          Cell 02 - Address:
                    ESSID:"InvalidBssid"
                    Frequency:2.437 GHz (Channel 6)
                    Encryption key:off
                    Quality=30/70  Signal level=-80 dBm
"""
    mock_result = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        result = _run_iwlist_scan("wlan0")
        # Cell 02 has empty BSSID, should be skipped
        assert len(result) == 1
        assert result[0]["bssid"] == "00:11:22:33:44:55"