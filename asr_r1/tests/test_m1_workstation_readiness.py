import unittest

from asr_r1.tools.check_m1_workstation_readiness import REPO_ROOT, verify


class M1WorkstationReadinessTest(unittest.TestCase):
    def test_current_tree_meets_static_development_contract(self) -> None:
        self.assertEqual([], verify(REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
