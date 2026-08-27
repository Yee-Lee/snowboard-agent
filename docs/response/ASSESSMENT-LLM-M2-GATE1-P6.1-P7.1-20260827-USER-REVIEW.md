# ASSESSMENT-LLM-M2-GATE1-P6.1-P7.1-20260827-USER-REVIEW

- **Status**: `USER APPROVED / QWEN DEFECT WAIVER / READY FOR CORE REVIEW`
- **Execution SHA**: `93772a1d86c9017e9889c39f2cb40cb8303bfcf6`
- **Execution surface**: `8c4856301618ee2eefd7b3c08470909bab4f70804b82df169ad9f796e5af79ac`
- **Target**: Raspberry Pi 5 4 GB, Debian 13 aarch64, swap zero, offline, `throttled=0x0`
- **Replacement scope**: legacy P6/P7 credit only

## Proposed adjudication

| Candidate | P1 | P6.1 | P7.1 | P10A | P11 | P12 | Gate 1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gemma 4 E2B | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Qwen2.5 1.5B Q8 | PASS | PASS | **FAIL** | PASS | PASS | PASS | **FAIL** |

The Gate 1 aggregate is `PASS`. Gemma is a normal finalist. Qwen's independent P7.1 rebuild missed
the unchanged ten-second product READY SLA, so its P7.1 and Gate 1 candidate scores remain FAIL.
The User explicitly retains Qwen as a Gate 2A candidate by defect waiver so it has a bounded
workaround opportunity; advancement does not rewrite the score or reuse superseded evidence.

## Replacement observations

| Run | Result | Initial READY | Required measurement | Receipt SHA-256 |
| --- | --- | ---: | --- | --- |
| `G1-P6.1-GEMMA-003` | PASS | `502.296 ms` | native cancel `1.069 ms`; async terminal `90.587 ms`; protocol CANCELLED `96.322 ms` | `a16297d5fe2417737f4489d74c7a88fe52321e38b8f6fd65f1f12a44a6ace8f1` |
| `G1-P7.1-GEMMA-001` | PASS | `505.050 ms` | abort-to-absence `15.109 ms`; rebuild READY `513.968 ms` | `72844e5278531294a897a1fdec3556f693082fae697008dd23c206247da27cbd` |
| `G1-P6.1-QWEN-001` | PASS | `3486.396 ms` | native cancel `1.046 ms`; async terminal `227.727 ms`; protocol CANCELLED `233.583 ms` | `d97be155e8a5b06a3d7f1796c6f04b48c45883b381334ba23fc9af2ad595ad77` |
| `G1-P7.1-QWEN-001` | FAIL | `3476.545 ms` | abort-to-absence `63.453 ms`; rebuild READY `18152.025 ms` (`SLOW_RECOVERY`) | `d1d6a67dbaaa99a6e60eac5fa7f9690dc834b6973cb9be64bdeb68b3db4ed034` |

All four valid observations used distinct boot IDs and one shared evidence root. Each authenticated
the full model once before READY, used the same source/surface/runtime/model/config identities,
ran with no swap or network route, and retained cleanup evidence. Both P6.1 runs invoked native
cancel exactly once, discarded the cancelled Conversation and completed a same-Engine fresh-
Conversation health RESULT. Neither P7.1 run invoked native cancel.

Qwen P7.1 did recover within the non-scoring 30-second diagnostic window and completed its health
RESULT and final cleanup. Its classification is therefore `SLOW_RECOVERY`, not wedged or corrupt;
the diagnostic recovery cannot convert the fixed ten-second P7.1 FAIL to PASS.

## Non-candidate attempts

Two pre-observation infrastructure attempts are retained separately and receive no P credit:

1. `G1-P6.1-GEMMA-001` stopped before model authentication because persistent model permissions
   were writable (`0664`); custody was restored to `0444` for both frozen artifacts.
2. `G1-P6.1-GEMMA-002` authenticated the model but the new adapter exited before Engine creation
   because direct-file execution did not insert the repository root. SHA `93772a1…` added the exact
   entrypoint regression; workstation focused tests then passed `36/36`.

Neither attempt reached READY, created a Conversation, invoked cancel or consumed a candidate
observation. They cannot replace or weaken the four immutable receipts above.

## Post-run target audit

- no LLM adapter or runner process remained;
- zram swap was restored at 2 GiB, priority 100, zero bytes used;
- Wi-Fi and the default route were restored;
- target checkout remained clean at `93772a1d86c9017e9889c39f2cb40cb8303bfcf6`;
- `vcgencmd get_throttled` remained `throttled=0x0`.

## User adjudication

The User adjudicated on 2026-08-27: keep Qwen P7.1 as a defect and retain its FAIL score, while
preserving Qwen candidate eligibility for Gate 2A and a workaround opportunity. Gemma and Qwen both
advance; Qwen carries the open defect. This approved result may now be committed/pushed and sent to
Core for one gate-completion review.
