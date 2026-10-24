# ASSESSMENT-LLM-M4-GATE2B-20260829-USER-REVIEW

- **Status**: `USER APPROVED / PUBLICATION AUTHORIZED`
- **Date**: 2026-08-29
- **Packet**: `G2B-PI-COMBINED-001`, revision `2026-08-29-r14-user-resource-adjustment`
- **Integration pairing**: `litert-lm-v0.16.0-pi-g2b-r5`
- **Formal run**: `G2B-PI-COMBINED-006`
- **Execution SHA**: `0c75536e6ee99b502c59438989ca852194648946`
- **Execution surface SHA-256**: `22f52d8b8b5b6d0aacbe2959c49441ccee30a0bacb68b9b8fcfc04877c14665a`
- **Sanitized evidence SHA-256**: `f5f5b3acd15e32bb0208da9f838cec4415469c28c12a45b25f8c2f5f55ad33fa`
- **Machine evidence publication flag**: `REVIEW_REQUIRED` at generation; satisfied by this User review
- **User finding classification**: `KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION`
- **User winner decision**: `CAND-LRT-G4E2B-MOBILE-R1 / POC WINNER / DEFECT WAIVER`

## User decision

The User approved publication of the immutable machine result, classified the retained-memory
observation as a known LiteRT-LM runtime defect, granted a defect waiver and selected
`CAND-LRT-G4E2B-MOBILE-R1` as the POC winner. The waiver changes the candidate disposition, not the
machine P-item values. Core final-winner ACK remains required before this becomes a production
dependency or model lock.

## Entry proof

The exact clean Pi checkout passed 84 tests, with one platform skip. Before formal evidence existed:

- `G2B-PREFLIGHT-006` returned `PASS`, created no evidence, loaded no domain and performed zero
  full-model hashes;
- `G2B-DIAGNOSTIC-006` returned `PASS` after one complete real
  VAD→ASR→LLM→TTS/ALSA session, created no evidence and left no process or ALSA residue;
- the diagnostic observed 19,639.210 ms end-to-end, 10,830.089 ms LLM time, 72 decode tokens,
  valid schema/current marker/trap boundaries, peak system-used memory 2,057.828 MiB, 51.8°C,
  `swap=0`, no OOM and no throttling;
- Accepted Audio controller, wheel/model/fixture identities, Gemma artifact receipt, LiteRT-LM
  v0.16.0 AArch64 runtime and execution surface were authenticated before residency.

Memory PSI was prospectively removed from this revision by User decision and is absent from the
runner, schema and result gate. This does not alter attempts 001–005. `DELIVERY-023` records the
corresponding Core contract adjustment request.

## Immutable machine result

The valid formal result is `FAIL`: P9 `FAIL`, P10B `FAIL`.

- All 20/20 held-out sessions completed the full VAD, ASR, LLM and TTS/ALSA path with terminal
  `SUCCESS`. Each LLM result satisfied schema, current-marker exactly-once, trap absence and
  prior-marker isolation requirements. No functional violation was recorded.
- The soak observed all 19 required pauses at or above five seconds and ran for 509,105.067 ms.
- Capacity and system health remained within bounds: peak system-used memory 2,382.969 MiB,
  peak temperature 54.0°C, `swap=0`, OOM delta zero, throttling zero, complete owner sets and
  maximum sample-start gap 0.254539 seconds.
- The frozen leak gate failed. Combined-process PSS slope was 5.900893 MiB/session versus the
  4 MiB/session limit, and late-minus-early median delta was 131.578 MiB versus the 64 MiB limit.
  The LLM owner contributed most of it: 5.484794 MiB/session and 115.865 MiB respectively.
- System-used memory did not show the same slope: 0.101957 MiB/session with a 32.750 MiB
  late-minus-early median delta, both within the frozen limits.
- The independent verifier reproduced `P9=FAIL` and `P10B=FAIL`. Under the frozen P10B rule,
  complete functional sessions do not produce P10B PASS when the shared P9 resource gate fails.

Attempt 006 is immutable. It must not be retuned, repeated under the same run ID or rewritten as a
PASS. The machine result proves that this pairing violates the predeclared process-PSS leak rule; it
does **not** by itself prove unreachable heap memory or impending system memory exhaustion.

## Lifecycle inspection

The Gate 2B adapter creates a fresh `Conversation` for every request and unconditionally executes
`conversation.close()` in a `finally` block. It clears the shared Python reference before close.
Thus there is no observed missing close or conversation reuse in the runner.

This matches LiteRT-LM's documented lifecycle: the Engine is the heavyweight model owner, a
Conversation is a lightweight stateful wrapper that internally owns a Session, and Conversation
close deletes its native resource. However, the official material does not promise that a retained
Engine returns process PSS to its prior baseline after every Conversation close, nor does it define
a repeated-conversation PSS plateau criterion.

## Primary-source experience review

- LiteRT-LM documents the expected one-Engine/multiple-Conversation lifecycle:
  <https://github.com/google-ai-edge/LiteRT-LM/blob/main/docs/api/cpp/conversation.md>.
- Its Kotlin implementation says `close()` releases the native Conversation resource and invokes
  `nativeDeleteConversation`:
  <https://github.com/google-ai-edge/LiteRT-LM/blob/main/kotlin/java/com/google/ai/edge/litertlm/Conversation.kt>.
- An upstream issue reports a close/recreate/send loop whose RSS ratchets upward while the Engine
  remains alive. That exact report is Android OpenCL/Qwen, while its CPU comparison plateaus, so it
  establishes precedent but does not reproduce this Pi CPU/Gemma case:
  <https://github.com/google-ai-edge/LiteRT-LM/issues/2699>.
- A separate CPU/Qwen report says fresh Conversations can retain Engine-level tool state and uses
  full Engine reload as a workaround. It concerns parser state rather than memory and is therefore
  corroborating lifecycle experience, not root-cause proof:
  <https://github.com/google-ai-edge/LiteRT-LM/issues/2256>.
- Another upstream report observes substantially larger memory use in LiteRT-LM 0.14/0.15 than
  0.13.1. It uses Gemma E4B with a much larger context on x86_64 and likewise cannot be treated as
  a reproduction of v0.16.0 on Pi:
  <https://github.com/google-ai-edge/LiteRT-LM/issues/2966>.
- Linux defines PSS as resident pages proportionally attributed across sharers. `smaps_rollup`
  separately exposes `Pss_Anon`, `Pss_File` and `Pss_Shmem`; `MemAvailable` instead estimates RAM
  available to new applications without swapping:
  <https://docs.kernel.org/filesystems/proc.html>.

The User classifies this observation as a **known LiteRT-LM runtime defect: Engine/Session resident
retention**. This is a project finding grounded in the Pi evidence and matching upstream experience;
it must not be represented as an upstream-confirmed reproduction for this exact Pi CPU/Gemma
v0.16.0 combination. The existing evidence records only total PSS, so it cannot distinguish
allocator/KV high-water (`Pss_Anon`) from lazy model/file residency (`Pss_File`) or shared memory.
The stable system-used slope explains why the Pi did not exhibit memory pressure despite the process
PSS gate failure; it does not invalidate the frozen PSS result.

## Cleanup and evidence integrity

- VAD, ASR, TTS and LLM stopped cooperatively in reverse order.
- Every recorded process group was absent; fallback cleanup was unused and ALSA owner count was zero.
- Pi postcondition retained `swap=0`, offline routes and `throttled=0x0`; the exact checkout was clean.
- The run performed zero full-model hashes and did not alter the authenticated model receipt.
- Raw transcript, prompt, output, audio, binaries, weights, credentials and endpoints are absent
  from this assessment and must remain outside Git.
- The pre-test `ollama.service` state has been restored to `active/enabled` after execution.

## Approved disposition

Accept Attempt 006 exactly as recorded and publish the retained-memory finding as
`KNOWN_RUNTIME_DEFECT`: functional integration completed 20/20 sessions, while the frozen
process-PSS rule still makes machine P9 and P10B fail. Preserve attempts 001–005 unchanged. Under the
User's defect waiver, Gemma is the POC winner and is submitted to Core for final-winner ACK. Neither
the waiver nor the winner decision rewrites the immutable machine scores.

If root-cause work is later authorized, use a new no-credit supplemental ID and collect
`Pss_Anon`, `Pss_File`, `Pss_Shmem`, `Private_Dirty` and allocator behavior before/after each
Conversation. Do not rerun or amend Attempt 006. An Engine/process-rebuild experiment may test a
workaround, but its READY/availability cost must remain explicit and it cannot change this score.
