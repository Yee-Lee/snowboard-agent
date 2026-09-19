# M4C-SS-POC-PACKET-001

Status：`WORKSTATION IMPLEMENTATION VERIFIED / PI PREFLIGHT PARTIAL / EXECUTION SHA PENDING`

## Identity and authority

This packet implements `REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001`. It is not executable on target until
the workstation changes are committed and pushed with User authorization, the lock is generated from those exact
bytes, and User separately authorizes the exact Pi/preflight/execution scope. The future execution commit must be
a descendant of `5080abd84dafcbc0f8307a086fa8009a0b6a818b`.

The runner must reject a dirty checkout, mismatched full SHA/surface/profile/artifact, active network interface,
non-Pi/non-Debian/non-CPython-3.13.5 target, missing USB measurement microphone or any untracked binary. Raw
prompt/output/audio and private paths never enter Git.

## Workstation commands

```text
.venv/bin/python -W error::ResourceWarning -m unittest discover -v -s poc_llm/tests/m4c_ss -p 'test_*.py'
.venv/bin/python -W error::ResourceWarning -m unittest discover -v -s poc_llm/tests/efficiency -p 'test_*.py'
.venv/bin/python -m poc_llm.tools.run_m4c_ss plan
.venv/bin/python -m poc_llm.tools.run_m4c_ss controller C01-ONE
```

Run each of the 15 controller IDs exactly once through the last command before target entry. A failure is retained;
there is no automatic retry.

Workstation result on 2026-09-19: M4C-SS 48/48 PASS, efficiency 46/46 PASS, and exactly 82 unique plan keys.
The full macOS suite retains unrelated Linux/platform failures, so only the two targeted suites are entry checks.

## Future exact target command shape

The following is deliberately blocked until `<IMPLEMENTATION_SHA>` and `<SURFACE_SHA256>` are replaced by the
User-authorized pushed values and `<PRIVATE_RECEIPT>` resolves through the approved private target configuration:

```text
python3 -m poc_llm.tools.run_m4c_ss preflight --operator-authorized --implementation-sha <IMPLEMENTATION_SHA> --surface-sha256 <SURFACE_SHA256> --private-receipt <PRIVATE_RECEIPT>
```

Mapping, live A/B and negative execution commands will be enabled only after this preflight and USB acoustic
calibration pass. No placeholder command may produce formal evidence.

## Fixed accounting

- controller：15 subcases (`C01`–`C10`, including all specified injection points);
- mapping：18 samples (B1/B2 × T01/T02/T03 × 3, alternating candidate order);
- live A/B：40 samples (L01–L04 × 5 pairs × 2 arms, `A-B/B-A/A-B/B-A/A-B`);
- live negative：9 subcases;
- total：82.

The authoritative keys come from `python3 -m poc_llm.tools.run_m4c_ss plan`. Missing keys force
`INCONCLUSIVE`. A single harness-defect rerun retains both attempts and does not replace the original.

## Stop and cleanup

Use the Income watchdogs and safety stops literally. Every negative/cancelled case must close admission, stop future
generation/TTS/playback, reject late callbacks, clear the bounded queue and prove no operation/iterator/Audio owner.
Cooperative abort is bounded at 2 seconds; Speak/TTS force abort at 1 second and Reasoner force abort at 3 seconds.
Forced destruction never becomes normal success. Any identity/sampler loss, cleanup failure, OOM/kernel fault,
temperature `>=80 C`, thermal throttling or pre-case `MemAvailable <512 MiB` stops the affected mode.

## USB acoustic gate

I²S remains the product playback path. A fixed-position USB microphone is measurement instrumentation only and
must not enter Listen/ASR. Freeze its ALSA identity, gain, sample rate, speaker volume, distance/angle, ambient
gate, detector and calibration. Measured clock plus detector uncertainty must be `<=50 ms`; otherwise acoustic
latency is `INCONCLUSIVE` and no `B_RECOMMENDED` disposition is allowed.

The 2026-09-19 engineering preflight proved simultaneous I2S VoiceHAT playback and independent USB AB13X
capture at the USB device's negotiated 48 kHz mono S16_LE format. The strict monotonic calibration did not run,
so the `<=50 ms` gate remains open. No packet case was executed.
