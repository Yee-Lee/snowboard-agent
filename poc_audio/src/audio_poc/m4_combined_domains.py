"""Persistent finalist adapters consumed by the formal M4 coordinator."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import select
import signal
import subprocess
from pathlib import Path
from typing import Any

from .m3_asr import BINARY_SHA256, MODEL_SHA256, PROMPT
from .m3_core_hal import play_stream_pcm
from .m3_packet import TTS_PROMPT_SHA256
from .m3_tts_playback import _read_json_line, _terminate
from .m4a_authorized_preflight import verify_candidate_inputs
from .m4a_candidate_smoke import safe_extract
from .m4a_tts_lifecycle import TTS_ID, sha256_file
from .m4a_whispercpp_qualification import NativeWhisperWorker
from .m4_p9 import P9Client


class PersistentVadDomain:
    def __init__(
        self,
        repo_root: Path,
        runtime_python: Path,
        model: Path,
        output_dir: Path,
        timeout: float,
    ) -> None:
        self.repo_root = repo_root
        self.runtime_python = runtime_python
        self.model = model
        self.output_dir = output_dir
        self.timeout = timeout
        self.process: subprocess.Popen[str] | None = None

    async def start(self) -> None:
        await asyncio.to_thread(self._start)

    def _start(self) -> None:
        if self.process is not None or not self.runtime_python.is_file():
            raise RuntimeError("M4 VAD runtime is unavailable or already started")
        environment = os.environ.copy()
        environment.update({
            "PYTHONPATH": str(self.repo_root / "poc_audio/src"),
            "PIP_NO_INDEX": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
            "NO_PROXY": "*",
        })
        self.process = subprocess.Popen(
            [
                str(self.runtime_python), "-m", "audio_poc.m4_vad_worker",
                "--model", str(self.model), "--output-dir", str(self.output_dir),
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=environment, start_new_session=True, bufsize=1,
        )
        ready = self._read()
        if ready.get("event") != "READY" or ready.get("model_sha256") != "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3":
            self._abort()
            raise RuntimeError("M4 VAD READY identity mismatch")

    async def run(self, session: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._run, session)

    def residency_identity(self) -> dict[str, Any]:
        process = self.process
        return {
            "pid": process.pid if process is not None else None,
            "alive": process is not None and process.poll() is None,
        }

    async def inject_error(self) -> None:
        """Make the loaded Silero worker reject a malformed protocol command."""
        await asyncio.to_thread(self._inject_error)

    def _inject_error(self) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("M4 VAD worker is not started")
        self.process.stdin.write('{"op":"INVALID"}\n')
        self.process.stdin.flush()
        if self._read().get("event") != "ERROR":
            raise RuntimeError("M4 VAD actual finalist did not report the injected error")

    async def abort_active(self) -> None:
        await asyncio.to_thread(self._abort_active)

    def _abort_active(self) -> None:
        if self.process is None:
            return
        process = self.process
        self._abort()
        self._close(process)
        self.process = None

    def _run(self, session: dict[str, Any]) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("M4 VAD worker is not started")
        wav_path = session.get("wav_path")
        if not isinstance(wav_path, Path) or not wav_path.is_file():
            raise ValueError("M4 VAD session WAV is unavailable")
        self.process.stdin.write(json.dumps({
            "op": "RUN", "session_id": session["session_id"], "wav_path": str(wav_path),
        }, sort_keys=True) + "\n")
        self.process.stdin.flush()
        result = self._read()
        if result.get("event") != "RESULT" or result.get("session_id") != session["session_id"]:
            raise RuntimeError(f"M4 VAD worker failed: {result.get('code', result.get('event'))}")
        bounded = self.output_dir / str(result.get("bounded_filename", ""))
        if not bounded.is_file() or sha256_file(bounded) != result.get("bounded_sha256"):
            raise RuntimeError("M4 VAD bounded WAV identity mismatch")
        return {
            "session_id": session["session_id"], "terminal": "SUCCESS",
            "bounded_wav": bounded, "bounded_sha256": result["bounded_sha256"],
            "capture_intervals_ms": result["capture_intervals_ms"],
        }

    async def stop(self) -> None:
        await asyncio.to_thread(self._stop)

    def _stop(self) -> None:
        if self.process is None:
            return
        process = self.process
        try:
            if process.poll() is None and process.stdin is not None:
                process.stdin.write('{"op":"SHUTDOWN"}\n')
                process.stdin.flush()
                if self._read().get("event") != "SHUTDOWN_ACK":
                    raise RuntimeError("M4 VAD worker shutdown acknowledgment mismatch")
                process.wait(timeout=self.timeout)
        finally:
            self._abort()
            self._close(process)
            self.process = None
        if process.returncode not in {0, None}:
            raise RuntimeError(f"M4 VAD worker exited with {process.returncode}")

    def _read(self) -> dict[str, Any]:
        if self.process is None or self.process.stdout is None:
            raise RuntimeError("M4 VAD stdout is unavailable")
        ready, _, _ = select.select([self.process.stdout], [], [], self.timeout)
        if not ready:
            raise TimeoutError("M4 VAD worker response timed out")
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("M4 VAD worker closed stdout")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError("M4 VAD worker protocol is invalid")
        return value

    def _abort(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=min(self.timeout, 5.0))
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=min(self.timeout, 5.0))
        except ProcessLookupError:
            pass

    @staticmethod
    def _close(process: subprocess.Popen[str]) -> None:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


class PersistentAsrDomain:
    def __init__(self, binary: Path, model: Path, work_dir: Path, timeout: float) -> None:
        self.binary = binary
        self.model = model
        self.work_dir = work_dir
        self.timeout = timeout
        self.worker: NativeWhisperWorker | None = None

    async def start(self) -> None:
        await asyncio.to_thread(self._start)

    def _start(self) -> None:
        if self.worker is not None or self.work_dir.exists():
            raise RuntimeError("M4 ASR worker is already started or work directory exists")
        if sha256_file(self.binary) != BINARY_SHA256 or sha256_file(self.model) != MODEL_SHA256:
            raise ValueError("M4 ASR artifact checksum mismatch")
        self.work_dir.mkdir(parents=True)
        self.worker = NativeWhisperWorker(
            [
                str(self.binary.resolve()), "--model", str(self.model.resolve()), "--threads", "4",
                "--initial-prompt", PROMPT,
            ],
            self.work_dir / "base-q8.stderr.log", ready_timeout=self.timeout,
        )
        self.worker.start()

    async def run(self, session: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._run, session)

    def residency_identity(self) -> dict[str, Any]:
        process = self.worker.process if self.worker is not None else None
        return {
            "pid": self.worker.pid if self.worker is not None else None,
            "alive": process is not None and process.poll() is None,
        }

    async def inject_error(self) -> None:
        """Ask the loaded native worker to process a nonexistent controlled WAV."""
        await asyncio.to_thread(self._inject_error)

    def _inject_error(self) -> None:
        if self.worker is None:
            raise RuntimeError("M4 ASR worker is not started")
        try:
            self.worker.transcribe(self.work_dir / "controlled-missing.wav", self.timeout)
        except Exception:
            return
        raise RuntimeError("M4 ASR actual finalist accepted the injected invalid WAV")

    async def abort_active(self) -> None:
        await asyncio.to_thread(self._abort_active)

    def _abort_active(self) -> None:
        if self.worker is not None:
            self.worker.terminate()
            self.worker = None

    def _run(self, session: dict[str, Any]) -> dict[str, Any]:
        if self.worker is None:
            raise RuntimeError("M4 ASR worker is not started")
        bounded = session.get("bounded_wav")
        if not isinstance(bounded, Path) or not bounded.is_file():
            raise ValueError("M4 ASR bounded WAV is unavailable")
        metrics = self.worker.transcribe(bounded, self.timeout)
        hypothesis = str(metrics.pop("hypothesis"))
        return {
            "session_id": session["session_id"], "terminal": "SUCCESS",
            "nonempty": bool(hypothesis.strip()),
            "hypothesis_sha256": hashlib.sha256(hypothesis.encode("utf-8")).hexdigest(),
            "latency_ms": metrics["latency_ms"],
        }

    async def stop(self) -> None:
        await asyncio.to_thread(self._stop)

    def _stop(self) -> None:
        if self.worker is None:
            return
        cleanup = self.worker.stop()
        self.worker = None
        if not cleanup.get("clean"):
            raise RuntimeError("M4 ASR worker cleanup failed")


class PersistentTtsDomain:
    def __init__(
        self,
        repo_root: Path,
        artifact_dir: Path,
        runtime_python: Path,
        work_dir: Path,
        audio: Any,
        config: Any,
        timeout: float,
    ) -> None:
        self.repo_root = repo_root
        self.artifact_dir = artifact_dir
        self.runtime_python = runtime_python
        self.work_dir = work_dir
        self.audio = audio
        self.config = config
        self.timeout = timeout
        self.process: asyncio.subprocess.Process | None = None
        self.prompts: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        if self.process is not None or self.work_dir.exists() or not self.runtime_python.is_file():
            raise RuntimeError("M4 TTS runtime is unavailable or already started")
        await asyncio.to_thread(_validate_tts_runtime, self.runtime_python)
        manifest = json.loads(
            (self.repo_root / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text(encoding="utf-8")
        )
        verify_candidate_inputs(manifest, TTS_ID, self.artifact_dir)
        prompts_path = self.repo_root / "poc_audio/fixtures/fake/tts_prompts.json"
        if sha256_file(prompts_path) != TTS_PROMPT_SHA256:
            raise ValueError("M4 TTS prompt checksum mismatch")
        self.prompts = {
            item["fixture_id"]: item
            for item in json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"]
        }
        self.work_dir.mkdir(parents=True)
        model_dir = safe_extract(
            self.artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
            self.work_dir, "matcha-icefall-zh-en",
        )
        environment = os.environ.copy()
        environment.update({
            "PYTHONPATH": str(self.repo_root / "poc_audio/src"),
            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PIP_NO_INDEX": "1",
            "NO_PROXY": "*",
        })
        self.process = await asyncio.create_subprocess_exec(
            str(self.runtime_python), "-m", "audio_poc.m3_tts_worker",
            "--model-dir", str(model_dir),
            "--vocos", str(self.artifact_dir / "models/vocos-16khz-univ.onnx"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, env=environment, start_new_session=True,
        )
        assert self.process.stdout is not None
        ready = await _read_json_line(self.process.stdout, self.timeout)
        if ready.get("event") != "READY":
            await _terminate(self.process, self.timeout)
            raise RuntimeError("M4 Matcha worker did not become READY")

    async def run(self, session: dict[str, Any]) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("M4 Matcha worker is not started")
        prompt_id = session.get("tts_fixture_id")
        prompt = self.prompts.get(prompt_id)
        if prompt is None:
            raise ValueError("M4 TTS prompt is absent from the locked catalog")
        text = session.get("failure_text", prompt["text"])
        if not isinstance(text, str) or not text:
            raise ValueError("M4 TTS failure text is invalid")
        self.process.stdin.write(json.dumps({
            "op": "GENERATE", "fixture_id": prompt_id, "text": text,
        }, ensure_ascii=False).encode("utf-8") + b"\n")
        await self.process.stdin.drain()
        header = await _read_json_line(self.process.stdout, self.timeout)
        if header.get("event") != "PCM" or header.get("fixture_id") != prompt_id:
            raise RuntimeError("M4 Matcha PCM protocol mismatch")
        pcm_bytes = int(header.get("pcm_bytes", 0))
        if pcm_bytes <= 0 or pcm_bytes % 2:
            raise RuntimeError("M4 Matcha PCM length is invalid")
        pcm = await asyncio.wait_for(self.process.stdout.readexactly(pcm_bytes), self.timeout)
        pcm_sha256 = hashlib.sha256(pcm).hexdigest()
        if pcm_sha256 != header.get("pcm_sha256"):
            raise RuntimeError("M4 Matcha PCM checksum mismatch")
        await play_stream_pcm(self.audio.make_audio_output(self.config), pcm, self.timeout)
        return {
            "session_id": session["session_id"], "terminal": "SUCCESS",
            "pcm_sha256": pcm_sha256, "sample_count": int(header["sample_count"]),
            "playback_complete": True,
        }

    def residency_identity(self) -> dict[str, Any]:
        process = self.process
        return {
            "pid": process.pid if process is not None else None,
            "alive": process is not None and process.returncode is None,
        }

    async def inject_error(self) -> None:
        """Make the loaded Matcha worker reject a malformed command."""
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("M4 Matcha worker is not started")
        self.process.stdin.write(b'{"op":"INVALID"}\n')
        await self.process.stdin.drain()
        if (await _read_json_line(self.process.stdout, self.timeout)).get("event") != "ERROR":
            raise RuntimeError("M4 Matcha actual finalist did not report the injected error")

    async def abort_active(self) -> None:
        if self.process is None:
            return
        process = self.process
        await _terminate(process, self.timeout)
        self.process = None

    async def stop(self) -> None:
        if self.process is None:
            return
        process = self.process
        try:
            if process.returncode is None and process.stdin is not None and process.stdout is not None:
                process.stdin.write(b'{"op":"SHUTDOWN"}\n')
                await process.stdin.drain()
                ack = await _read_json_line(process.stdout, self.timeout)
                if ack.get("event") != "SHUTDOWN_ACK":
                    raise RuntimeError("M4 Matcha shutdown acknowledgment mismatch")
                if await asyncio.wait_for(process.wait(), self.timeout) != 0:
                    raise RuntimeError("M4 Matcha worker exited nonzero")
        finally:
            await _terminate(process, self.timeout)
            self.process = None


class AsyncP9Overlap:
    """Async coordinator bridge around the locked synchronous P9 client."""

    def __init__(self, client: P9Client, timeout: float) -> None:
        self.client = client
        self.timeout = timeout

    async def begin(self, request_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self.client.begin_infer, request_id, self.timeout)

    async def complete(self, request_id: str, token: dict[str, Any]) -> dict[str, Any]:
        workers = token.get("worker_pids")
        if not isinstance(workers, list) or not all(isinstance(pid, int) for pid in workers):
            raise RuntimeError("M4 P9 coordinator token is invalid")
        return await asyncio.to_thread(self.client.complete_infer, request_id, workers, self.timeout)


def _validate_tts_runtime(runtime_python: Path) -> None:
    """Verify the named isolated interpreter, never the controller's Python."""
    venv_config = runtime_python.parent.parent / "pyvenv.cfg"
    if not venv_config.is_file() or "include-system-site-packages = false" not in venv_config.read_text(encoding="utf-8"):
        raise RuntimeError("M4 Matcha runtime must be an isolated venv")
    check = subprocess.run(
        [str(runtime_python), "-c", "import importlib.metadata as m; print(m.version('sherpa-onnx'))"],
        capture_output=True, text=True, check=False,
    )
    version = check.stdout.strip() if check.returncode == 0 else "unavailable"
    if version != "1.13.5":
        raise RuntimeError(f"M4 Matcha runtime identity mismatch: sherpa-onnx={version}")
