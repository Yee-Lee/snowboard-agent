# Dev Progress: Core AudioOutput Stream-to-Native Adaptation

**Milestone**: M3 (HAL append-only revision)
**Designer ref**: `RESP-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001`
**CR source**: `CR-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001` (Audio POC)
**Status**: `IMPLEMENTED — awaiting Designer review / candidate decision`

---

## Context

`AlsaAudioOutput.play()` currently requires 48 kHz / stereo / S32_LE frames.
Matcha TTS emits 16 kHz / mono / S16_LE. A `StreamFormatAdapter` must be
added inside Core AudioOutput so TTS passes stream-format chunks and Core
handles all conversion internally.

`samplerate==0.2.4` is already declared in `dev` and `rpi-audio` extras.

---

## Work items

### WI-1: New file `src/sbd/core/audio/alsa/adaptation.py`

```python
class StreamFormatAdapter:
    """Stateful 16kHz/mono/S16_LE → 48kHz/stereo/S32_LE converter."""

    def __init__(self) -> None:
        # import samplerate lazily (rpi-audio optional dep)
        ...
    
    def convert(self, chunk: bytes) -> bytes:
        """Accept S16_LE mono bytes; return S32_LE stereo bytes.
        Resampler state is preserved across calls within a session."""
        ...

    def flush(self) -> bytes:
        """Drain resampler tail; return remaining converted bytes."""
        ...

    def reset(self) -> None:
        """Discard resampler state. Call between independent play() sessions."""
        ...
```

**Conversion pipeline per chunk** (in order):
1. Unpack `chunk` as little-endian int16 array.
2. Normalise to float32 in [-1.0, 1.0] (divide by 32768.0).
3. Pass float array + ratio=3.0 to `samplerate.CallbackResampler` or
   `samplerate.resample` with converter type `sinc_best`; keep state between
   calls within a session.
4. Scale output floats back to int32: `s32 = clamp(round(f * 2147483648), INT32_MIN, INT32_MAX)`.
   (Using full int32 range; simple left-shift from s16 gives the same result
   for valid s16 input — use whichever is cleaner.)
5. Interleave into stereo by duplicating each sample: `[s, s, s, s, ...]`.
6. Pack as little-endian int32 (`<i`) sequence.

**`flush()`**: call the resampler's end-of-input drain (pass empty input with
`end_of_input=True` if using `CallbackResampler`); apply steps 4-6 to residue.

**`reset()`**: discard current resampler instance; create a fresh one on the
next `convert()` call.

---

### WI-2: Modify `src/sbd/core/audio/alsa/output.py`

Add at top of file:
```python
_STREAM_FRAME_BYTES = 2  # S16_LE mono: 2 bytes per sample
```

Modify `__init__`:
```python
self._adapter: StreamFormatAdapter | None = None
# If stream_format != native_format, set self._adapter = StreamFormatAdapter()
# Read from config.output.stream_format and config.output.native_format
```

Modify `play()`:
```python
async def play(self, pcm: AsyncIterator[bytes]) -> None:
    if not self._started:
        raise RuntimeError("ALSA audio output is not started")
    if self._adapter is None:
        # passthrough: existing native-frame validation unchanged
        async for chunk in pcm:
            if type(chunk) is not bytes or len(chunk) % _NATIVE_FRAME_BYTES:
                raise ValueError("ALSA output requires complete 48k stereo S32_LE frames")
            await self._run(lambda c=chunk: self._write_worker(c))
    else:
        # stream-format path
        async for chunk in pcm:
            if type(chunk) is not bytes or len(chunk) % _STREAM_FRAME_BYTES:
                raise ValueError("ALSA output requires complete 16k mono S16_LE frames")
            native = self._adapter.convert(chunk)
            if native:
                await self._run(lambda n=native: self._write_worker(n))
        tail = self._adapter.flush()
        if tail:
            await self._run(lambda t=tail: self._write_worker(t))
```

Modify `stop()` / cancel / reopen paths: call `self._adapter.reset()` if
adapter is not None, before or after `_close_worker`.

---

### WI-3: Config validation

In `src/sbd/core/audio/alsa/output.py` `__init__` or a validator:

```python
stream = config.output.stream_format
native = config.output.native_format
if native is not None and native != stream:
    # Only supported conversion: 16kHz/mono/s16_le → 48kHz/stereo/s32_le
    if not (
        stream.sample_rate == 16_000 and stream.channels == 1 and stream.sample_format == "s16_le"
        and native.sample_rate == 48_000 and native.channels == 2 and native.sample_format == "s32_le"
    ):
        raise ValueError(
            "AlsaAudioOutput: unsupported stream→native conversion "
            f"{stream} → {native}; only 16kHz/mono/s16_le → 48kHz/stereo/s32_le is supported"
        )
    self._adapter = StreamFormatAdapter()
```

---

### WI-4: Tests

Add to `tests/test_m3_aud_001_002_003_004.py` or new file
`tests/test_m3_audo_001_002_003_004_005_006_007.py`.

```
test_m3_audo_001  deterministic conversion (sine, silence, impulse)
test_m3_audo_002  chunking byte-equivalence (1, 2, 3, 7-byte and aligned splits)
test_m3_audo_003  sample count / channel / container accounting
test_m3_audo_004  impulse onset and tail retention after flush
test_m3_audo_005  lifecycle: cancel / force-abort / 5-reopen → zero delta, fresh adapter
test_m3_audo_006  config validation: unsupported route rejected; stream==native passthrough OK
test_m3_audo_007  regression: existing passthrough path and ALSA negotiation unchanged
```

All tests must be portable (no `rpi` marker). Use `_FakePCM` pattern from
`test_m3_aud_004` for write-path tests.

---

## Acceptance criteria

- All 7 portable test groups pass under `pytest -q -m "not rpi"`.
- Existing `test_m3_aud_001_002_003_004.py` remains fully green.
- `AlsaAudioOutput(config_with_adaptation).play(stream_format_iterator)` works
  end-to-end with a `_FakePCM` sink.
- Config with unsupported conversion raises `ValueError` at construction.

---

## Out of scope

- Barge-in, AEC, AGC.
- Changing the ALSA device negotiation (48kHz/stereo/S32_LE/period960).
- Any change to `AlsaAudioInput` or other modules.
- Pi `rpi` test execution (Pi evidence is Audio POC M3 responsibility for
  Matcha prompts; Core may add a tone-only rpi regression separately).

---

## Return

When complete, Developer reports back to Designer with:
- Commit SHA on `core`
- `pytest -q -m "not rpi"` exit code and summary

## Developer verification (2026-08-23)

- Implemented `StreamFormatAdapter` with lazy `samplerate` / `numpy` imports,
  stateful `sinc_best` 1:3 conversion, mono-to-stereo expansion, S32_LE
  packing, end-of-input flush and session reset.
- Updated `AlsaAudioOutput` to validate either exact native passthrough or the
  selected 16 kHz mono S16_LE to 48 kHz stereo S32_LE route; its one-worker
  operation now uses the same polling pattern as ALSA input to avoid the
  supported Python 3.12 second-bridge hang.
- `PYTHONPATH=src python3 -m pytest -q tests/test_m3_audo_001_002_003_004_005_006_007.py tests/test_m3_aud_001_002_003_004.py::test_m3_aud_002 tests/test_m3_aud_001_002_003_004.py::test_m3_aud_003 tests/test_m3_aud_001_002_003_004.py::test_m3_aud_004 tests/test_m3_cfg_001_002.py` → `12 passed`.
- The full portable command is blocked only at existing `test_m3_aud_001`:
  this host lacks the declared optional `samplerate==0.2.4` dependency, so its
  existing input anti-aliasing check cannot import the package. New output
  tests use deterministic resampler seams and do not hide that dependency.
