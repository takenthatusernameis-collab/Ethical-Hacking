#!/usr/bin/env python3
"""Independent oracle verification for ethscan.dnssec pure parsers.

This script verifies the pure parser functions in ethscan.dnssec against
stdlib oracles over a hostile input matrix.

Functions verified:
- _get_parent_zone
- _parse_dns_name
- _parse_dnskey_response
- _parse_ds_response

The script runs silently on success, prints mismatches on failure, and
exits with non-zero code if any oracle mismatch is found.
"""

from __future__ import annotations

import random
import struct
import sys

from ethscan.dnssec import (
    _get_parent_zone,
    _parse_dns_name,
    _parse_dnskey_response,
    _parse_ds_response,
)

# ──────────────────────────────────────────────────────────────────────────────
# Oracle implementations using stdlib only
# ──────────────────────────────────────────────────────────────────────────────

def oracle_get_parent_zone(domain: str) -> str:
    """Oracle for _get_parent_zone using stdlib only."""
    labels = domain.strip().rstrip(".").split(".")
    if len(labels) <= 1:
        return "."
    return ".".join(labels[1:]) + "."


def oracle_parse_dns_name(data: bytes, offset: int) -> tuple[str, int]:
    """Oracle for _parse_dns_name using stdlib only."""
    labels: list[str] = []
    jumped = False
    end_offset = offset
    seen = set()

    while True:
        if offset >= len(data):
            break
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                offset += 2
                break
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if pointer in seen or pointer >= len(data):
                offset += 2
                break
            seen.add(pointer)
            if not jumped:
                end_offset = offset + 2
                jumped = True
            offset = pointer
            continue
        if length & 0xC0 != 0:
            offset += 1
            break
        offset += 1
        if offset + length > len(data):
            break
        labels.append(data[offset:offset + length].decode("ascii", errors="replace"))
        offset += length

    if not jumped:
        end_offset = offset
    return ".".join(labels), end_offset


def oracle_parse_dnskey_response(data: bytes, domain: str) -> dict[str, object]:
    """Oracle for _parse_dnskey_response using stdlib only."""
    result: dict[str, object] = {
        "success": False,
        "keys": [],
        "error": None,
    }
    if len(data) < 12:
        result["error"] = "response too short"
        return result

    try:
        struct.unpack(">H", data[0:2])[0]
        flags = struct.unpack(">H", data[2:4])[0]
    except struct.error:
        result["error"] = "response too short"
        return result

    response_code = flags & 0x000F
    if response_code != 0:
        result["error"] = f"response code {response_code}"
        return result

    try:
        question_count = struct.unpack(">H", data[4:6])[0]
        answer_count = struct.unpack(">H", data[6:8])[0]
    except struct.error:
        result["error"] = "response too short"
        return result

    offset = 12
    for _ in range(question_count):
        _, offset = oracle_parse_dns_name(data, offset)
        offset += 4

    keys = []
    for _ in range(answer_count):
        name, offset = oracle_parse_dns_name(data, offset)
        if offset + 10 > len(data):
            break
        try:
            record_type = struct.unpack(">H", data[offset:offset + 2])[0]
        except struct.error:
            break
        offset += 2
        offset += 2  # class
        offset += 4  # ttl
        try:
            rdlength = struct.unpack(">H", data[offset:offset + 2])[0]
        except struct.error:
            break
        offset += 2

        if record_type == 48:  # DNSKEY_QTYPE
            if offset + 4 > len(data):
                break
            try:
                key_flags = struct.unpack(">H", data[offset:offset + 2])[0]
            except struct.error:
                break
            offset += 2
            if offset >= len(data):
                break
            protocol = data[offset]
            offset += 1
            if offset >= len(data):
                break
            algorithm = data[offset]
            offset += 1
            key_data = data[offset:offset + rdlength - 4] if rdlength >= 4 else b""
            offset += rdlength - 4

            # We can't compute key_tag without dnspython, so leave as None
            keys.append({
                "name": name,
                "flags": key_flags,
                "protocol": protocol,
                "algorithm": algorithm,
                "algorithm_name": f"Unknown({algorithm})",
                "key_tag": None,
                "key_data": key_data.hex() if key_data else "",
            })

    result["success"] = True
    result["keys"] = keys
    return result


def oracle_parse_ds_response(data: bytes, domain: str) -> dict[str, object]:
    """Oracle for _parse_ds_response using stdlib only."""
    result: dict[str, object] = {
        "success": False,
        "records": [],
        "error": None,
    }
    if len(data) < 12:
        result["error"] = "response too short"
        return result

    try:
        struct.unpack(">H", data[0:2])[0]
        flags = struct.unpack(">H", data[2:4])[0]
    except struct.error:
        result["error"] = "response too short"
        return result

    response_code = flags & 0x000F
    if response_code != 0:
        result["error"] = f"response code {response_code}"
        return result

    try:
        question_count = struct.unpack(">H", data[4:6])[0]
        answer_count = struct.unpack(">H", data[6:8])[0]
    except struct.error:
        result["error"] = "response too short"
        return result

    offset = 12
    for _ in range(question_count):
        _, offset = oracle_parse_dns_name(data, offset)
        offset += 4

    records = []
    for _ in range(answer_count):
        name, offset = oracle_parse_dns_name(data, offset)
        if offset + 10 > len(data):
            break
        try:
            record_type = struct.unpack(">H", data[offset:offset + 2])[0]
        except struct.error:
            break
        offset += 2
        offset += 2  # class
        offset += 4  # ttl
        try:
            rdlength = struct.unpack(">H", data[offset:offset + 2])[0]
        except struct.error:
            break
        offset += 2

        if record_type == 43:  # DS_QTYPE
            if offset + 4 > len(data):
                break
            try:
                key_tag = struct.unpack(">H", data[offset:offset + 2])[0]
            except struct.error:
                break
            offset += 2
            if offset >= len(data):
                break
            algorithm = data[offset]
            offset += 1
            if offset >= len(data):
                break
            digest_type = data[offset]
            offset += 1
            digest = data[offset:offset + rdlength - 4] if rdlength >= 4 else b""
            offset += rdlength - 4

            records.append({
                "name": name,
                "key_tag": key_tag,
                "algorithm": algorithm,
                "algorithm_name": f"Unknown({algorithm})",
                "digest_type": digest_type,
                "digest_type_name": f"Unknown({digest_type})",
                "digest": digest.hex() if digest else "",
            })

    result["success"] = True
    result["records"] = records
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Hostile input generators
# ──────────────────────────────────────────────────────────────────────────────

def generate_domains() -> list[str]:
    """Generate domain names for _get_parent_zone."""
    return [
        "", "   ", "example.com", "sub.example.com", "a.b.c.d.example.com",
        "com", ".", "..", "example.", "example.com.", "a.example.com.",
        "xn--bcher-kva.ch", "localhost", "a", "a.b", "a.b.c",
        "very.long.domain.name.with.many.labels.example.com",
    ]


def generate_dns_name_data() -> list[tuple[bytes, int]]:
    """Generate hostile data for _parse_dns_name."""
    test_cases = []

    # Simple names
    test_cases.append((b"\x07example\x03com\x00", 0))
    test_cases.append((b"\x03www\x07example\x03com\x00", 0))
    test_cases.append((b"\x00", 0))  # root
    test_cases.append((b"\x01a\x00", 0))

    # Compression pointers
    # Pointer to offset 0 (root) - would be \xc0\x00 but that's invalid
    # Valid pointer: \xc0\x0c (points to offset 12)
    data = b"\x07example\x03com\x00\xc0\x0c"
    test_cases.append((data, 0))  # Parse first name, then pointer
    test_cases.append((data, 12))  # Parse from pointer

    # Multiple labels with pointer
    data = b"\x03www\x07example\x03com\x00\x02ns\xc0\x00"
    test_cases.append((data, 0))
    test_cases.append((data, 13))

    # Self-referential pointer (should break)
    data = b"\x03foo\xc0\x03"
    test_cases.append((data, 0))

    # Pointer to out of bounds
    data = b"\x03foo\xc0\xff"
    test_cases.append((data, 0))

    # Invalid label type (neither 0 nor compression nor normal)
    data = b"\x80\x00"  # 0x80 & 0xC0 != 0xC0, but not 0
    test_cases.append((data, 0))

    # Truncated data
    test_cases.append((b"\x07example", 0))
    test_cases.append((b"\x07example\x03", 0))

    # Length exceeds remaining data
    test_cases.append((b"\x10" + b"a" * 5, 0))

    # Very long label
    test_cases.append((bytes([100]) + b"a" * 100 + b"\x00", 0))

    # Offset at end
    test_cases.append((b"\x03com\x00", 4))

    return test_cases


def generate_dnskey_responses() -> list[tuple[bytes, str]]:
    """Generate hostile DNSKEY responses."""
    test_cases = []

    # Too short
    test_cases.append((b"", "example.com"))
    test_cases.append((b"\x00" * 11, "example.com"))

    # Valid header with response code != 0
    # Header: ID=1, Flags=0x8003 (NXDOMAIN), QD=1, AN=0, NS=0, AR=0
    header = struct.pack(">HHHHHH", 1, 0x8003, 1, 0, 0, 0)
    question = b"\x07example\x03com\x00\x00\x30\x00\x01"  # example.com DNSKEY IN
    test_cases.append((header + question, "example.com"))

    # Valid header, response code 0, no answers
    header = struct.pack(">HHHHHH", 1, 0x8180, 1, 0, 0, 0)
    test_cases.append((header + question, "example.com"))

    # Valid header with one DNSKEY answer
    # Flags: 0x8180 (standard response), QD=1, AN=1
    header = struct.pack(">HHHHHH", 1, 0x8180, 1, 1, 0, 0)
    # Question
    question = b"\x07example\x03com\x00\x00\x30\x00\x01"
    # Answer: name=example.com (pointer to question), type=48, class=1, ttl=3600, rdlength=20
    # Name pointer to offset 12
    name_ptr = b"\xc0\x0c"
    answer_header = struct.pack(">HHIH", 48, 1, 3600, 20)
    # RDATA: flags=257 (KSK), protocol=3, algorithm=8 (RSASHA256), key_data=16 bytes
    rdata = struct.pack(">HBB", 257, 3, 8) + b"\x00" * 16
    test_cases.append((header + question + name_ptr + answer_header + rdata, "example.com"))

    # Multiple DNSKEY answers
    header = struct.pack(">HHHHHH", 1, 0x8180, 1, 2, 0, 0)
    rdata2 = struct.pack(">HBB", 256, 3, 13) + b"\x00" * 32  # ECDSAP256SHA256
    test_cases.append((header + question + name_ptr + answer_header + rdata + name_ptr + answer_header + rdata2, "example.com"))

    # Truncated RDATA
    rdata_short = struct.pack(">HBB", 257, 3, 8)  # only 4 bytes, no key_data
    answer_header_short = struct.pack(">HHIH", 48, 1, 3600, 4)
    test_cases.append((header + question + name_ptr + answer_header_short + rdata_short, "example.com"))

    # Wrong record type (should be skipped)
    header = struct.pack(">HHHHHH", 1, 0x8180, 1, 1, 0, 0)
    answer_header_a = struct.pack(">HHIH", 1, 1, 3600, 4)  # A record
    rdata_a = b"\x7f\x00\x00\x01"
    test_cases.append((header + question + name_ptr + answer_header_a + rdata_a, "example.com"))

    # Very long response
    long_header = struct.pack(">HHHHHH", 1, 0x8180, 1, 10, 0, 0)
    long_data = long_header + question
    for _ in range(10):
        long_data += name_ptr + answer_header + rdata
    test_cases.append((long_data, "example.com"))

    # Malformed: answer count says 1 but data ends early
    test_cases.append((header + question + name_ptr + answer_header, "example.com"))

    # Non-ASCII in name (should be replaced)
    question_utf8 = b"\x03\xc3\xa9\x03com\x00\x00\x30\x00\x01"
    test_cases.append((header + question_utf8 + name_ptr + answer_header + rdata, "example.com"))

    return test_cases


def generate_ds_responses() -> list[tuple[bytes, str]]:
    """Generate hostile DS responses."""
    test_cases = []

    # Too short
    test_cases.append((b"", "example.com"))
    test_cases.append((b"\x00" * 11, "example.com"))

    # Valid header with response code != 0
    header = struct.pack(">HHHHHH", 1, 0x8003, 1, 0, 0, 0)
    question = b"\x07example\x03com\x00\x00\x2b\x00\x01"  # example.com DS IN
    test_cases.append((header + question, "example.com"))

    # Valid header, response code 0, no answers
    header = struct.pack(">HHHHHH", 1, 0x8180, 1, 0, 0, 0)
    test_cases.append((header + question, "example.com"))

    # Valid header with one DS answer
    header = struct.pack(">HHHHHH", 1, 0x8180, 1, 1, 0, 0)
    question = b"\x07example\x03com\x00\x00\x2b\x00\x01"
    name_ptr = b"\xc0\x0c"
    answer_header = struct.pack(">HHIH", 43, 1, 3600, 20)
    # RDATA: key_tag=12345, algorithm=8, digest_type=2, digest=16 bytes
    rdata = struct.pack(">HBB", 12345, 8, 2) + b"\x00" * 16
    test_cases.append((header + question + name_ptr + answer_header + rdata, "example.com"))

    # Multiple DS answers
    header = struct.pack(">HHHHHH", 1, 0x8180, 1, 2, 0, 0)
    rdata2 = struct.pack(">HBB", 54321, 13, 4) + b"\x00" * 32  # algorithm=13, digest_type=4
    test_cases.append((header + question + name_ptr + answer_header + rdata + name_ptr + answer_header + rdata2, "example.com"))

    # Truncated RDATA
    rdata_short = struct.pack(">HBB", 12345, 8, 2)  # only 4 bytes
    answer_header_short = struct.pack(">HHIH", 43, 1, 3600, 4)
    test_cases.append((header + question + name_ptr + answer_header_short + rdata_short, "example.com"))

    # Wrong record type
    header = struct.pack(">HHHHHH", 1, 0x8180, 1, 1, 0, 0)
    answer_header_a = struct.pack(">HHIH", 1, 1, 3600, 4)
    rdata_a = b"\x7f\x00\x00\x01"
    test_cases.append((header + question + name_ptr + answer_header_a + rdata_a, "example.com"))

    # Very long
    long_header = struct.pack(">HHHHHH", 1, 0x8180, 1, 10, 0, 0)
    long_data = long_header + question
    for _ in range(10):
        long_data += name_ptr + answer_header + rdata
    test_cases.append((long_data, "example.com"))

    # Malformed
    test_cases.append((header + question + name_ptr + answer_header, "example.com"))

    return test_cases


# ──────────────────────────────────────────────────────────────────────────────
# Verification functions
# ──────────────────────────────────────────────────────────────────────────────

def verify_get_parent_zone() -> list[tuple[str, str, str]]:
    """Verify _get_parent_zone against oracle."""
    mismatches = []
    domains = generate_domains()

    rng = random.Random(20261126)
    for _ in range(1000):
        domain = rng.choice(domains) + "." + ".".join(rng.choices(["a", "b", "c", "example", "test", "com", "net", "org"], k=rng.randint(0, 5)))
        domains.append(domain)

    for domain in domains:
        try:
            our_result = _get_parent_zone(domain)
        except Exception as e:
            mismatches.append((domain, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_get_parent_zone(domain)

        if our_result != oracle_result:
            mismatches.append((domain, our_result, oracle_result))

    return mismatches


def verify_parse_dns_name() -> list[tuple[str, tuple, tuple]]:
    """Verify _parse_dns_name against oracle."""
    mismatches = []
    test_cases = generate_dns_name_data()

    for data, offset in test_cases:
        try:
            our_result = _parse_dns_name(data, offset)
        except Exception as e:
            mismatches.append((f"data={data!r}, offset={offset}", f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_parse_dns_name(data, offset)

        if our_result != oracle_result:
            mismatches.append((f"data={data!r}, offset={offset}", our_result, oracle_result))

    return mismatches


def verify_parse_dnskey_response() -> list[tuple[str, dict, dict]]:
    """Verify _parse_dnskey_response against oracle."""
    mismatches = []
    test_cases = generate_dnskey_responses()

    for data, domain in test_cases:
        try:
            our_result = _parse_dnskey_response(data, domain)
        except Exception as e:
            mismatches.append((f"data={data!r}, domain={domain!r}", f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_parse_dnskey_response(data, domain)

        # Compare key fields
        if our_result.get("success") != oracle_result.get("success"):
            mismatches.append((f"data={data!r}, domain={domain!r}", dict(our_result), dict(oracle_result)))
            continue
        if our_result.get("error") != oracle_result.get("error"):
            mismatches.append((f"data={data!r}, domain={domain!r}", dict(our_result), dict(oracle_result)))
            continue

        our_keys = our_result.get("keys") or []
        oracle_keys = oracle_result.get("keys") or []
        if len(our_keys) != len(oracle_keys):
            mismatches.append((f"data={data!r}, domain={domain!r}", dict(our_result), dict(oracle_result)))
            continue
        for i, (our_key, oracle_key) in enumerate(zip(our_keys, oracle_keys)):
            for field in ["name", "flags", "protocol", "algorithm", "key_data"]:
                if our_key.get(field) != oracle_key.get(field):
                    mismatches.append((f"data={data!r}, domain={domain!r}, key={i}", dict(our_result), dict(oracle_result)))
                    break

    return mismatches


def verify_parse_ds_response() -> list[tuple[str, dict, dict]]:
    """Verify _parse_ds_response against oracle."""
    mismatches = []
    test_cases = generate_ds_responses()

    for data, domain in test_cases:
        try:
            our_result = _parse_ds_response(data, domain)
        except Exception as e:
            mismatches.append((f"data={data!r}, domain={domain!r}", f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_parse_ds_response(data, domain)

        if our_result.get("success") != oracle_result.get("success"):
            mismatches.append((f"data={data!r}, domain={domain!r}", dict(our_result), dict(oracle_result)))
            continue
        if our_result.get("error") != oracle_result.get("error"):
            mismatches.append((f"data={data!r}, domain={domain!r}", dict(our_result), dict(oracle_result)))
            continue

        our_recs = our_result.get("records") or []
        oracle_recs = oracle_result.get("records") or []
        if len(our_recs) != len(oracle_recs):
            mismatches.append((f"data={data!r}, domain={domain!r}", dict(our_result), dict(oracle_result)))
            continue
        for i, (our_rec, oracle_rec) in enumerate(zip(our_recs, oracle_recs)):
            for field in ["name", "key_tag", "algorithm", "digest_type", "digest"]:
                if our_rec.get(field) != oracle_rec.get(field):
                    mismatches.append((f"data={data!r}, domain={domain!r}, rec={i}", dict(our_result), dict(oracle_result)))
                    break

    return mismatches


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    """Run all verifications. Returns 0 on success, 1 on mismatch."""
    all_mismatches = []

    print("Verifying _get_parent_zone...", file=sys.stderr)
    mismatches = verify_get_parent_zone()
    if mismatches:
        all_mismatches.extend([("_get_parent_zone",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying _parse_dns_name...", file=sys.stderr)
    mismatches = verify_parse_dns_name()
    if mismatches:
        all_mismatches.extend([("_parse_dns_name",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying _parse_dnskey_response...", file=sys.stderr)
    mismatches = verify_parse_dnskey_response()
    if mismatches:
        all_mismatches.extend([("_parse_dnskey_response",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying _parse_ds_response...", file=sys.stderr)
    mismatches = verify_parse_ds_response()
    if mismatches:
        all_mismatches.extend([("_parse_ds_response",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    if all_mismatches:
        print(f"\n=== TOTAL MISMATCHES: {len(all_mismatches)} ===", file=sys.stderr)
        for func, inp, ours, oracle in all_mismatches[:20]:
            print(f"  {func}({inp!r}) => ours={ours!r}, oracle={oracle!r}", file=sys.stderr)
        if len(all_mismatches) > 20:
            print(f"  ... and {len(all_mismatches) - 20} more", file=sys.stderr)
        return 1

    print("\n=== ALL VERIFICATIONS PASSED ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    import random
    sys.exit(main())