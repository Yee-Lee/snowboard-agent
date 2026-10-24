# Audio POC → PM → Core Team: M4a Gate Plan Response

- **Response ID**: `RESP-AUDIO-M4A-GATE-PLAN-001`
- **In response to**: `DELIVERY-AUDIO-POC-M4A-CONTRACT-001`, revision
  `2026-08-17 / PM-OUT-260817-016`
- **Finding IDs**: `OUT-M4A-2026-001` – `OUT-M4A-2026-005`
- **Status**: `PROPOSED / NOT AUTHORIZED — CORE PLANNING ACK AND DECISIONS REQUIRED`
- **Authoritative plan path**:
  `poc_audio/deliveries/RESP-AUDIO-M4A-GATE-PLAN-001.md`
- **POC branch**: `dev_audio_m2`
- **Committed HEAD**: supplied in the relay message after commit; never prefilled here
- **Prepared**: 2026-08-17
- **Architecture change**: `No`

## 1. Designer disposition

Audio POC conditionally accepts the revised Gate 1, Gate 2A, Gate 2B and Gate 3
separation. In particular, the POC accepts exact-SHA evidence binding, portable
conformance assets, explicit evidence inheritance/product deltas, and the rule
that a Gate 2A selection ACK permits only an artifact-independent Core adapter
scaffold. Gate 2A is not `POC Accepted`, and no production dependency, model or
voice may be frozen before the Gate 2B final reference package is accepted.

This response is the committed planning packet requested by contract section 10.
It does not request or imply permission to download, build or benchmark a real
candidate. M2 remains `PLANNED / NEXT`; all future test results remain
`Pending` until their stated entry condition and exact-SHA cut point are met.

The plan advances final checklist sections 2–7: reproducible runners and schema,
candidate provenance/results, quality/lifecycle evidence, Pi/HAL qualification,
combined sessions, and winner/no-go/productization material.

## 2. Decisions required before Gate 1 can close

| Decision ID | Blocking question | POC recommendation | Effect until written decision |
| --- | --- | --- | --- |
| `M4A-G1-D01` | Is the product language `zh-TW` or `en fallback`? | Confirm `zh-TW`. M1 already froze 100 controlled fixtures, ASR references and 20 TTS prompts for `zh-TW`; switching to English requires a change request and new frozen fixtures/metrics. | Candidate model/voice variants cannot be fixed; Gate 1 cannot close. |
| `M4A-G1-D02` | Is VAD in the authorized Audio POC scope even though the Core Gate 1 baseline lists only ASR/TTS? | Authorize Silero VAD ONNX and WebRTC VAD with the frozen endpoint state machine. VAD remains outside HAL and is not a Core M4a production dependency decision. | No real VAD candidate run. Final POC VAD checklist has no authorized closure path. |
| `M4A-G1-D03` | How can source archive SHA-256 be supplied when pre-ACK candidate download is forbidden? | Split Gate 1 into `G1A planning ACK`, permitting provenance-only acquisition into a controlled, non-Git artifact area, then `G1B candidate-scope ACK` after exact hashes/licenses are returned. Benchmarking remains forbidden until G1B. | Only upstream metadata may be reviewed. No POC-computed archive/model/voice hash may be claimed. |
| `M4A-G1-D04` | What exact M4b reservation must P9 use? | Core supplies a versioned deterministic surrogate identity, checksum, RSS/thread/CPU envelope, command and acceptance rule before the M3 P9 packet is cut. | P9 is `Blocked`; no substitute stub may be invented by POC. |
| `M4A-G1-D05` | Does one Core response accept both this plan and the eventual exact candidate list? | Issue separate, unambiguous ACKs for G1A planning and G1B candidate scope, each listing the accepted POC full SHA. | No implied authorization from receipt, branch name or elapsed review time. |

Core AudioOutput permits its sample rate to be selected by the TTS winner. The POC
therefore interprets P4/P5 as: a candidate must disclose native PCM; the selected
AudioOutput configuration is frozen to that native format at Gate 2A; Speak/TTS
must not resample. If Core instead has a preselected output format, it must be
returned with G1B and will become an eligibility condition.

## 3. Gate and milestone crosswalk

| External gate | POC milestone/work package | Evidence produced | Exit and SHA binding |
| --- | --- | --- | --- |
| Gate 1A planning | M1 frozen baseline + `WP0` | This plan, frozen fixture/metric references, unresolved decision register | Core planning ACK names this response ID and committed full SHA. No real candidate work is authorized. |
| Gate 1B candidate scope | M2 `WP1` | Exact candidate/version/variant proposal, source/model/voice SHA-256, dependency and license table, clean-Pi build proposal | Core candidate ACK lists accepted rows and proposal full SHA. Only listed rows may enter Gate 2A. |
| Gate 2A isolated selection | M2 `WP2–WP3` + M3 `WP4` | P1–P8, P9 reservation, P10–P12; M2 preliminary plus Pi/HAL final disposition; advance/reject table | Core selection ACK names the evidence manifest full SHA. Core may scaffold an artifact-independent adapter; no final lock. |
| Gate 2B final reference | M4 `WP5` | 20 sessions, failure injection, offline run, final checklist, conformance kit and review findings | `POC Accepted` only after blocking findings close. Final handoff names immutable POC SHA and kit revision. |
| Gate 3 Core product | External Core work | Product inheritance/delta mapping and product-SHA reruns | Core Tester/Designer decision; POC evidence is referenced but never relabelled as product PASS. |

M2 may reject candidates and recommend finalists, but cannot produce the final
hardware winner. M3 may produce hardware-qualified ASR/TTS selections and a
Gate 2A packet, but cannot produce `POC Accepted`. M4 alone supplies Gate 2B's
combined reference package; Core Gate 3 remains outside this repository.

## 4. Work packages, order and estimates

Estimates are engineering days after dependencies are available, not calendar
commitments. One Pi session means one clean checkout/pre-test/test/evidence-return
cycle. Throughput assumes one candidate variant per Pi day after its controlled
artifact set builds successfully, exclusive Pi access, stable hardware, and one
User review sitting for all 20 TTS prompts per finalist.

| WP | Owner / producer | Dependency and order | Estimate / throughput | Entry | Exit | Re-estimation trigger |
| --- | --- | --- | --- | --- | --- | --- |
| `WP0` contract alignment | Technical Lead / Designer | First | 1 day, one review commit | Revised contract received | This committed plan and Core decision request relayed | Contract or frozen gate changes |
| `WP1` provenance and Gate 1B proposal | Developer prepares; Technical Lead reviews; Core approves | G1A ACK + D01/D02/D03 | 2–4 days metadata/license work; no benchmark | Provenance-only acquisition authorized | Every proposed row has immutable identity, hashes, notices, transitive dependencies and Pi build recipe; G1B ACK received | Missing upstream source, ambiguous model license, non-aarch64 dependency |
| `WP2` shared conformance scaffold | Developer; Reviewer reviews lifecycle boundary | G1A ACK; may overlap WP1 only with fake assets | 4–6 days | Protocol/schema work authorized | Fake success/error/timeout/cancel/force-abort tests pass; reusable kit skeleton fixed at `S2` | Native runtime cannot cancel; schema changes product semantics |
| `WP3` isolated comparison | Developer cuts SHA; Tester executes; Technical Lead decides | G1B ACK + WP2 + controlled artifacts | 8–12 days; normally one authorized variant/Pi day, 6–10 Pi sessions depending on authorized scope | Exact authorized rows, frozen fixture checksums, clean Pi | All authorized candidates have result/advance/reject records; at least one finalist per class or no-go/CR | Build exceeds 1 day, thermal drift, fixture/hash mismatch, all rows fail a hard gate |
| `WP4` Pi/HAL qualification | Developer prepares packet; Tester runs; User operates; Technical Lead reviews | WP3 finalists + accepted M3 HAL SHA + D04 surrogate | 5–8 days, 4–6 Pi sessions | Clean exact-SHA HAL/POC checkouts and target hardware | P1–P12 final M2/M3 disposition, winner/no-go recommendation, Gate 2A submission | HAL delta, device instability, surrogate change, finalist fails hardware gate |
| `WP5` combined/final reference | Tester runs; User reviews TTS; Reviewer/Designer close findings | Gate 2A selection ACK + fixed finalists | 4–6 days, 3–4 Pi sessions plus review | Winner identities fixed for POC validation; no Core production lock implied | 20 sessions, injection/offline evidence, final manifest, kit, `Ready for internal review`; then `POC Accepted` only after review | Any residual resource growth, cleanup/offline failure, winner/artifact change |

Separate source cut points are mandatory:

- `S0`: this plan commit; no real-candidate execution.
- `S1`: exact Gate 1B proposal/provenance commit; no benchmark result.
- `S2`: shared protocol, fake runner, schemas and validators; local tests pass.
- `S3`: isolated-comparison runner commit; Pi checks out this clean SHA.
- `S4`: M3 HAL integration packet commit; P1–P12 runs bind both POC and HAL SHA.
- `S5`: M4 combined runner/final handoff commit; 20-session evidence binds this SHA.

Evidence must never mix a source edit and a gate result in one run. Any runner,
threshold, candidate identity or fixture checksum change invalidates the affected
packet and requires a new cut point.

## 5. Candidate eligibility and proposal policy

### 5.1 Proposed comparison scope

The Gate 1B manifest will enumerate variants, not only engine names. Until D01
and G1A close, every row below is `PROPOSED / IDENTITY PENDING`; none is authorized.

| Domain | Contract baseline rows | Alternative rows | Proposal rule |
| --- | --- | --- | --- |
| VAD | Silero VAD ONNX; WebRTC VAD | None initially | Submit only after D02; keep a shared, separately versioned endpoint state machine. |
| ASR | whisper.cpp; Vosk; PocketSphinx | sherpa-onnx SenseVoice int8; sherpa-onnx Paraformer small/int8 | Preserve all Core baseline rows in eligibility review. Run an alternative only when G1B names its exact model variant. |
| TTS | Piper; espeak-ng; Coqui TTS | sherpa-onnx VITS/MeloTTS voice | Preserve all Core baseline rows in eligibility review. A voice is a distinct variant and must match D01. |

No exact version, checksum or license conclusion is asserted in this S0 packet.
After G1A, WP1 records for each variant: upstream project and immutable tag/commit,
source archive name and POC-computed SHA-256, model/voice file name and SHA-256,
engine and artifact licenses/notices, quantization, aarch64 build/install command,
transitive native/Python dependencies, expected native PCM, offline cache layout,
commercial/redistribution restrictions, and controlled source URLs. Auto-generated
archives without a stable immutable identity are mirrored only in the approved
controlled store and referenced by checksum; they are never committed.

### 5.2 Eligibility order

1. Verify G1B row authorization, immutable provenance and every checksum.
2. Review engine plus model/voice licenses and notices; unknown, incompatible or
   non-redistributable identity is recorded, not silently replaced.
3. Prove aarch64/Python/OS compatibility from a clean Pi recipe with all build
   inputs pre-acquired and hashed.
4. Confirm inference is fully offline after installation and has no credential,
   endpoint or runtime download requirement.
5. Confirm native input/output format and absence of hidden ASR/TTS/Speak resample.
6. Only eligible variants enter equal-fixture, equal-thread, fixed warm-up/cold/hot
   comparison. A parameter, model, voice or quantization change creates a new row.

Failure at steps 1–4 is `INELIGIBLE`, not a quality `FAIL`. The row and reason remain
in the final rejected-candidate index. No model, wheel, `.so`, private audio or raw
result enters Git.

## 6. Shared protocol, harness and conformance design

`WP2` will extend the existing deterministic child-process harness without
placing orchestration in the product composition root.

- Common worker protocol: `START -> READY -> RUN -> terminal result`, plus
  `CANCEL`, bounded graceful shutdown and observable force-abort/exit. Each
  session has a unique ID and cannot retain transcript/session history.
- VAD adapter: consumes 16 kHz mono S16_LE chunks, emits model observations;
  the frozen endpoint state machine owns utterance reset and remains separate.
- ASR adapter: consumes one bounded 20 ms/320-sample/640-byte-frame utterance and
  emits final text or a typed terminal error. Language/normalization is fixed.
- TTS adapter: consumes text and emits an ordered, finite PCM iterator with an
  explicit native format. Cancellation ends generation and closes the iterator.
- Validators: candidate/provenance schema, actual PCM/frame validator, transcript
  normalization/CER, TTS sequence/duration, monotonic latency/resource samples,
  offline trace, and before/after process/thread/fd/iterator/stream/device-owner
  cleanup assertions.
- Reusable kit: protocol and result JSON schemas, small non-sensitive vectors,
  fixture/prompt IDs and checksums, validators and scenario assertions. Candidate
  orchestration, raw/private audio, weights and large results remain POC-controlled.

The frozen M1 rules remain authoritative where stricter than the Core minimum:
ASR uses `zh-TW` CER <= 20% and sentence correctness >= 70%; TTS requires User
median >= 4/5, no unrecorded critical misread, hot first chunk p95 <= 1.5 s and
generation RTF p95 <= 1.0. Core P2 non-empty text and P6 mean >= 3.5/5 do not
relax these gates.

## 7. Evidence boundary and data handling

| Stage | Platform and boundary | Git-tracked evidence | Controlled/raw evidence | Status limit |
| --- | --- | --- | --- | --- |
| M2 isolated | Pi 5 preferred for comparable resources; fixed delivered WAV/text; no live HAL ownership | Candidate/provenance index, sanitized per-run index, aggregate quality/resource/lifecycle/offline summary | Source/model/voice artifacts, private WAV, full hypotheses, process/resource samples | `preliminary` for P1–P12; finalist recommendation only |
| M3 Pi/HAL | Target Pi 5, accepted M3 HAL full SHA, target mic/speaker; P9 uses approved surrogate | Environment/config checksum, P1–P12 manifest, sanitized result and decision table | Raw capture/playback, logs, resource series, installed artifacts | Gate 2A `PASS/FAIL/INCONCLUSIVE`; no `POC Accepted` |
| M4 combined | Same target with VAD/ASR/TTS resident; 20 fixed sessions and injection/offline | Final manifest/index, sanitized summaries, kit revision, findings and closure | Private session audio/text, full raw resource/network/lifecycle logs | `Ready for internal review`, then Gate 2B `POC Accepted` after review |

Each Pi session starts with exact local/Pi SHA equality, clean worktree and
environment pre-test. The packet records command, start/end UTC, exit code,
hardware/environment, config/runner/fixture hashes and cleanup. Raw paths are
relative logical paths in the manifest and map to the controlled store; secrets,
operator endpoints and private content are sanitized before any tracked summary.

## 8. M4A-P1–P12 executable crosswalk

The commands and paths below are planned stable interfaces to be implemented in
WP2–WP4. They do not exist at S0 and must not be executed before their stated gate.
All `manifest.json` statuses start `Pending`. `<packet>` is an immutable,
timestamped controlled directory whose sanitized index is committed separately.

| ID | Producer / milestone / platform | Fixture or input; planned command | Output path | Decision / no-go and cleanup | SHA cut |
| --- | --- | --- | --- | --- | --- |
| P1 | Developer validator; Tester M2 preliminary + M3 final; Pi/HAL | Frozen delivered 16 kHz WAV then M3 `AudioInput.frames()`; `bash poc_audio/tools/run_m4a_asr.sh --packet <packet> --test P1` | `evidence/m4a/<packet>/raw/p1.*`; sanitized `results/p1.json` | Assert 20 ms, 320 samples, 640 bytes, mono S16_LE at ASR boundary and no ASR resample. Format mismatch is candidate/HAL `FAIL`; close worker/stream/device. | S3/S4 |
| P2 | Tester; M2/M3; Pi | Known-speech fixture IDs; same ASR runner `--test P2` | raw hypotheses controlled; sanitized non-empty/WER-CER summary | Every required utterance has terminal result; empty output fails Core P2 and frozen CER remains separately binding. Zero child/thread/fd. | S3/S4 |
| P3 | Tester + Technical Lead; M2/M3; Pi | Frozen silence, noise and ASR sets; ASR runner `--test P3` | `results/p3.json`, raw timing/hypotheses controlled | Silence produces no non-empty hypothesis; speech has no garble; p95 RTF <= 2.0 and stricter frozen CER/sentence gates. Hard-gate failure rejects row. Full worker cleanup. | S3/S4 |
| P4 | Developer validator; Tester; M2 preliminary + M3 final; Pi/HAL | Frozen prompt; `bash poc_audio/tools/run_m4a_tts.sh --packet <packet> --test P4` | `results/p4.json`, controlled native PCM | Assert disclosed native rate/channels/S16_LE and exact chunk sequence; no TTS/Speak resample. Mismatch fails. Close iterator/worker/output. | S3/S4 |
| P5 | Tester + User operator; M3; target speaker/HAL | Fixed text/native PCM; TTS runner `--test P5 --playback` | controlled playback log; sanitized duration/completion summary | HAL consumes all chunks and completion proof shows no truncation/xrun. Playback/device failure is `FAIL` or environmental `INCONCLUSIVE`; release owner/stream. | S4 |
| P6 | User scores; Tester controls blinding/index; M2 preliminary + M3 confirmation; Pi | 20 frozen prompts; `bash poc_audio/tools/run_m4a_tts_review.sh --packet <packet>` | controlled samples/scores; sanitized mean, median and critical-misread IDs | Report Core mean and frozen median; require median >= 4/5 and no unrecorded critical misread, plus latency/RTF gates. Lower score rejects variant. Remove transient playback ownership; no score changes after unblinding. | S3/S4 |
| P7 | Tester; M2 isolated + M3/HAL; Pi | Authorized ASR set after fixed warm-up; `bash poc_audio/tools/run_m4a_resource.sh --domain asr --packet <packet>` | raw samples; `results/p7.json` | Record p50/p95 latency, RTF, CPU/RSS/temp/throttle, all samples. Frozen RSS/thermal/no-growth gates apply. Stop sampler/worker; zero fd/thread/process. | S3/S4 |
| P8 | Tester; M2 isolated + M3/HAL; Pi | Authorized TTS prompts; resource runner `--domain tts` | raw samples; `results/p8.json` | Same method; include first chunk, synthesis latency and RTF. Hard resource/thermal/lifecycle failure rejects. Close iterator/output/worker/sampler. | S3/S4 |
| P9 | Core supplies surrogate; Tester; M3; Pi | D04-approved identity/envelope plus finalists; `bash poc_audio/tools/run_m4a_reservation.sh --packet <packet> --surrogate <spec>` | raw residency series; `results/p9.json` | Reserve specified RSS/thread/CPU envelope and record audio headroom/thermal. Missing/changed surrogate is `Blocked`; failure prevents finalist. Stop all named processes and verify baseline. | S4 |
| P10 | Developer scenarios; Tester; M2 preliminary + M3 final; Pi/HAL | init/warm/run/shutdown >=5 plus success/error/timeout/cancel/force-abort/reopen; `bash poc_audio/tools/run_m4a_lifecycle.sh --packet <packet>` | per-scenario raw; `results/p10.json` | Every path has terminal result and child/thread/fd/iterator/stream/device-owner counts zero. Any leak is `FAIL`, never averaged away. | S3/S4 |
| P11 | Developer recipe; Tester clean-build; M2 provenance + M3 clean Pi | Hashed controlled inputs; `bash poc_audio/tools/run_m4a_clean_build.sh --candidate <id> --artifact-dir <controlled> --packet <packet>` | build log controlled; sanitized environment/license/provenance index | Rebuild/install/import/identity/rerun without network; exact OS/package/native deps. Unknown license/hash/build input is ineligible or `FAIL`. Remove disposable env/processes. | S1/S4 |
| P12 | Tester; M2 standalone + M3/HAL; isolated-network Pi | Installed artifacts and main ASR/TTS run; `bash poc_audio/tools/run_m4a_offline.sh --packet <packet>` | network/process trace controlled; `results/p12.json` | Inference completes with zero attempted network call, endpoint or credential. Any runtime fetch is `FAIL`. Restore operator-managed network only after process/device cleanup. | S3/S4 |

The M4 runner at S5 will reuse these scenario IDs and validators:

```text
bash poc_audio/tools/run_m4_combined.sh \
  --packet <packet> --sessions 20 --offline --inject-each-domain
```

It records total RSS/threads/load/latency/temperature and success, timeout,
error, cancel and force-abort cleanup for VAD, ASR and TTS. Its outputs live under
`poc_audio/evidence/m4/<packet>/`; only reviewed sanitized indexes are tracked.

## 9. Failure, fallback and change-request policy

- Preserve every eligibility failure, test failure and inconclusive packet.
  Rerun only after the cause and new SHA/config/artifact identity are recorded.
- A candidate failing license, immutable artifact, aarch64 or offline eligibility
  is rejected before performance work. No same-name artifact is substituted.
- A candidate failing P3, P6, P9 or P12 cannot be a Gate 2A finalist. Lifecycle or
  cleanup failure also blocks advance under the frozen POC gate.
- If all authorized candidates in one class fail, stop that class and submit an
  evidence-backed no-go/change request. Alternatives require a new G1B ACK.
- If a finalist fails M3 HAL, return to an already-authorized M2 finalist only;
  otherwise request scope change. Never lower a frozen quality/resource gate.
- If M4 combined validation fails, evaluate already-declared smaller artifact,
  quantization, thread or execution-container variants only when separately
  authorized; a changed model/voice is a new candidate identity.
- Contract/HAL/fixture/language/surrogate changes after results exist require a
  change request stating trigger evidence, affected final items, options, cost,
  risk, recommendation and Core/User decision owner.

## 10. Requested Core reply

Within the contract's five-working-day review target, please return a written
disposition that:

1. accepts or rejects this plan by response ID, path and committed full SHA;
2. resolves D01–D05 explicitly;
3. if G1A is accepted, states exactly which provenance-only network/artifact
   actions are permitted before G1B and confirms real execution remains blocked;
4. identifies the Core owner and due point for the versioned P9 surrogate; and
5. states the durable PM relay path by which Core ACK documents are returned to
   this repository.

Until that reply is received, the only permitted next work is review/correction
of this planning packet. No candidate is approved, no candidate artifact is
acquired, and no benchmark, Pi candidate run or production integration begins.
