from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc import m4_vad_worker  # noqa: E402


class M4VadWorkerDispatchTests(unittest.TestCase):
    def test_run_dispatch_passes_loaded_model_session_separately_from_session_id(self) -> None:
        model_session = object()
        numpy_runtime = object()
        output_dir = Path("controlled-output")
        wav_path = Path("controlled-input.wav")
        result = {"event": "RESULT", "session_id": "M4-SESSION-01"}
        commands = [
            json.dumps({
                "op": "RUN",
                "session_id": "M4-SESSION-01",
                "wav_path": str(wav_path),
            }) + "\n",
            '{"op":"SHUTDOWN"}\n',
        ]

        with (
            patch.object(m4_vad_worker, "_run_one", return_value=result) as run_one,
            patch.object(m4_vad_worker, "_emit") as emit,
        ):
            exit_code = m4_vad_worker._serve(
                model_session, output_dir, numpy_runtime, commands,
            )

        self.assertEqual(exit_code, 0)
        run_one.assert_called_once_with(
            model_session, "M4-SESSION-01", wav_path, output_dir, numpy_runtime,
        )
        self.assertEqual(emit.call_args_list[0].args[0], result)
        self.assertEqual(emit.call_args_list[1].args[0], {"event": "SHUTDOWN_ACK"})


if __name__ == "__main__":
    unittest.main()
