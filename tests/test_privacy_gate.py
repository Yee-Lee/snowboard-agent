from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.privacy_gate import Finding, PUBLIC_IDENTITIES, scan_blob, scan_files


def test_privacy_gate_rejects_private_paths_tokens_and_payload_types() -> None:
    private_home = "/".join(("", "home", "alice", "private", "result.json"))
    token = "gh" + "p_" + "abcdefghijklmnopqrstuv"
    findings = scan_blob(
        "evidence/result.json",
        ('{"path":"' + private_home + '","token":"' + token + '"}').encode(),
    )
    assert findings == {
        Finding("evidence/result.json", "private-posix-home"),
        Finding("evidence/result.json", "github-token"),
    }
    assert Finding("fixtures/private.wav", "private-file-type") in scan_blob(
        "fixtures/private.wav", b"RIFFdata"
    )


def test_privacy_gate_accepts_placeholders_and_public_digests() -> None:
    content = (
        b'path: /home/<user>/placeholder\n'
        b'sha256: 181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c\n'
    )
    assert scan_blob("docs/example.yaml", content) == set()


def test_privacy_gate_allows_public_identity() -> None:
    assert "Yee.Lee" in PUBLIC_IDENTITIES
    assert "yeelee.tw@gmail.com" in PUBLIC_IDENTITIES
    assert scan_blob(
        "evidence/environment.txt",
        b"operator=Yee.Lee email=yeelee.tw@gmail.com",
    ) == set()


def test_public_evidence_rejects_unknown_fields_and_invalid_values() -> None:
    def check(record: dict) -> set[Finding]:
        blob = json.dumps({"schema_version": 1, "records": [record]}).encode()
        return scan_blob("public.json", blob, strict_evidence=True)

    valid = {"test_id": "T-001", "status": "PASS", "metrics": {"cer": 0.12},
             "user": "Yee.Lee", "email": "yeelee.tw@gmail.com"}
    assert check(valid) == set()
    for field in ("host", "device", "machine", "os", "platform", "cwd", "home",
                  "transcript", "unknown_field"):
        assert check({**valid, field: "synthetic-value"}) == {
            Finding("public.json", "public-evidence-schema")
        }
    for metrics in ({"cer": "raw-text"}, {"cer": {"raw": "text"}},
                    {"cer": True}, {"cer": float("nan")}):
        assert check({**valid, "metrics": metrics})
    assert check({**valid, "candidate_sha": "not-a-digest"})
    assert check({**valid, "error_counts": {"timeout": -1}})
    assert check({**valid, "status": "free-form-comment"})


def test_public_evidence_requires_json_and_unique_fields() -> None:
    for blob in (b"plain prose", b"[]", b'{"schema_version":1,"records":{},"extra":0}',
                 b'{"schema_version":1,"schema_version":1,"records":[]}'):
        assert Finding("public.json", "public-evidence-schema") in scan_blob(
            "public.json", blob, strict_evidence=True
        )


def test_scanner_and_tests_pass_the_general_scan() -> None:
    root = Path(__file__).resolve().parents[1]
    assert scan_files((root / "scripts/privacy_gate.py", Path(__file__)),
                      strict_evidence=False, sentinels=()) == set()


def test_privacy_gate_detects_canary_without_echoing_value() -> None:
    secret = b"customer-private-canary"
    findings = scan_blob("result.json", b'{"value":"customer-private-canary"}', sentinels=(secret,))
    assert findings == {Finding("result.json", "private-sentinel")}


def test_privacy_gate_rejects_symlink_and_binary() -> None:
    with tempfile.TemporaryDirectory() as directory:
        _check_symlink_and_binary(Path(directory))


def _check_symlink_and_binary(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("safe")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    binary = tmp_path / "result.dat"
    binary.write_bytes(b"a\x00b")
    findings = scan_files((link, binary), strict_evidence=False, sentinels=())
    assert Finding(f"<external>/{link.name}", "unsafe-file-kind") in findings
    assert Finding(f"<external>/{binary.name}", "binary-content") in findings


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(
        unittest.FunctionTestCase(value)
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    )


if __name__ == "__main__":
    unittest.main()
