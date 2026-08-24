# M3-RISK-FOCUSED-QUALIFICATION-REVIEW-001

Status: `USER APPROVED FOR PUBLICATION — READY FOR GATE 2A RETURN`

## Scope and identity

This review advances delivery-checklist sections 4 and 5 and the M3 exit gate. It
reviews the final Raspberry Pi 5 run without changing the accepted packet, gates,
fixtures, M3.1 boundary or candidate identities.

| Field | Exact value |
| --- | --- |
| Packet | `M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001` |
| Audio execution SHA | `f7b9694d1477f26513880526e0718d2b3c5766b3` |
| Core HAL execution SHA | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| Core packet ACK commit | `cae21217b2f7d812511bde77edb2cd1eb65e8f06` |
| Packet manifest SHA-256 | `64efb3bf3299ad8d017914f307d70dedd8a4bcf88d74e23a87911fcf0ddb65f3` |
| Hardware | Raspberry Pi 5 Model B Rev 1.1; VoiceHAT `hw:0,0`; target mic/speaker |
| Product distance | `0.8–1.0 m`, as confirmed by User |
| Controlled session | `controlled://audio-m3/20260824-r3` |

The fail-closed summary accepted exactly 22 unique results with one Audio SHA and
one Core SHA. It contains `18 PASS`, `0 FAIL`, and four intentionally
human-reviewed `INCONCLUSIVE` results: VAD set, direct ASR, HAL-path ASR and TTS.
Those four runner dispositions do not indicate execution failure; each runner
requires the review below before publication.

## Reviewed draft disposition

| Area | Evidence | Proposed disposition |
| --- | --- | --- |
| Capture | Ten fixed cases completed; final five speech captures use `f7b9694...`; every capture cleanup delta is zero | `PASS` |
| VAD | All five speech items retained; low-volume start retained; natural-pause intervals merged into one bounded utterance; 60 s silence, device-start silence, impact and cough produced zero events; playback speech was detected | `PASS` |
| Direct ASR | Five non-empty outputs; three exact, normal sentence edit distance 1, pause sentence edit distance 3; p50/p95 latency `1333.591/1363.075 ms`; peak RSS `285.531 MiB` | `PASS` recommended after semantic review |
| HAL/VAD ASR | Three exact, normal sentence edit distance 1, pause sentence edit distance 1; no paired item regressed versus direct PCM and pause improved; p50/p95 latency `1330.243/1366.650 ms`; peak RSS `284.500 MiB` | `PASS` recommended |
| TTS | Six native 16 kHz mono S16_LE sequences completed physical Core AudioOutput playback; User scored all six `5/5`, confirmed publication with no critical meaning-changing misread, and cleanup delta was zero | `PASS` |
| PCM output | Isolated recovery playback completed through the pinned Core drain path with zero cleanup | `PASS`; the earlier overlapping capture/playback cleanup failure remains preserved |
| Lifecycle | Start/stop, reopen ×5, invalid input, invalid output, ASR/TTS cancellation and controlled force-abort all completed within bounds with final cleanup zero | `PASS` |
| Offline | VAD, direct ASR, HAL ASR, TTS and candidate lifecycle ran in an isolated network namespace with loopback down | `PASS` |

The controlled semantic diagnostic retained raw text outside Git. Its sanitized
review is: low-volume, code-switch and product-term items were exact on both paths;
the normal command had one intent-preserving character substitution on both paths;
the pause item improved from three edits on direct PCM to one edit through the
HAL/VAD path and retained the intended pause concept. No reproducible critical
semantic misrecognition or category-wide paired regression was found. Small Q8 is
therefore not activated.

## Frozen-gate review

- The unchanged Silero profile is `0.5/0.35`, 250 ms minimum speech, 160 ms startup
  mask, 500 ms close, and 500/600 ms capture padding. No gain, pre-roll or threshold
  change was applied after observing results.
- The low-volume case at the target product distance produced one retained event and
  exact ASR on both direct and HAL paths. The observed low microphone level does not
  establish an M3.1 blocker.
- Base Q8 used the fixed P0 prompt, four threads and greedy decoding. The HAL path did
  not cause a material regression, so the fallback trigger is false.
- Matcha used its pinned archive and Vocos identities. M2 performance evidence remains
  applicable: first-buffer p95 `285.098 ms`, generation RTF p95 `0.112776`, peak RSS
  `227.531 MiB`, 49.05 °C end temperature and `throttled=0x0`. M3 adds target-speaker
  playback and six-prompt User review.
- ASR isolated resource/thermal evidence is inherited from the accepted Pi M2 packet;
  M3 target captures add paired HAL quality, `~1.37 s` worst observed five-item
  latency, `<=285.531 MiB` peak RSS, offline proof and cleanup.
- Final shutdown check found no test worker or audio-device owner, flushed evidence
  with `sync`, and reported `throttled=0x0`.

## Rejected and superseded evidence

- The first direct-ASR attempt at superseded Audio SHA `25e263b...` remains `FAIL`
  because of the scoring-manifest packaging path; it was not rewritten or promoted.
- The overlapping capture/direct-PCM attempt remains `FAIL` because capture still
  owned the input device at the PCM cleanup snapshot. The isolated recovery remains
  the selected result.
- The first LIFE-03 result remains `FAIL` for a one-thread delta. A named-thread and
  `/proc/self/task` diagnostic found only the main thread from completion through two
  seconds; append-only recovery then passed with zero delta. No gate was relaxed.

## Evidence checksums and storage

| Evidence | SHA-256 |
| --- | --- |
| 22-result draft summary | `8fdaad48f829dde784db7f4c5f9410a3a18539360ef790d5b4994ad2c90e06ca` |
| Final VAD result | `64e1404490133a351e4e2abd82e0ff0be1e2a37fd44745adee90e039ac0142b4` |
| Final direct-ASR result | `1883b1e4c85f85eca282537dd7ccb24488807f579a1c81fa91a001e11bd18c50` |
| Final HAL-ASR result | `23a3e43413852c575141b52c947edde268969cd3a1d028770e718f9fb003c650` |
| Paired source fixture lock | `703de09992914ab39f78174121e1e33e664f511114c280ab79d5f7ab226787ed` |

The complete controlled evidence remains on the Pi under
`/home/yee/workspace/poc_audio/m3-session-20260824-r3/controlled`. The four principal
sanitized files are also preserved in the workstation's Git-ignored
`poc_audio/artifacts/m3-session-20260824-r3-final-f7/` directory. No raw audio or raw
transcript is added to Git.

## Recommendation and remaining authority

User approved publication on 2026-08-24. The reviewed VAD, base-Q8 ASR and Matcha
TTS rows are published as M3 `PASS` and advance as the unique M4 finalists. Small Q8
and M3.1 are not activated. Audio submits one complete Gate 2A return packet to Core
for ACK.

Core must ACK the committed Gate 2A return SHA before M3 is marked `COMPLETE`. P9
remains separately recorded as Core accepted and
Audio integration unblocked but not executed; it does not masquerade as LLM credit.
M4 and `POC Accepted` are not declared by this review.

## Append-only Gate 2A closure

Core commit `5aac035d25f6498c3c0affe1ace4afd7de8f7254` subsequently issued
`RESP-AUDIO-M3-GATE2A-MECHANICAL-ACK-001` with status
`ACKNOWLEDGED — GATE 2A CLOSED`. It confirmed the evidence/return commits, exact
Audio/Core execution SHAs, three finalists and unchanged M4/legal/P9 boundaries.
This closes M3; P9 execution and combined Gate 2B validation remain M4 work.
