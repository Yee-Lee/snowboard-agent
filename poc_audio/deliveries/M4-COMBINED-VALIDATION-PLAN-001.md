# M4-COMBINED-VALIDATION-PLAN-001

Status: `P9.1 USER APPROVED / IMPLEMENTATION AUTHORIZED / FORMAL EXECUTION NOT AUTHORIZED`

## 1. Purpose and delivery contribution

This plan advances final delivery checklist sections 1, 6, 7 and 8. It defines
the work needed to prove that the M3-qualified Silero VAD, whisper.cpp base-Q8
ASR and Matcha TTS remain offline, bounded and clean while resident together on
the target Raspberry Pi 5. It also defines the evidence needed for the Gate 2B
portable conformance kit and final delivery manifest.

User approved the proposed catalog and execution order on 2026-08-25. This plan
does not start a formal run, publish a disposition, close Matcha legal
lineage, or change the authoritative M4 status. Formal evidence requires a clean
Pi checkout at an immutable Audio candidate SHA and the pinned Core HAL SHA.

## 2. Authority and inherited identities

The authoritative sources are:

- `docs/milestone/README.md` and
  `docs/milestone/m4_combined_validation_and_delivery.md`;
- `docs/audio_poc_workflow.md` and
  `docs/specs/audio_poc_delivery_checklist.md`;
- `RESP-AUDIO-M3-GATE2A-MECHANICAL-ACK-001` at Core commit
  `5aac035d25f6498c3c0affe1ace4afd7de8f7254`;
- the accepted P9 artifact and corrected ACK at Core commit
  `caf4f7ba867e4ebc1972df0ade86c605a873a286`.

The M4 runner must inherit, without substitution:

| Item | Fixed identity |
| --- | --- |
| Audio M3 execution baseline | `f7b9694d1477f26513880526e0718d2b3c5766b3` |
| Core HAL execution SHA | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| VAD | Silero 6.2.1, model SHA-256 `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` |
| ASR | whisper.cpp 1.9.2 base Q8, model SHA-256 `c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9` |
| ASR recipe | 4 threads, language `zh`, greedy best-of-1, fixed prompt SHA-256 `e3b2606c90009ce609aa23183c2229619619cf1173dc17d2ecd2308bfe4fe8ef` |
| TTS | sherpa-onnx 1.13.5 Matcha archive `271b804af570400d3bcdcb53bf6e53cc9f75180ee763b9f13eb5eaf2b0d086ef`, Vocos `b599142a1fb8ff03de3e84ac35ff537c619e56f4267a6fe894851a42844acf9e` |
| P9 | `M4B-P9-RESIDENCY-SURROGATE-001`, protocol 1.0, source SHA `f18f823146727b50cb3ef15e9e14b51983643406` |

The formal M4 candidate SHA will be cut only after the local fake, schema,
protocol, cleanup and packet-validator tests pass. That new SHA must append to,
not rewrite, the published M3 history.

## 3. Proposed fixed 20-session catalog

The proposed catalog uses 20 distinct frozen, controlled M1 recordings. It is
balanced across five ASR categories and clear/pause speech. No fresh recording,
best-take selection or retrospective filtering is allowed.

| Sessions | Category | Fixture IDs |
| --- | --- | --- |
| 01-04 | Taiwan Mandarin | `asr-clear-002`, `asr-clear-003`, `asr-pause-026`, `asr-pause-031` |
| 05-08 | code switch | `asr-clear-011`, `asr-clear-012`, `asr-pause-036`, `asr-pause-037` |
| 09-12 | number | `asr-clear-016`, `asr-clear-017`, `asr-pause-041`, `asr-pause-043` |
| 13-16 | date | `asr-clear-020`, `asr-clear-021`, `asr-pause-045`, `asr-pause-046` |
| 17-20 | product term | `asr-clear-023`, `asr-clear-024`, `asr-pause-048`, `asr-pause-049` |

Each session performs:

```text
locked 16 kHz mono S16_LE fixture
  -> exact 20 ms HAL-facing frames
  -> persistent Silero endpoint
  -> bounded utterance
  -> persistent base-Q8 ASR
  -> deterministic mock Reasoner
  -> persistent Matcha PCM iterator
  -> pinned Core AudioOutput and physical completion
```

The deterministic Reasoner consumes the typed ASR terminal result and selects
the correspondingly numbered frozen `tts-001` through `tts-020` response. It is
test orchestration only: it must not implement a static correction lexicon,
change the transcript, or enter the product composition root. The session
manifest locks the 20 input checksums, reference hashes, TTS prompt-file checksum
and one-to-one mapping before formal execution.

ASR hypotheses are retained in controlled evidence. Git-tracked results contain
fixture IDs, outcome classes and hashes, not private transcripts or raw PCM.

## 4. Work packages and order

### WP4.0 - Freeze the packet

1. Review and approve the 20-session catalog, Reasoner mapping and gates.
2. Generate a machine-readable M4 packet manifest and JSON schemas.
3. Bind Audio/Core SHAs, candidate identities, fixture hashes, P9 hashes,
   hardware, timeouts, cleanup counters and evidence paths.
4. Keep every formal result `Pending`; fake results are explicitly ineligible
   for hardware credit.

The packet/schema/fail-closed validator and local fake suite are now implemented.
The formal preflight implementation also provides a candidate-SHA-bound controlled
20-WAV fixture lock and a checksum-locked P9 client. Formal Pi execution remains
disabled until the persistent HAL pipeline and immutable candidate packet are cut.

### WP4.1 - Build and locally verify the S5 runner

Implement an M4 runner by reusing the M3 HAL, VAD, ASR, TTS and lifecycle
adapters. Add deterministic fakes for all three domains and P9 protocol
regression. Local tests must cover:

- success and 20-session ordering without model reload;
- error, timeout, cancel and force-abort in each domain;
- recovery after each injected failure;
- malformed/missing result, checksum mismatch and reused output path;
- process, thread, fd, iterator, stream and device-owner cleanup assertions;
- result-schema validation and fail-closed summary generation.

No local test may be reported as Pi, P9 or Gate 2B evidence.

### WP4.2 - Execute P9.1 realistic-turn residency first

On the target Pi 5 4GB with Debian 13 aarch64, `swap=0` and networking disabled:

1. verify the exact P9 source, executable, schema and lock hashes;
2. verify clean Audio/Core SHAs, baseline ownership, temperature and throttling;
3. start the three Audio finalists and the P9 surrogate as separate bounded
   process groups; keep all three Audio process identities stable for the full catalog;
4. require P9 `READY` within 10 seconds and sample at intervals no greater than
   one second;
5. for each approved catalog entry, run VAD and ASR, then send one `INFER` and
   keep all Audio finalists resident while all four P9 CPU workers execute; after
   matched `INFERENCE_COMPLETE`, run deterministic Reasoner mapping and TTS playback;
6. preserve timestamps, request IDs, PIDs, `MemTotal`, `MemAvailable`, swap,
   per-PID RSS/PSS/CPU/threads, latency, temperature, throttling and xruns;
7. require matched `INFERENCE_COMPLETE`, then bounded `SHUTDOWN_ACK`, process-group
   cleanup and restored device ownership.

P9.1 `PASS` requires every primary capacity sample
`MemTotal - MemAvailable <= 3584 MiB`, complete overlap, no OOM/memory-pressure
event, disqualifying xrun, crash, thermal/session breach or residue. `sum(RSS)` is
diagnostic only. A valid breach is `FAIL`; invalid preconditions are `Blocked`;
lost evidence after start is `INCONCLUSIVE` only when pass/fail cannot be derived.

The User rejected the original full-session CPU overlap method as unrealistic on
2026-08-25 and approved `P9.1-REALISTIC-TURN-RESIDENCY-DESIGN-001`. P9.1 keeps
the unchanged surrogate artifact, memory envelope and all 20 fixed sessions, but
places the CPU-heavy `INFER` at the realistic `ASR -> LLM -> TTS` boundary. The
historical draft failure remains retained and receives no M4 credit.

### WP4.3 - Execute independent 20-session combined validation

After reviewed P9 evidence permits continuation, restart from a clean baseline
and run the same 20 sessions without the P9 surrogate. Keep VAD, ASR and TTS
resident for the entire sequence; no session may reload or replace a model.

All formal sessions run with networking disabled and record:

- per-stage and end-to-end monotonic latency;
- model load count/time, total RSS/PSS, swap, CPU, threads and file descriptors;
- temperature, frequency, throttling and xrun/overflow/underrun observations;
- ordered PCM chunk/byte counts and physical playback completion;
- before/after cleanup counters and controlled raw-evidence locators.

The combined run passes only when all 20 sessions have complete terminal results,
all required evidence is present, no model identity changes, no OOM/crash/deadlock,
no sustained or monotonic resource growth, no throttle transition, no
disqualifying audio error and final cleanup deltas are zero. Existing bounded
operation timeouts remain binding. Latency and resource values are reported as
observations unless an already accepted numeric gate applies; this plan does not
invent a new ceiling after seeing results.

M2A/M2B quality dispositions are inherited and are not retrospectively relabeled.
The 20 outputs feed the required semantic-mishearing frequency report, with pure
format normalization excluded and raw/fixed-prompt benefit and regression kept.

### WP4.4 - Failure injection and recovery

Run dedicated cases after the successful combined sequence. For each of VAD,
ASR and TTS, execute one `error`, `timeout`, `cancel` and `force-abort` case. Each
case must have a typed terminal result within its fixed bound, zero child/thread/
fd/iterator/stream/device-owner residue, and one subsequent normal recovery probe.

Any residue, unbounded wait, hidden model replacement or failed recovery is a
hard `FAIL` and stops publication of a passing M4 disposition. Failed and
inconclusive evidence remains append-only.

### WP4.5 - Delivery, review and Gate 2B handoff

Build the delivery manifest, evidence index and portable conformance kit. Audit:

- every executed candidate identity, license, source, checksum and rejected path;
- lockfile/setup, schemas, fixture catalog, deterministic fake and commands;
- M3 HAL/full-SHA inheritance and M4 raw-to-sanitized evidence mapping;
- winner/no-go table, ASR semantic patterns, productization boundary and estimate;
- Git data safety and controlled artifact revalidation;
- Gate 1/Gate 2A ACK chain and the final Gate 2B handoff SHA.

The first submission is `Ready for internal review`. Any draft PASS/FAIL/
INCONCLUSIVE or winner/no-go report requires User publication confirmation before
commit or external handoff. `POC Accepted` requires blocking findings closed,
Designer approval and written Core receipt. Core Gate 3 remains external work.

## 5. Planned evidence layout

```text
poc_audio/
├── deliveries/
│   ├── M4-COMBINED-VALIDATION-TEST-PACKET-001.md
│   └── POC-audio-DEL-YYYY-NNN-RN.md
├── manifests/
│   └── m4_combined_packet.json
├── schemas/
│   ├── m4_combined_packet.schema.json
│   └── m4_combined_result.schema.json
├── tools/
│   └── run_m4_combined.sh
└── evidence/m4/<run-id>/
    ├── manifest.json
    ├── environment.txt
    ├── config.sanitized.json
    ├── results.sanitized.json
    └── raw/                 # controlled only; never committed
```

Tracked indexes use logical controlled locators and checksums. Model files,
private audio, raw hypotheses, full TTS text, large samples, endpoints, secrets
and operator configuration remain outside Git.

## 6. Stop conditions and open risks

- Matcha archive notice/training-data lineage remains blocking for
  redistribution, product adoption and final-winner approval. Technical M4 work
  may proceed, but Gate 2B cannot close without a written legal disposition or
  an approved evidence-backed no-go/change request.
- Any P9 identity mismatch, missing approved session catalog, non-Pi/non-Debian
  target, nonzero swap or unavailable controlled fixture blocks P9 execution.
- A P9, combined, offline, failure-injection, cleanup or thermal failure stops
  the current gate path. Fallback changes require separate authorization and a
  new candidate identity; gates and product semantics remain unchanged.
- A dirty Pi worktree, SHA mismatch, missing raw evidence, reused result path or
  incomplete sanitization makes the affected run invalid and prevents PASS.

## 7. Proposed execution sessions

| Session | Purpose | Exit |
| --- | --- | --- |
| Workstation | implement schemas/runner/fakes and pass local tests | reviewable S5 candidate commit |
| Pi 1 | environment pre-test, exact-SHA preflight and P9 reservation | reviewed P9 draft disposition |
| Pi 2 | offline 20-session combined sequence | complete session/resource/thermal evidence |
| Pi 3 | 12 failure injections, recovery probes and cleanup | complete lifecycle evidence |
| Review | User publication confirmation, package audit and findings | `Ready for internal review` handoff |

Additional Pi sessions are append-only reruns after a documented failure or
inconclusive cause; they never replace earlier evidence.
