# M4a M2A Common Comparative Packet 001

- **Packet ID**: `M4A-M2A-COMMON-PACKET-001`
- **Authority**: `DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003`
- **Branch**: `audio`
- **Status**: `PREPARED — CONTROLLED FIXTURE LOCK PENDING / NOT EXECUTABLE`
- **Delivery contribution**: final checklist candidate identity, shared fixture index,
  bounded comparison method, result-schema and cleanup evidence

## Decision boundary

This packet fixes the M2A candidate landscape and the deterministic method used to
lock its fixtures. It does not authorize candidate load or inference yet. Execution
remains fail closed until the controlled internal labels/audio and authenticated
Common Voice sources have produced one reviewed fixture lock with derived 16 kHz
mono S16_LE checksums. The Common Voice source acquisition is now complete; the
internal exact eight and derived 8+12 PCM lock remain pending.

M2A metrics are comparative observations. This packet must not emit `PASS`, `FAIL`,
winner or production-baseline labels. SenseVoice, Matcha and Whisper small-Q8
historical evidence retains its original disposition and is not relabeled.

## Machine-readable authority

The executable identities and budgets are fixed in
[`m4a_m2a_common_packet.json`](../manifests/m4a_m2a_common_packet.json) and validated by
[`m4a_m2a_packet.py`](../src/audio_poc/m4a_m2a_packet.py). The manifest pins:

- whisper.cpp `1.9.2` at commit
  `306c88f4d1286aec1bf96e544632897886af5501`, using the previously proven native
  four-thread CPU-only closure;
- small Q8_0, small Q5_1, base Q5_1, medium Q5_0 and optional large-v3-turbo Q5_0
  model filenames, immutable repository revision, byte sizes and SHA-256 values;
- official sherpa-onnx bilingual zh-en streaming Zipformer int8 as the required
  non-Whisper streaming representative;
- official Vosk `vosk-model-small-cn-0.22` with the existing official aarch64
  runtime identity;
- optional sherpa-onnx Qwen3-ASR 0.6B int8 as load plus one-longest-item feasibility
  only, stopping on bounded timeout or OOM;
- sherpa-onnx `1.13.5` exact two-wheel CPython 3.13/aarch64 closure already used by
  the POC, so the new ASR models do not silently change runtime family or license.

The ACK-002 Q5 conditional trigger is absent. Required M2A rows are independent of
the small-Q8 result. HAT, accelerator models, PocketSphinx, cloud APIs and unpinned
community conversions remain prohibited.

## Fixture selection fixed before candidate output

### Internal eight

The controlled resolver verifies the frozen recording-plan SHA-256
`d197078d78ad422e1ec6465aea36472adcc4e77c24827c426a03dcbc4b4ba920`
and VAD-label index SHA-256
`85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74`.
Before any M2A candidate output is reviewed, it selects the two longest bounded
items in each group:

- Taiwan Mandarin;
- code-switch;
- number or date;
- product term.

This produces exactly eight unique fixtures and necessarily includes the globally
longest frozen-label-bounded item. Selection uses only frozen metadata, never model
output. Exact IDs remain pending because controlled labels and WAVs correctly do not
exist in Git.

### Common Voice twelve

The external sanity subset is pinned to official `Common Voice Scripted Speech 26.0
- Chinese (Taiwan)`, Mozilla Data Collective dataset ID
`cmqinooq000x0nr07b4p4ct4q`, locale `zh-TW`, license `CC0-1.0`, release timestamp
`2026-06-17T22:42:04.968Z`.

The resolver deterministically ranks eligible `validated.tsv` rows by SHA-256 over
dataset ID, clip path and sentence, then selects exactly twelve. Candidate output is
not an input to the rank. The controlled index retains reference text outside Git;
the eventual tracked index records only clip ID, source MP3 checksum, reference hash,
derived WAV checksum and duration.

Mozilla Data Collective requires authenticated download and acceptance of the
dataset terms. Codex did not create an account, accept terms for the User or receive
a token. The User supplied the downloaded archive; deterministic pre-output
selection and per-clip checksum review have now locked the exact twelve source MP3s.
Derived PCM remains pending, so this source lock does not advance the packet to
`LOCKED_NOT_EXECUTED` by itself.

The roughly 3 GB archive and extracted dataset do not need to reside on the
workstation system disk and must never be placed in this repository. An external
storage mount is supported: pass absolute paths on that mount for `validated.tsv`
and `clips/`, keep the mount stable until preselection finishes, and write the
controlled output outside Git. After the twelve selected MP3 checksums and derived
PCM lock have been reviewed, later candidate runs need only the locked twelve-clip
subset; retention of the full extracted tree follows the operator's data policy.

## Low-cost execution budget

For each standard row and each of the twenty locked fixtures:

- one unscored warm-up and one scored inference;
- per-item timeout: 120 seconds;
- row-level budget: 2400 seconds;
- no cold matrix, repeated hot cycles, soak or full lifecycle campaign.

The optional Qwen feasibility row uses only the globally longest internal item, a
180-second item timeout and a 600-second row budget. Timeout/OOM stops that row and is
retained as an observation.

Every standard row records transcript identity, normalized CER, exact-sentence
diagnostic, number/date and product correctness, load time, latency, RTF, peak RSS,
disk/runtime identity and cleanup. Artifact mismatch, unknown provenance/license,
runtime network access, OOM, bounded timeout and incomplete cleanup remain fail-closed
conditions, not quality rankings.

## Commands

The tracked packet can be validated locally without models or audio:

```sh
bash poc_audio/tools/run_m4a_m2a_packet.sh --validate-only
```

For the current external-storage archive, no extraction or write access to its
directory is required. The packet streams `validated.tsv` and the selected twelve
MP3 members directly from the archive:

```sh
bash poc_audio/tools/run_m4a_m2a_packet.sh \
  --recording-plan poc_audio/fixtures/authorized/recording_plan_v1.json \
  --vad-label-index /controlled/audio-poc/fixtures/review/vad-labels-v1.json \
  --common-voice-archive \
    /home/yee/utm/common_voice/1781716235246-cv-corpus-26.0-2026-06-12-zh-TW.tar.gz \
  --output /home/yee/utm/common_voice/m2a_work/fixture-preselection.json
```

After the User/operator has downloaded Common Voice 26.0 through the approved MDC
account and made the controlled frozen inputs available, create the pre-output
selection outside Git. The `/controlled/...` examples may be absolute paths on an
external storage mount:

```sh
bash poc_audio/tools/run_m4a_m2a_packet.sh \
  --recording-plan poc_audio/fixtures/authorized/recording_plan_v1.json \
  --vad-label-index /controlled/audio-poc/fixtures/review/vad-labels-v1.json \
  --common-voice-validated-tsv /controlled/audio-poc/common-voice-26/validated.tsv \
  --common-voice-clips-dir /controlled/audio-poc/common-voice-26/clips \
  --output /controlled/audio-poc/m2a/fixture-preselection.json
```

The preselection is still controlled and not committable because it contains Common
Voice text. The next implementation step derives and hashes selected PCM, records the
conversion identity/durations, emits a sanitized tracked index, changes manifest
status to `LOCKED_NOT_EXECUTED`, and only then prepares Pi execution commands.

The source selection is now recorded without transcript or audio in
[`m4a_m2a_common_voice_source_lock.json`](../manifests/m4a_m2a_common_voice_source_lock.json).
The twelve original MP3 files and controlled reference-text selection are retained
locally under the Git-ignored paths named in that lock. The tracked lock records the
controlled selection's size and SHA-256 without exposing its text. Verify a local or
newly downloaded MP3 handoff copy with:

```sh
bash poc_audio/tools/run_m4a_m2a_packet.sh \
  --verify-common-voice-clips-dir /controlled/path/to/the-twelve-clips
```

The UTM shared mount was too slow to finish a whole-archive SHA-256 before storage
handoff, so the archive filename and exact byte size are advisory. The twelve member
paths, byte sizes and per-clip SHA-256 values are authoritative and sufficient to
verify a fresh download even when its outer archive packaging differs.

## Current disposition

- Candidate/runtime identity: `PREPARED / LOCAL VALIDATION REQUIRED`
- Internal exact eight: `PENDING CONTROLLED LABEL RESOLUTION`
- Common Voice exact twelve source MP3s: `LOCKED / PER-CLIP SHA-256 VERIFIED`
- Derived PCM checksum lock: `NOT STARTED`
- Candidate build/load/inference: `PROHIBITED`
- M2A scorecard/shortlist: `NOT STARTED`
- M2B: `PENDING M2A SHORTLIST`
