# Core Team → Audio POC Team: M4a M2A/M2B Comparative Evaluation ACK

- **Delivery ID**: `DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003`
- **Related contract**: `DELIVERY-AUDIO-POC-M4A-CONTRACT-001`
- **Supersedes ASR execution order and quality/performance gates in**:
  `DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001` and
  `DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002`
- **Preserves**: prior candidate evidence, artifact identity records, offline boundary,
  bounded execution, cleanup requirements and immutable tested SHAs
- **Status**: `ACCEPTED — M2A BASELINE SURVEY AND M2B OPTIMIZATION AUTHORIZED`
- **Owner**: Core Team Designer
- **User decision**: `Accepted 2026-08-21`
- **Architecture change**: `No`

## 1. Disposition

Core accepts a comparative funnel for Audio POC ASR work. Audio M2 is split into
two internal substages, `M2A Baseline Survey` and `M2B Optimization Feasibility`.
They do not create separate milestone tags; Audio M2 completes only after both
substages have a reviewed outcome.

M2A and M2B do not use CER, sentence correctness, latency, RTF or RSS thresholds
as candidate-elimination gates. These metrics remain observations used to compare
trade-offs and score the final candidates. Historical results keep their original
labels under the contract revision that produced them; this ACK neither deletes nor
retroactively relabels SenseVoice or Whisper small Q8 evidence.

Artifact mismatch, unknown provenance/license, runtime network access, OOM, bounded
timeout and incomplete cleanup remain fail-closed execution conditions. They protect
result validity and product safety; they are not quality rankings.

## 2. M2A Baseline Survey

### 2.1 Required Whisper rows

POC is authorized to materialize, hash, build/load and execute the following
multilingual whisper.cpp `1.9.2` rows using the existing CPU-only native aarch64
closure. Exact model filename, upstream immutable revision, byte size, SHA-256 and
license/notice must be recorded before first load; no separate row ACK is required.

| Row | Baseline role |
| :--- | :--- |
| `asr-whispercpp-small-q8_0-1.9.2` | Existing reference; preserve prior evidence and run only the common M2A packet needed for comparison |
| `asr-whispercpp-small-q5_1-1.9.2` | Quantization trade-off against small Q8 |
| `asr-whispercpp-base-q5_1-1.9.2` | Low-resource / low-latency reference |
| `asr-whispercpp-medium-q5_0-1.9.2` | Higher-capacity quality reference |
| `asr-whispercpp-large-v3-turbo-q5_0-1.9.2` | Optional same-cost-class quality/speed probe; may be omitted only with recorded resource or schedule reason |

The Q5 conditional trigger in ACK-002 is removed. Small Q5, base Q5 and medium Q5
may run independently of the small-Q8 result. HAT and accelerator-specific models
are out of scope.

### 2.2 Non-Whisper rows

The following low-cost engine families are authorized for M2A after the same
pre-load identity/provenance record. POC chooses one exact official model artifact
per family and records why it is representative; another Core round-trip is not
required unless the family or license boundary changes.

| Family | Authorized representative | Purpose |
| :--- | :--- | :--- |
| sherpa-onnx | One aarch64-compatible int8 streaming bilingual `zh-en` Zipformer or Paraformer | Non-Whisper streaming and code-switch comparison |
| Vosk | `vosk-model-small-cn-0.22` with official Vosk native/runtime API | Low-resource Raspberry Pi and dynamic-vocabulary potential |
| Qwen3-ASR via sherpa-onnx | `Qwen3-ASR-0.6B` int8 | Optional load plus minimal inference feasibility only; stop after bounded timeout/OOM evidence |

PocketSphinx, HAT, cloud APIs and unpinned community conversions remain out of scope.
Fun-ASR Nano and other large runtimes require a new written scope decision if M2A
shows that the authorized families leave a material capability gap.

### 2.3 Common low-cost packet

Each row uses one shared, committed packet:

1. eight preselected frozen internal fixtures: two Taiwan Mandarin, two code-switch,
   two number/date and two product-term items, including one longest bounded item;
2. ten to fifteen validated Common Voice `zh-TW` clips selected before candidate
   output is reviewed, with dataset version, clip IDs, license and derived 16 kHz
   mono PCM checksums;
3. one unscored warm-up and one scored inference per item; no cold matrix, twenty-run
   repetition, soak or full lifecycle campaign;
4. one bounded row-level budget and per-item timeout fixed in the packet. Timeout or
   OOM is recorded as an observation and stops wasteful execution; it is not rewritten
   as a quality rejection;
5. transcript, normalized CER, exact-sentence diagnostic, number/product-term
   correctness, load time, latency, RTF, peak RSS, disk/runtime identity and cleanup.

M2A returns a single comparative scorecard and a two-to-three-row shortlist. It does
not return `PASS`, `FAIL`, winner or production baseline labels.

## 3. M2B Optimization Feasibility

Only the M2A shortlist enters M2B. Every experiment changes one variable against a
named baseline and retains both raw and adjusted transcript/result identities.

| Track | Authorized probes | Required comparison |
| :--- | :--- | :--- |
| Front-end / endpoint | raw, DC removal, fixed gain, noise suppression, AGC, frozen-label endpoint/padding simulation; dereverb only when the signal audit supports it | Same WAV, same engine/profile; signal metrics plus ASR score delta and added CPU/RSS/latency |
| Decoder/runtime | greedy/beam, initial prompt, grammar, dynamic vocabulary/keyword boost, context policy, token suppression, native/flash-attention/BLAS where supported | One variable per row; quality categories plus latency/RTF/RSS |
| Number/domain | number/date canonicalization, product alias table, intent/slot parser, engine vocabulary controls | Exact numeric/entity value, false correction, unsafe silent correction and latency |
| Recovery | LLM-assisted correction and low-confidence confirmation | Preserve raw transcript; separately score corrected value, invented value and clarification outcome |
| External sanity | Reuse the frozen Common Voice subset | Detect overfitting or regression outside internal product phrases |

AEC and barge-in remain out of scope. DSP stays outside the Audio HAL: it is an
explicit `perception/listen` front-end stage and may not introduce hidden resampling
or change the accepted AudioInput stream contract.

This ACK does not authorize a real VAD engine row. Until the separate VAD scope is
decided, M2B may use frozen labels to compare endpoint/padding effects but may not
build, load or benchmark Silero, WebRTC VAD or another VAD candidate.

M2B returns a primary finalist, one fallback, the exact pipeline recipe and a delta
table showing benefit, cost and regression for every retained optimization. Quality
and performance metrics rank the choices but do not independently block selection.
Core/User makes the comparative provisional selection.

## 4. Core implementation release boundary

| Audio outcome | Core authorization |
| :--- | :--- |
| M2A in progress | Generic ASR protocol, fake adapter, schema, runner and config placeholder only |
| M2B reviewed selection | Candidate-specific adapter and provisional dependency/config integration for the named primary/fallback; no production lock |
| Audio M3 target/HAL qualification | Core product exact-SHA integration and acceptance preparation for the qualified recipe |
| Audio M4 `POC Accepted` final handoff | Freeze production engine/model/DSP/decoder profile and conformance-kit reference |

Any candidate-affecting change after M2B selection updates the recipe identity and
requires the directly affected comparison/target evidence. It does not reopen
unrelated candidates or require the full M2A landscape to be rerun.

## 5. Required return

POC returns one committed M2A/M2B packet with branch and full 40-character SHA,
exact artifact/runtime identities, fixture/Common Voice index, commands, bounded
budgets, comparative scorecard, optimization delta table, primary/fallback proposal,
known risks and cleanup proof. Large models, raw/private audio and uncontrolled
transcripts remain outside Git; the committed index records their checksums and
controlled locations.

This ACK authorizes the work above. It does not declare Gate 2A selection, Audio M3
qualification, `POC Accepted`, Core product acceptance or a production dependency
lock.
