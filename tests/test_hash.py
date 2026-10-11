"""Unit tests for ethscan.hash module."""

import hashlib
import json
import pytest

from ethscan.hash import (
    run_hash,
    format_hash_report_json,
    format_hash_report_markdown,
    _compute_hash,
    ALGORITHMS,
    DEFAULT_ALGORITHMS,
)


class TestComputeHash:
    """Tests for the _compute_hash helper."""

    def test_md5(self):
        assert _compute_hash("password", "md5") == "5f4dcc3b5aa765d61d8327deb882cf99"

    def test_sha1(self):
        assert _compute_hash("password", "sha1") == "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"

    def test_sha256(self):
        assert _compute_hash("password", "sha256") == "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"

    def test_sha512(self):
        expected = "b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb980b1d7785e5976ec049b46df5f1326af5a2ea6d103fd07c95385ffab0cacbc86"
        assert _compute_hash("password", "sha512") == expected

    def test_ntlm(self):
        assert _compute_hash("password", "ntlm") == "8846f7eaee8fb117ad06bdd830b7586c"

    def test_ntlm_unicode(self):
        pwd = "P@ssw0rd"
        # Use our own _md4 implementation for comparison since hashlib.md4 may not be available
        from ethscan.hash import _md4
        expected = _md4(pwd.encode("utf-16le")).hex()
        assert _compute_hash(pwd, "ntlm") == expected


class TestRunHash:
    """Tests for run_hash function."""

    def test_run_hash_default_algorithms(self):
        results = run_hash(["password"])
        assert results["passwords_hashed"] == 1
        assert results["algorithms"] == ["MD5", "SHA-1", "SHA-256", "SHA-512", "NTLM"]
        assert len(results["results"]) == 1
        assert results["results"][0]["password"] == "password"
        assert "MD5" in results["results"][0]["hashes"]
        assert "SHA-1" in results["results"][0]["hashes"]
        assert "SHA-256" in results["results"][0]["hashes"]
        assert "SHA-512" in results["results"][0]["hashes"]
        assert "NTLM" in results["results"][0]["hashes"]

    def test_run_hash_custom_algorithms(self):
        results = run_hash(["password"], algorithms=["md5", "sha256"])
        assert results["algorithms"] == ["MD5", "SHA-256"]
        assert set(results["results"][0]["hashes"].keys()) == {"MD5", "SHA-256"}

    def test_run_hash_multiple_passwords(self):
        results = run_hash(["password", "123456"])
        assert results["passwords_hashed"] == 2
        assert len(results["results"]) == 2
        assert results["results"][0]["password"] == "password"
        assert results["results"][1]["password"] == "123456"

    def test_run_hash_case_insensitive_algorithms(self):
        results = run_hash(["password"], algorithms=["MD5", "Sha256"])
        assert results["algorithms"] == ["MD5", "SHA-256"]

    def test_run_hash_empty_passwords(self):
        results = run_hash([])
        assert results["passwords_hashed"] == 0
        assert results["results"] == []

    def test_run_hash_invalid_algorithm_raises(self):
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            run_hash(["password"], algorithms=["invalid"])

    def test_run_hash_special_characters(self):
        pwd = "P@ssw0rd!#$%"
        results = run_hash([pwd], algorithms=["sha256"])
        assert results["results"][0]["password"] == pwd
        assert "SHA-256" in results["results"][0]["hashes"]


class TestFormatHashReportJson:
    """Tests for JSON formatter."""

    def test_format_json_basic(self):
        results = run_hash(["password"], algorithms=["md5", "sha256"])
        output = format_hash_report_json(results)
        data = json.loads(output)
        assert data["passwords_hashed"] == 1
        assert data["algorithms"] == ["MD5", "SHA-256"]
        assert len(data["results"]) == 1

    def test_format_json_empty(self):
        results = {"passwords_hashed": 0, "algorithms": ["MD5"], "results": []}
        output = format_hash_report_json(results)
        data = json.loads(output)
        assert data["passwords_hashed"] == 0
        assert data["results"] == []


class TestFormatHashReportMarkdown:
    """Tests for Markdown formatter."""

    def test_format_markdown_basic(self):
        results = run_hash(["password"], algorithms=["md5", "sha256"])
        output = format_hash_report_markdown(results)
        assert "# Password Hash Report" in output
        assert "**Passwords Hashed:** 1" in output
        assert "**Algorithms:** MD5, SHA-256" in output
        assert "| Password | MD5 | SHA-256 |" in output
        assert "5f4dcc3b5aa765d61d8327deb882cf99" in output

    def test_format_markdown_multiple_passwords(self):
        results = run_hash(["password", "123456"], algorithms=["md5"])
        output = format_hash_report_markdown(results)
        assert "**Passwords Hashed:** 2" in output
        assert "5f4dcc3b5aa765d61d8327deb882cf99" in output
        assert "e10adc3949ba59abbe56e057f20f883e" in output

    def test_format_markdown_empty(self):
        results = {"passwords_hashed": 0, "algorithms": ["MD5"], "results": []}
        output = format_hash_report_markdown(results)
        assert "*No passwords provided.*" in output

    def test_format_markdown_pipe_escaping(self):
        pwd = "pass|word"
        results = run_hash([pwd], algorithms=["md5"])
        output = format_hash_report_markdown(results)
        assert "pass\\|word" in output


class TestAlgorithmsConstants:
    """Tests for algorithm constants."""

    def test_algorithms_mapping(self):
        assert ALGORITHMS["md5"] == "MD5"
        assert ALGORITHMS["sha1"] == "SHA-1"
        assert ALGORITHMS["sha256"] == "SHA-256"
        assert ALGORITHMS["sha512"] == "SHA-512"
        assert ALGORITHMS["ntlm"] == "NTLM"

    def test_default_algorithms_order(self):
        assert DEFAULT_ALGORITHMS == ["md5", "sha1", "sha256", "sha512", "ntlm"]