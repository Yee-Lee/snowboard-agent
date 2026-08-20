# M4A Gate 1B ACK-002 whisper.cpp Q8 partial diagnostic

Status: `REVIEWED — STRONG NO-GO SIGNAL / NOT FORMAL GATE EVIDENCE`

## Delivery contribution

This packet advances final-checklist candidate identity, Pi 5 build, preliminary
ASR quality/performance, determinism, thermal, security and cleanup evidence for
the ACK-002 Q8 primary. It does not complete the frozen 20-repetition
qualification, reject the row formally, unlock Q5, close lifecycle, or claim
Gate 2A PASS.

## Test packet and binding

| Field | Reviewed value |
| --- | --- |
| Test ID | `M4A-G1B-ASR-RECOVERY-Q8-PARTIAL-001` |
| Delivery requirement | Final checklist sections 3 and 4; preliminary M4A P2/P3/P7/P8/P12 |
| POC SHA | `1b29f685de64970f6abbc12a0820a2ef4ec0a444` |
| Platform | Raspberry Pi 5 Model B Rev 1.1, aarch64, Debian 13, kernel `6.12.47+rpt-rpi-2712` |
| Candidate | `asr-whispercpp-small-q8_0-1.9.2`; whisper.cpp `1.9.2`; four threads; one persistent worker; multilingual small Q8_0 |
| Source / model | Source SHA-256 `988945d81af6abcf52d5e8034f516c74ffc61057c32c3a4b84f3451c2c7e5e47`; model SHA-256 `49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f` |
| Build | Isolated CPU-only build report SHA-256 `6e4778ff9861b4025d5e48ff8d6db2f2a15bd681a30b0788d4bead0e642c2c17`; binary SHA-256 `caa7184b34f56a5dcbfd97a564be6d0ee822b4da19ed8b329c1e0fdc98b501fa` |
| Fixture | 50 delivered Option A WAVs; manifest SHA-256 `1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2` |
| Method | No cold suites; three unscored single-fixture warmups; two complete 50-item hot cycles; nearest-rank percentiles; 15-second per-inference timeout |
| Raw report | External controlled return `m2/20260820T055755Z-whispercpp-q8-partial-1b29f68/report.json`; 67,496 bytes; SHA-256 `1c880408c4d7b4fc9a8e46dbc0e31b242227ad7c56fbb5add11cfed1c60232a4` |
| Command | `bash poc_audio/tools/run_m4a_whispercpp_qualification.sh ... --diagnostic-hot-repetitions 2` with exact artifact, fixture, binary, build-report, new work and output paths |

Artifact preflight verified the exact source, Q8 model and three notices. The
isolated build retained all frozen CPU-only CMake flags, and `ldd` listed only
the standard C/C++ runtime. The diagnostic validator independently passed after
the raw report was copied back with the same SHA-256.

## Reviewed observations

| Gate or observation | Partial result | Disposition |
| --- | --- | --- |
| Taiwan-Mandarin core CER `<= 20%` | `9.502262%` | threshold observed met; not gate PASS |
| Overall sentence correctness `>= 70%` | `28%` | strong quality failure signal |
| Hot final-transcript p50 / p95 / max | `10.950 / 11.080 / 11.125 s` | strong failure signal against `<= 1.5 s` |
| Hot RTF p50 / p95 / max | `1.390565 / 1.831987 / 1.835854` | threshold observed met; not gate PASS |
| Peak RSS / Q5 trigger | `554 / 1250 MiB` | below resource trigger |
| Model load | `120.192 ms` | observation |
| Determinism | 50 fixtures; maximum one hypothesis hash per fixture across two cycles | threshold observed met; not gate PASS |
| Thermal | `35.85 C` before, `55.1 C` after; `throttled=0x0` both | observation |

Category CER was 33.540373% for code-switch, 20.634921% for dates,
35.955056% for numbers, 19.402985% for product terms, and 9.502262% for
Taiwan-Mandarin. The result completed 100 measured inferences. All report-level
gate fields remained false because this packet is intentionally ineligible for
formal gate claims.

## Interrupted formal run and lifecycle finding

The initially started frozen three-cold/twenty-hot run was stopped at the User's
direction after three cold suites and part of the hot stage. It produced no
final JSON and is not evidence for a quality or performance disposition.
Interrupting the local SSH transport did not terminate remote runner PID 4972,
Python PID 4978 or worker PID 12276. The controller inspected their exact
process groups, sent TERM only to groups 4972 and 12276, and then confirmed all
three PIDs and audio-device owners were zero. This is a retained lifecycle
finding; remote transport interruption is not yet self-cleaning.

## Security, cleanup and disposition

The completed diagnostic emitted no raw transcript or PCM, opened no audio
device, and performed no speaker playback. Its final child, thread, iterator,
stream and device-owner counters were all zero; the worker did not require
force-abort. An independent post-run process and `fuser` check also returned no
owner.

Q8 shows a strong no-go signal under the approved Pi/4-thread profile because
overall sentence correctness and hot final-transcript latency are far outside
the frozen boundaries. Q5 remains prohibited: the ACK requires a reviewed,
complete Q8 quality PASS before fallback, while this partial result is
gate-ineligible and its quality observation fails. The 20-repetition formal Q8
qualification remains incomplete; M2 ASR is therefore not formally closed.
