---
requestor: USER
owner: Reviewer
status: Resolved
---

# IR_review_M4B_III — M4B replacement cognition/product design review

Scope: complete cross-file review of [`ch_m4b_llm_production.md`](../../implement/ch_m4b_llm_production.md)
against `arch.md`, `m4b_foundation_revision.md`, `protocol.md` §4, `model_spec.md` §6, `milestone.md`,
`M4B_MVA.md`, `M4.md`, `ch02b_workers.md` §3 and `ch10_config.md` §6. The resolved
[`AR_impl_M4B_IV`](AR_impl_M4B_IV.md) timing decision is used only for the confirmed SM
authorization boundary. Accepted M4A, generic Foundation, and the architecture document itself are not
reopened.

## Consolidated disposition: **PASS — no Blocking findings**

The replacement product design is internally consistent, architecturally aligned, and sufficiently
specified for independent Tester coverage and subsequent Developer implementation. All sections trace
correctly to their upstream authority. The design appropriately defers to the architecture where required
and does not introduce unauthorized scope.

Below are Advisory observations followed by a verification summary.

---

## Advisory findings

### A1. `generation_timeout_seconds` default discrepancy between §9.1 and ch10 example YAML

**Location**: `ch_m4b_llm_production.md` §9.1 line 379 vs `ch10_config.md` §13 example YAML.

**Observation**: The design §9.1 declares `generation_timeout_seconds: float = 30.0` in the `LLMConfig`
dataclass. The `ch10_config.md` §6 production schema repeats the same `30.0` default. However, the
§13 example YAML skeleton shows `generation_timeout_seconds: 15.0`. This is a documentation-layer
inconsistency in the example file only; the canonical dataclass default and the §6 production schema are
both `30.0` and internally consistent.

**Impact**: Low. The example YAML is explicitly not auto-loaded (§10 loader rules). Developer will use the
dataclass default. The example file inconsistency may cause confusion during deployment but does not affect
production behavior.

**Suggested fix**: Designer may align `ch10_config.md` §13 example YAML to `30.0`, or add an inline
comment noting the reduced value is intentional for development convenience. No design document change
required.

---

### A2. `spoken_length` counting rule — edge case documentation for Tester

**Location**: `ch_m4b_llm_production.md` §4.1 lines 148–151.

**Observation**: The 30-character rule defines `spoken_length` as "normalized non-whitespace code points
whose Unicode general category does not begin with `P`." This is precise and testable. However, the
interaction between CJK punctuation (category `Po`, excluded) and CJK ideographic full-width forms
(category `Lo`, included) may benefit from one or two explicit examples in the Tester coverage request
(§11.1 item 2) to prevent Tester from independently inventing a different interpretation.

**Impact**: None to the design itself. The rule is unambiguous given Unicode property tables. This is a
coverage-quality suggestion for the downstream Tester round.

**Suggested fix**: No design change. Designer may optionally add a parenthetical example (e.g., "「你好嗎」
has spoken_length=3; punctuation 「」 excluded") when activating `TR_spec_M4B_VI`.

---

### A3. `MEASURE` request ID lifecycle vs protocol §4.3 `conversation_revision`

**Location**: `ch_m4b_llm_production.md` §5.1 vs `protocol.md` §4.3–§4.4.

**Observation**: The design's `AdmissionSnapshot` includes `generation` but not `conversation_revision`.
The protocol `MEASURED` event returns `conversation_revision` and the subsequent `GENERATE` requires it.
This is consistent: the `ticket` opaquely binds the revision, so the parent adapter need not expose it in
the snapshot dataclass. The design correctly states "ticket binds the child generation, Conversation
revision, exact normalized input digest and all counts."

**Impact**: None. Noted for completeness — no action required.

---

## Cross-file verification matrix

| Design section | Upstream authority | Alignment status |
| :--- | :--- | :--- |
| §1 Scope | `M4B_MVA.md` gate matrix, `milestone.md` M4 boundary | ✓ Correctly excludes legacy M4B, M4A, and Foundation scope |
| §2 V2D2 profile | `arch.md` §2.7 M4 Reasoner LLM role boundary | ✓ Listen-only, text-only output, no hardware control |
| §2.2 System prompt | `model_spec.md` §6.3 profile status | ✓ Exact bytes, hashes and token counts match; Designer adopted V2D2 |
| §3 Perception/normalization | `arch.md` §2.6 PerceptionResult contract, §2.7 capability boundary | ✓ Single listen, UNSUPPORTED_INPUT for violations = E1 per arch |
| §4 Constrained JSON | `arch.md` §2.7 "LLM only outputs short text or end intent" | ✓ `text/end` is the exact semantic surface; Reasoner owns action_kind |
| §4.2 S2 extraction | `arch.md` §2.8 M4B full-response mode | ✓ Records first-safe time but does not dispatch; M4C deferred |
| §5.1 MEASURE ticket | `protocol.md` §4.3 non-mutating measurement | ✓ One-use, opaque, invalidated by mutation |
| §5.2 Context equation | `arch.md` §4.1 capacity principle, config-driven | ✓ 128 reserve + 1024 context from frozen profile |
| §5.3 Memory decision | `AR_impl_M4B_IV` confirmed SM authorization | ✓ Adapter marks RECYCLE_PENDING only; SM authorizes in post-close convergence |
| §6 Outcome matrix | `arch.md` §2.7 R1/R2/R3/E1, §6.6 error two-layer | ✓ Every row maps to exactly one classification; application speech excluded from model history |
| §6 "repeated R2" | `arch.md` §6.5 "重複的可替換失敗不因次數轉成 E1" | ✓ Never auto-escalates by count |
| §6 model `end=true` | `arch.md` §2.7 "非空最終 model speech 必須表示為 speak + END_SESSION" | ✓ Non-empty end=true → speak+END_SESSION; empty end=true → rest+END_SESSION |
| §7.1 LLMEngineAdapter | `m4b_foundation_revision.md` §3.1 ConversationLifecycleControl | ✓ Adapter protocol extends foundation port with MEASURE/GENERATE |
| §7.2 Reasoner lifecycle | `m4b_foundation_revision.md` §4 SessionContext, §6.1 THINK | ✓ Single operation lock, generation verification, one canonical Fact |
| §8 Private child protocol | `protocol.md` §4 snowboard.llm/3 | ✓ Design product rules are subset of protocol state machine |
| §9.1 LLMConfig | `ch10_config.md` §6 CognitionConfig | ✓ Identical dataclass; legacy keys rejected; mock paths null |
| §9.1 Cross-field validation | `ch10_config.md` §6 item 22b | ✓ read/look/tool disabled for real profile |
| §9.2 Startup order | `arch.md` §6.2, §4.3 WAKE readiness | ✓ No prewarm; Conversation open in WAKE after Reasoner READY |
| §10 Privacy | `arch.md` §1.3 P5, protocol §1 no-log rules | ✓ Forbidden data list consistent |
| §11 Verification | `milestone.md` §1.4 common conditions | ✓ No delete/skip/xfail; explicit barriers; portable + Pi evidence |
| §12 Cutover | `ch02b_workers.md` §3, `ch10_config.md` §6 | ✓ File inventory matches; path survival ≠ legacy behavior |

---

## Boundary verification

| Boundary | Verified |
| :--- | :--- |
| Does not modify `arch.md` | ✓ |
| Does not reopen M4A | ✓ |
| Does not reopen Foundation | ✓ (builds on, does not modify) |
| Does not reopen `AR_impl_M4B_IV` | ✓ (consumes resolved decision) |
| Does not introduce public SM state | ✓ |
| Does not introduce new Worker Fact type | ✓ |
| Does not introduce cross-session memory | ✓ |
| Respects protocol.md §4 state machine | ✓ |
| Legacy M4B-MVA-001/002 not compatibility target | ✓ |

---

## Next owner

**Designer** — resolve or acknowledge Advisory findings, close `M4B-DESIGN-REVIEW`, and activate
`TR_spec_M4B_VI` per `status/current.md` ordered exits.

## Designer resolution — Resolved

Designer accepts the PASS disposition and closes `M4B-DESIGN-REVIEW`:

- **A1 adopted:** the Ch 10 example YAML now uses `generation_timeout_seconds: 30.0`, matching the canonical
  dataclass/schema default. The same local edit corrected the three LLM profile-field indentation levels so the
  example remains structurally valid; neither change alters the product contract.
- **A2 adopted:** active `TR_spec_M4B_VI` now pins `「你好嗎？」 -> spoken_length=3` and
  `嗨🙂！ -> spoken_length=2`, explicitly distinguishing Unicode punctuation from a counted emoji symbol.
- **A3 acknowledged:** no change; the opaque admission ticket remains sufficient to bind
  `conversation_revision` without exposing it in `AdmissionSnapshot`.

There are no Blocking findings and no architecture change. `M4B-DESIGN-REVIEW` is Closed;
`TR_spec_M4B_VI` is active for Tester specification only. Developer entry remains closed.
