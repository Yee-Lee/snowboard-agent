# ASSESSMENT-LLM-M3-GATE2A-20260829 — User Evidence Review and Model Finalist Decision

- **Date**: 2026-08-29
- **Status**: `USER APPROVED / GEMMA MODEL FINALIST / MACHINE RESULTS IMMUTABLE`
- **Packet**: `G2A-PI-LLM-002`
- **Execution SHA**: `e2b59fac609e0d768ff3554754363900cbed70a9`
- **Execution surface SHA-256**: `eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1`
- **User decision**: approve the completed comparison, advance Gemma as the sole model finalist, and close the Gate 2A POC round

## Evidence reviewed

Both final observations used distinct reboot-isolated Pi 5 boots, the same clean execution SHA and
locked surface, read-only artifact staging, a private offline network namespace, `swap=0`, and no
full-model rehash. Raw evidence remains outside Git; only sanitized measurements and checksums are
reported here.

| Run | Candidate | Sanitized evidence SHA-256 | Bytes | Machine scope result |
| --- | --- | --- | ---: | --- |
| `G2A-PI-QWEN-004` | Qwen2.5-1.5B Q8 | `e0c000df51c26af5c9cc1f1704f13b8b8816b087d64ba596808b4e3be5b4530f` | 27645 | `FAIL / NOT_ELIGIBLE` |
| `G2A-PI-GEMMA-002` | Gemma 4 E2B mobile | `41f1d8e4f74bac25fd83a17fd0bdb776e9cb0bae1c4c04fdc345f378592681e7` | 27357 | `FAIL / NOT_ELIGIBLE` |

The earlier Qwen pre-READY, environment-preflight and controller-race attempts remain immutable
diagnostic history and provide no scored replacement. The earlier Gemma result was not reused after
the shared adapter surface changed; `G2A-PI-GEMMA-002` is the final-surface observation.

## Immutable machine dispositions

| Candidate | P2 | P3 | P4 | P5 | P8 | Causal interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen | `FAIL` (0/30) | `PASS` | `Core threshold decision required` | `PASS` | `FAIL` | P2 requests reached child-owned timeout; P8 has no prior-state leak but lacks successful current-turn semantics, therefore `DEPENDENCY_LIMITED_BY_P2` |
| Gemma | `FAIL` (3/30) | `PASS` | `PASS` | `PASS` | `FAIL` | P2 returned results but only `P2-005` matched all three repetitions; P8 has no prior-state leak but lacks the current marker, therefore `DEPENDENCY_LIMITED_BY_P2` |

No stored receipt is relabelled. P2 remains evidence that each frozen model/chat-template/prompt/config
pairing is not a deliverable product baseline. P8 is not described as history pollution: both
candidates showed zero prior-marker leakage, and Gemma kept every request inside the single-turn KV
envelope. P3 safety containment and log hygiene passed independently for both candidates.

## Comparative measurements

| Candidate | TTFT P95 | Decode P50 | Hot wall P50 | P5 timeout | Rebuild READY |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen | `3069.772 ms` | `4.313 tok/s` | `6554.854 ms` | `15175.288 ms` | `18054.122 ms` |
| Gemma | `727.983 ms` | `11.293 tok/s` | `2065.820 ms` | `15069.013 ms` | `460.339 ms` |

Both P5 runs produced the required bounded timeout, exactly one active-chunk native cancel, healthy
same-child generation, clean rebuild and zero residue. Gemma also carries accepted Gate 1 PASS for
P1, P6.1, P7.1, P10A, P11 and P12. Qwen retains its immutable Gate 1 P7.1 slow-recovery FAIL and its
deferred P1.2 true-cold startup finding.

## User selection and closure

The User selects `CAND-LRT-G4E2B-MOBILE-R1` as the sole **model finalist** and excludes Qwen from the
formal Gate 2B path. This is a model-selection decision under the requested P2/P3/P8 semantic split;
it is not a claim that the frozen Gemma product configuration passed P2 or P8, and it is not a final
winner or production baseline decision.

The M3/Gate 2A POC execution and selection round is complete. External Core closure remains a separate
ACK. Before scored Gate 2B execution, the Gemma product integration must be versioned as a new
candidate revision, frozen before scoring, checked against a precommitted or held-out catalog, and
reviewed without overwriting either Gate 2A observation. The accepted Audio identity, 4 GB offline
staging and separate Pi execution authorization remain mandatory Gate 2B entry conditions.

## Remaining items

- Core ACK of `DELIVERY-019` and the Gate 2A closure/model-finalist delivery.
- A new integration-qualified Gemma prompt/config candidate revision and Gate 2B consumer boundary.
- User/reviewer/Core entry review and physical-Pi authorization before Gate 2B execution.
- Deferred, no-credit P1.2 cause matrix and optional left-candidate Gate 2B comparison remain
  post-delivery informational backlog only.
