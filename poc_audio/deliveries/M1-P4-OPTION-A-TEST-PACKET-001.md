# M1 P4 Option A test packet

- **Test packet ID:** `M1-P4-OPTION-A-001`
- **Delivery requirement:** `DELIVERY-AUDIO-POC-M3-VALIDATION-001`, P4-A01–A10
- **Purpose:** qualify one exploratory 48 kHz stereo S32_LE to 16 kHz mono
  S16_LE implementation without changing Core production source
- **Current disposition:** `PREPARED / NOT EXECUTED`

## Preconditions

- Raspberry Pi 5, INMP441, MAX98357A, `googlevoicehat-soundcard`, and wiring
  attestation are available.
- Pi worktree is clean and checked out at the packet's full 40-character SHA.
- `environment_pre_test.sh` passes before the audio session.
- Candidate source archives match `manifests/option_a_candidates.json`; target
  build dependencies and license notices are retained outside Git.
- Capture and playback overrides name direct ALSA `hw:` devices only.
- Formal resource measurement does not overlap pre-test, fixture recording, or
  another audio-device owner.

## Packet preparation

```sh
PYTHONPATH=poc_audio/src python3 -m unittest discover -s poc_audio/tests -v
bash poc_audio/tools/run_option_a_validation.sh prepare
PYTHONPATH=poc_audio/src python3 -m audio_poc.option_a_fixtures \
  poc_audio/evidence/m3_option_a/<timestamp>/raw/deterministic-fixtures
bash poc_audio/tools/run_option_a_conversion.sh \
  poc_audio/evidence/m3_option_a/<timestamp>/raw/conversion
bash poc_audio/tools/run_option_a_valid_bits.sh \
  poc_audio/fixtures/artifacts/<authorized-pilot> \
  poc_audio/evidence/m3_option_a/<timestamp>/raw/valid-bits.json
```

Preparation creates a manifest with every test `Pending`; it is not hardware
evidence. The Tester records the exact realized commands in the manifest as
the implementation runners become available in P4-02 through P4-06.

## Frozen gates and repetitions

| ID | Gate | Repetition / duration | Required evidence |
| --- | --- | --- | --- |
| P4-A01 | Direct `hw:` realizes 48000 Hz, 2 ch, S32_LE | open, stop, reopen | requested/realized parameters and ALSA identity |
| P4-A02 | Channel, valid bits, alignment, sign, and full-scale mapping agree across three evidence sources | known signal plus raw analysis | wiring attestation, sanitized sample statistics, formula |
| P4-A03 | One stateful converter survives irregular chunks without dropping samples or per-chunk rebuild | all deterministic chunk patterns | ratio, mode, state and flush trace |
| P4-A04 | 12 kHz alias attenuation is at least 40 dB; S16 saturates without wrap | all six deterministic fixtures | raw calculations and fixture hashes |
| P4-A05 | Every steady-state yield is 320 samples / 640 bytes | irregular chunks through flush | frame sizes, delay, startup and partial-output trace |
| P4-A06 | Event loop remains responsive and does not busy-poll | capture plus playback heartbeat | ownership model and worst heartbeat gap |
| P4-A07 | Stop is idempotent; all normal, cancel and failure paths clean | at least 10 reopen cycles | task/thread/fd/ALSA-owner counters per path |
| P4-A08 | Buffer model is explicit; all xruns are explained | at least 5 minutes capture adaptation plus shared-clock playback | period/buffer settings and xrun series |
| P4-A09 | Raw latency/resources follow 10 warm-ups | measured run after warm-up | latency samples, P50/P95/max, CPU, RSS, temperature, throttling |
| P4-A10 | Clean target source build and rerun are reproducible | one clean build plus identity rerun | environment, commands, hashes, licenses, native-library identity |

No threshold may be relaxed after observing results. A missing environment is
`Blocked`; insufficient evidence is `INCONCLUSIVE`; a measured gate miss is
`FAIL`.

## Required cleanup

After every normal, cancel, failure, and endurance path, record task, thread,
file-descriptor, and ALSA-owner counts. `PASS` is invalid unless every counter
is zero. Preserve raw evidence in the packet's ignored `raw/` directory and
promote only reviewed, sanitized summaries.
