# GATE1-ARM64-CANDIDATE-PREP-001 — Safe-Stop Preparation Checkpoint

- **Track**: ARM64 primary / `wip/m2-arm64-preflight`
- **Baseline SHA**: `bda47427cb17075caf74a22feaa61b556a2c04d7`
- **Authority**: `ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001`
- **Status**: `TWO LITERTLM MODEL SMOKES PASS / QWEN 0.5B DEFERRED`
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
records no model text. ARM64 synthetic tests plus retained R5/M1 regressions pass (46/46). This scaffold
does not alter frozen R5 or create candidate evidence.

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

## Provenance and License Preparation

- Official LiteRT-LM `v0.16.0` source archive: size `451258203`; SHA-256
  `4a790f5c56e3622891d0784c2b153e53ba2d2a140f739e8dc6bff71613b78e07`; gzip integrity passed.
- The ARM64 API wheel metadata declares no `Requires-Dist` entries; the sanitized runtime bundle
  records an empty Python dependency closure and separately binds the embedded native library.
- Each model's frozen-revision `README.md` was retained outside Git and hashed. All three model
  cards declare `license: apache-2.0`; sanitized hashes and base-model identities are recorded in
  `arm64-model-license-metadata-v1.json`.

## Remaining Gate1 Work

- Model-backed cold/hot TTFT, tokens/second, output-token count, peak RSS and disk measurements.
- Longer fixed prompt, timeout, cancel, BUSY, failure recovery and rebuild probes.
- At least 20 combined sessions across the two active `.litertlm` candidates.
- Runner-owned log hygiene, final result-schema validation, candidate comparison and finalist advice.
- Qwen 0.5B remains deferred and does not block the two active candidates.

## Immutable WIP Candidate Inputs

Three candidate-specific strict configs, acquisition manifests and WIP candidate manifests now bind
the fixed `/tmp/llm-poc-g1-arm64-001` staging root, canonical offline install/runtime argv and all
runtime/model/config/bundle hashes. The staged wheel and three models were copied and re-hashed; all
three pre-launch projections authenticate. The ARM64 WIP lock SHA-256 is
`b869e1279364cedba088458182bd2699783955d626abbbf29c1001e08673384f`.

The first offline namespace installation attempt proved an isolated namespace but stopped because
the base Ubuntu Python has no `pip`. The replacement dependency-free, fail-closed wheel installer
has synthetic traversal/dirty-target coverage and subsequently passed in the operator-owned network
namespace (`net:[4026532352]`) with no IPv4 routes and no non-loopback IPv6 routes. The installed
runtime reports version `0.16.0`; native import passed; `liblitert-lm.so` is ARM aarch64, matches
SHA-256 `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4`, and all reported dynamic
dependencies resolve. The successful log SHA-256 is
`d408d1577b71e4e1a9b56b6e6833b07cc7af33c82b7619775b645537c5ced8ff`. This is an offline-install
pre-screen `PASS`, not an environment, model or candidate result.

The next round advances only Qwen 1.5B and Gemma into bounded Gate1 measurement. These model-smoke
passes must not be promoted to complete Gate1 candidate `PASS`, P4 `PASS`, or Gate2 evidence.
