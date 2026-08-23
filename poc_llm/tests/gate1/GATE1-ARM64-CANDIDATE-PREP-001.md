# GATE1-ARM64-CANDIDATE-PREP-001 — Safe-Stop Preparation Checkpoint

- **Track**: ARM64 primary / `wip/m2-arm64-preflight`
- **Baseline SHA**: `bda47427cb17075caf74a22feaa61b556a2c04d7`
- **Authority**: `ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001`
- **Status**: `OFFLINE INSTALL PRE-SCREEN PASS / NO MODEL EXECUTION`
- **Prepared delivery areas**: D1, D2, D8

## Acquired Candidate Artifacts

The controlled Git-ignored bundle contains all three proposed models and the previously
authenticated LiteRT-LM ARM64 API wheel. No model was loaded and no candidate result was produced.

| Item | Frozen identity | Preparation result |
| --- | --- | --- |
| Model | `CAND-LRT-Q25-05B-Q8-R1`; upstream revision `6c237a59eedeb06a821b21f0a59b03d346ac8bc3`; `Qwen2.5-0.5B-Instruct_multi-prefill-seq_q8_ekv1280.task` | size `546660344`; SHA-256 `e608953f169aeb1bd7b9155fec2559825e08453fc209b84eda3a781ed0452fd2` authenticated |
| Model | `CAND-LRT-Q25-15B-Q8-R1`; upstream revision `19edb84c69a0212f29a6ef17ba0d6f278b6a1614`; `Qwen2.5-1.5B-Instruct_multi-prefill-seq_q8_ekv4096.litertlm` | size `1597931520`; SHA-256 `faa60663b333290c1496c499828b21d3e3254a788cacd8cce917ce0f761a2dc9` authenticated |
| Model | `CAND-LRT-G4E2B-MOBILE-R1`; upstream revision `6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94`; `gemma-4-E2B-it.litertlm` | size `2588147712`; SHA-256 `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` authenticated |
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
records no model text. ARM64 synthetic tests plus retained R5/M1 regressions pass (44/44). This scaffold
does not alter frozen R5, execute a model or create candidate evidence.

## Provenance and License Preparation

- Official LiteRT-LM `v0.16.0` source archive: size `451258203`; SHA-256
  `4a790f5c56e3622891d0784c2b153e53ba2d2a140f739e8dc6bff71613b78e07`; gzip integrity passed.
- The ARM64 API wheel metadata declares no `Requires-Dist` entries; the sanitized runtime bundle
  records an empty Python dependency closure and separately binds the embedded native library.
- Each model's frozen-revision `README.md` was retained outside Git and hashed. All three model
  cards declare `license: apache-2.0`; sanitized hashes and base-model identities are recorded in
  `arm64-model-license-metadata-v1.json`.

## Missing Immutable Inputs

- Fresh raw path, operator binding and immutable execution SHA for model-backed execution.
- Model-backed adapter lifecycle evidence; current adapter tests are synthetic only.

## Immutable WIP Candidate Inputs

Three candidate-specific strict configs, acquisition manifests and WIP candidate manifests now bind
the fixed `/tmp/llm-poc-g1-arm64-001` staging root, canonical offline install/runtime argv and all
runtime/model/config/bundle hashes. The staged wheel and three models were copied and re-hashed; all
three pre-launch projections authenticate. The ARM64 WIP lock SHA-256 is
`be70735aeb1a2cac289380ad39f7e9b0e23541803996f45a42c6230a05d3a4b4`.

The first offline namespace installation attempt proved an isolated namespace but stopped because
the base Ubuntu Python has no `pip`. The replacement dependency-free, fail-closed wheel installer
has synthetic traversal/dirty-target coverage and subsequently passed in the operator-owned network
namespace (`net:[4026532352]`) with no IPv4 routes and no non-loopback IPv6 routes. The installed
runtime reports version `0.16.0`; native import passed; `liblitert-lm.so` is ARM aarch64, matches
SHA-256 `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4`, and all reported dynamic
dependencies resolve. The successful log SHA-256 is
`d408d1577b71e4e1a9b56b6e6833b07cc7af33c82b7619775b645537c5ced8ff`. This is an offline-install
pre-screen `PASS`, not an environment, model or candidate result.

Until these inputs are committed and self-tested, model load, generation, performance measurement
and candidate evidence are prohibited. The next session resumes from this checkpoint; it must not
silently treat artifact acquisition or the accepted environment preflight as a candidate `PASS`.
