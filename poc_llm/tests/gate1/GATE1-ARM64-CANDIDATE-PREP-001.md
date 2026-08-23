# GATE1-ARM64-CANDIDATE-PREP-001 — Safe-Stop Preparation Checkpoint

- **Track**: ARM64 primary / `wip/m2-arm64-preflight`
- **Baseline SHA**: `bda47427cb17075caf74a22feaa61b556a2c04d7`
- **Authority**: `ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001`
- **Status**: `TWO LITERTLM P4 + P7 PASS / P6 CONDITIONAL / QWEN 0.5B DEFERRED`
- **Prepared delivery areas**: D1, D2, D8

## Acquired Candidate Artifacts

The controlled Git-ignored bundle contains all three proposed models and the previously
authenticated LiteRT-LM ARM64 API wheel. Model smoke execution has occurred, but no complete Gate1
candidate result has been produced.

| Item | Frozen identity | Preparation result |
| --- | --- | --- |
| Model | `CAND-LRT-Q25-05B-Q8-R1`; upstream revision `6c237a59eedeb06a821b21f0a59b03d346ac8bc3`; `Qwen2.5-0.5B-Instruct_multi-prefill-seq_q8_ekv1280.task` | authenticated; `DEFERRED` because the MediaPipe `.task` container is not generation-compatible with LiteRT-LM v0.16 Engine/Conversation |
| Model | `CAND-LRT-Q25-15B-Q8-R1`; upstream revision `19edb84c69a0212f29a6ef17ba0d6f278b6a1614`; `Qwen2.5-1.5B-Instruct_multi-prefill-seq_q8_ekv4096.litertlm` | authenticated; model smoke `PASS` |
| Model | `CAND-LRT-G4E2B-MOBILE-R1`; upstream revision `6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94`; `gemma-4-E2B-it.litertlm` | authenticated; model smoke `PASS` |
| Runtime | `litert_lm_api-0.16.0-py3-none-manylinux_2_27_aarch64.whl` | SHA-256 `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` authenticated by accepted preflight |

## Capacity and Resumable Acquisition Checkpoint

The root filesystem was expanded to approximately 30.5 GB. The former capacity blocker is resolved,
and all three model files are complete and authenticated against their frozen sizes and SHA-256
values. The files remain outside Git and are preparation inputs only; acquisition does not authorize
model load or constitute candidate evidence.

## ARM64 Append-Only Projection Scaffold

An independent `G1-ARM64-PRESCREEN-WIP-001` projection now admits only
`ubuntu-aarch64` and authenticates candidate, acquisition, strict-config, command and local
artifact identities. The append-only ARM64 protocol schema validates ARM64 READY identity. A real
LiteRT-LM adapter implements persistent engine lifecycle, single active generation, BUSY,
cooperative cancel, timeout, result normalization and shutdown; tests inject a fake backend and do
not load a model. A fail-closed smoke runner authenticates the execution SHA and ARM64 projection,
requires route isolation, owns the candidate process group, bounds READY/generation/TERM/KILL, and
records no model text. A locked measurement runner now schedules exactly 10 sessions for Qwen 1.5B
and 10 for Gemma, records native LiteRT benchmark metrics and peak RSS without retaining prompts or
model text, and adds model-backed BUSY, bounded cancellation, shutdown, and cleanup probes. Its
single batch wrapper keeps Qwen 0.5B excluded. ARM64 synthetic tests plus retained R5/M1 regressions
pass (66/66). This scaffold does not alter frozen R5 or create candidate evidence.

## First Model-Backed Smoke Finding

Qwen2.5 0.5B reached authenticated READY in `1448.577 ms` under execution SHA
`ee8dbd06e6db25b9337b54a3c510035fff79f665`, proving model and XNNPACK CPU initialization. The first
generation returned protocol `ERROR` after `24.02 ms`; shutdown was therefore not requested, and the
runner bounded cleanup with SIGTERM, wait, and proof that the process group was absent. The sanitized
result is `FAIL`; raw stderr SHA-256 is
`b0871a4a69911655fa97fbe5537b9fa4a2b52f1204235a0d86f6085e6ea237f6`.

Review identified that the adapter had mapped the 128-input/16-output request envelope onto LiteRT
Engine's `max_num_tokens`, which the pinned API defines as total KV-cache capacity. The correction
left the model artifact's KV-cache default intact and continued to enforce 16 output tokens per
conversation. A regression test locks this boundary. A fresh-path rerun under execution SHA
`e2f71a5ddbe28adaba2b4ac8c9617fcfa222a477` nevertheless returned the same immediate protocol
`ERROR` after READY, so the KV-cache override was a real adapter defect but not the observed failure's
root cause. Both failed runs remain recorded and must not be reclassified.

The adapter now emits a sanitized failure diagnostic containing only failure stage, exception class,
and SHA-256 of the exception message. It never emits the exception message, prompt, or model output.
The third fresh-path run localized the failure to `send_message_async`, with cause class
`RuntimeError` and message SHA-256
`38495c0f8b88d89e77061ab14f56583a1081936d9ea24396cbe74a18d539bd58`. The message hash matched
neither Python binding fixed errors nor static native-library strings, identifying a dynamically
composed native streaming callback error.

The pinned LiteRT-LM v0.16.0 official Python example uses synchronous `send_message()`. The adapter
now follows that API while retaining generation in its worker thread and control-thread
`cancel_process()` for cancellation and timeout. A regression test rejects accidental async-stream
use. A fourth Qwen 0.5B run reached READY but the synchronous C API returned its fixed
`litert_lm_conversation_send_message failed` error. The `.task` begins with a ZIP container marker,
whereas both successful candidates carry the `LITERTLM` container magic. Qwen 0.5B is therefore
deferred until a native `.litertlm` artifact or approved conversion flow is available.

## Successful Native `.litertlm` Smokes

| Candidate | Startup to READY | Generation | Shutdown and cleanup | Result |
| --- | ---: | ---: | --- | --- |
| Qwen2.5 1.5B | `6673.523 ms` | `1790.669 ms` | ACK; exit 0; no TERM/KILL; process group absent | `PASS` |
| Gemma 4 E2B | `8584.138 ms` | `1754.206 ms` | ACK; exit 0; no TERM/KILL; process group absent | `PASS` |

These wall-clock smoke timings are promising feasibility signals on the 4-vCPU/4-GB UTM guest.
They do not establish TTFT, tokens/second, output-token count, peak RSS, long-input behavior or P4.

## Reviewed 20-Session ARM64 Measurement

Execution SHA `19aca08a83caacb19ce1fab10fa9961fe188dab2` completed 10 bounded sessions
for each active `.litertlm` candidate in the offline namespace. The frozen sanitized result hashes
are `0f55e6b6e71cee7b2d55b00c57224a83436ba7a424fa95a33bf6d75d3de82cfc`
for Qwen 1.5B and
`25c426cb685487cf38d6f9def3cfec7de6a490f3ddd32b34d303f0489e8d0ddf`
for Gemma.

| Candidate | Hot TTFT P50 / P95 | Hot decode P50 | Hot wall P50 / P95 | Peak RSS | P6 |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen2.5 1.5B | `814.259 / 928.259 ms` | `16.879 tok/s` | `1702.121 / 1919.596 ms` | unavailable because the original runner finalized early | `Conditional escalation`: no terminal frame within 500 ms |
| Gemma 4 E2B | `386.952 / 397.822 ms` | `19.657 tok/s` | `1154.295 / 1171.501 ms` | `2071472 KiB` | `PASS`: CANCELLED in `139.839 ms` |

Both candidates returned 16 output tokens in every measured session and passed the model-backed
BUSY probe. Gemma also proved clean shutdown with exit 0 and no TERM/KILL. Qwen's runner preserved
all 10 samples and proved bounded SIGTERM/wait cleanup with no process-group residue, but its raw
packet remains `FAIL`; review maps only the P6 finding to the contract-defined
`Conditional escalation` and does not rewrite that result. The measurement runner now retains
summary and RSS on this failure path and emits the explicit P6 disposition. A separate locked P7
packet is prepared to prove terminate/wait/rebuild/READY and post-rebuild generation.

This is a workstation pre-screen. It is not formal P4 because the contract's three warm-ups,
three cold samples and twenty hot samples were not executed, and it is not Pi/Gate 2 evidence.

## Qwen P7 Recovery Review

The locked P7 packet executed under SHA
`9b6c2a20f95695c26c6bb727f72d63be5c6b3860`; sanitized result SHA-256 is
`96cef6bd2f2fa776cf986747770e9463cbea1d9d216bf157eb3d385ccba9322e`.
P6 again produced no terminal frame within 500 ms and remains
`Conditional escalation`. Level 2 then sent SIGTERM, bounded the wait, observed exit `-15`
without SIGKILL, and proved the process group absent. Rebuild reached authenticated READY in
`4081.878 ms`, returned a real model-backed RESULT, acknowledged shutdown, exited 0 without
TERM/KILL and left no process group. The strict P7 result schema validates with no violations.

Qwen 1.5B therefore retains eligibility under the contract's P6 conditional rule because its full
P7 workstation proof passes. This does not convert P6 itself to PASS and is not Pi/Gate 2 credit.

Gemma's candidate-specific P7 packet executed under SHA
`2d5b1e9ad59258272a1f4581e733456261101bf2`; sanitized result SHA-256 is
`7d28f5fd539a1f236bc5e14ede2d42d54a1c523b7079612b6dc3bf807d7671dc`.
Unlike its earlier 139.839 ms cancellation PASS, this observation produced no terminal frame within
500 ms. Gemma P6 is therefore nondeterministic and conservatively classified
`Conditional escalation`. Level 2 sent SIGTERM, observed exit `-15` without SIGKILL, completed
wait/process-group-absence proof, rebuilt authenticated READY in `5727.829 ms`, returned a real
RESULT and shut down cleanly. Its strict P7 result also validates with no violations.

Both active candidates now pass the bounded workstation P7 proof and retain eligibility. Both carry
P6 conditional risk; Gemma additionally has one prior native-cancel PASS, but that success cannot
override the later timeout.

## Formal P4 Results

The locked P4 packet followed the frozen Gate1 method: one persistent authenticated process per
candidate, three discarded warm-ups, three cold samples and twenty hot samples using the fixed
128-input/16-output, temperature-zero envelope. It retains every sanitized native LiteRT metric
sample, calculates P50/P95 for wall time, TTFT, prefill and decode throughput, samples peak process
RSS, records model/runtime disk bytes, enforces the contract's 2.5 s TTFT P95 and 4 tok/s decode P50
decision rule, and proves clean shutdown. Qwen 0.5B and x86 inputs are excluded from the batch.

Both results validate against the locked schema and pass the P4 decision rule under execution SHA
`629f6136404366afc2db4b0e496bb261e2a920d6`.

| Candidate | Hot TTFT P50 / P95 | Hot decode P50 / P95 | Hot wall P50 / P95 | Peak RSS | Result SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen2.5 1.5B | `812.486 / 846.984 ms` | `16.930 / 17.190 tok/s` | `1703.930 / 1920.652 ms` | `2052192 KiB` | `9745a6091e000a97e07961609fb63454673adac1d0c7fdfeeccd264f52ef6634` |
| Gemma 4 E2B | `349.678 / 356.481 ms` | `22.301 / 22.574 tok/s` | `1025.415 / 1063.333 ms` | `2072316 KiB` | `a39aadef00aadae5b494898a88666caac93f05dcd12e5f4d2f09d1679fb072bf` |

Gemma is materially faster in TTFT, total wall time and decode throughput while measured process
peak RSS is nearly equal. Qwen's combined model/runtime artifacts are smaller
(`1644017274` vs `2634233466` bytes). These are UTM comparison results, not Pi acceptance.

## Long-Prompt, P5 and P8 Packet Preparation

The locked `G1-ARM64-LONG-P8-001` packet is ready for both active `.litertlm` candidates. It runs a
baseline and a longer fixed schema-valid prompt, requires a bounded increase in native prefill
tokens, then sends the same prompt through five independent conversations in one persistent engine.
P8 passes only when response hashes and prefill/decode/KV token counts remain stable across all five
turns. The report retains hashes and native metrics, never prompt or model text, and requires clean
shutdown plus process-group absence. Qwen 0.5B and x86 inputs remain excluded.

The frozen strict config permits only 16 output tokens and the observed model generations complete
far below the 15-second generation timeout. This packet therefore records P5 as
`INCONCLUSIVE_FIXED_16_OUTPUT_ENVELOPE` unless a real timeout occurs; it does not manufacture a
timeout or weaken the frozen config. The batch result is consequently expected to be overall
`INCONCLUSIVE` while long-prompt and P8 can independently pass. Hardware execution has not yet
occurred for this packet.

## Provenance and License Preparation

- Official LiteRT-LM `v0.16.0` source archive: size `451258203`; SHA-256
  `4a790f5c56e3622891d0784c2b153e53ba2d2a140f739e8dc6bff71613b78e07`; gzip integrity passed.
- The ARM64 API wheel metadata declares no `Requires-Dist` entries; the sanitized runtime bundle
  records an empty Python dependency closure and separately binds the embedded native library.
- Each model's frozen-revision `README.md` was retained outside Git and hashed. All three model
  cards declare `license: apache-2.0`; sanitized hashes and base-model identities are recorded in
  `arm64-model-license-metadata-v1.json`.

## Remaining Gate1 Work

- Execute and review the locked long-prompt/P8 batch for both active candidates.
- P5 timeout remains inconclusive under the frozen 16-output-token envelope; resolving it requires
  an approved test envelope or another naturally slow preapproved fixture.
- Runner-owned log hygiene, final result-schema validation, candidate comparison and finalist advice.
- Qwen 0.5B remains deferred and does not block the two active candidates.

## Immutable WIP Candidate Inputs

Three candidate-specific strict configs, acquisition manifests and WIP candidate manifests now bind
the fixed `/tmp/llm-poc-g1-arm64-001` staging root, canonical offline install/runtime argv and all
runtime/model/config/bundle hashes. The staged wheel and three models were copied and re-hashed; all
three pre-launch projections authenticate. The ARM64 WIP lock SHA-256 is
`b2a0d0b7fe503acc654e9a6fcc716ee3ce8e843503a03e8518ac45b51ca3fc6d`.

The first offline namespace installation attempt proved an isolated namespace but stopped because
the base Ubuntu Python has no `pip`. The replacement dependency-free, fail-closed wheel installer
has synthetic traversal/dirty-target coverage and subsequently passed in the operator-owned network
namespace (`net:[4026532352]`) with no IPv4 routes and no non-loopback IPv6 routes. The installed
runtime reports version `0.16.0`; native import passed; `liblitert-lm.so` is ARM aarch64, matches
SHA-256 `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4`, and all reported dynamic
dependencies resolve. The successful log SHA-256 is
`d408d1577b71e4e1a9b56b6e6833b07cc7af33c82b7619775b645537c5ced8ff`. This is an offline-install
pre-screen `PASS`, not an environment, model or candidate result.

The next bounded hardware work is the prepared long-prompt/P8 batch, followed by the ARM64 finalist
comparison. P5 remains explicitly inconclusive under the frozen envelope. The reviewed workstation
proofs must not be promoted to Pi or Gate2 evidence.
