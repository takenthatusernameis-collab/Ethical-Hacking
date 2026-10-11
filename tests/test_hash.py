"""Tests for the ethscan password hash module."""

import json

from ethscan.hash import (
    MD4_AVAILABLE,
    _compute_hash,
    _compute_md4,
    _compute_md5,
    _compute_ntlm,
    _compute_password_hash,
    _compute_peppered_hash,
    _compute_pbkdf2_hash,
    _compute_sha1,
    _compute_sha256,
    _compute_sha512,
    _hashlib_name,
    _infer_algorithm,
    _normalize_algorithm,
    _normalize_passwords,
    _supported_algorithms,
    format_check_report_json,
    format_check_report_markdown,
    format_hash_report_json,
    format_hash_report_markdown,
    load_passwords_from_file,
    run_check,
    run_hash,
)

# ---------------------------------------------------------------------------
# Algorithm normalization
# ---------------------------------------------------------------------------


def test_normalize_algorithm_md5() -> None:
    assert _normalize_algorithm("md5") == "md5"


def test_normalize_algorithm_case_insensitive() -> None:
    assert _normalize_algorithm("MD5") == "md5"
    assert _normalize_algorithm("SHA-256") == "sha256"
    assert _normalize_algorithm("Sha1") == "sha1"


def test_normalize_algorithm_aliases() -> None:
    assert _normalize_algorithm("sha-1") == "sha1"
    assert _normalize_algorithm("sha-256") == "sha256"
    assert _normalize_algorithm("sha-512") == "sha512"


def test_normalize_algorithm_ntlm() -> None:
    assert _normalize_algorithm("ntlm") == "ntlm"


def test_normalize_algorithm_strips_whitespace() -> None:
    assert _normalize_algorithm("  md5  ") == "md5"


def test_normalize_algorithm_unsupported_raises() -> None:
    try:
        _normalize_algorithm("ripemd160")
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Hashlib name / supported algorithms
# ---------------------------------------------------------------------------


def test_hashlib_name_known() -> None:
    assert _hashlib_name("md5") == "md5"
    assert _hashlib_name("sha256") == "sha256"


def test_hashlib_name_ntlm_returns_none() -> None:
    assert _hashlib_name("ntlm") is None


def test_supported_algorithms_includes_basics() -> None:
    algos = _supported_algorithms()
    for name in ("md5", "sha1", "sha256", "sha512", "ntlm"):
        assert name in algos


# ---------------------------------------------------------------------------
# Password normalization
# ---------------------------------------------------------------------------


def test_normalize_passwords_strips_whitespace() -> None:
    assert _normalize_passwords(["  password  ", ""]) == ["password"]


def test_normalize_passwords_drops_empty() -> None:
    assert _normalize_passwords(["", "x", ""]) == ["x"]


# ---------------------------------------------------------------------------
# Password file loading
# ---------------------------------------------------------------------------


def test_load_passwords_from_file_basic(tmp_path) -> None:
    path = tmp_path / "passwords.txt"
    path.write_text("password\n123456\n", encoding="utf-8")
    assert load_passwords_from_file(str(path)) == ["password", "123456"]


def test_load_passwords_from_file_strips_and_skips_empty(tmp_path) -> None:
    path = tmp_path / "passwords.txt"
    path.write_text("  password  \n\n   \nsecret\n", encoding="utf-8")
    assert load_passwords_from_file(str(path)) == ["password", "secret"]


def test_load_passwords_from_file_empty_file(tmp_path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")
    assert load_passwords_from_file(str(path)) == []


def test_load_passwords_from_file_missing_raises(tmp_path) -> None:
    import pytest

    missing = tmp_path / "does-not-exist.txt"
    with pytest.raises(FileNotFoundError):
        load_passwords_from_file(str(missing))


def test_load_passwords_from_file_preserves_special_characters(tmp_path) -> None:
    path = tmp_path / "passwords.txt"
    path.write_text("p@ss|word\n#notacomment\n", encoding="utf-8")
    assert load_passwords_from_file(str(path)) == ["p@ss|word", "#notacomment"]


# ---------------------------------------------------------------------------
# Individual hash computations
# ---------------------------------------------------------------------------


def test_compute_md5_known_value() -> None:
    assert _compute_md5("password") == "5f4dcc3b5aa765d61d8327deb882cf99"


def test_compute_md5_empty() -> None:
    assert _compute_md5("") == "d41d8cd98f00b204e9800998ecf8427e"


def test_compute_sha1_known_value() -> None:
    assert _compute_sha1("password") == "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"


def test_compute_sha256_known_value() -> None:
    assert (
        _compute_sha256("password")
        == "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    )


def test_compute_sha512_known_value() -> None:
    assert _compute_sha512("password") == (
        "b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb98"
        "0b1d7785e5976ec049b46df5f1326af5a2ea6d103fd07c95385ffab0cacbc86"
    )


def test_compute_hash_dispatch_md5() -> None:
    assert _compute_hash("password", "md5") == _compute_md5("password")


def test_compute_hash_dispatch_sha256() -> None:
    assert _compute_hash("password", "sha256") == _compute_sha256("password")


def test_compute_ntlm_uses_md4_of_utf16le() -> None:
    if not MD4_AVAILABLE:
        try:
            _compute_ntlm("password")
            assert False, "Expected ValueError"
        except ValueError:
            return
    import hashlib

    expected = hashlib.new("md4", "password".encode("utf-16-le")).hexdigest()
    assert _compute_ntlm("password") == expected


def test_compute_md4_unavailable_when_no_openssl() -> None:
    if MD4_AVAILABLE:
        assert _compute_md4("password") is not None
    else:
        try:
            _compute_md4("password")
            assert False, "Expected ValueError"
        except ValueError:
            pass


def test_compute_hash_ntlm_unavailable_when_md4_missing() -> None:
    if MD4_AVAILABLE:
        assert _compute_hash("password", "ntlm") is not None
    else:
        try:
            _compute_hash("password", "ntlm")
            assert False, "Expected ValueError"
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# run_hash
# ---------------------------------------------------------------------------


def test_run_hash_md5_basic() -> None:
    result = run_hash(["password"], "md5")
    assert result["algorithm"] == "md5"
    assert result["passwords_hashed"] == 1
    assert result["results"][0]["password"] == "password"
    assert result["results"][0]["hash"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert result["results"][0]["error"] is None


def test_run_hash_multiple_passwords() -> None:
    result = run_hash(["password", "123456"], "sha256")
    assert result["passwords_hashed"] == 2
    assert len(result["results"]) == 2


def test_run_hash_drops_empty_passwords() -> None:
    result = run_hash(["  ", "password", ""], "md5")
    assert result["passwords_hashed"] == 1
    assert result["results"][0]["password"] == "password"


def test_run_hash_default_algorithm_md5() -> None:
    result = run_hash(["password"])
    assert result["algorithm"] == "md5"


def test_run_hash_normalizes_algorithm() -> None:
    result = run_hash(["password"], "SHA-256")
    assert result["algorithm"] == "sha256"


def test_run_hash_unsupported_algorithm_raises() -> None:
    try:
        run_hash(["password"], "ripemd160")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_run_hash_ntlm_unavailable_note() -> None:
    result = run_hash(["password"], "ntlm")
    if not MD4_AVAILABLE:
        assert result["results"][0]["hash"] is None
        assert result["results"][0]["error"] is not None
        assert any("MD4" in n for n in result["notes"])
    else:
        assert result["results"][0]["hash"] is not None


def test_run_hash_md4_unavailable_note() -> None:
    result = run_hash(["password"], "md4")
    if not MD4_AVAILABLE:
        assert result["results"][0]["hash"] is None
        assert any("MD4" in n for n in result["notes"])
    else:
        assert result["results"][0]["hash"] is not None


def test_run_hash_empty_passwords() -> None:
    result = run_hash([], "md5")
    assert result["passwords_hashed"] == 0
    assert result["results"] == []


def test_run_hash_all_algorithms() -> None:
    for algo in ("md5", "sha1", "sha256", "sha512"):
        result = run_hash(["password"], algo)
        assert result["algorithm"] == algo
        assert result["results"][0]["hash"] is not None


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def test_format_hash_report_json_basic() -> None:
    data = run_hash(["password"], "md5")
    output = format_hash_report_json(data)
    parsed = json.loads(output)
    assert parsed["algorithm"] == "md5"
    assert parsed["passwords_hashed"] == 1
    assert parsed["results"][0]["hash"] == "5f4dcc3b5aa765d61d8327deb882cf99"


def test_format_hash_report_json_empty() -> None:
    data = run_hash([], "md5")
    output = format_hash_report_json(data)
    parsed = json.loads(output)
    assert parsed["passwords_hashed"] == 0
    assert parsed["results"] == []


def test_format_hash_report_json_includes_notes() -> None:
    data = run_hash(["password"], "ntlm")
    output = format_hash_report_json(data)
    parsed = json.loads(output)
    assert "notes" in parsed


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------


def test_format_hash_report_markdown_basic() -> None:
    data = run_hash(["password"], "md5")
    output = format_hash_report_markdown(data)
    assert "Password Hash Report" in output
    assert "md5" in output
    assert "5f4dcc3b5aa765d61d8327deb882cf99" in output
    assert "password" in output


def test_format_hash_report_markdown_empty() -> None:
    data = run_hash([], "md5")
    output = format_hash_report_markdown(data)
    assert "Password Hash Report" in output
    assert "No passwords provided for hashing" in output


def test_format_hash_report_markdown_pipe_escape() -> None:
    data = run_hash(["pass|word"], "md5")
    output = format_hash_report_markdown(data)
    assert "pass\\|word" in output


def test_format_hash_report_markdown_includes_notes() -> None:
    data = run_hash(["password"], "ntlm")
    output = format_hash_report_markdown(data)
    if not MD4_AVAILABLE:
        assert "Notes" in output
        assert "MD4" in output


def test_format_hash_report_markdown_multiple_algorithms() -> None:
    data = run_hash(["password"], "sha256")
    output = format_hash_report_markdown(data)
    assert "sha256" in output
    assert "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8" in output


# ---------------------------------------------------------------------------
# Password check (run_check)
# ---------------------------------------------------------------------------


def test_run_check_md5_match() -> None:
    result = run_check("password", "5f4dcc3b5aa765d61d8327deb882cf99")
    assert result["match"] is True
    assert result["algorithm"] == "md5"
    assert result["computed"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert result["error"] is None
    assert result["password"] == "password"


def test_run_check_md5_mismatch() -> None:
    result = run_check("wrongpass", "5f4dcc3b5aa765d61d8327deb882cf99")
    assert result["match"] is False
    assert result["computed"] != "5f4dcc3b5aa765d61d8327deb882cf99"


def test_run_check_sha256_match() -> None:
    result = run_check(
        "password",
        "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
    )
    assert result["match"] is True
    assert result["algorithm"] == "sha256"


def test_run_check_explicit_algorithm() -> None:
    result = run_check(
        "password",
        "5f4dcc3b5aa765d61d8327deb882cf99",
        algorithm="md5",
    )
    assert result["match"] is True
    assert result["algorithm"] == "md5"


def test_run_check_case_insensitive_digest() -> None:
    result = run_check("password", "5F4DCC3B5AA765D61D8327DEB882CF99")
    assert result["match"] is True


def test_run_check_infers_sha1_from_length() -> None:
    result = run_check("password", "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8")
    assert result["match"] is True
    assert result["algorithm"] == "sha1"


def test_run_check_infers_sha512_from_length() -> None:
    sha512 = (
        "b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb98"
        "0b1d7785e5976ec049b46df5f1326af5a2ea6d103fd07c95385ffab0cacbc86"
    )
    result = run_check("password", sha512)
    assert result["match"] is True
    assert result["algorithm"] == "sha512"


def test_run_check_unknown_length_error() -> None:
    result = run_check("password", "deadbeef")
    assert result["match"] is None
    assert result["error"] is not None
    assert "Could not infer algorithm" in result["error"]


def test_run_check_unsupported_algorithm_error() -> None:
    result = run_check("password", "5f4dcc3b5aa765d61d8327deb882cf99", algorithm="ripemd160")
    assert result["match"] is None
    assert result["error"] is not None


def test_run_check_md4_explicit_when_unavailable() -> None:
    # 32-char digest with explicit md4 algorithm
    result = run_check(
        "password",
        "5f4dcc3b5aa765d61d8327deb882cf99",
        algorithm="md4",
    )
    if not MD4_AVAILABLE:
        assert result["match"] is None
        assert result["error"] is not None
    else:
        assert result["algorithm"] == "md4"


# ---------------------------------------------------------------------------
# Check formatters
# ---------------------------------------------------------------------------


def test_format_check_report_json_basic() -> None:
    result = run_check("password", "5f4dcc3b5aa765d61d8327deb882cf99")
    output = format_check_report_json(result)
    parsed = json.loads(output)
    assert parsed["match"] is True
    assert parsed["algorithm"] == "md5"


def test_format_check_report_json_mismatch() -> None:
    result = run_check("wrongpass", "5f4dcc3b5aa765d61d8327deb882cf99")
    output = format_check_report_json(result)
    parsed = json.loads(output)
    assert parsed["match"] is False


def test_format_check_report_json_error() -> None:
    result = run_check("password", "deadbeef")
    output = format_check_report_json(result)
    parsed = json.loads(output)
    assert parsed["match"] is None
    assert parsed["error"] is not None


def test_format_check_report_markdown_match() -> None:
    result = run_check("password", "5f4dcc3b5aa765d61d8327deb882cf99")
    output = format_check_report_markdown(result)
    assert "Password Check Report" in output
    assert "MATCH" in output
    assert "md5" in output


def test_format_check_report_markdown_mismatch() -> None:
    result = run_check("wrongpass", "5f4dcc3b5aa765d61d8327deb882cf99")
    output = format_check_report_markdown(result)
    assert "MISMATCH" in output


def test_format_check_report_markdown_error() -> None:
    result = run_check("password", "deadbeef")
    output = format_check_report_markdown(result)
    assert "UNKNOWN" in output
    assert "Error" in output


def test_format_check_report_markdown_pipe_escape() -> None:
    result = run_check("pass|word", "5f4dcc3b5aa765d61d8327deb882cf99")
    output = format_check_report_markdown(result)
    assert "pass\\|word" in output


def test_format_check_report_markdown_no_algorithm() -> None:
    result = run_check("password", "deadbeef")
    output = format_check_report_markdown(result)
    # algorithm is None -> no Algorithm line
    assert "**Algorithm:**" not in output


# ---------------------------------------------------------------------------
# Salt / pepper (salted & peppered hashing)
# ---------------------------------------------------------------------------


def test_compute_peppered_hash_known_value() -> None:
    import hmac

    expected = hmac.new(b"secretpepper", b"password", "sha256").hexdigest()
    assert _compute_peppered_hash("password", "sha256", "secretpepper") == expected


def test_compute_peppered_hash_matches_inline() -> None:
    assert (
        _compute_peppered_hash("password", "sha256", "secretpepper")
        == "e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad"
    )


def test_compute_peppered_hash_unsupported_algorithm() -> None:
    try:
        _compute_peppered_hash("password", "ntlm", "pepper")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_compute_password_hash_no_salt_no_pepper() -> None:
    assert _compute_password_hash("password", "md5") == _compute_md5("password")


def test_compute_password_hash_salt_prepends() -> None:
    # salt+password via standard hash
    assert _compute_password_hash("password", "md5", salt="saltvalue") == (
        "e137588f7bb4aa4f0c24592088b82f31"
    )


def test_compute_password_hash_pepper_is_hmac() -> None:
    assert _compute_password_hash("password", "sha256", pepper="secretpepper") == (
        "e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad"
    )


def test_compute_password_hash_salt_and_pepper_combined() -> None:
    # HMAC(pepper, salt+password, sha256)
    assert _compute_password_hash("password", "sha256", salt="saltvalue", pepper="secretpepper") == (
        "862e3f4b4c304c5da6c560833847a8434f110c55c23dfba9bff2982238c8fc59"
    )


def test_compute_password_hash_pepper_unsupported_raises() -> None:
    try:
        _compute_password_hash("password", "ntlm", pepper="pepper")
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# PBKDF2 iterations
# ---------------------------------------------------------------------------


def test_compute_pbkdf2_hash_known_value() -> None:
    import hashlib

    expected = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    assert _compute_pbkdf2_hash("password", "sha256", "saltvalue", 1000) == expected


def test_compute_pbkdf2_hash_unsupported_algorithm() -> None:
    try:
        _compute_pbkdf2_hash("password", "ntlm", "saltvalue", 1000)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_compute_pbkdf2_hash_non_positive_iterations() -> None:
    try:
        _compute_pbkdf2_hash("password", "sha256", "saltvalue", 0)
        assert False, "Expected ValueError"
    except ValueError:
        pass
    try:
        _compute_pbkdf2_hash("password", "sha256", "saltvalue", -5)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_compute_password_hash_iterations() -> None:
    import hashlib

    expected = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    assert _compute_password_hash(
        "password", "sha256", salt="saltvalue", iterations=1000
    ) == expected


def test_compute_password_hash_iterations_requires_salt() -> None:
    try:
        _compute_password_hash("password", "sha256", iterations=1000)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_compute_password_hash_iterations_with_pepper() -> None:
    import hashlib
    import hmac

    pbkdf2_digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    expected = hmac.new(
        b"secretpepper",
        pbkdf2_digest.encode("utf-8"),
        "sha256",
    ).hexdigest()
    assert _compute_password_hash(
        "password",
        "sha256",
        salt="saltvalue",
        pepper="secretpepper",
        iterations=1000,
    ) == expected


def test_compute_password_hash_iterations_ntlm_error() -> None:
    try:
        _compute_password_hash(
            "password", "ntlm", salt="saltvalue", iterations=1000
        )
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_run_hash_with_salt() -> None:
    result = run_hash(["password"], "md5", salt="saltvalue")
    assert result["salt"] is True
    assert result["pepper"] is False
    assert result["results"][0]["salt"] is True
    assert result["results"][0]["pepper"] is False
    assert result["results"][0]["hash"] == "e137588f7bb4aa4f0c24592088b82f31"
    assert any("Salt applied" in n for n in result["notes"])


def test_run_hash_with_pepper() -> None:
    result = run_hash(["password"], "sha256", pepper="secretpepper")
    assert result["salt"] is False
    assert result["pepper"] is True
    assert result["results"][0]["hash"] == "e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad"
    assert any("Pepper applied" in n for n in result["notes"])


def test_run_hash_with_salt_and_pepper() -> None:
    result = run_hash(["password"], "sha256", salt="saltvalue", pepper="secretpepper")
    assert result["salt"] is True
    assert result["pepper"] is True
    assert result["results"][0]["hash"] == "862e3f4b4c304c5da6c560833847a8434f110c55c23dfba9bff2982238c8fc59"
    assert len(result["notes"]) == 2


def test_run_hash_salt_changes_hash_from_unsalted() -> None:
    unsalted = run_hash(["password"], "md5")["results"][0]["hash"]
    salted = run_hash(["password"], "md5", salt="saltvalue")["results"][0]["hash"]
    assert unsalted != salted


def test_run_hash_pepper_not_in_salt_only_mode() -> None:
    result = run_hash(["password"], "sha256", salt="saltvalue")
    assert result["pepper"] is False
    assert result["results"][0]["pepper"] is False


def test_run_hash_pepper_not_in_pepper_only_mode() -> None:
    result = run_hash(["password"], "sha256", pepper="secretpepper")
    assert result["salt"] is False
    assert result["results"][0]["salt"] is False


def test_run_hash_ntlm_with_pepper_graceful_error() -> None:
    result = run_hash(["password"], "ntlm", pepper="pepper")
    assert result["results"][0]["error"] is not None
    assert result["results"][0]["hash"] is None


def test_run_hash_md5_pepper_known_value() -> None:
    assert run_hash(["password"], "md5", pepper="secretpepper")["results"][0]["hash"] == (
        "6f356fbe1394b2277fac9a919342967d"
    )


def test_run_hash_salt_multiple_passwords() -> None:
    result = run_hash(["password", "123456"], "sha256", salt="s")
    assert result["passwords_hashed"] == 2
    assert result["salt"] is True
    assert result["results"][0]["salt"] is True
    assert result["results"][1]["salt"] is True


def test_format_hash_report_json_includes_salt_pepper() -> None:
    data = run_hash(["password"], "sha256", salt="s", pepper="p")
    parsed = json.loads(format_hash_report_json(data))
    assert parsed["salt"] is True
    assert parsed["pepper"] is True
    assert parsed["results"][0]["salt"] is True
    assert parsed["results"][0]["pepper"] is True


def test_format_hash_report_markdown_shows_salt_and_pepper() -> None:
    data = run_hash(["password"], "sha256", salt="s", pepper="p")
    output = format_hash_report_markdown(data)
    assert "Salt" in output
    assert "Pepper" in output


def test_format_hash_report_markdown_no_salt_no_pepper_lines() -> None:
    data = run_hash(["password"], "md5")
    output = format_hash_report_markdown(data)
    assert "**Salt:**" not in output
    assert "**Pepper:**" not in output


# ---------------------------------------------------------------------------
# run_check with salt / pepper
# ---------------------------------------------------------------------------


def test_run_check_with_salt_match() -> None:
    digest = "e137588f7bb4aa4f0c24592088b82f31"
    result = run_check("password", digest, algorithm="md5", salt="saltvalue")
    assert result["match"] is True
    assert result["salt"] is True
    assert result["pepper"] is False


def test_run_check_with_salt_mismatch() -> None:
    digest = "e137588f7bb4aa4f0c24592088b82f31"
    result = run_check("wrongpass", digest, algorithm="md5", salt="saltvalue")
    assert result["match"] is False


def test_run_check_with_pepper_match() -> None:
    digest = "e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad"
    result = run_check(
        "password", digest, algorithm="sha256", pepper="secretpepper"
    )
    assert result["match"] is True
    assert result["pepper"] is True
    assert result["salt"] is False


def test_run_check_with_salt_and_pepper_match() -> None:
    digest = "862e3f4b4c304c5da6c560833847a8434f110c55c23dfba9bff2982238c8fc59"
    result = run_check(
        "password",
        digest,
        algorithm="sha256",
        salt="saltvalue",
        pepper="secretpepper",
    )
    assert result["match"] is True
    assert result["salt"] is True
    assert result["pepper"] is True


def test_run_check_pepper_unsupported_algorithm_error() -> None:
    result = run_check("password", "5f4dcc3b5aa765d61d8327deb882cf99", algorithm="ntlm", pepper="p")
    assert result["match"] is None
    assert result["error"] is not None


def test_format_check_report_json_includes_salt_pepper() -> None:
    digest = "e137588f7bb4aa4f0c24592088b82f31"
    result = run_check("password", digest, algorithm="md5", salt="saltvalue")
    parsed = json.loads(format_check_report_json(result))
    assert parsed["salt"] is True
    assert parsed["pepper"] is False


def test_format_check_report_markdown_shows_salt_and_pepper() -> None:
    digest = "862e3f4b4c304c5da6c560833847a8434f110c55c23dfba9bff2982238c8fc59"
    result = run_check(
        "password",
        digest,
        algorithm="sha256",
        salt="saltvalue",
        pepper="secretpepper",
    )
    output = format_check_report_markdown(result)
    assert "Salt" in output
    assert "Pepper" in output
    assert "MATCH" in output


def test_format_check_report_markdown_no_salt_no_pepper_lines() -> None:
    result = run_check("password", "5f4dcc3b5aa765d61d8327deb882cf99")
    output = format_check_report_markdown(result)
    assert "**Salt:**" not in output
    assert "**Pepper:**" not in output


# ---------------------------------------------------------------------------
# PBKDF2 iterations (run_hash / run_check / formatters)
# ---------------------------------------------------------------------------


def test_run_hash_iterations() -> None:
    import hashlib

    expected = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    result = run_hash(["password"], "sha256", salt="saltvalue", iterations=1000)
    assert result["iterations"] == 1000
    assert result["salt"] is True
    assert result["salt_value"] == "saltvalue"
    assert result["results"][0]["iterations"] == 1000
    assert result["results"][0]["salt_value"] == "saltvalue"
    assert result["results"][0]["hash"] == expected
    assert any("PBKDF2" in n for n in result["notes"])


def test_run_hash_iterations_requires_salt() -> None:
    result = run_hash(["password"], "sha256", iterations=1000)
    assert result["results"][0]["error"] is not None
    assert "PBKDF2" in result["results"][0]["error"]
    assert result["results"][0]["hash"] is None


def test_run_hash_iterations_ntlm_error() -> None:
    result = run_hash(["password"], "ntlm", salt="saltvalue", iterations=1000)
    assert result["results"][0]["error"] is not None
    assert result["results"][0]["hash"] is None


def test_run_hash_iterations_with_pepper() -> None:
    import hashlib
    import hmac

    pbkdf2_digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    expected = hmac.new(
        b"secretpepper",
        pbkdf2_digest.encode("utf-8"),
        "sha256",
    ).hexdigest()
    result = run_hash(
        ["password"],
        "sha256",
        salt="saltvalue",
        pepper="secretpepper",
        iterations=1000,
    )
    assert result["results"][0]["hash"] == expected
    assert result["results"][0]["pepper"] is True
    assert result["results"][0]["iterations"] == 1000


def test_run_hash_iterations_zero_or_negative() -> None:
    for bad in (0, -1):
        result = run_hash(["password"], "sha256", salt="s", iterations=bad)
        assert result["results"][0]["error"] is not None
        assert result["results"][0]["hash"] is None


def test_run_check_iterations_match() -> None:
    import hashlib

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    result = run_check(
        "password",
        digest,
        algorithm="sha256",
        salt="saltvalue",
        iterations=1000,
    )
    assert result["match"] is True
    assert result["iterations"] == 1000
    assert result["salt_value"] == "saltvalue"


def test_run_check_iterations_mismatch() -> None:
    import hashlib

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    result = run_check(
        "wrongpass",
        digest,
        algorithm="sha256",
        salt="saltvalue",
        iterations=1000,
    )
    assert result["match"] is False
    assert result["iterations"] == 1000


def test_run_check_iterations_requires_salt() -> None:
    result = run_check(
        "password",
        "5f4dcc3b5aa765d61d8327deb882cf99",
        algorithm="md5",
        iterations=1000,
    )
    assert result["match"] is None
    assert result["error"] is not None
    assert "PBKDF2" in result["error"]


def test_format_hash_report_json_includes_iterations() -> None:
    data = run_hash(["password"], "sha256", salt="saltvalue", iterations=1000)
    parsed = json.loads(format_hash_report_json(data))
    assert parsed["iterations"] == 1000
    assert parsed["salt_value"] == "saltvalue"
    assert parsed["results"][0]["iterations"] == 1000
    assert parsed["results"][0]["salt_value"] == "saltvalue"


def test_format_hash_report_markdown_shows_iterations() -> None:
    data = run_hash(["password"], "sha256", salt="saltvalue", iterations=1000)
    output = format_hash_report_markdown(data)
    assert "Iterations" in output
    assert "1000" in output
    assert "Salt Value" in output


def test_format_hash_report_markdown_no_iterations_lines() -> None:
    data = run_hash(["password"], "md5")
    output = format_hash_report_markdown(data)
    assert "**Iterations:**" not in output
    assert "**Salt Value:**" not in output


def test_format_check_report_json_includes_iterations() -> None:
    import hashlib

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    result = run_check(
        "password",
        digest,
        algorithm="sha256",
        salt="saltvalue",
        iterations=1000,
    )
    parsed = json.loads(format_check_report_json(result))
    assert parsed["iterations"] == 1000
    assert parsed["salt_value"] == "saltvalue"


def test_format_check_report_markdown_shows_iterations() -> None:
    import hashlib

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    result = run_check(
        "password",
        digest,
        algorithm="sha256",
        salt="saltvalue",
        iterations=1000,
    )
    output = format_check_report_markdown(result)
    assert "Iterations" in output
    assert "1000" in output
    assert "Salt Value" in output
    assert "MATCH" in output


def test_format_check_report_markdown_no_iterations_lines() -> None:
    result = run_check("password", "5f4dcc3b5aa765d61d8327deb882cf99")
    output = format_check_report_markdown(result)
    assert "**Iterations:**" not in output
    assert "**Salt Value:**" not in output
