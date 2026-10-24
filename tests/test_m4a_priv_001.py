"""M4A-PRIV-001 — product output never exposes private Audio content."""

from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path

import pytest

from scripts.m4a_audio_product import main as product_main
from scripts.m4a_target_metrics import privacy_hits
from sbd.adaptor.framed_child import AudioProtocolError, FramedProcess


TRANSCRIPT = "M4A_PRIVATE_TRANSCRIPT_SENTINEL"
TTS_TEXT = "M4A_PRIVATE_TTS_INPUT_SENTINEL"
PROMPT = "M4A_PRIVATE_PROMPT_SENTINEL"
MODEL_OUTPUT = "M4A_PRIVATE_MODEL_OUTPUT_SENTINEL"
CREDENTIAL = "M4A_PRIVATE_CREDENTIAL_SENTINEL"
PCM = b"\x13\x37\xde\xad\xbe\xef\x55\xaa"


def _assert_private_absent(output: str, private_path: Path) -> None:
    prohibited = (
        TRANSCRIPT,
        TTS_TEXT,
        PROMPT,
        MODEL_OUTPUT,
        CREDENTIAL,
        str(private_path),
        PCM.hex(),
        base64.b64encode(PCM).decode(),
        PCM.decode("latin1"),
    )
    assert all(value not in output for value in prohibited)


def test_m4a_priv_001_product_failure_is_sanitized(capsys, tmp_path: Path) -> None:
    private = tmp_path / "private-work-path"
    private.mkdir()
    code = product_main([
        "preflight",
        "--lock-root", str(private / CREDENTIAL),
        "--install-root", str(private / TTS_TEXT),
        "--core-repo", str(private),
        "--core-sha", "1" * 40,
        "--config", str(private / TRANSCRIPT),
    ])
    assert code == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert set(payload) == {"status", "operation", "error_code"}
    _assert_private_absent(captured.out + captured.err, private)


def test_m4a_priv_001_child_stderr_is_digest_only_and_workdir_is_removed(
    capsys, tmp_path: Path,
) -> None:
    async def run() -> None:
        child_script = (
            "import json,os,sys;"
            f"sys.stderr.write({(TRANSCRIPT + TTS_TEXT + PROMPT + MODEL_OUTPUT + CREDENTIAL)!r});"
            "print(json.dumps({'protocol':1,'event':'READY','pid':os.getpid(),"
            "'pgid':os.getpid(),'identity':'0'*64}),flush=True)"
        )
        process = FramedProcess(
            argv_builder=lambda workdir: [sys.executable, "-c", child_script],
            work_root=tmp_path / "private-child-root",
            expected_ready={"identity": "1" * 64},
            ready_timeout=1,
            terminate_timeout=0.2,
            kill_timeout=0.2,
        )
        with pytest.raises(AudioProtocolError, match="identity mismatch"):
            await process.start()
        assert process.workdir is None
        assert list((tmp_path / "private-child-root").iterdir()) == []

    asyncio.run(run())
    captured = capsys.readouterr()
    _assert_private_absent(captured.out + captured.err, tmp_path)


def test_m4a_priv_001_scanner_detects_raw_hex_and_base64_pcm() -> None:
    sentinels = (PCM, PCM.hex(), base64.b64encode(PCM).decode())
    blobs = [
        ("raw", b"prefix" + PCM + b"suffix"),
        ("hex", PCM.hex().encode()),
        ("base64", base64.b64encode(PCM)),
        ("clean", b'{"status":"Pass"}'),
    ]
    assert privacy_hits(blobs, sentinels) == ["raw", "hex", "base64"]
