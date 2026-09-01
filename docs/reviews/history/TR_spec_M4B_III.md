---
requestor: "Designer"
owner: "Tester"
status: "Resolved"
severity: "Blocking"
---

# TR_spec_M4B_III — Core generic renderer quality-oracle delta

## Review boundary

`IR_dev_M4B_II` proved that the approved Core generic renderer/schema cannot guarantee the Gate 2B harness-only
current literal. Designer selected Option 3: preserve immutable Gate 2B marker evidence, but replace the Core
Gate 3 exact-literal oracle with current semantic binding plus fresh-Conversation/prior-state isolation.

Tester shall revise only `M4B-OUT-001`, `M4B-HIST-001`, `M4B-RES-001`, their direct catalog/result-card fields,
and the M4b conclusion/card validator mappings. The other 12 M4b Test IDs, r14 resource thresholds, portable/Pi
platform split, runtime/model/config/renderer identities, lifecycle and M4a Accepted contract do not reopen.

## Required spec corrections

### TR-M4B-III-01 — `M4B-OUT-001` current semantic oracle

- Remove Core current-marker exactly-once, forbidden-literal and prior-marker fields/assertions from OUT. State
  explicitly that `speak.text` is nonblank and is not required to echo an arbitrary literal.
- Keep a bounded table-driven `speak/tool/rest` product catalog. Each real Pi case must pass the exact constrained
  response schema and independent Reasoner validator, match the current input's expected `action_kind`, use the
  exact current tool name when `tool`, and use only current `next_perceptions` capabilities.
- Preserve `tool_handler_calls=0`, P5/invalid-output coverage, capability allowlist and raw-output privacy.
- Recommended card fields: `catalog_case_count`, `schema_pass_count`, `expected_action_pass_count`,
  `reasoner_validation_pass_count`, `current_input_binding_pass_count`, `tool_handler_calls`.

### TR-M4B-III-02 — `M4B-HIST-001` isolation oracle

- Replace the five current-marker positive assertions with five current-turn semantic positive assertions. Every
  transition must also prove a fresh Conversation was created and closed, and assert zero prior action/tool/
  perception/canary state in the current result.
- Retain the existing contamination dimensions: prior perception sentinel, prior tool intent/arguments, prior
  speak content, prior `next_perceptions`, and injected pre-filled Conversation. Bind each to a current expected
  action/tool/next-perception so empty/P5/unrelated output cannot false-pass the negative check.
- Keep persistent Engine/PID within each generation and only the planned attempt-8/16 generation changes.
- Recommended card fields: `turn_count`, `conversation_count`, `conversation_close_count`,
  `current_semantic_pass_count`, `prior_state_hits`, `child_pid_stable`.

### TR-M4B-III-03 — `M4B-RES-001` 20-session functional validity

- Keep 20 accepted sessions, three child generations, Audio→LLM→TTS terminals, same-SHA identity, offline,
  cleanup, resource samples and every r14 4/64 / 4 GB / swap / OOM / throttle / thermal gate unchanged.
- Replace per-session marker counting with 20/20 exact schema, Reasoner validation, current `speak` binding,
  nonblank text, exact current singleton `next_perceptions`, and successful TTS terminal.
- Resource success must not mask any functional failure; P5, wrong action, wrong next perception, blank output or
  TTS failure makes the session rejected and the full run Fail.

### TR-M4B-III-04 — Catalog, candidate cards and privacy

- Revise the canonical Gate 3 catalog schema and card validator mappings so no Core field requires
  `current_format`, `forbidden_format`, `instruction_format`, `current_marker_exactly_once`,
  `current_marker_pass_count`, `prior_marker_hits` or `forbidden_literal_hits`.
- Preserve the POC provenance locator/checksum and inheritance statement, while declaring its marker profile
  harness-only and not copied into the Core request/schema.
- Result cards may contain counts, statuses, public catalog identity and response digests only. They must not contain
  perception text, model output, prior canary text, tool arguments or private paths.
- Exact implementation touchpoints for the downstream Developer are
  `requirements/m4b/gate3-product-catalog.json`,
  `scripts/m4b_target_metrics.py::load_gate3_catalog`,
  `tests/m4b_target_cases.py::test_m4b_exact_product_gate3_cards`,
  `scripts/candidate_gate.py` M4B card schemas, `tests/test_m4b_res_001.py`, and
  `tests/test_candidate_gate.py`. No production renderer/schema change is required.

## Minimum regression package

1. A schema-valid, current-semantic `speak` result with no literal marker passes OUT and the combined session row.
2. Fixed semantic `speak/tool/rest` cases all match current action/capability/tool bindings and pass Reasoner;
   P5 or a schema-only but semantically wrong result cannot count.
3. Five history transitions prove current semantic PASS, fresh create/close, zero prior-state hits and correct
   engine/PID/generation behavior; inject each prior-state dimension to prove it fails closed.
4. The 20-session row retains every resource, lifecycle, offline, cleanup and Audio/TTS assertion while replacing
   only marker counts with current-input-binding counts.
5. Catalog/card negative tests reject obsolete marker fields and reject missing/wrong new semantic evidence;
   stdout/stderr/cards contain none of the private values.

## Exit

Tester revises `docs/test_spec/test_spec_M4.md`, records exact revised locations and changes this review to
`Revised`. Designer then checks only `TR-M4B-III-01..04`, direct evidence schema and new regression requirements.
Until this review is `Resolved`, Developer fast-loop work may continue, but provisional candidate creation,
formal portable matrix, Pi Gate 3 and acceptance evidence remain blocked.

## Tester revision response（2026-09-01，USER-authorized proxy execution）

| Finding | Revised location in `docs/test_spec/test_spec_M4.md` | Disposition |
| :--- | :--- | :--- |
| `TR-M4B-III-01` current semantic oracle | `M4B-OUT-001` heading, Evidence, constrained catalog, `Current semantic binding`, canonical catalog | Removed all Core exact-marker PASS requirements. Fixed OUT card to 23/23 schema/action/Reasoner/current-binding with `tool_handler_calls=0`; nonblank `speak` no longer echoes a literal. |
| `TR-M4B-III-02` history isolation | `M4B-HIST-001` Evidence, five-turn catalog, create/close reconciliation, generation table | Replaced marker positive oracle with five current-semantic transitions, portable fresh-object/close proof, zero prior-state hits and same-generation PID evidence. |
| `TR-M4B-III-03` combined functional validity | `M4B-RES-001` Evidence, Additional assertions, `Semantic result-card exactness` | Preserved all 20-session, three-generation, r14 4/64, offline, cleanup and Audio/TTS gates; added six independent 20/20 functional counters. |
| `TR-M4B-III-04` catalog/card/privacy | `M4B-OUT-001` canonical catalog; `M4B-RES-001` card exactness; `M4B-INH-001` P2/P3/P8/delta rows; M4b conclusion fields | Bound exact marker-free catalog digest `9539cc4d...ce6a`, declared POC marker provenance harness-only, rejected obsolete marker fields, fixed sanitized card fields and added conclusion catalog digest. |

Catalog `schema_version=1` / `catalog_id=M4B-CORE-GATE3-PRODUCT-001` remains valid because the old marker-shaped
Core catalog never became a provisional/frozen candidate or formal evidence. The exact tracked digest is changed
and frozen before candidate creation, so no published candidate identity or historical Gate 2B evidence is rewritten.

### Tester regression evidence

Command:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  tests/test_m4b_out_001.py tests/test_m4b_hist_001.py \
  tests/test_m4b_res_001.py tests/test_candidate_gate.py
```

Result: exit code 0, all collected cases PASS. `git diff --check` also PASS. No Pi execution or acceptance
claim was made; this evidence is only the portable spec/regression closure required by this review.

## Designer final confirmation（2026-09-01）

Designer rechecked only `TR-M4B-III-01..04`, their direct evidence schema and regression package:

- OUT now proves current action/tool/next-perception binding and independent Reasoner validation without a
  non-product literal requirement;
- HIST combines a nontrivial current positive oracle, prior-state negatives and fresh Conversation/create-close
  structural proof, so absence-only or P5 output cannot false-pass;
- RES retains every resource/lifecycle/composition gate and makes each of the six functional dimensions 20/20;
- catalog/card identity is fail-closed by candidate SHA plus the exact tracked digest, obsolete marker fields are
  rejected, and POC marker history remains immutable and clearly separate;
- no renderer, wire, model/runtime/config, pre-warm, threshold, M4a Accepted boundary or unrelated Test ID reopened.

Blocking findings: **0**. `TR_spec_M4B_III` is **Resolved** and shall be archived. Developer may continue the
remaining implementation/handoff and prepare candidate scope. A provisional candidate commit still requires the
normal Designer scope check and separate explicit USER commit approval; formal portable/Pi evidence may only use
that externally specified candidate SHA.
