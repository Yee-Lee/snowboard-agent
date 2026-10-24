# DELIVERY-019 — Gate 2A P2/P3/P8 Semantics Adjustment Request

- Date: 2026-08-29
- From: LLM POC Team
- To: PM / Core Designer
- Status: `REQUESTED — ACK MAY FOLLOW EXECUTION`
- Governing input: `DELIVERY-LLM-POC-M4B-CONTRACT-001.md`
- Current physical execution source: `ed7aaca2e187b2287d442d6841e1ab2610b67570`

## Decision requested

Please separate model selection from product-integration qualification for M4B-P2, preserve M4B-P3
as a deterministic safety-boundary test, and narrow M4B-P8 to history/KV isolation. This request does
not weaken the final product contract: a proposed production baseline must still produce valid product
results before final acceptance. It corrects what each result is allowed to conclude about a bare model.

Core ACK may arrive after the already-authorized frozen Gate 2A comparison finishes. This request does
not block the second candidate run, does not authorize Gate 2B, and does not permit a provisional
candidate proposal before User evidence review and the resulting disposition are complete.

## Requested semantics

| Item | Revised role | Result interpretation |
| --- | --- | --- |
| P2 | Model + chat template + PromptBuilder + generation config integration qualification | A failure rejects the tested candidate configuration as a deliverable baseline. It must not, by itself, reject the underlying model artifact or rank bare model capability. |
| P3 | Reference normalizer, fallback, allowlist and log-hygiene safety qualification | Remains independently mandatory. It evaluates deterministic containment of untrusted output and is not a model-quality ranking. |
| P8 | Fresh-conversation, prior-turn marker, KV-envelope and context-pollution qualification | A proven prior-state leak remains `FAIL`. If current-turn semantic compliance is unavailable because P2 failed, P8 must be reported as dependency-limited rather than described as observed history pollution. |

The existing closed result vocabulary may remain unchanged in stored receipts. Until Core chooses a
schema revision, the assessment must pair the stored P8 disposition with an explicit causal qualifier:
`DEPENDENCY_LIMITED_BY_P2`, `OBSERVED_HISTORY_POLLUTION`, or `INCONCLUSIVE_OBSERVATION`. No stored
receipt may be relabelled or overwritten.

## Anti-overfitting boundary

The LLM POC Team will not tune a prompt, token envelope, fixture, repetition count or decision rule
against the current scored catalog and then claim the rerun is the same acceptance cycle. The current
frozen evidence remains immutable.

If integration adaptation is pursued, it must be a separately identified development cycle:

1. use declared development cases and a bounded adaptation budget;
2. version the complete model/runtime/chat-template/prompt/config pairing as a new candidate revision;
3. freeze the revised surface before scoring;
4. score it with a new precommitted or independently held-out catalog; and
5. retain the present observations as prior-cycle evidence, not replacement evidence.

## Execution and publication boundary

- Continue the authorized two-candidate Gate 2A run at exact `ed7aaca…`; do not patch the Pi checkout.
- Preserve machine dispositions and raw evidence from both candidates exactly as produced.
- Treat the comparison as evidence about the frozen configurations, not permission to select a bare
  model from P2/P8 alone.
- Do not publish benchmark results or propose a provisional finalist until the User reviews the complete
  two-candidate evidence.
- Do not start Gate 2B until the Gate 2A review and applicable Core disposition are complete.

## Requested Core ACK

Please ACK the three semantic roles above and confirm that the current frozen comparison may finish
while this adjustment is under review. If Core requires a schema revision, please require it only for a
new candidate/configuration cycle and do not request mutation or rerun of the preserved current evidence.
