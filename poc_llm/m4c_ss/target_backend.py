"""Private binding over the accepted TTS and AudioOutput object contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
import asyncio
import inspect
import time
from typing import Protocol


class TtsPort(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def synthesize(self, text: str) -> AsyncIterator[bytes]: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> object: ...


class AudioOutputPort(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def play(self, pcm: AsyncIterator[bytes]) -> None: ...


class CoreSpeechBackend:
    """Drive accepted objects without changing either public contract.

    The caller constructs the accepted Core objects and wires the AudioOutput
    ``observe`` callback to the same observer.  This wrapper owns only the
    current iterator and operation state.  Abort destroys the private output
    owner for the affected case; a later fresh case must create a new wrapper.
    """

    def __init__(
        self,
        *,
        tts: TtsPort,
        audio_output: AudioOutputPort,
        observe: Callable[[str, int], None],
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.tts = tts
        self.audio_output = audio_output
        self.observe = observe
        self.clock_ns = clock_ns
        self._pcm: AsyncIterator[bytes] | None = None
        self._started = False
        self._active = False
        self._destroyed = False
        self._idle = asyncio.Event()
        self._idle.set()

    async def start(self) -> None:
        if self._started or self._destroyed:
            raise RuntimeError("backend is not startable")
        await self.tts.start()
        try:
            await self.audio_output.start()
        except BaseException:
            await self.tts.stop()
            raise
        self._started = True

    async def stop(self) -> None:
        failures: list[BaseException] = []
        if self._active:
            try:
                await self.abort()
            except BaseException as error:
                failures.append(error)
        if self._started:
            try:
                await self.audio_output.stop()
            except BaseException as error:
                failures.append(error)
            try:
                await self.tts.stop()
            except BaseException as error:
                failures.append(error)
        self._started = False
        self._destroyed = True
        if failures:
            raise failures[0]

    async def speak(self, text: str) -> None:
        if not self._started or self._destroyed or self._active:
            raise RuntimeError("backend is unavailable")
        self._active = True
        self._idle.clear()
        self.observe("tts_start", self.clock_ns())
        pcm = self.tts.synthesize(text)
        self._pcm = pcm
        observed = self._observed_pcm(pcm)
        try:
            await self.audio_output.play(observed)
            self.observe("playback_complete", self.clock_ns())
        finally:
            await observed.aclose()
            if self._pcm is not None:
                await self._pcm.aclose()
            self._pcm = None
            self._active = False
            self._idle.set()

    async def abort(self) -> None:
        if self._destroyed:
            return
        self.observe("abort_requested", self.clock_ns())
        await self.tts.abort()
        await self._idle.wait()
        await self.audio_output.stop()
        self._started = False
        self._destroyed = True
        if not self._active:
            await self._close_pcm()

    async def force_abort(self) -> None:
        if self._destroyed:
            return
        self.observe("force_abort_requested", self.clock_ns())
        report = self.tts.force_abort()
        if inspect.isawaitable(report):
            await report
        await self._idle.wait()
        await self.audio_output.stop()
        self._started = False
        self._destroyed = True
        if not self._active:
            await self._close_pcm()

    def operation_idle(self) -> bool:
        return not self._active and self._pcm is None

    async def _observed_pcm(self, source: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        first = True
        async for chunk in source:
            if type(chunk) is not bytes or not chunk or len(chunk) % 2:
                raise RuntimeError("invalid canonical PCM chunk")
            if first:
                first = False
                self.observe("tts_first_pcm", self.clock_ns())
            yield chunk
        if first:
            raise RuntimeError("empty PCM stream")

    async def _close_pcm(self) -> None:
        pcm, self._pcm = self._pcm, None
        if pcm is not None:
            await pcm.aclose()
        self._active = False
