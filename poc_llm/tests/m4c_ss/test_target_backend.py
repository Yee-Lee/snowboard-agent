from __future__ import annotations

import asyncio
import unittest

from poc_llm.m4c_ss.target_backend import CoreSpeechBackend


class FakeTts:
    def __init__(self) -> None:
        self.started = False
        self.aborted = False
        self.forced = False
        self.release = asyncio.Event()

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False

    def synthesize(self, text):
        async def generate():
            await self.release.wait()
            if self.aborted or self.forced:
                raise RuntimeError("cancelled")
            yield b"\x01\x00" * 4
        return generate()

    async def abort(self):
        self.aborted = True
        self.release.set()

    async def force_abort(self):
        self.forced = True
        self.release.set()


class FakeAudio:
    def __init__(self, observer) -> None:
        self.started = False
        self.observer = observer

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False

    async def play(self, pcm):
        first = True
        async for _chunk in pcm:
            if first:
                first = False
                self.observer("audio_first_write", 4)


class TargetBackendTests(unittest.IsolatedAsyncioTestCase):
    def make(self):
        events = []
        tts = FakeTts()
        audio = FakeAudio(lambda name, stamp: events.append((name, stamp)))
        stamps = iter((1, 2, 3, 5, 6, 7))
        backend = CoreSpeechBackend(
            tts=tts, audio_output=audio,
            observe=lambda name, stamp: events.append((name, stamp),),
            clock_ns=lambda: next(stamps),
        )
        return backend, tts, audio, events

    async def test_normal_path_observes_tts_pcm_audio_and_completion(self):
        backend, tts, audio, events = self.make()
        await backend.start()
        speak = asyncio.create_task(backend.speak("public"))
        await asyncio.sleep(0)
        tts.release.set()
        await speak
        self.assertEqual([name for name, _ in events], [
            "tts_start", "tts_first_pcm", "audio_first_write", "playback_complete",
        ])
        self.assertTrue(backend.operation_idle())
        await backend.stop()
        self.assertFalse(tts.started or audio.started)

    async def test_abort_stops_future_pcm_and_destroys_case_owner(self):
        backend, tts, audio, events = self.make()
        await backend.start()
        speak = asyncio.create_task(backend.speak("public"))
        await asyncio.sleep(0)
        await backend.abort()
        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            await speak
        self.assertTrue(tts.aborted)
        self.assertFalse(audio.started)
        self.assertTrue(backend.operation_idle())
        with self.assertRaisesRegex(RuntimeError, "not startable"):
            await backend.start()

    async def test_force_abort_stops_future_pcm(self):
        backend, tts, audio, events = self.make()
        await backend.start()
        speak = asyncio.create_task(backend.speak("public"))
        await asyncio.sleep(0)
        await backend.force_abort()
        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            await speak
        self.assertTrue(tts.forced)
        self.assertTrue(backend.operation_idle())


if __name__ == "__main__":
    unittest.main()
