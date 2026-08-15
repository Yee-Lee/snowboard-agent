"""M3 Test ID inventory and planned pytest traceability.

The inventory is intentionally separate from executable evidence: a Pending
record is a scheduling fact, never a passing test result.  Work packages move
records into ``M3_TEST_NODES`` only after their product assertions exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Platform = Literal["DEV-PY311", "RPI-NATIVE"]

_IMPLEMENTED_IDS = frozenset({
    "M3-HAL-001", "M3-HAL-002", "M3-AUD-001", "M3-AUD-002",
    "M3-AUD-003", "M3-AUD-004", "M3-CFG-002",
    "M3-DSP-001", "M3-DSP-002", "M3-CAM-001", "M3-GPIO-001",
    "M3-GPIO-002", "M3-ARB-001", "M3-ARB-002", "M3-ARB-003",
    "M3-ARB-004", "M3-ARB-005", "M3-ARB-006", "M3-ARB-007",
    "M3-REND-001", "M3-REND-002", "M3-REND-003", "M3-REND-004",
    "M3-REND-005", "M3-SCN-001", "M3-CFG-001", "M3-REG-001",
    "M3-BTN-001", "M3-BTN-002", "M3-BTN-003", "M3-BTN-004", "M3-BTN-005",
    "M3-AUDI-001", "M3-AUDI-002", "M3-AUDI-003", "M3-AUDI-004",
    "M3-CAMI-001", "M3-CAMI-002", "M3-CAMI-003",
    "M3-DSPI-001", "M3-DSPI-002", "M3-DSPI-003", "M3-DSPI-004",
    "M3-DSPI-005", "M3-DSPI-006", "M3-GPIOI-001", "M3-GPIOI-002",
})

_BLOCKED_IDS = frozenset()


@dataclass(frozen=True, slots=True)
class M3TestRecord:
    """One approved M3 test requirement and its future executable location."""

    test_id: str
    platform: Platform
    planned_node: str
    status: Literal["Pending", "Blocked", "Implemented"] = "Pending"


def _records(
    platform: Platform, test_file: str, *test_ids: str
) -> tuple[M3TestRecord, ...]:
    return tuple(
        M3TestRecord(
            test_id=test_id,
            platform=platform,
            planned_node=(
                f"{test_file}::test_{test_id.lower().replace('-', '_')}"
            ),
            status=(
                "Implemented" if test_id in _IMPLEMENTED_IDS
                else "Blocked" if test_id in _BLOCKED_IDS
                else "Pending"
            ),
        )
        for test_id in test_ids
    )


M3_TEST_RECORDS: tuple[M3TestRecord, ...] = (
    *_records("DEV-PY311", "tests/test_m3_hal_001_002.py", "M3-HAL-001", "M3-HAL-002"),
    *_records("DEV-PY311", "tests/test_m3_aud_001_002_003_004.py", "M3-AUD-001", "M3-AUD-002", "M3-AUD-003", "M3-AUD-004"),
    *_records("DEV-PY311", "tests/test_m3_dsp_001_002.py", "M3-DSP-001", "M3-DSP-002"),
    *_records("DEV-PY311", "tests/test_m3_cam_001.py", "M3-CAM-001"),
    *_records("DEV-PY311", "tests/test_m3_gpio_001_002.py", "M3-GPIO-001", "M3-GPIO-002"),
    *_records("DEV-PY311", "tests/test_m3_arb_001_002_003_004_005_006_007.py", "M3-ARB-001", "M3-ARB-002", "M3-ARB-003", "M3-ARB-004", "M3-ARB-005", "M3-ARB-006", "M3-ARB-007"),
    *_records("DEV-PY311", "tests/test_m3_rend_001_002_003_004_005.py", "M3-REND-001", "M3-REND-002", "M3-REND-003", "M3-REND-004", "M3-REND-005"),
    *_records("DEV-PY311", "tests/test_m3_scn_001.py", "M3-SCN-001"),
    *_records("DEV-PY311", "tests/test_m3_cfg_001_002.py", "M3-CFG-001", "M3-CFG-002"),
    *_records("DEV-PY311", "tests/test_m3_reg_001.py", "M3-REG-001"),
    *_records("RPI-NATIVE", "tests/test_m3_btn_001_002_003_004_005_rpi.py", "M3-BTN-001", "M3-BTN-002", "M3-BTN-003", "M3-BTN-004", "M3-BTN-005"),
    *_records("RPI-NATIVE", "tests/test_m3_audi_001_002_003_004_rpi.py", "M3-AUDI-001", "M3-AUDI-002", "M3-AUDI-003", "M3-AUDI-004"),
    *_records("RPI-NATIVE", "tests/test_m3_cami_001_002_003_rpi.py", "M3-CAMI-001", "M3-CAMI-002", "M3-CAMI-003"),
    *_records("RPI-NATIVE", "tests/test_m3_dspi_001_002_003_004_005_006_rpi.py", "M3-DSPI-001", "M3-DSPI-002", "M3-DSPI-003", "M3-DSPI-004", "M3-DSPI-005", "M3-DSPI-006"),
    *_records("RPI-NATIVE", "tests/test_m3_gpioi_001_002_rpi.py", "M3-GPIOI-001", "M3-GPIOI-002"),
)


def pending_test_ids() -> tuple[str, ...]:
    """Return requirements neither implemented nor dispositioned as Blocked."""
    return tuple(record.test_id for record in M3_TEST_RECORDS if record.status == "Pending")


def blocked_test_ids() -> tuple[str, ...]:
    return tuple(record.test_id for record in M3_TEST_RECORDS if record.status == "Blocked")


def implemented_nodes() -> tuple[str, ...]:
    """Return executable pytest nodes only; Pending plans never run as evidence."""
    return tuple(
        record.planned_node
        for record in M3_TEST_RECORDS
        if record.status == "Implemented"
    )


def implemented_nodes_for(platform: Platform) -> tuple[str, ...]:
    return tuple(
        record.planned_node
        for record in M3_TEST_RECORDS
        if record.status == "Implemented" and record.platform == platform
    )
