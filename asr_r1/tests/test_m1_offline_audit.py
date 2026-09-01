import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from asr_r1.m1_offline_audit import _network_syscall_lines


class M1OfflineAuditTest(unittest.TestCase):
    def test_empty_trace_has_no_network_syscalls(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "trace"
            trace.write_text("", encoding="utf-8")
            self.assertEqual([], _network_syscall_lines(trace))

    def test_any_nonempty_trace_line_is_a_violation(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "trace"
            trace.write_text(
                "123 socket(AF_INET, SOCK_STREAM, IPPROTO_IP) = 3\n",
                encoding="utf-8",
            )
            self.assertEqual(1, len(_network_syscall_lines(trace)))


if __name__ == "__main__":
    unittest.main()
