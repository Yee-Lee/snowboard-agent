# CR-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001

Status: `USER APPROVED / READY FOR CORE REVIEW / M3 FORMAL EXECUTION BLOCKED`

## Decision requested

Core Designer is asked to authorize and deliver an explicit Core AudioOutput HAL
adaptation from the accepted Matcha finalist's native PCM contract to the target
ALSA device contract:

```text
AudioOutput public stream input: 16 kHz / mono / S16_LE
                         explicit Core HAL adaptation
Physical ALSA output:            48 kHz / stereo / S32_LE
```

Core must return the new full implementation SHA, accepted configuration contract,
dependency/artifact identities, tests and Pi evidence before Audio POC begins formal
M3 hardware qualification. This request advances final delivery checklist section 5
by making native TTS PCM playback reproducible on the accepted M3 HAL.

## Trigger and evidence

Audio POC began implementing the User-approved
`M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001` and inspected the Core repository at
`~/workspace/snowboard-agent/`.

Two identity/contract mismatches were found before hardware execution:

1. `de3b0bab4daaf47f62956d4b27f6697b3d4fa823` is the Audio POC Option A
   implementation/test validation SHA. It does not contain
   `src/sbd/core/audio/alsa/`. It must remain preserved as the POC validation
   identity, not be labelled as the Core HAL implementation SHA.
2. Core's accepted M3 product HAL implementation is
   `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`, accepted by completion commit/tag
   `2fb2e18f934c3d06392074adba3c4518402101e9` / `core_m3`. At that implementation,
   `AlsaAudioOutput.play()` accepts only complete 48 kHz stereo S32_LE native frames.
   The Matcha 1.13.5 finalist emits native 16 kHz mono PCM, so its ordered iterator
   cannot be sent to that AudioOutput without an unapproved conversion layer.

The governing Audio contract says the selected TTS native format determines the
AudioOutput stream boundary and prohibits hidden resampling in TTS/Speak. Audio POC
therefore cannot insert a private converter, relabel converted PCM as native, or use
generic ALSA playback as M3 HAL evidence.

No formal M3 hardware result has been produced. The mismatch was found during local
packet/runner preparation, before candidate SHA publication or Core packet sign-off.

## Requested Core implementation contract

### Public and native formats

- `audio.output.stream_format`: 16,000 Hz, mono, S16_LE.
- `audio.output.native_format`: 48,000 Hz, stereo, S32_LE.
- `AudioOutput.play()` accepts ordered legal chunks in stream format and consumes the
  complete iterator or returns one explicit bounded error.
- Format adaptation is owned by Core AudioOutput HAL. TTS/Speak remains a native
  16 kHz producer and performs no resampling, channel expansion or container change.

### Explicit adaptation

Core must document and pin:

- the 16→48 kHz resampler implementation, version, quality/profile and dependency
  checksums;
- state lifetime across arbitrary ordered PCM chunks and the exact end-of-input flush
  behavior;
- mono→stereo channel duplication/mapping;
- S16_LE→S32_LE scaling, clipping and valid-bit/alignment semantics; and
- buffering/period behavior at the existing direct `hw:` target.

The converter must be stateful across chunks and reset between independent play
sessions. Chunk boundaries must not change output samples, truncate the beginning or
end, repeat samples, or silently drop a final partial buffer.

### Lifecycle and failure requirements

- start/READY, stop/completion, cancel, force-abort and reopen remain bounded;
- invalid output device and write failure return the accepted explicit error/fallback
  behavior;
- cancellation/error/EOF release converter state, worker, iterator, PCM stream, file
  descriptors and device ownership;
- five reopen cycles produce fresh conversion state with zero final resource delta;
  and
- no runtime network access or artifact fetch is introduced.

### Required validation

Core local/portable tests must include:

1. deterministic conversion of fixed 16 kHz mono S16_LE fixtures;
2. one-shot versus adversarial legal chunking byte-equivalence;
3. exact input-consumption and output frame/channel/container accounting;
4. impulse/onset and final-tail retention, clipping and silence preservation;
5. success, invalid-device, write-error, cancel, force-abort and five-reopen cleanup;
6. strict config validation separating stream and native formats; and
7. regression proof that the accepted 48 kHz direct ALSA device negotiation remains
   unchanged.

Core Pi evidence must bind the new exact SHA and target INMP441/MAX98357A VoiceHAT
topology, then demonstrate complete playback through the physical speaker without
xrun corruption, truncation, repeated chunks or device residue. User listening of
the Matcha risk prompt set remains Audio POC M3 evidence and is not replaced by a
Core tone-only test.

## Exact identities after resolution

The M3 packet will record three distinct immutable identities:

| Identity | SHA |
| --- | --- |
| Audio POC Option A validation | `de3b0bab4daaf47f62956d4b27f6697b3d4fa823` |
| Superseded Core accepted HAL implementation | `5c9e5aac47e7f4f0dd168d8c75541438ee74f858` |
| New Core HAL implementation with output adaptation | `PENDING CORE DELIVERY` |

The existing Core M3 acceptance commit `2fb2e18f934c3d06392074adba3c4518402101e9`
remains historical acceptance evidence. Core must state whether the new AudioOutput
change is an append-only M3 HAL revision or an M4a-owned product delta, and provide
the authoritative acceptance/ACK commit that the POC must pin.

## Scope and execution boundary

- This request does not change the accepted VAD, ASR or TTS finalist identities.
- It does not authorize POC-side resampling, a format/candidate matrix, AEC, barge-in
  or product composition work.
- M4A-P9 remains a parallel Core/LLM input and does not block this M3 qualification
  preparation or the requested AudioOutput correction.
- Local packet validation, fake lifecycle and artifact-independent orchestration may
  continue.
- Formal M3 capture/playback qualification, candidate publication and hardware
  disposition remain stopped until the new Core SHA is received, packet identities
  are corrected, and Core signs off the committed packet.

## Response requested

Please return one written disposition that:

1. accepts or amends Core ownership of the explicit 16 kHz mono S16_LE to 48 kHz
   stereo S32_LE adaptation;
2. fixes the public/native output configuration and exact conversion semantics;
3. supplies the implementation/test plan and the new full Core SHA/acceptance SHA;
4. confirms the distinct POC validation and Core implementation identities above;
5. identifies any remaining blocker to Audio POC M3 packet sign-off; and
6. confirms M4A-P9 is not an Audio M3 hardware-qualification entry gate.
