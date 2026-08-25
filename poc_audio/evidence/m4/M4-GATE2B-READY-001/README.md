# M4 Gate 2B technical completion report

Status: `READY FOR INTERNAL REVIEW / CORE RESPONSE REQUIRED`

Delivery ID: `POC-audio-DEL-2026-001-R1`

## Result

All frozen M4 runtime gates passed on Raspberry Pi 5 with Core HAL
`6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf`. User confirmed P9.1 PASS and,
after receiving the combined and corrected failure summaries, instructed the
team to complete the report, deliver it to Core and wait for response. The
three formal results are therefore published in this sanitized package.

| Test | Audio SHA | Reviewed result | Evidence |
| --- | --- | --- | --- |
| P9.1 realistic turn residency | `8be3bc095b504b8eab1dfeb21b94173728b9656f` | PASS, 20/20; 3339.688 MiB peak within 3584 MiB; zero swap; 62.8 C; no throttling; cleanup zero | `controlled://audio-poc/m4/20260825/p9.1-8be3bc0`, SHA-256 `5883a6399c6d183d18bb7fb7a98fc7a60b6b42396fd5bde46168ae625e3ac880` |
| Independent combined | `8be3bc095b504b8eab1dfeb21b94173728b9656f` | PASS, 20/20; all VAD/ASR/TTS SUCCESS; offline; 979.109 MiB; 58.95 C; no throttling; cleanup zero | `controlled://audio-poc/m4/20260825/combined-8be3bc0`, SHA-256 `c48adb395eae6db5ae69c544be6ef1228ad331cd08091507c5186846199c4810` |
| Failure/recovery | `26f33a3c371eee61df46924432839d0fa9ee3bf8` | PASS, 12/12 expected terminals and 12/12 same-finalist recoveries; all cleanup zero | `controlled://audio-poc/m4/20260825/failure-26f33a3`, SHA-256 `68d4f77b6f8a372f15c590c0fb4065154fa6c21c18aa1d2cf4a00b034a711862` |

P9.1 used 886 samples; its maximum sample-start gap was 0.254273 s and maximum
collection duration was 0.104933 s. Combined used 387 samples with a 0.253048 s
maximum start gap and 0.039213 s maximum collection duration. Both used an
isolated user/network namespace with loopback down. Failure cases covered VAD,
ASR and TTS error, timeout, cancel and force-abort. Error/timeout/cancel exercised
the actual finalists; force-abort alone used the controlled double.

## Finalists and legal disposition

| Domain | Technical finalist | License status | Gate 2B disposition |
| --- | --- | --- | --- |
| VAD | Silero 6.2.1 ONNX | MIT, pinned identity | Technical PASS; Core final-reference response required |
| ASR | whisper.cpp 1.9.2 base Q8, P0 greedy fixed prompt | MIT repository notice; model-lineage notice review retained | Technical PASS; Core must confirm final-reference and product packaging disposition |
| TTS | sherpa-onnx 1.13.5 Matcha zh/en + Vocos 16 kHz | Runtime and pinned author model card explicitly Apache-2.0; training-data lineage and complete component notices remain incomplete | Technical PASS; **Core data-lineage/notice disposition is blocking** |

[`M4-MATCHA-LICENSE-LINEAGE-AUDIT-001`](../M4-MATCHA-LICENSE-LINEAGE-AUDIT-001.md)
corrects the earlier broad wording: the pinned Matcha author model card does
publish Apache-2.0, and its exact ONNX hash matches the tested archive. What
remains open is the unnamed mixed Chinese/English training-data lineage and a
complete redistribution notice bundle. Audio POC does not have authority to
manufacture the legal conclusion. Core must explicitly clear the stated use
boundary or return an evidence-backed no-go/replacement request. Until then,
this package is not `POC Accepted`, no
`audio_m4` tag is created, and Core must not lock a product dependency.

## Evidence and conformance kit

- Machine-readable summary: `manifest.json` in this directory.
- Frozen packet: `poc_audio/manifests/m4_combined_packet.json`.
- Schemas: `poc_audio/schemas/m4_combined_packet.schema.json` and
  `poc_audio/schemas/m4_combined_result.schema.json`.
- Entry point: `poc_audio/tools/run_m4_combined.sh`; implementation is under
  `poc_audio/src/audio_poc/m4_*` with tests under `poc_audio/tests/`.
- M3 reviewed hardware result:
  `poc_audio/evidence/m3/M3-RISK-FOCUSED-QUALIFICATION-REVIEW-001.md`.
- ASR productization report: `poc_audio/evidence/m4/M4-ASR-SEMANTIC-PATTERNS-001.md`.
- Rejected evidence is preserved in `poc_audio/deliveries/`, including the P9.1
  catalog, sampler race/timestamp findings and failure executor-baseline finding.

The controlled raw JSON, audio, models, runtimes and private transcripts are
not committed. Reproduction requires the exact controlled fixtures/artifacts,
the execution SHA named per result, the pinned Core checkout and the formal
runner arguments recorded in the controlled result. Local packet validation is:

```bash
bash poc_audio/tools/run_m4_combined.sh validate
```

## Core blocking response required

Core must return one committed response containing:

1. Written intake of delivery ID, Audio branch/full delivery SHA, the two Audio
   execution SHAs, Core HAL SHA and all three controlled evidence hashes.
2. PASS/FAIL findings for the portable kit and all M4 exit-gate evidence.
3. A legal disposition for Silero, base-Q8 and Matcha; Matcha must acknowledge
   its pinned Apache-2.0 model card and explicitly decide the remaining
   data-lineage/notice risk plus internal/product/redistribution boundaries.
4. Either acceptance of the three final references or an evidence-backed no-go,
   replacement request or blocking-finding list.
5. Core response path, branch and full committed SHA.

Only after that response, closure of every blocking finding and Designer
approval may Audio mark M4 complete and create the immutable `audio_m4` tag.
