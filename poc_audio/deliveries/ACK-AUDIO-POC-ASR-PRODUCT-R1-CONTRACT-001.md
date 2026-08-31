# ACK-AUDIO-POC-ASR-PRODUCT-R1-CONTRACT-001

- **In response to**: `DELIVERY-AUDIO-POC-ASR-PRODUCT-R1-CONTRACT-001`
- **Status**: `RECEIVED / AR1M0 INTAKE OPEN / EXECUTION NOT STARTED`
- **Date**: 2026-08-31
- **Contract SHA-256**:
  `25236948bad47de80c72cfb68e62f83d1195e27bea2905c97e76b1df33cda6d7`
- **Branch base**: `audio_m4` /
  `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`
- **POC branch**: `asr_r1`
- **Research owner**: Audio POC Team
- **Product decision owner**: User

## Receipt

Audio POC accepts the outcome contract without changing its product question.
The authorized research will determine whether a new low-latency, local,
streaming ASR pipeline is feasible on Raspberry Pi 5 CPU-only hardware and is
worth continued Core development toward `ALPHA.R1`.

This receipt opens `AR1M0` intake only. It does not complete readiness, authorize
a Core merge, establish an `ALPHA.R1` baseline, inherit prior M4 acceptance
credit, or claim that candidate execution has started. The existing `audio`
branch and `audio_m4` tag remain the immutable historical Audio POC line.

## Agreed research boundary

The initial official-model candidates are:

1. `sherpa-onnx-streaming-zipformer-zh-int8-2025-06-30`;
2. PengChengStarling Multilingual Zipformer RNN-T; and
3. WeNet U2++ Conformer.

Exact identities for the second and third checkpoints, and exact official
runtime identities for every candidate, remain `PENDING AR1M0/AR1M1 LOCK`.
Each candidate will use its official runtime first. Official artifacts are the
named baselines; a bounded, reproducible INT8 conversion or other officially
supported conversion is permitted only after evidence shows that a valuable
candidate needs it.

Formal execution is Raspberry Pi 5 CPU-only. Models remain resident while each
utterance uses a fresh or reset streaming session. Native runtime measurements
isolate engine capability; a thin POC Python adapter measures Snowboard-relevant
integration cost. Product code and the Snowboard composition root remain
unchanged.

Whisper.cpp 1.9.2 base Q8 with the accepted M4 configuration is the current
non-streaming control. Silero remains its accepted VAD control. Streaming
candidates may use the VAD or endpoint method that produces their best
evidence-backed product pipeline; ASR-core and endpoint costs will be reported
separately.

Post-process and second-scorer work is exploratory only. AR1M1 will investigate
feasible directions and prove a fake interface scaffold. AR1M2 may run small
diagnostic probes, but no real post-process component enters AR1M3 or the formal
comparison with Whisper.

## Evaluation boundary

Semantic and intent correctness is primary. Exact sentence correctness and
CER/WER are supporting measures. The scorecard also records English entity and
code-switch accuracy, RTF, first-partial latency, speech-end-to-final latency,
RSS/PSS, simplified partial-revision observations, and N-best readiness.

No single result automatically eliminates a candidate. All results remain in
the evidence. Audio POC supplies a reproducible comparative recommendation;
User confirms whether the observed quality, latency, resource, and stability
trade-off is worthwhile.

Fixtures will be audited before reuse. Existing audio and identities are reused
where suitable; previously tuned material remains regression evidence, and only
coverage gaps receive minimal new data. Deterministic pre-recorded PCM provides
the common comparison layer. AR1M3 adds target-microphone sessions, blind-first
review, offline and lifecycle testing, recovery, cleanup, and resource evidence.

## Milestones and identities

The authorized internal milestones are:

- `AR1M0`: Contract Intake and Research Readiness;
- `AR1M1`: Runtime Feasibility and Integration Readiness;
- `AR1M2A`: Official Baseline Evaluation;
- `AR1M2B`: Bounded Adjustment and Pipeline Selection;
- `AR1M3`: Integrated Product Qualification; and
- `AR1M4`: Product R1 Feasibility Outcome and Handoff.

AR1M2A and AR1M2B are substages of AR1M2. Completed milestone tags will be
`asr_r1_m0` through `asr_r1_m4`. A tag is created only after its milestone exit
is reviewed and complete; tags are annotated, immutable, and never moved.

AR1M4 completes only after User confirms the final report, Audio commits the
single `SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE` handoff, and Core closes
blocking evidence-intake findings. This completion does not accept any Core
product gate or select the eventual M5 baseline.

## Immediate AR1M0 control

Before legacy files are removed from the `asr_r1` working tree, Audio POC will
prepare a `keep / port / remove` manifest for User review. Until that review:

- no legacy tracked file is removed;
- no AR1 milestone is marked complete;
- no `asr_r1_m0` tag is created; and
- no real model acquisition, build, or execution begins.

The clean AR1 baseline will retain direct Git ancestry from `audio_m4` while
moving active milestones, tests, and code into an AR1-specific scope. Complete
legacy content remains recoverable from the immutable `audio_m4` tag.
