"""Cross-module consistency contract between ``ethscan.cidr`` and ``ethscan.validate``.

Both commands analyze the same networks and must report identical fields for
every network *except* IPv6 ``/127``, where they intentionally differ:

- ``cidr`` treats the all-zeros host as the subnet-router anycast address
  (RFC 4291) and reports a single usable host (``::1``).
- ``validate`` treats both ``/127`` addresses as usable (RFC 6164) and reports
  two usable hosts (``::`` and ``::1``).

This divergence is deliberate and each side is pinned by its own module tests
(``tests/test_cidr.py`` and ``tests/test_validate.py``). The guards here exist
so a future change cannot silently break the contract in either direction:
they assert the two analyzers agree on every other field/network, and that the
``/127`` difference stays exactly as documented.
"""
from __future__ import annotations

import pytest

from ethscan.cidr import run_cidr
from ethscan.validate import _validate_cidr

# Networks for which cidr and validate must agree on every reported field.
_AGREE_NETWORKS = [
    "10.0.0.0/24",
    "192.168.1.0/31",
    "10.0.0.5/32",
    "10.0.0.0/30",
    "172.16.0.0/12",
    "0.0.0.0/0",
    "2001:db8::/32",
    "2001:db8::/126",
    "2001:db8::5/128",
]

_FIELDS = [
    "network_address",
    "netmask",
    "broadcast_address",
    "wildcard_mask",
    "first_host",
    "last_host",
    "usable_host_count",
    "total_addresses",
    "prefixlen",
    "is_private",
]


@pytest.mark.parametrize("spec", _AGREE_NETWORKS)
def test_cidr_and_validate_agree(spec: str) -> None:
    """The two analyzers report identical fields for non-/127 networks."""
    cidr_net = run_cidr(spec)["network"]
    validate_net = _validate_cidr(spec)["network"]
    for field in _FIELDS:
        assert cidr_net[field] == validate_net[field], (
            f"{spec} field {field!r}: cidr={cidr_net[field]!r} "
            f"validate={validate_net[field]!r}"
        )


def test_ipv6_127_divergence_is_intentional() -> None:
    """cidr (RFC 4291 anycast) and validate (RFC 6164) differ only on /127 hosts."""
    cidr_net = run_cidr("2001:db8::/127")["network"]
    validate_net = _validate_cidr("2001:db8::/127")["network"]

    # cidr: only the second address is usable (first is subnet-router anycast).
    assert cidr_net["usable_host_count"] == 1
    assert cidr_net["first_host"] == "2001:db8::1"
    assert cidr_net["last_host"] == "2001:db8::1"

    # validate: both addresses are usable.
    assert validate_net["usable_host_count"] == 2
    assert validate_net["first_host"] == "2001:db8::"
    assert validate_net["last_host"] == "2001:db8::1"

    # Everything except the usable-host set must still agree.
    for field in _FIELDS:
        if field in ("usable_host_count", "first_host"):
            continue
        assert cidr_net[field] == validate_net[field], (
            f"/127 field {field!r}: cidr={cidr_net[field]!r} "
            f"validate={validate_net[field]!r}"
        )