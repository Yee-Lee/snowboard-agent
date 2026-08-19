# Gate 1 Candidate Pairing Preflight 001

- **Record ID**: `G1-CANDIDATE-PREFLIGHT-001`
- **Checked**: 2026-08-19
- **Milestone**: M1
- **Status**: `PROPOSED / MANIFESTS NOT ISSUED`
- **Purpose**: D1, D2, D3 and D8 provenance/licensing/aarch64 preflight

This record fixes the candidate proposal inputs that are supported by official metadata. It is not
a candidate manifest, artifact-acquisition record, benchmark authorization, finalist decision or
hardware result. No model was downloaded while preparing it.

## Runtime proposal

Use LiteRT-LM `v0.16.0` as the first M1 pairing revision. The official Git tag currently resolves
to commit `924e79c91542761242244e4f1651851f822e4cbb`; the PyPI packages declare Apache-2.0.
The platform API wheels required for the two Gate 1 Ubuntu environments are:

| Platform | Artifact | SHA-256 |
| --- | --- | --- |
| Ubuntu x86_64 | `litert_lm_api-0.16.0-py3-none-manylinux_2_27_x86_64.whl` | `a5d58ff8e1c14057d6a8c1f0333372bc685361e6311ea87bfa49fc131cb00a95` |
| Ubuntu aarch64 | `litert_lm_api-0.16.0-py3-none-manylinux_2_27_aarch64.whl` | `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` |

The CLI wheel SHA-256 is
`ae9a14fcbb5c8f3e53652b89624bf4473df0f858257fa70a31425ded14d90d8b`; its exact dependency
closure and hashes must be captured in the acquisition lock before offline execution. An official
`v0.16.1` release was published on 2026-08-18, but it is not silently substituted into this
proposal. Any upgrade requires a new pairing revision and affected regression rerun.

Official metadata:

- <https://github.com/google-ai-edge/LiteRT-LM/releases/tag/v0.16.0>
- <https://pypi.org/project/litert-lm/0.16.0/>
- <https://pypi.org/project/litert-lm-api/0.16.0/>

## Model proposal

| Candidate ID | Exact upstream revision and file | Artifact SHA-256 | Size | Quantization / license | Disposition |
| --- | --- | --- | ---: | --- | --- |
| `CAND-LRT-G4E2B-MOBILE-R1` | `litert-community/gemma-4-E2B-it-litert-lm@6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94` / `gemma-4-E2B-it.litertlm` | `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` | 2,588,147,712 | artifact embedded mobile quantization; Apache-2.0 | primary proposal |
| `CAND-LRT-Q25-15B-Q8-R1` | `litert-community/Qwen2.5-1.5B-Instruct@19edb84c69a0212f29a6ef17ba0d6f278b6a1614` / `Qwen2.5-1.5B-Instruct_multi-prefill-seq_q8_ekv4096.litertlm` | `faa60663b333290c1496c499828b21d3e3254a788cacd8cce917ce0f761a2dc9` | 1,597,931,520 | Q8/dynamic INT8 family; Apache-2.0 | fallback proposal |
| `CAND-LRT-Q25-05B-Q8-R1` | `litert-community/Qwen2.5-0.5B-Instruct@6c237a59eedeb06a821b21f0a59b03d346ac8bc3` / `Qwen2.5-0.5B-Instruct_multi-prefill-seq_q8_ekv1280.task` | `e608953f169aeb1bd7b9155fec2559825e08453fc209b84eda3a781ed0452fd2` | 546,660,344 | Q8/dynamic INT8 family; Apache-2.0 | resource-floor proposal |

Official model metadata:

- <https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm>
- <https://huggingface.co/litert-community/Qwen2.5-1.5B-Instruct>
- <https://huggingface.co/litert-community/Qwen2.5-0.5B-Instruct>

## Manifest issuance gate

No `fixtures/gate1/candidates/*.json` may be issued until all of the following are true:

1. The runtime wheel set, full transitive dependency lock and selected model artifact are acquired
   into an operator-approved, Git-ignored location and independently SHA-256 verified.
2. Candidate-specific strict config and adapter artifacts exist, are locally hashed, and bind
   single-turn state, temperature 0, the frozen 128-input/16-output envelope and both platform
   commands.
3. The adapter proves the complete packet protocol, including runner-owned timeout/cancel,
   request/operation correlation, READY recovery, shutdown and process-group cleanup.
4. License files and source/archive SHA-256 are retained with the controlled artifact bundle;
   Git records only their sanitized metadata.
5. Owners approve the Ubuntu 24.04 x86_64 full runner、product Pi compatibility runner and unique
   raw/isolated paths；x86 preselection must be frozen before at most two Pi try-runs.

Until these conditions close, the candidates remain `PROPOSED`, Gate 1 real execution remains
`NOT_STARTED / BLOCKED`, and the only valid results are deterministic fake/regression observations.

## Runner availability observation

- The workstation is Ubuntu 24.04.4 LTS x86_64 with glibc 2.39 and Python 3.12.3. It is a
  potential native x86_64 runner, subject to owner/raw-path approval and artifact capacity review;
  approximately 6.35 GB was free at observation time.
- `snowboard.local` is the product-target Pi environment: Debian 13 aarch64. Gate 2 does not require
  replacing it with Ubuntu, and this observation is not a porting failure. It remains reserved for
  Pi validation after Gate 1 written authorization; its configured swap must be disabled before the
  frozen Gate 2A run.
- Core's 2026-08-19 contract revision removed the separate native Ubuntu aarch64 runner requirement.
  Product-Pi compatibility now supplies Gate 1 aarch64 eligibility only after acquired-bundle proof
  and a bounded `PASS`; it still grants no Gate 2A credit.
