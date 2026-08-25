from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4_combined_coordinator import M4CombinedCoordinator  # noqa: E402
from audio_poc.m4_packet import SESSION_ROWS  # noqa: E402


class FakeDomain:
    def __init__(self, domain: str, events: list[str]) -> None:
        self.domain = domain
        self.events = events
        self.started = 0
        self.stopped = 0

    async def start(self) -> None:
        self.started += 1
        self.events.append(f"{self.domain}:start")

    async def run(self, session: dict[str, object]) -> dict[str, object]:
        session_id = str(session["session_id"])
        self.events.append(f"{self.domain}:{session_id}")
        if self.domain == "vad":
            return {
                "session_id": session_id, "terminal": "SUCCESS",
                "bounded_wav": f"/controlled/{session_id}.wav", "bounded_sha256": "a" * 64,
                "capture_intervals_ms": [[0, 100]],
            }
        if self.domain == "asr":
            return {
                "session_id": session_id, "terminal": "SUCCESS", "nonempty": True,
                "hypothesis_sha256": "b" * 64, "latency_ms": 10.0,
            }
        return {
            "session_id": session_id, "terminal": "SUCCESS", "pcm_sha256": "c" * 64,
            "sample_count": 160, "playback_complete": True,
        }

    async def stop(self) -> None:
        self.stopped += 1
        self.events.append(f"{self.domain}:stop")


class FakeP9:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def begin(self, request_id: str) -> dict[str, str]:
        self.events.append(f"p9:begin:{request_id}")
        return {"request_id": request_id}

    async def complete(self, request_id: str, token: dict[str, str]) -> dict[str, object]:
        self.events.append(f"p9:complete:{request_id}")
        return {"request_id": request_id, "worker_pids": [101, 102, 103, 104]}


def fixture_lock() -> dict[str, object]:
    return {
        "records": [
            {
                "session_id": session_id,
                "category": category,
                "fixture_id": fixture_id,
                "tts_fixture_id": tts_fixture_id,
                "filename": f"{fixture_id}.wav",
                "sha256": "d" * 64,
            }
            for session_id, category, fixture_id, tts_fixture_id in SESSION_ROWS
        ]
    }


class M4CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_persistent_domains_run_all_sessions_in_order_with_p9_overlap(self) -> None:
        events: list[str] = []
        vad = FakeDomain("vad", events)
        asr = FakeDomain("asr", events)
        tts = FakeDomain("tts", events)
        results = await M4CombinedCoordinator(vad, asr, tts).run(fixture_lock(), FakeP9(events))
        self.assertEqual([domain.started for domain in (vad, asr, tts)], [1, 1, 1])
        self.assertEqual([domain.stopped for domain in (vad, asr, tts)], [1, 1, 1])
        self.assertEqual(len(results), 20)
        self.assertEqual(results[0]["session_id"], "M4-SESSION-01")
        self.assertEqual(results[-1]["session_id"], "M4-SESSION-20")
        self.assertEqual(events[:5], [
            "vad:start", "asr:start", "tts:start", "p9:begin:M4-SESSION-01",
            "vad:M4-SESSION-01",
        ])
        self.assertEqual(events[-3:], ["tts:stop", "asr:stop", "vad:stop"])

    async def test_asr_empty_result_stops_all_domains(self) -> None:
        events: list[str] = []
        vad = FakeDomain("vad", events)
        asr = FakeDomain("asr", events)
        tts = FakeDomain("tts", events)
        original = asr.run

        async def empty(session: dict[str, object]) -> dict[str, object]:
            result = await original(session)
            result["nonempty"] = False
            return result

        asr.run = empty  # type: ignore[method-assign]
        with self.assertRaisesRegex(RuntimeError, "ASR terminal result is unusable"):
            await M4CombinedCoordinator(vad, asr, tts).run(fixture_lock())
        self.assertEqual([domain.stopped for domain in (vad, asr, tts)], [1, 1, 1])


if __name__ == "__main__":
    unittest.main()
