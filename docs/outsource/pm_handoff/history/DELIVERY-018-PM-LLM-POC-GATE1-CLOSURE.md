# DELIVERY-018-PM-LLM-POC-GATE1-CLOSURE

- **Status**: `USER APPROVED / READY FOR CORE GATE-COMPLETION REVIEW`
- **Date**: 2026-08-27
- **From**: LLM POC Team (M4b)
- **To**: Core Designer / PM Team
- **Gate**: Gate 1 cumulative closure review
- **Branch**: `llm`
- **Delivery SHA**: supplied after this delivery commit; never self-prefilled
- **Execution SHA**: `93772a1d86c9017e9889c39f2cb40cb8303bfcf6`
- **Execution surface**: `8c4856301618ee2eefd7b3c08470909bab4f70804b82df169ad9f796e5af79ac`
- **Core input**: `DELIVERY-LLM-POC-M4B-CUMULATIVE-GATES-R3-ACK-001`

## 1. Single decision requested

Please perform one gate-completion review and ACK all of the following together:

1. accept the four immutable reboot-isolated P6.1/P7.1 replacement receipts below;
2. preserve Qwen P7.1 as `FAIL / SLOW_RECOVERY` without threshold or score modification;
3. close Gate 1 aggregate `PASS` with Gemma as a normal finalist;
4. record the User's explicit defect waiver retaining Qwen as a Gate 2A candidate with its P7.1
   defect open and a bounded workaround opportunity; and
5. allow both candidates to enter Gate 2A for P2/P3/P4/P5/P8, without rerunning or rewriting P7.1.

This is not a request to declare Qwen P7.1 PASS. The waiver separates candidate advancement from
the immutable test score. Qwen cannot become the eventual accepted baseline unless its open
recovery defect receives an explicit product workaround disposition from User/Core.

## 2. Corrective execution surface

Official LiteRT-LM v0.16 source review invalidated the legacy synchronous-cancel P6 method and the
P7 observation coupled to it. The replacement surface uses official asynchronous inference for
P6.1 and a completely independent reboot/force-abort path for P7.1:

- P6.1 uses one `send_message_async()`, proven stream activity, exactly one native cancel,
  correlated terminal within 500 ms, poisoned Conversation disposal, then same-Engine fresh-
  Conversation health.
- P7.1 calls no cancel API. It proves TERM/bounded wait/KILL-if-needed/waitpid/group absence, then
  performs one rebuild. READY at ten seconds fixes the score; observation to 30 seconds is
  diagnostic only.
- Each `{candidate,test}` uses a distinct boot ID, one source/surface and a shared fail-closed
  evidence root that rejects duplicate observations.

Workstation Gate 1 regression passed `135/135`; the Pi-discovered direct-file import correction
added an exact entrypoint regression, after which the focused surface passed `36/36`.

## 3. Replacement evidence

| Run | Candidate/test | Result | Key measurement | Sanitized receipt SHA-256 |
| --- | --- | --- | --- | --- |
| `G1-P6.1-GEMMA-003` | Gemma P6.1 | PASS | READY `502.296 ms`; native cancel `1.069 ms`; CANCELLED `96.322 ms` | `a16297d5fe2417737f4489d74c7a88fe52321e38b8f6fd65f1f12a44a6ace8f1` |
| `G1-P7.1-GEMMA-001` | Gemma P7.1 | PASS | abort/absence `15.109 ms`; rebuild READY `513.968 ms` | `72844e5278531294a897a1fdec3556f693082fae697008dd23c206247da27cbd` |
| `G1-P6.1-QWEN-001` | Qwen P6.1 | PASS | READY `3486.396 ms`; native cancel `1.046 ms`; CANCELLED `233.583 ms` | `d97be155e8a5b06a3d7f1796c6f04b48c45883b381334ba23fc9af2ad595ad77` |
| `G1-P7.1-QWEN-001` | Qwen P7.1 | **FAIL** | initial READY `3476.545 ms`; rebuild READY `18152.025 ms` | `d1d6a67dbaaa99a6e60eac5fa7f9690dc834b6973cb9be64bdeb68b3db4ed034` |

Qwen P7.1 invoked no cancel API. It proved process-group absence in `63.453 ms`, recovered within
the diagnostic 30-second window, completed a health RESULT and cleaned up. It is therefore a clear
`SLOW_RECOVERY` defect, not a wedge and not cancellation contamination. The unchanged ten-second
product SLA makes the score an immutable FAIL.

Two retained infrastructure attempts receive no candidate credit: one stopped before model
authentication on writable custody permissions, and one stopped after authentication but before
Engine creation on the direct-file import defect. Neither reached READY or invoked candidate work.

## 4. Cumulative Gate 1 adjudication

| Candidate | P1 | P6.1 | P7.1 | P10A | P11 | P12 | Score | Gate 2A eligibility |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gemma 4 E2B | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | **Finalist** |
| Qwen2.5 1.5B Q8 | PASS | PASS | **FAIL** | PASS | PASS | PASS | **FAIL** | **User defect waiver / candidate retained** |

The User explicitly adjudicated: retain the Qwen P7 defect and score, but allow a workaround
opportunity by advancing Qwen to Gate 2A. This does not consume a retry, extend the threshold or
change the evidence. Gate 2A compares both candidates on the remaining formal items.

## 5. Environment and cleanup closure

The four receipts were produced on Raspberry Pi 5 4 GB / Debian 13 aarch64 with a clean exact
checkout, swap zero, offline routes/interfaces, authenticated runtime/model/config identity and
`throttled=0x0`. Post-run audit found no LLM process, restored Wi-Fi/default route, restored 2 GiB
priority-100 zram with zero usage, clean SHA `93772a1…`, and `throttled=0x0`. Models, wheel, raw
stderr, prompts, payloads, outputs, credentials, endpoints and host identity remain outside Git.

## 6. Carry-forward and workaround boundary

Gate 2A runs P2/P3/P4/P5/P8 for both retained candidates and carries every Gate 1 score unchanged.
It must not rerun P7.1 merely to seek a favorable result. Qwen's workaround study is non-scoring
and may consider product lifecycle controls such as avoiding on-demand Engine rebuild or maintaining
a pre-initialized recovery process, subject to actual 4 GB resource evidence and Core architecture
acceptance. A workaround cannot silently weaken the ten-second requirement or claim P7 PASS.

At most one provisional candidate may leave Gate 2A. Qwen is eligible for that comparison, but any
Qwen provisional recommendation must explicitly carry the P7 defect and a written workaround
disposition. Gate 2B and final winner acceptance remain separate Core decisions.

## 7. Review references

- `docs/response/ASSESSMENT-LLM-M2-GATE1-P6.1-P7.1-20260827-USER-REVIEW.md`
- `docs/response/ASSESSMENT-LLM-M2-GATE1-RUNNER-EXECUTION-LESSONS-001.md`
- `poc_llm/tests/gate1/GATE1-P6.1-P7.1-REDESIGN-001.md`
- `poc_llm/harness/gate1-p6-1-p7-1-lock-v1.json`

Gate 1 is User-adjudicated but is not externally closed until Core issues its written ACK against
the committed delivery SHA and the four receipt hashes above.
