---
requestor: "Developer"
owner: "Designer"
status: "Open"
---

# IR_dev_M4_I — ONNX Runtime telemetry offline boundary and correction timing

## Decision requested

Please decide when Core should add the production-owned ONNX Runtime telemetry
disable invariant described below. Tester has now reported that formal acceptance
of candidate `7aba0719e9f7858a68b44f28d2d99e3d3d2ef25d` was rejected by the runner
because its trace still contains IPv4/IPv6 network syscalls. This request does
**not** authorize changing that immutable candidate or reusing the rejected run.

The USER preference was to keep the Tester run intact and, if this round was
rejected, include the telemetry correction in the next append-only candidate.
That trigger has occurred. Tester completed caller attribution in
`TRDEV-M4A-005`, locked the minimum correction below, and the USER directed
Developer to implement it immediately. Designer timing input is therefore no
longer needed to start the correction; the remaining design decision is whether
the production invariant must also be made explicit in the implementation design.

## Contract and dependency context

- `docs/test_spec/test_spec_M4.md` `M4A-OFF-001` requires a real Pi ASR + TTS +
  HAL session with no DNS query, TCP connect or HTTP request. Network isolation
  prevents successful egress but does not make an attempted syscall acceptable.
- `docs/implement/ch_m4a_audio_production.md` §2 says an audio child must not open
  network access, and §9 maps `M4A-OFF-001` to zero network attempts.
- Core locks the official Linux aarch64 `onnxruntime==1.29.0` wheel in
  `requirements/m4a/vad-rpi-cp313.json` and `audio-artifacts.json`.
- ONNX Runtime 1.29.0 introduced POSIX telemetry for Linux and other non-Windows
  platforms when telemetry is compiled in. Its official privacy guidance says
  official builds enable telemetry by default and use the Microsoft 1DS SDK.
  Full runtime disablement requires `ORT_DISABLE_TELEMETRY=1` **before** ONNX
  Runtime initializes.

Upstream references:

- <https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md>
- <https://github.com/microsoft/onnxruntime/releases/tag/v1.29.0>

## Developer forensic evidence

The rejected candidate `306dbc96585d1eef55ba0c6380e2eeceaa2057fc`
contained two concurrent behaviours:

1. buffered stdin plus `select()` stalled the ASR supervisor on coalesced
   `BEGIN + FRAME` input;
2. while that VAD process remained alive, its ONNX Runtime 1DS provider attempted
   network access.

The formal 600-second stalled trace contained 72 IPv4/IPv6 calls. A separate
30-second reproduction of the same rejected SHA remained `BUSY` and captured 27
calls. PID/process mapping assigned the calls to the VAD supervisor, not the Core
controller or native whisper worker. `gdb` breakpoints on `connect()` and
`getaddrinfo()` showed the call chain entering
`onnxruntime_pybind11_state.cpython-313-aarch64-linux-gnu.so` and resolving
`mobile.events.data.microsoft.com`; the observed DNS connects targeted
`192.168.0.1:53` and returned `ENETUNREACH`.

Calling Python `onnxruntime.disable_telemetry_events()` before session creation
did not change the rejected-SHA reproduction: it still emitted 27 calls. This is
consistent with upstream guidance that a minimal initialization event may occur
before the API can suppress non-essential events. The API is therefore not an
adequate zero-attempt control for Core.

## Current candidate boundary

Candidate `7aba0719e9f7858a68b44f28d2d99e3d3d2ef25d` contains the accepted raw-stdin
stall correction and the later CPython 3.11 exit-oracle correction. Developer
exact-candidate Pi diagnostics completed two ASR turns, finite no-endpoint, TTS
ALSA playback and recovery with zero IPv4/IPv6 calls. Those bounded diagnostics
show that the corrected process does not attempt network access during the short
run, but they do not independently prove that a longer persistent 20-turn or
600-second session cannot reach the telemetry uploader interval.

Tester reports that the formal acceptance runner rejected this candidate on the
network syscall gate. The run cannot be promoted, repaired in place or reused.
The rejected run used a reboot baseline and a fresh-build whisper worker with
hash prefix `c5e862d2…`; Developer's earlier short diagnostic used the persisted
worker with hash prefix `72f590be…`. This difference means the current failure
cannot be dismissed as reuse of Developer's worker artifact. Tester is now
mapping the new trace's PID, syscall, destination and executable and separately
checking whether the functional product cases completed. The completed finding
records that all seven product cases passed in 170.911 seconds, while the outer
trace found 54 IPv4/IPv6 records across 18 TIDs and attributed the signature to
the persistent VAD supervisor's ONNX Runtime 1DS telemetry.

No telemetry change is included in `7aba0719…`. Adding product source or tests
requires a new USER-approved append-only candidate, a new portable matrix and a
new formal acceptance run ID. `TRDEV-M4A-005` confirms the prior ONNX Runtime
finding and makes the correction a current acceptance requirement.

## Proposed minimum production correction

The lowest-cost robust correction does not rebuild ONNX Runtime, replace a wheel,
change the protocol or add a public config field:

1. force `ORT_DISABLE_TELEMETRY=1` in
   `sbd.adaptor.framed_child.offline_child_environment()`, overriding conflicting
   inherited values;
2. set the same invariant at the ASR supervisor and TTS worker module entry
   boundaries before any direct or indirect ONNX Runtime initialization;
3. add portable regressions proving a conflicting source value is overridden and
   the variable is already `1` when the VAD session/native engine initializes.

The child-entry guards cover direct diagnostic/tool invocation that bypasses the
normal parent launcher. This remains an internal launch invariant; no API, schema,
artifact checksum, dependency version or engine profile changes.

## Required verification if adopted

- Run the affected portable tests and complete CPython 3.11/3.12/3.13 M4a matrix
  against a new USER-approved append-only candidate.
- Reproduce a persistent ONNX Runtime process for longer than the prior 30-second
  trigger window under full-tree `strace`; require zero IPv4/IPv6 calls.
- Reboot the Pi and repeat fresh exact-SHA product/controller preflight plus the
  full real 20-turn ASR/TTS/HAL acceptance shape, not only the short Developer
  diagnostic; require zero DNS/connect/HTTP attempts and zero cleanup deltas.
- Keep the active Tester evidence and candidate SHA immutable; do not relabel or
  combine it with results from the future candidate.

## Requested Designer disposition

Tester rejection and USER direction resolve the implementation timing: the
minimum correction belongs in the next append-only M4a candidate. Please decide
whether `ch_m4a_audio_production.md` must explicitly name
`ORT_DISABLE_TELEMETRY=1` as a production launch invariant, or whether the
existing no-network child contract plus regression coverage is sufficient.

Developer is implementing the locked correction without modifying the rejected
candidate or asking Tester to restart/reuse the failed run. Any protected change
will be delivered only through a new USER-approved append-only candidate.
