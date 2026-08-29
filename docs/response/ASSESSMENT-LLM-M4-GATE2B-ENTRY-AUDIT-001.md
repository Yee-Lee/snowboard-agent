# ASSESSMENT-LLM-M4-GATE2B-ENTRY-AUDIT-001

- **Status**: `TWO INCONCLUSIVE ATTEMPTS RETAINED / ATTEMPT 003 USER AUTHORIZED`
- **Date**: 2026-08-29
- **Correction base HEAD**: `d79ade7cacc5bcd7abe4fbc2825d601c3fb58c39`
- **Packet**: `G2B-PI-COMBINED-001`, revision `2026-08-29-r7-resource-probe-preflight`
- **Gate 2B replacement lock SHA-256**: `fc59e26d2739c24be39e09c495dcd637bf073ba7370162af0a8b444a9d61975f`
- **Formal credit**: P9 and P10B only

## Conclusion

The obsolete Gate 2B consumer required an all-PASS Gate 2A provisional receipt and therefore could
not consume the User-reviewed final evidence, which preserves Gemma P2/P8 as `FAIL`. The worktree
now implements a replacement model-finalist boundary: only Gemma can enter; its old product pairing
remains rejected; a new generic structured-product prompt/config revision is frozen; and its first
model contact is the held-out Accepted Audio 20-session execution. Qwen is not present in the Gate
2B candidate lock.

The initial formal attempt is `INCONCLUSIVE`, not a candidate failure. Its controlled Audio store
omitted two sherpa-onnx wheel source files required by the Accepted TTS startup verifier. VAD and ASR
started, TTS rejected the incomplete store, LLM never started, zero sessions ran, and cleanup left
zero process or ALSA residue. The immutable sanitized evidence SHA-256 is
`50714d383cbefb75b96ae320e86bbb1ca64756f897f6b05eddd64f4f61a008f0`. The replacement authenticates
both wheel identities before any residency and used a new execution SHA, controlled-input root,
evidence root and run ID `G2B-PI-COMBINED-002`.

Attempt 002 authenticated that complete closure and started all four domains, then its first resource
sample found memory PSI unavailable. The Pi kernel has `CONFIG_PSI=y` and
`CONFIG_PSI_DEFAULT_DISABLED=y`, but the boot command line lacked `psi=1`; no cgroup memory-pressure
alternative exists because memory cgroups are disabled. Zero sessions ran, every domain stopped
cooperatively, and process/ALSA residue was zero. Its immutable sanitized evidence SHA-256 is
`1e3604406ce71d6a05a44bd3781838d92d6643ded4a67e32e7147db075f5f8ce`. Attempt 003 requires all
frozen resource probes before residency and runs under a reversible PSI-enabled test boot. That
reboot restored the platform's 2 GiB zram swap and cleared the boot-local `/tmp` artifact bind mount;
attempt 003 must explicitly restore `swap=0` and the same read-only persisted artifact mount. Neither
operation downloads or rehashes the model.

## Entry identities and immutable prior results

- Gate 2A execution: `e2b59fac609e0d768ff3554754363900cbed70a9`, surface
  `eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1`.
- Gemma reviewed result SHA-256:
  `41f1d8e4f74bac25fd83a17fd0bdb776e9cb0bae1c4c04fdc345f378592681e7`.
- Entry receipt retains P2/P8 `FAIL`, P3/P4/P5 and carried Gemma items `PASS`, and P8 qualifier
  `DEPENDENCY_LIMITED_BY_P2`. User selection advances the model only and cannot rewrite those
  observations.
- New pairing: `litert-lm-v0.16.0-pi-g2b-r1`; product-config SHA-256
  `78d55bdee44bbc4f22b12533674f74026324c118127f8878a0a0072e3f9734cd`.
- Core has received `DELIVERY-019` and `DELIVERY-021`, but no result/selection response is present
  yet. The newly received `DELIVERY-LLM-POC-M4B-GATE2A-PI-AUTH-001` explicitly says
  `GATE 2A PI EXECUTION AUTHORIZED / RESULT PENDING`; it is historical execution authority, not the
  missing result ACK, and has been archived accordingly. Per the User's sequencing decision, the
  result ACK does not block this authorized run but remains mandatory before final delivery.

## Accepted Audio provenance audit

The local Accepted Audio checkout is clean at completion
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`; annotated tag object
`24b2571a23dde2f77027242b61142b0c1a59924c` resolves to that completion. The exact Core HAL commit
`6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` exists locally, but the current Core checkout is dirty
and at another SHA, so it is not eligible for execution. Gate 2B requires a separate clean exact
Core checkout.

The 20 selected WAV bytes were copied to a disposable repo-external directory only for a static
audit. Running the unchanged Accepted Audio lock builder, which has no diff between Audio execution
`8be3bc095b504b8eab1dfeb21b94173728b9656f` and completion, produced:

- fixture-lock SHA-256 `d7d3086c578511763b60074ef7c049e37ef814094e399ad3562e3be2fda0e0f8`;
- exactly 20 ordered sessions, 4,480,880 bytes and 140.0 seconds total;
- zero checksum mismatches against delivered fixture manifest SHA-256
  `1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2`.

No audio content, transcript or lock is added to Git. The runner now statically authenticates the
fixture lock/manifest, VAD model, ASR worker/model, TTS archive/vocoder, both sherpa wheel sources and
isolated VAD/TTS runtime identities before any domain becomes resident. These hashes are outside both
LLM READY and combined P9/P10B timing.

## Executable behavior

- A dedicated Gate 2B adapter renders one deterministic generic schema instruction and contains no
  scored Audio session ID or prior P2 case.
- The real Accepted Audio VAD and ASR feed an in-memory transcript to one resident Gemma child. Its
  schema-valid `speak` text is passed in memory to the accepted TTS and exact Core HAL AudioOutput.
- P9 and P10B share one four-domain residency and exactly 20 sessions with 19 measured five-second
  pauses; no surrogate or broad P1–P8 rerun is selectable.
- Post-READY VAD/ASR/TTS session faults and LLM deadline/pipe/frame faults are typed candidate
  violations. Probe/evidence/environment failures remain `INCONCLUSIVE`.
- Installer logs, LLM stderr and accepted ASR stderr are scanned for static and per-session runtime
  markers. Sanitized evidence retains hashes and counters only.
- Cleanup registers ownership before awaiting start, stops LLM→TTS→ASR→VAD, and requires cooperative
  stop, waitpid, zero process-group residue and zero ALSA ownership for PASS.

## Workstation verification

The focused Gate 2B replacement suite returns `28/28 PASS`; Python compilation, JSON parsing and
`git diff --check` pass. The suite authenticates every lock entry, excludes Qwen, preserves Gate 2A
FAILs, rejects artifact/runtime/fixture drift, covers Audio and LLM post-READY failure typing,
recomputes P9/P10B, exercises partial-start cleanup and requires the Gate 2A-proven private-mount,
read-only-sysfs offline launch. It additionally requires both TTS wheel sources and proves omission
fails closed before residency. These are definition tests only and provide no Pi credit.

## Remaining entry work

1. complete replacement verification and User-authorized milestone commit/push;
2. confirm the reversible PSI-enabled Pi boot and complete pre-residency resource probe;
3. execute immutable replacement `G2B-PI-COMBINED-003` under the User's explicit authorization;
4. non-blocking independent review of the exact surface; and
5. User review before any result publication or final winner proposal.
