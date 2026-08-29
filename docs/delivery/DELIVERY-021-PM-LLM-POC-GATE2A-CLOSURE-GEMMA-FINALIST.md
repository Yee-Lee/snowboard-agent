# DELIVERY-021 — Gate 2A Closure and Gemma Model Finalist

- **Date**: 2026-08-29
- **From**: LLM POC Team
- **To**: PM / Core Designer
- **Status**: `SUBMITTED — USER DECIDED / CORE ACK REQUESTED`
- **Packet**: `G2A-PI-LLM-002`
- **Execution SHA**: `e2b59fac609e0d768ff3554754363900cbed70a9`
- **Execution surface SHA-256**: `eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1`
- **User review**: `ASSESSMENT-LLM-M3-GATE2A-20260829-USER-REVIEW`

## Decision delivered

The User reviewed the complete final-surface Pi evidence, approved publication of the sanitized
comparison, selected `CAND-LRT-G4E2B-MOBILE-R1` (Gemma 4 E2B mobile) as the sole model finalist, and
closed the M3/Gate 2A POC execution and selection round. Qwen does not advance to the formal Gate 2B
path. This is a provisional model-selection decision, not a Gate 2B winner or production baseline.

## Evidence summary

| Candidate/run | P2 | P3 | P4 | P5 | P8 | Sanitized SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen / `G2A-PI-QWEN-004` | `FAIL` 0/30 | `PASS` | `Core threshold decision required` | `PASS` | `FAIL / DEPENDENCY_LIMITED_BY_P2` | `e0c000df51c26af5c9cc1f1704f13b8b8816b087d64ba596808b4e3be5b4530f` |
| Gemma / `G2A-PI-GEMMA-002` | `FAIL` 3/30 | `PASS` | `PASS` | `PASS` | `FAIL / DEPENDENCY_LIMITED_BY_P2` | `41f1d8e4f74bac25fd83a17fd0bdb776e9cb0bae1c4c04fdc345f378592681e7` |

Both observations used the same clean locked execution surface, distinct fresh boots, read-only
authenticated artifacts, offline namespaces, `swap=0`, zero full-model rehashes, clean log-hygiene
scans and zero final process residue. Machine dispositions and raw evidence are immutable.

Gemma materially outperformed Qwen on the fixed Pi method: TTFT P95 `727.983 ms` versus
`3069.772 ms`, decode P50 `11.293 tok/s` versus `4.313 tok/s`, and rebuild READY `460.339 ms` versus
`18054.122 ms`. Gemma also carries accepted Gate 1 PASS for P1, P6.1, P7.1, P10A, P11 and P12;
Qwen retains its P7.1 slow-recovery FAIL.

## Boundary preserved

This delivery does not rewrite Gemma P2/P8 as PASS. It applies the semantic separation requested in
`DELIVERY-019`: P2 qualifies the complete frozen integration configuration rather than ranking the
bare model, P3 remains an independent mandatory safety boundary, and P8 has no observed history
pollution but is dependency-limited by missing current-turn semantic compliance.

Consequently, Gemma is the selected **model finalist**, while its current product prompt/config is not
a deliverable baseline. Before scored Gate 2B execution, any integration adaptation must be a new
versioned candidate revision, frozen before scoring and evaluated against precommitted or held-out
cases. The current Gate 2A receipts must remain unchanged and must not be replaced by a tuned rerun.

## Core ACK requested

Please acknowledge in one response:

1. the User's sole Gemma model-finalist selection and Qwen exclusion from formal Gate 2B;
2. the immutable P2/P8 machine FAIL results and both P8 `DEPENDENCY_LIMITED_BY_P2` qualifiers;
3. the P2/P3/P8 semantic roles requested by `DELIVERY-019`;
4. the requirement for a new frozen, integration-qualified Gemma revision before Gate 2B scoring; and
5. that physical Gate 2B execution remains separately controlled by entry review, Accepted Audio
   staging and Pi authorization.

The repository closure commit SHA will be supplied after this delivery, assessment, milestone state
and round-close audit are committed and pushed together.
