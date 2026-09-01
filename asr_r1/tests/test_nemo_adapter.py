import ctypes
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from asr_r1.nemo_adapter import NemoSpeechCBackend, _RecognitionOptions


class FakeFunction:
    def __init__(self, operation):
        self.operation = operation
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.operation(*args)


def _set_handle(pointer, value: int) -> None:
    ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.c_void_p(value)


class FakeNemoLibrary:
    def __init__(self, version: bytes = b"nemo-speech-asr 0.1.0") -> None:
        self.closed_streams = []
        self.destroyed_results = []
        self.destroyed_recognizers = []
        self.pushed_samples = 0
        self.next_results = [301, 0]
        self.nemo_speech_asr_version = FakeFunction(lambda: version)
        self.nemo_speech_asr_last_error = FakeFunction(lambda: b"fake native error")
        self.nemo_speech_asr_create = FakeFunction(self._create)
        self.nemo_speech_asr_destroy = FakeFunction(
            lambda handle: self.destroyed_recognizers.append(handle.value)
        )
        self.nemo_speech_asr_recognition_options_default = FakeFunction(
            lambda: _RecognitionOptions(size=ctypes.sizeof(_RecognitionOptions))
        )
        self.nemo_speech_asr_streaming_recognize = FakeFunction(self._create_stream)
        self.nemo_speech_asr_stream_push_f32 = FakeFunction(self._push)
        self.nemo_speech_asr_stream_finish = FakeFunction(lambda handle: 0)
        self.nemo_speech_asr_stream_next = FakeFunction(self._next)
        self.nemo_speech_asr_stream_close = FakeFunction(
            lambda handle: self.closed_streams.append(handle.value)
        )
        self.nemo_speech_asr_result_is_final = FakeFunction(lambda result: False)
        self.nemo_speech_asr_result_alternative_count = FakeFunction(lambda result: 1)
        self.nemo_speech_asr_result_transcript = FakeFunction(
            lambda result, alternative: b"fake partial"
        )
        self.nemo_speech_asr_result_destroy = FakeFunction(
            lambda result: self.destroyed_results.append(result.value)
        )

    @staticmethod
    def _create(config, output) -> int:
        _set_handle(output, 101)
        return 0

    @staticmethod
    def _create_stream(recognizer, options, output) -> int:
        _set_handle(output, 201)
        return 0

    def _push(self, stream, values, count, sample_rate) -> int:
        self.pushed_samples += count
        return 0

    def _next(self, stream, output) -> int:
        _set_handle(output, self.next_results.pop(0))
        return 0


class NemoAdapterTest(unittest.TestCase):
    def _backend(self, temporary: str, library: FakeNemoLibrary) -> NemoSpeechCBackend:
        model = Path(temporary) / "model.gguf"
        runtime = Path(temporary) / "libnemo_speech_asr_c.so.1"
        model.touch()
        runtime.touch()
        return NemoSpeechCBackend(
            "nemo-test",
            model,
            runtime,
            library_loader=lambda path: library,
        )

    def test_stable_c_abi_stream_ownership_and_cleanup(self) -> None:
        library = FakeNemoLibrary()
        with TemporaryDirectory() as temporary:
            backend = self._backend(temporary, library)
            backend.load_model()
            stream = backend.create_stream()
            backend.accept_waveform(stream, [0.0, 0.25, -0.25])
            self.assertTrue(backend.is_ready(stream))
            backend.decode_stream(stream)
            self.assertEqual("fake partial", backend.get_text(stream))
            self.assertFalse(backend.is_ready(stream))
            backend.input_finished(stream)
            backend.close_stream(stream)
            backend.close()
        self.assertEqual(3, library.pushed_samples)
        self.assertEqual([301], library.destroyed_results)
        self.assertEqual([201], library.closed_streams)
        self.assertEqual([101], library.destroyed_recognizers)

    def test_runtime_version_mismatch_fails_closed(self) -> None:
        library = FakeNemoLibrary(version=b"0.2.0")
        with TemporaryDirectory() as temporary:
            backend = self._backend(temporary, library)
            with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
                backend.load_model()

    def test_runtime_identity_check_does_not_create_recognizer(self) -> None:
        library = FakeNemoLibrary()
        with TemporaryDirectory() as temporary:
            backend = self._backend(temporary, library)
            self.assertEqual(
                "nemo-speech-asr 0.1.0", backend.verify_runtime_identity()
            )
        self.assertEqual([], library.destroyed_recognizers)

    def test_invalid_or_closed_stream_is_rejected(self) -> None:
        library = FakeNemoLibrary()
        with TemporaryDirectory() as temporary:
            backend = self._backend(temporary, library)
            backend.load_model()
            stream = backend.create_stream()
            backend.close_stream(stream)
            with self.assertRaisesRegex(RuntimeError, "closed or invalid"):
                backend.get_text(stream)
            backend.close()

    def test_finished_stream_requires_a_native_final_result(self) -> None:
        library = FakeNemoLibrary()
        with TemporaryDirectory() as temporary:
            backend = self._backend(temporary, library)
            backend.load_model()
            stream = backend.create_stream()
            backend.accept_waveform(stream, [0.0])
            self.assertTrue(backend.is_ready(stream))
            backend.decode_stream(stream)
            backend.input_finished(stream)
            with self.assertRaisesRegex(RuntimeError, "final result"):
                backend.get_text(stream)
            backend.close_stream(stream)
            backend.close()


if __name__ == "__main__":
    unittest.main()
