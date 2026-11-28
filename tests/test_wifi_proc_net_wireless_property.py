"""Property tests locking ``wifi._parse_proc_net_wireless``.

Independent oracle: a data line is parsed iff it has at least 9 whitespace
tokens, the interface token ends with ':', and the next four tokens parse as
int/float (with trailing '.'). Everything else is skipped. Valid interfaces
are built by construction so the expected result is known without re-running
the implementation.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from ethscan.wifi import _parse_proc_net_wireless

_PROPERTY_SEED = 20261128
_HEADER = (
    "Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE\n"
    " face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22\n"
)


def _random_iface(rng: random.Random) -> str:
    return "wlan" + str(rng.randint(0, 9))


def test_valid_lines_parsed_by_construction(tmp_path: Path) -> None:
    rng = random.Random(_PROPERTY_SEED)
    lines = [_HEADER]
    expected = []
    for _ in range(500):
        iface = _random_iface(rng)
        status = rng.randint(0, 65535)
        lq = rng.randint(-100, 100)
        sl = rng.randint(-100, 0)
        nl = rng.randint(-300, -200)
        lines.append(
            f" {iface}: {status:04d}  {lq}.  {sl}.  {nl}    0      0   0   0   0        0\n"
        )
        expected.append(
            {
                "interface": iface,
                "status": status,
                "link_quality": float(lq),
                "signal_level": float(sl),
                "noise_level": float(nl),
            }
        )
    f = tmp_path / "wireless"
    f.write_text("".join(lines))
    result = _parse_proc_net_wireless(str(f))
    assert result == expected


def test_malformed_and_short_lines_skipped(tmp_path: Path) -> None:
    lines = [_HEADER]
    # short lines
    for _ in range(200):
        lines.append("wlan0: 0000  45.\n")
    # unparseable numbers
    for _ in range(200):
        lines.append("wlan0: not_a_number  45.  -45.  -256    0      0   0   0   0        0\n")
    f = tmp_path / "wireless"
    f.write_text("".join(lines))
    result = _parse_proc_net_wireless(str(f))
    assert result == []


def test_nonexistent_returns_empty() -> None:
    assert _parse_proc_net_wireless("/nonexistent/path/does/not/exist") == []


@pytest.mark.parametrize("bad", [b"\xff\xfe", b"\x00"])
def test_binary_handled(tmp_path: Path, bad: bytes) -> None:
    f = tmp_path / "wireless"
    f.write_bytes(
        b"Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE\n"
        b" face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22\n"
        + bad + b"\n"
    )
    # must not raise
    _parse_proc_net_wireless(str(f))
