# M4A Tester verification — candidate 7aba071

## Identity and disposition

| Field | Value |
| :--- | :--- |
| Candidate SHA | `7aba0719e9f7858a68b44f28d2d99e3d3d2ef25d` |
| Tester run ID | `m4a-7aba071-20260828-p01` |
| Portable matrix | **Pass** |
| Pi acceptance run ID | `m4a-7aba071-20260829-pi01` |
| Target status | **Rejected — network syscall gate** |

Raw logs and machine-readable results remain Git-external under
`<tester-run-root>/m4a-tester-evidence-7aba071-20260828-p01/`. The candidate was
checked out detached and every protected path remained clean.

## Anti-flake re-verification

Before the matrix, Tester executed
`test_m4a_ipc_001_actual_asr_process_handles_coalesced_and_fragmented_input[False]`
in 20 independent CPython 3.11 pytest processes. All 20 passed. This directly
re-verifies the exit-oracle correction that rejected candidate `ed1b2cf`.

## Formal portable matrix

| Python | Result | Counts |
| :--- | :--- | :--- |
| CPython 3.11.16 | Pass | 167 passed; 0 failed/skipped/xfailed |
| CPython 3.12.3 | Pass | 167 passed; 0 failed/skipped/xfailed |
| CPython 3.13.15 | Pass | 167 passed; 0 failed/skipped/xfailed |

`matrix-index.json` has status `Pass`; all three result files bind candidate
`7aba0719e9f7858a68b44f28d2d99e3d3d2ef25d` and run
`m4a-7aba071-20260828-p01`. Each runner used a 120-second hard suite timeout,
the tracked 13-module M4A manifest, marker `not rpi`, an empty inherited
`PYTHONPATH`, and disabled third-party pytest entry-point autoload.

## Pi target re-verification

Designer froze the exact candidate after portable sign-off. Tester then rebooted
the Pi and recorded boot ID `64a0d1f8-04fe-4a84-a340-ad449ea28e57`. The clean
baseline had zero M4A processes, ALSA holders and ASR/TTS temp entries. A fresh
detached candidate checkout, native worker build, eight-wheel product install and
no-system-site-packages controller closure passed. The product preflight bound
the Accepted Audio identity, product lock, Matcha tree and notice checksums and
reported zero network attempts. Candidate target preflight also passed and bound
the portable index, CPython 3.13.5, hardware, config and product-preflight
checksums to the new target run.

The acceptance pytest subprocess completed seven of seven real-device cases in
170.911 seconds. ASR/TTS lifecycle, ALSA playback, 20-turn Audio-only resource
envelope, package checks and privacy scan all reached their test assertions;
cleanup finished with zero processes, ALSA holders and temp entries. The resource
draft recorded 20 turns, P99 latency 7252.582 ms, peak system-used memory
866.781 MiB, zero cleanup counters and `throttled=0x0`.

The formal runner nevertheless rejected the run before result/card finalization.
Its full-tree network trace contained 54 IPv4/IPv6 records across 18 TIDs,
including 24 DNS connects to `192.168.0.1:53` returning `ENETUNREACH`.
Consequently `<pi-run-root>/acceptance/result.json` does not exist;
`<pi-run-root>/acceptance/accept-failure.json` is the authoritative formal
result. The seven JUnit passes and unsigned draft cards are diagnostic details,
not acceptance evidence.

The pattern matches the existing ONNX Runtime 1.29.0 telemetry investigation in
`docs/reviews/IR_dev_M4_I.md`: the persistent VAD process can cross its telemetry
uploader interval during the 20-turn run. A loopback-only namespace blocks
egress but does not satisfy the zero-attempt contract. Tester returned
`TRDEV-M4A-005` with the required production environment invariant and locked
re-verification conditions.

## Gate disposition

Portable sign-off remains valid evidence for the immutable rejected candidate,
but candidate `7aba0719…` is not acceptable for M4A Gate 3. The network fix changes
protected source/tests, so Developer must create a new append-only candidate and
the workflow returns to the complete three-minor portable matrix before another
fresh Pi preflight/acceptance. No inheritance index or final M4A sign-off is
produced from this rejected run.
