"""Wi-Fi reconnaissance module for ethscan.

Lists nearby Wi-Fi access points (SSID, BSSID, channel, encryption, signal strength).
On Linux, parses /proc/net/wireless and uses iwlist/iw scan output (shell out with
graceful fallback when tools unavailable). On other platforms, reports platform not supported.
"""
from __future__ import annotations

import csv
import io
import json
import platform
import re
import subprocess


def _is_linux() -> bool:
    """Check if running on Linux."""
    return platform.system().lower() == "linux"


def _parse_proc_net_wireless(filepath: str = "/proc/net/wireless") -> list[dict]:
    """Parse /proc/net/wireless for interface status."""
    interfaces: list[dict] = []
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except OSError:
        return interfaces

    # Skip header lines (first 2 lines)
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        # Format: "face | sta- | Quality | link level noise | nwid crypt frag retry misc | beacon | WE"
        # Example: "wlan0: 0000  45.  -45.  -256    0      0   0   0   0        0"
        parts = line.split()
        if len(parts) < 9:
            continue
        iface = parts[0].rstrip(":")
        try:
            status = int(parts[1])
            link_quality = float(parts[2].rstrip("."))
            signal_level = float(parts[3].rstrip("."))
            noise_level = float(parts[4].rstrip("."))
            interfaces.append({
                "interface": iface,
                "status": status,
                "link_quality": link_quality,
                "signal_level": signal_level,
                "noise_level": noise_level,
            })
        except (ValueError, IndexError):
            continue
    return interfaces


def _run_iwlist_scan(interface: str) -> list[dict]:
    """Run iwlist scan on the given interface and parse results."""
    aps: list[dict] = []
    try:
        result = subprocess.run(
            ["iwlist", interface, "scan"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return aps
        output = result.stdout
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return aps

    # Parse iwlist output
    # Cell 01 - Address: 00:11:22:33:44:55
    # ESSID:"MyNetwork"
    # Protocol:IEEE 802.11bgn
    # Mode:Master
    # Frequency:2.412 GHz (Channel 1)
    # Encryption key:on
    # Bit Rates:1 Mb/s; 2 Mb/s; ...
    # Quality=45/70  Signal level=-65 dBm
    cell_pattern = re.compile(r"\d+\s+-\s+Address:\s+([0-9A-Fa-f:]{17})")
    essid_pattern = re.compile(r'ESSID:"([^"]*)"')
    freq_pattern = re.compile(r"Frequency:([\d.]+)\s+GHz\s+\(Channel\s+(\d+)\)")
    channel_pattern = re.compile(r"Channel\s+(\d+)")
    enc_pattern = re.compile(r"Encryption key:(on|off)")
    quality_pattern = re.compile(r"Quality=(\d+)/(\d+)\s+Signal level=(-?\d+)\s*dBm")
    wpa_pattern = re.compile(r"IE:\s+(WPA|WPA2|WPA3)")
    wpa2_pattern = re.compile(r"IE:\s+WPA Version 2")
    wpa3_pattern = re.compile(r"IE:\s+WPA Version 3")

    cells = output.split("Cell ")
    for cell in cells[1:]:  # Skip first split part
        ap = {"bssid": "", "ssid": "", "channel": None, "frequency": None, "encryption": "unknown", "signal_dbm": None, "quality": None}
        lines = cell.split("\n")
        for line in lines:
            line = line.strip()
            m = cell_pattern.search(line)
            if m:
                ap["bssid"] = m.group(1).upper()
            m = essid_pattern.search(line)
            if m:
                ap["ssid"] = m.group(1)
            m = freq_pattern.search(line)
            if m:
                ap["frequency"] = float(m.group(1))
                ap["channel"] = int(m.group(2))
            else:
                m = channel_pattern.search(line)
                if m and ap["channel"] is None:
                    ap["channel"] = int(m.group(1))
            m = enc_pattern.search(line)
            if m:
                ap["encryption"] = "open" if m.group(1) == "off" else "wep"
            m = quality_pattern.search(line)
            if m:
                ap["quality"] = f"{m.group(1)}/{m.group(2)}"
                ap["signal_dbm"] = int(m.group(3))
            m = wpa3_pattern.search(line)
            if m:
                ap["encryption"] = "wpa3"
            elif wpa2_pattern.search(line):
                ap["encryption"] = "wpa2"
            elif wpa_pattern.search(line):
                ap["encryption"] = "wpa"
        if ap["bssid"]:
            aps.append(ap)
    return aps


def _run_iw_scan(interface: str) -> list[dict]:
    """Run iw scan on the given interface and parse results (modern alternative to iwlist)."""
    aps: list[dict] = []
    try:
        result = subprocess.run(
            ["iw", "dev", interface, "scan"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return aps
        output = result.stdout
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return aps

    # Parse iw output (similar structure to iwlist but different format)
    # BSS 00:11:22:33:44:55(on wlan0)
    # TSF: 123456789
    # freq: 2412
    # beacon interval: 100
    # capability: ESS Privacy ShortSlotTime (0x0411)
    # signal: -65.00 dBm
    # SSID: MyNetwork
    # Supported rates: 1.0* 2.0* 5.5* 11.0*
    # DS Parameter set: channel 1
    # RSN: ... (indicates WPA2)
    # WPA: ... (indicates WPA1)
    bss_pattern = re.compile(r"BSS\s+([0-9A-Fa-f:]{17})")
    freq_pattern = re.compile(r"freq:\s+(\d+)")
    signal_pattern = re.compile(r"signal:\s+(-?\d+\.?\d*)\s*dBm")
    ssid_pattern = re.compile(r"SSID:\s+(.+)")
    channel_pattern = re.compile(r"DS Parameter set:\s+channel\s+(\d+)")
    cap_pattern = re.compile(r"capability:\s+(\w+)")
    wpa1_pattern = re.compile(r"WPA:\s+.*")
    wpa2_pattern = re.compile(r"RSN:\s+.*")

    current_ap = None
    for line in output.split("\n"):
        line = line.strip()
        m = bss_pattern.search(line)
        if m:
            if current_ap and current_ap["bssid"]:
                aps.append(current_ap)
            current_ap = {"bssid": m.group(1).upper(), "ssid": "", "channel": None, "frequency": None, "encryption": "unknown", "signal_dbm": None, "quality": None}
            continue
        if not current_ap:
            continue
        m = freq_pattern.search(line)
        if m:
            current_ap["frequency"] = int(m.group(1)) / 1000.0
        m = signal_pattern.search(line)
        if m:
            current_ap["signal_dbm"] = float(m.group(1))
        m = ssid_pattern.search(line)
        if m:
            current_ap["ssid"] = m.group(1)
        m = channel_pattern.search(line)
        if m:
            current_ap["channel"] = int(m.group(1))
        m = cap_pattern.search(line)
        if m:
            caps = m.group(1).lower()
            if "privacy" in caps:
                current_ap["encryption"] = "wep"  # Will be upgraded if WPA found
        if wpa2_pattern.search(line):
            current_ap["encryption"] = "wpa2"
        elif wpa1_pattern.search(line):
            current_ap["encryption"] = "wpa"
    if current_ap and current_ap["bssid"]:
        aps.append(current_ap)
    return aps


def _scan_interface(interface: str) -> list[dict]:
    """Scan a single interface using available tools."""
    # Try iw first (modern), then iwlist (legacy)
    aps = _run_iw_scan(interface)
    if aps:
        return aps
    return _run_iwlist_scan(interface)


def run_wifi(interface: str | None = None) -> dict:
    """Run Wi-Fi reconnaissance.

    Args:
        interface: Optional specific interface to scan. If None, scans all available interfaces.

    Returns:
        Dictionary with scan results including interfaces, access_points, notes, and platform info.
    """
    result = {
        "platform": platform.system(),
        "platform_supported": _is_linux(),
        "interfaces": [],
        "access_points": [],
        "notes": [],
    }

    if not _is_linux():
        result["notes"].append("Platform not supported: Wi-Fi scanning only implemented for Linux.")
        return result

    # Get interface status from /proc/net/wireless
    iface_status = _parse_proc_net_wireless()
    result["interfaces"] = iface_status

    if not iface_status:
        result["notes"].append("No wireless interfaces found in /proc/net/wireless.")
        return result

    # Determine which interfaces to scan
    target_interfaces = []
    if interface:
        # User specified an interface - check if it exists
        iface_names = [i["interface"] for i in iface_status]
        if interface in iface_names:
            target_interfaces = [interface]
        else:
            result["notes"].append(f"Specified interface '{interface}' not found in /proc/net/wireless.")
            return result
    else:
        # Scan all interfaces
        target_interfaces = [i["interface"] for i in iface_status]

    # Scan each interface
    all_aps = []
    for iface in target_interfaces:
        aps = _scan_interface(iface)
        if aps:
            for ap in aps:
                ap["interface"] = iface
            all_aps.extend(aps)
        else:
            result["notes"].append(f"No scan results for interface '{iface}' (tools may be unavailable or require root).")

    result["access_points"] = all_aps

    # Deduplicate by BSSID (keep strongest signal)
    seen: dict[str, dict] = {}
    for ap in all_aps:
        bssid = ap["bssid"]
        if bssid not in seen or (ap["signal_dbm"] is not None and seen[bssid]["signal_dbm"] is not None and ap["signal_dbm"] > seen[bssid]["signal_dbm"]):
            seen[bssid] = ap
    result["access_points"] = list(seen.values())

    return result


def format_wifi_report_json(results: dict) -> str:
    """Format Wi-Fi scan results as JSON."""
    return json.dumps(results, indent=2)


def format_wifi_report_markdown(results: dict) -> str:
    """Format Wi-Fi scan results as Markdown."""
    lines = ["# Wi-Fi Reconnaissance Report", ""]

    # Platform info
    lines.append("## Platform")
    lines.append(f"- **OS:** {results['platform']}")
    lines.append(f"- **Supported:** {'Yes' if results['platform_supported'] else 'No'}")
    lines.append("")

    # Interfaces
    lines.append("## Wireless Interfaces")
    if results["interfaces"]:
        lines.append("| Interface | Status | Link Quality | Signal (dBm) | Noise (dBm) |")
        lines.append("|-----------|--------|--------------|--------------|-------------|")
        for iface in results["interfaces"]:
            lines.append(f"| {iface['interface']} | {iface['status']} | {iface['link_quality']} | {iface['signal_level']} | {iface['noise_level']} |")
    else:
        lines.append("*No wireless interfaces found.*")
    lines.append("")

    # Access Points
    lines.append("## Access Points")
    if results["access_points"]:
        lines.append("| Interface | BSSID | SSID | Channel | Freq (GHz) | Encryption | Signal (dBm) | Quality |")
        lines.append("|-----------|-------|------|---------|------------|------------|--------------|---------|")
        for ap in results["access_points"]:
            ssid = ap["ssid"] if ap["ssid"] else "<hidden>"
            freq = f"{ap['frequency']:.3f}" if ap["frequency"] else "N/A"
            channel = str(ap["channel"]) if ap["channel"] else "N/A"
            signal = str(ap["signal_dbm"]) if ap["signal_dbm"] is not None else "N/A"
            quality = ap["quality"] if ap["quality"] else "N/A"
            lines.append(f"| {ap['interface']} | {ap['bssid']} | {ssid} | {channel} | {freq} | {ap['encryption']} | {signal} | {quality} |")
    else:
        lines.append("*No access points discovered.*")
    lines.append("")

    # Notes
    if results["notes"]:
        lines.append("## Notes")
        for note in results["notes"]:
            lines.append(f"- {note}")

    return "\n".join(lines)


def format_wifi_report_csv(results: dict) -> str:
    """Format Wi-Fi scan results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Platform info
    writer.writerow(["field", "value"])
    writer.writerow(["platform", results.get("platform", "")])
    writer.writerow(["platform_supported", "true" if results.get("platform_supported") else "false"])

    # Interfaces
    writer.writerow([])
    writer.writerow(["interface", "status", "link_quality", "signal_level", "noise_level"])
    for iface in results.get("interfaces", []):
        writer.writerow([
            iface.get("interface", ""),
            iface.get("status", ""),
            iface.get("link_quality", ""),
            iface.get("signal_level", ""),
            iface.get("noise_level", ""),
        ])

    # Access Points
    writer.writerow([])
    writer.writerow(["interface", "bssid", "ssid", "channel", "frequency_ghz", "encryption", "signal_dbm", "quality"])
    for ap in results.get("access_points", []):
        ssid = ap.get("ssid", "") if ap.get("ssid") else "<hidden>"
        freq = f"{ap['frequency']:.3f}" if ap.get("frequency") else "N/A"
        channel = str(ap.get("channel")) if ap.get("channel") else "N/A"
        signal = str(ap.get("signal_dbm")) if ap.get("signal_dbm") is not None else "N/A"
        quality = ap.get("quality", "") if ap.get("quality") else "N/A"
        writer.writerow([
            ap.get("interface", ""),
            ap.get("bssid", ""),
            ssid,
            channel,
            freq,
            ap.get("encryption", ""),
            signal,
            quality,
        ])

    # Notes
    if results.get("notes"):
        writer.writerow([])
        writer.writerow(["note"])
        for note in results["notes"]:
            writer.writerow([note])

    return output.getvalue().rstrip("\r\n")