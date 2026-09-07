# DELIVERY-P9-SURROGATE-SPEC-001

**Date**: 2026-08-23
**From**: Core Designer
**To**: Audio POC Team (M4a)
**Subject**: M4A-P9 M4b (LLM) Resource Reservation Surrogate Specification
**Status**: `OFFICIALLY DELIVERED — READY FOR AUDIO POC INTAKE`
**Authority**: `DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001` §D04 & §5
**Upstream Reference**: `RESP-LLM-POC-P9-SURROGATE-ENVELOPE-001`

---

## 1. Purpose and Boundary

Per `DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001` §D04, Core Designer hereby delivers the official
versioned, deterministic surrogate specification for **M4A-P9** (Co-residency Resource Reservation).

### Boundaries:
1. **Audio POC Planning Input Only**: The surrogate provides a deterministic resource envelope representing
   a resident LLM runtime on Raspberry Pi 5 4GB. It proves that Audio finalists can operate concurrently
   within the memory, CPU, and thermal budget.
2. **No LLM Gate 2B Credit**: Surrogate execution does not produce LLM Gate 2B combined acceptance or
   product milestone PASS. Real combined system validation remains governed by Core Gate 3 and LLM Gate 2B.
3. **No Quality / Semantic Simulation**: The surrogate allocates and holds resource budgets; it does not
   simulate token generation semantics or LLM response quality.

---

## 2. Deterministic Resource Envelope

Based on the conservative model-backed evidence provided in `RESP-LLM-POC-P9-SURROGATE-ENVELOPE-001`,
the surrogate specification is locked as follows:

| Parameter | Specification | Description / Justification |
| :--- | :--- | :--- |
| **Process Topology** | 1 independent child process | Run in a dedicated process group |
| **Memory Allocation** | **`2304 MiB`** (Process RSS) | Allocated, touched, and held continuously from `READY` through `SHUTDOWN` |
| **CPU Allocation** | **4 cores / up to 400% synthetic load** | Active during the simulated inference load phase |
| **Startup Delay to READY** | **`6.0 seconds`** | Bounded initialization delay; protocol READY timeout is `10.0 seconds` |
| **Simulated Inference Phase** | **`6.0 seconds`** | Synthetic compute burst per simulated conversation turn |
| **System Capacity Gate** | **`system_used <= 3584 MiB`** | `system_used = MemTotal - MemAvailable`; mandatory on 4GB Pi 5 (`swap=0`) |
| **Cleanup Verification** | Zero process/FD/thread residue | Bounded `SIGTERM` -> wait -> `SIGKILL` (if needed) -> zero orphan processes |

---

## 3. Reference Surrogate Implementation / Runner

Audio POC can implement the surrogate using the following reference Python script structure or integrate it
directly into `poc_audio/tools/run_m4a_reservation.sh`:

```python
#!/usr/bin/env python3
"""Deterministic M4b LLM Residency Surrogate for Audio M4A-P9."""

import mmap
import os
import signal
import sys
import time
from concurrent.futures import ProcessPoolExecutor

RESERVE_MIB = 2304
PAGE_SIZE = 4096


def _cpu_worker(duration_sec: float) -> None:
    end_time = time.time() + duration_sec
    while time.time() < end_time:
        _ = 12345 * 67890


def main() -> None:
    # 1. Allocate and touch 2304 MiB memory
    total_bytes = RESERVE_MIB * 1024 * 1024
    buf = mmap.mmap(-1, total_bytes, mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS, mmap.PROT_READ | mmap.PROT_WRITE)
    for offset in range(0, total_bytes, PAGE_SIZE):
        buf[offset] = 1

    # 2. Simulate startup delay (6s) then announce READY
    time.sleep(6.0)
    sys.stdout.write("SURROGATE_READY\n")
    sys.stdout.flush()

    # 3. Handle signals cleanly
    running = True
    def _sig_handler(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    # 4. Main loop: simulate periodic inference load when triggered or run background load
    while running:
        time.sleep(0.5)

    # 5. Cleanup
    buf.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
```

---

## 4. Evaluation and Decision Rules (M4A-P9)

1. **PASS**:
   - Audio VAD, ASR, and TTS finalists execute successfully while the surrogate is actively holding
     `2304 MiB` and generating simulated compute bursts.
   - Throughout the run on Raspberry Pi 5 (4GB, `swap=0`), `system_used` does not exceed `3584 MiB`.
   - Zero OOM killer activations, zero kernel crashes, zero unhandled audio xruns.
   - Post-run cleanup terminates the surrogate process group with zero residual processes.
2. **FAIL**:
   - System crashes, OOM killer triggers, `system_used > 3584 MiB`, or Audio finalists fail under
     co-residency pressure.
3. **BLOCKED**:
   - Raspberry Pi 5 test environment is missing, `swap != 0`, or surrogate configuration is modified.

---

## 5. Handoff Status Update

With the issuance of this document:
- Dependency `M4A-G1-D04` is **RESOLVED**.
- Audio POC is authorized to unblock M4A-P9 preparation in their test matrix.
