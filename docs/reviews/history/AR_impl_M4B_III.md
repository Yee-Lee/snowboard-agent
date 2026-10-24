---
requestor: Designer
owner: Architect
status: Resolved
severity: Blocking
---

# AR_impl_M4B_III — M4B foundation contract revision

- Date: 2026-09-10
- Blocking gate: `M4B-FOUNDATION-ARCH-REVIEW`
- Requested outcome: revise the affected architecture contract before a separately gated foundation
  implementation; M4B cognition/product development remains closed

## Review boundary

The USER and Designer have converged on four changes needed by the clean M4B rewrite:

1. One Product Session may replace its Conversation sequentially while keeping exactly one active
   Conversation at a time.
2. Cognition selects a primary action and a post-action route: rest/session end or next turn.
   Non-empty final speech must complete before rest and must not create a fake listen turn.
3. A post-send model failure with provable cleanup and a usable Engine is replaceable (`R2`), not a
   system error. An explicit USER reset/end is the graceful `R3` route. Wiring/contract failure or
   loss of safe cleanup proof remains on the existing system-error boundary (`E1`).
4. Conversation open must not race active listen/ASR. The existing external state sequence remains
   `IDLE -> WAKE -> PERCEPTION -> THINK -> ACTION`; a Conversation-readiness barrier gates entry to
   PERCEPTION and may overlap only application-owned preparation UX.

This review is limited to the cross-module architecture delta required to make those decisions
implementable. Exact prompt text, tokenizer numbers, Display artwork, recorded-voice wording,
production code and test cases are out of scope. Accepted M4A and unaffected EventBus, Resource
Manager, Level 1/2/3 convergence, privacy and process-isolation contracts remain closed.

The prior `AR_impl_M4B_II` concerns the retired M4B package and cannot release this request. Do not
use retired M4B design, production or test behavior as a compatibility target.

## Blocking finding A — Product Session and Conversation cardinality conflict

### Basis and location

`arch.md` §4.1 currently states both:

- a Product Session claims at most one Conversation; and
- capacity overflow closes the session and returns to IDLE.

The confirmed replacement behavior keeps the Product Session alive while closing one Conversation
and claiming a new clean Conversation. The existing wording therefore prohibits the required route.

### Required architecture outcome

Please revise §4.1 and its direct session-end/convergence references to establish all of the
following:

- a Product Session owns at most one **active** Conversation at any instant;
- it may own multiple Conversation generations sequentially, never concurrently;
- replacement first blocks new model admission, obtains terminal/join proof for the active request,
  closes the old Conversation with cleanup proof, and only then claims a new clean Conversation;
- Product Session identity and monotonically increasing turn identity survive replacement;
- Conversation-local history/KV does not survive replacement, and no user input is silently replayed;
- replacement does not run session-end external-message `flush-to-wake` or `discard` policy;
- failure to prove request termination or Conversation cleanup leaves the R2 route and enters the
  existing E1/Level 1/2/3 system-error boundary;
- normal rest, interrupt, error and shutdown still close the currently active Conversation and end
  the Product Session under the existing convergence contract.

Context admission may select replacement only before the rejected input mutates the old
Conversation. After replacement, application-owned speech asks the USER to repeat or restate the
input; the rejected input is not automatically submitted against context with different history.

## Blocking finding B — Final speech cannot be represented by the current action contract

### Basis and location

`arch.md` §2.7 and §4.5 currently make `speak`, `tool` and `rest` mutually exclusive values of one
`LLMResponse.action_kind`. Successful `speak/tool` always advances to PERCEPTION, while `rest`
directly performs session convergence. Consequently, a model result with non-empty speech and an
end intent cannot say the final text and then rest without either losing the text or creating a fake
next perception.

### Preferred contract shape

Keep the current state names, but separate the primary action from its post-action route. One
implementable shape is:

```text
Reasoner outcome
  primary action: speak | tool | rest
  post-action route: KEEP_NEXT | REPLACE_NEXT | END_SESSION
  next_perceptions: tuple[kind, ...]
```

Required semantics, independent of the final field names:

| Primary action | Post-action route | Required result |
| :--- | :--- | :--- |
| `speak` / `tool` | `KEEP_NEXT` | action completes, keep Conversation, enter the next PERCEPTION using normalized non-empty `next_perceptions` |
| `speak` / `tool` | `REPLACE_NEXT` | action completes, run the sequential replacement barrier, then enter the next PERCEPTION |
| `speak` / `tool` | `END_SESSION` | action completes, then run rest/session convergence without another perception |
| `rest` | `END_SESSION` | no primary user-content action is needed; run rest/session convergence directly |

Invalid combinations must be rejected by State Manager THINK Exit as a Reasoner contract violation.
`next_perceptions` is required and normalized only for `KEEP_NEXT` and `REPLACE_NEXT`; it is ignored
for `END_SESSION`. A canonical Reasoner should emit an empty tuple for `END_SESSION`.

Please decide whether `rest` remains a compatibility value of the primary-action enum or becomes an
internal post-action phase. Either representation is acceptable only if it preserves these outcomes:

- non-empty final model speech is model-owned `speak + END_SESSION`;
- empty end intent reaches rest without synthesizing speech;
- application-owned retry speech uses `speak + KEEP_NEXT`;
- final-speech action failure still proceeds to rest/session convergence and does not fall back to
  `default_perceptions`;
- ordinary continuing `speak/tool` action failure may retain the existing
  `default_perceptions` behavior;
- one cognition Fact remains authoritative for the turn; no second LLM inference is introduced.

The external observable state sequence may remain unchanged. If a post-action rest worker executes
while State Manager remains in ACTION, architecture must define its in-flight and terminal-Fact
handling without accepting two ambiguous `ActionCompleted` facts for one active record.

## Blocking finding C — Conversation readiness is currently too late

### Basis and location

`arch.md` §4.6 currently obtains the session Conversation at first-turn THINK Entry. The confirmed
design requires Conversation open to finish before actual perception begins, so that Conversation
construction does not compete with listen/ASR. The existing location cannot enforce this ordering.

### Required architecture outcome

Please move the first Conversation acquisition to a WAKE/session-preparation readiness barrier while
preserving the current public state sequence:

```text
WAKE
  ├─ start/claim one clean Conversation
  ├─ run application preparation UX when available
  └─ keep SM inbox responsive

WAKE exit to PERCEPTION
  only after the normal wake acknowledgement and Conversation readiness are both satisfied
```

The architecture must also state:

- no listen/ASR perception operation starts before the readiness barrier passes;
- model generation still cannot start before the claimed Conversation is ready;
- preparation Display animation or recorded voice is application-owned UX and is not model speech,
  a perception, a turn, or Conversation content;
- exact UX content belongs to later Display/product design; absence of optional Display/Audio cannot
  break readiness correctness;
- interrupt, error and shutdown during open cancel and converge the open operation under the
  existing in-flight completion-proof rules;
- Conversation-open failure follows the same proven-replaceable versus unsafe/system-error boundary
  as other Conversation lifecycle operations;
- the production path does not overlap Conversation open with active listen/ASR. M4B measures open
  overlapped with the selected preparation UX instead.

No new public State Manager state is requested. The precise component/API that owns preparation is
implementation design, provided State Manager remains the Product Session and transition owner.

## Blocking finding D — Error boundary must distinguish replacement from recovery

### Required classification

Please incorporate or explicitly permit this boundary in §2.7 and §6.5–§6.7:

| Class | Minimum proof | Route |
| :--- | :--- | :--- |
| Clean pre-inference rejection | Conversation was not mutated | application-owned retry; `KEEP_NEXT` |
| Replaceable post-send failure | active request terminal/join and old Conversation cleanup are provable; Engine remains usable | `R2`; sequential replacement inside the same Product Session |
| USER reset/end | explicit user intent or interrupt; not an automatic retry-count escalation | `R3`; close Conversation and end Product Session |
| Wiring/contract/system failure | unsupported input, illegal Reasoner outcome, worker crash, protocol desync, unusable backend or missing cleanup proof | `E1`; existing ERROR recovery |
| Failed forced convergence/recovery | Level 2 or recovery cannot provide proof | existing Level 3 process restart |

Repeated replaceable failures do not become E1 merely by count. The USER may explicitly choose R3.
No automatic retry counter or silent Conversation reset is requested.

## Direct impact inventory

Please confirm or correct this initial architecture impact set:

- `arch.md` §2.7 Reasoner responsibility and `next_perceptions`;
- `arch.md` §2.8 action/rest ownership;
- `arch.md` §3.3 Reasoner outcome event semantics;
- `arch.md` §4.1 Conversation lifetime and capacity;
- `arch.md` §4.5–§4.6 THINK/ACTION transitions and first-turn acquisition;
- `arch.md` §4.8 `default_perceptions` boundary;
- `arch.md` §6.5–§6.7 convergence and error classification.

After architecture resolution, Designer expects a separately gated
`M4B-FOUNDATION-REVISION` implementation before M4B cognition/product development. It will migrate
the affected event/outcome, State Manager, rest routing, Conversation lifecycle, mock workers and
regression expectations while preserving the observable M1/M2 state sequence and all unaffected
M1/M2 behavior.

## Minimum review acceptance

This request is ready for `Resolved` only when:

1. `arch.md` has one non-contradictory contract for sequential Conversation replacement,
   post-action rest/next-turn routing and pre-perception Conversation readiness.
2. Normal final speech, empty end, normal continuation, context replacement, replaceable model
   failure, USER reset, system error, interrupt and shutdown each have exactly one route.
3. Action failure behavior distinguishes continuing actions from final actions.
4. R2 never bypasses cleanup proof, and E1/Level 3 ownership remains consistent with existing
   convergence rules.
5. The changed architecture does not claim that historical M1/M2 acceptance verified the new
   behavior; it identifies the required foundation migration and regression surface instead.

Architect: please respond in this file, update `arch.md` as the authority, list any additional direct
impact discovered, and move the request to `Revised` for Designer confirmation. Do not create a
parallel review or modify retired M4B design artifacts.

---

## Architect response (2026-09-10)

Disposition: **Revised — Blocking A–D accepted.** `docs/arch.md` now carries the approved
architecture delta. This response does not authorize foundation implementation or M4B
cognition/product work; the separately gated `M4B-FOUNDATION-REVISION` remains closed until
Designer confirmation and routing.

### A — Product Session / Conversation cardinality: accepted

- §4.1 now permits sequential Conversation generations while retaining at most one active claimed
  Conversation at any instant.
- Replacement is one ordered barrier: block model admission -> prove active-request terminal/join ->
  close and prove cleanup -> claim a clean Conversation. `session_id` and monotonically increasing
  `turn_id` survive; Conversation-local history/KV and rejected input do not.
- Replacement is not session end and therefore does not run `flush-to-wake` or `discard`. Missing
  termination/cleanup proof or an unusable Engine leaves R2 and enters E1 / Level 1–3.
- Capacity admission may choose replacement only before the rejected input mutates the old
  Conversation. Application-owned speech requests restatement; only input received after the barrier
  may enter the new history.

### B — Primary action and post-action route: accepted

- §2.7 / §3.3 define one `LLMResponse` with `action_kind`, `action_payload`,
  `post_action_route` (`KEEP_NEXT | REPLACE_NEXT | END_SESSION`) and `next_perceptions`.
- `rest` remains a compatibility primary value and is legal only with `END_SESSION`. Non-empty final
  model speech is `speak + END_SESSION`; empty end intent is `rest + END_SESSION`.
- ACTION tracks mutually exclusive `primary` and `post-action-rest` records. Final speak/tool
  completion starts the rest phase without a perception; kind/correlation/phase matching makes its
  two terminal Facts unambiguous. Final primary failure still rests and converges, while continuing
  action failure may use `default_perceptions`.
- One cognition Fact and one inference per turn remain authoritative.

### C — Pre-perception Conversation readiness: accepted

- §4.3 / §4.5–§4.6 move initial start/claim to WAKE. WAKE exits only after both normal wake
  acknowledgement and Conversation readiness; listen/ASR and generation cannot begin earlier.
- Conversation open may overlap only application-owned preparation UX. That UX is not model speech,
  perception, a turn or Conversation content, and optional Display/Audio availability cannot satisfy
  or break the readiness proof.
- Open is tracked as in-flight lifecycle work. Interrupt, error and shutdown require terminal/join
  proof; failed open follows the same replaceable-versus-E1 boundary without a retry-count escalation.

### D — R1 / R2 / R3 / E1 boundary: accepted

- §2.7 and §6.5–§6.7 now distinguish clean pre-inference retry (R1), proven sequential
  replacement (R2), explicit USER reset/end (R3) and system error (E1).
- Repeated replaceable failures do not become E1 by count. R2 cannot complete without cleanup proof;
  Level 2 proof failure or recovery failure retains the existing Level 3 process-restart boundary.
- Illegal Reasoner outcomes remain E1 via the SM self-check path without a fabricated
  `ErrorOccurred`.

### Direct impact and unchanged invariants

The request's initial inventory was correct. Necessary same-root additions were §2.6 (continuing
perception authority), §3.2 and §3.7 (Fact validation and identity continuity), §4.2–§4.3
(public-state semantics), §5.1 (replacement buffer policy) and §6.3 (Conversation lifecycle
handles and private completion proof).

Unchanged: the public `IDLE -> WAKE -> PERCEPTION -> THINK -> ACTION` sequence; SM ownership of
Product Session, transitions and action dispatch; one cognition Fact/inference per turn; EventBus
roles; Resource Manager recovery; Level 1/2/3 convergence; process isolation; privacy and absence of
cross-session memory. Historical M1/M2 acceptance does not verify this new behavior; the future
foundation migration must cover the event/outcome schema, State Manager routing, rest phases,
Conversation lifecycle, mock workers and regressions.

Review status is `Revised`; next owner is **Designer** for confirmation and gate routing.

---

## Reviewer 審查意見（2026-09-10）

審查結果：**PASS（Blocking 0 / Advisory 0）**

審查對象：`docs/arch.md` 本輪架構修訂（針對 Blocking A–D）與 Architect response。

### 逐項審查結論

| 項目 | 審查結果 | 關鍵契約與依據落點驗證 |
| :--- | :--- | :--- |
| **Blocking A — Cardinality & Replacement** | **PASS** | §4.1 明定 Product Session 任一瞬間至多 claim 一個 active Conversation，可順序替換多個 generations，永不並存。Replacement barrier 嚴格固定「阻擋新 admission → 取得 active request terminal/join proof → 舊 Conversation close & cleanup proof → claim clean Conversation」順序。§3.7 明定保留 `session_id` 與單調遞增 `turn_id`；§4.1 明定 Conversation-local history/KV 不保留且禁止自動重送 rejected input。§5.1 / §6.5 明記 replacement 不等同 session end，不發布 `flush-to-wake` 或 `discard`。任一 proof 缺失或 Engine 不可用即轉 E1。 |
| **Blocking B — Primary Action & Post-Action Route** | **PASS** | §2.7 / §3.3 明確解耦 primary action（`speak | tool | rest`）與 post-action route（`KEEP_NEXT | REPLACE_NEXT | END_SESSION`），並將 `next_perceptions` 限定為 continuing routes 所需。§2.7 / §4.6 明確規範非空最終 speech 為 `speak + END_SESSION`，空結束意圖為 `rest + END_SESSION`，不合法組合（如 `rest` 非搭配 `END_SESSION`）由 SM 自檢進 ERROR。§2.8 / §4.6 確立 ACTION 內 `primary` 與 `post-action-rest` 互斥 phase，各 phase 僅接受對應之唯一 `ActionCompleted`；final action failure 仍走 post-action rest 與 session 收斂，不使用 `default_perceptions`，消弭 terminal fact 歧義。 |
| **Blocking C — Pre-Perception Readiness** | **PASS** | §4.3 / §4.5 / §4.6 將首個 Conversation acquisition 移至 WAKE 階段作為 readiness barrier。WAKE 僅在 wake acknowledgement 與 Conversation readiness 皆滿足時才轉移至 PERCEPTION；在此之前嚴格禁止啟動 listen / ASR 與 generation。§4.3 明確切分 application-owned preparation UX（非 model speech、非 turn、非 Conversation 內容），其存在與否不破壞 readiness 正確性。§4.6 / §6.3 將 open 納入 in-flight tracking，異常退出時要求取得 terminal/join proof，failed open 遵循可證明替換（R2）與系統錯誤（E1）分界。 |
| **Blocking D — R1/R2/R3/E1 Error Boundary** | **PASS** | §2.7 / §6.5 / §6.6 正式建立四級路徑分界（R1 clean retry、R2 replace、R3 USER reset/end、E1 system error）。明定 R1/R2/R3 為正常可預期路徑不假造 `ErrorOccurred`，E1 維持 Level 1/2/3 收斂體系。明確規定重複之可替換失敗不因計數升級為 E1，亦不自動觸發 R3；R2 絕不可繞過 cleanup proof。 |

### Direct Impact Inventory 與驗收條件查核

1. **直接影響清單核對**：除原單列出之 §2.7, §2.8, §3.3, §4.1, §4.5–§4.6, §4.8, §6.5–§6.7 外，同根增修之 §2.6（continuing perception authority）、§3.2（SM 自檢 illegal route / action）、§3.7（turn id continuity）、§4.2–§4.3（狀態時序與 UX 邊界）、§5.1（replacement buffer policy）、§6.3（lifecycle handles 與 private completion notice）均屬必要且自洽之延伸，無未授權之額外擴散。
2. **Minimum Review Acceptance 1–5 核對**：
   - 條件 1（無矛盾契約）：§4.1, §4.3, §4.6 契約一致自洽。**PASS**
   - 條件 2（各情境唯一路徑）：正常結束、空結束、繼續、替換、可替換失敗、使用者重設、系統錯誤、中斷、關機均具唯一轉移路徑。**PASS**
   - 條件 3（Failure 分歧）：Continuing routes 錯誤可降級 `default_perceptions`，Final routes 錯誤嚴格收斂至 rest / session end。**PASS**
   - 條件 4（Proof 邊界與 Level 3）：R2 必須具備 cleanup proof，缺失即走 E1；Level 2 失敗一律進 Level 3。**PASS**
   - 條件 5（歷史邊界）：未假稱歷史 M1/M2 驗證新行為，明確指出後續 foundation migration 範圍。**PASS**

### 審查結論與交接

本輪 Architect 對 `docs/arch.md` 提出的架構修訂完整滿足 `AR_impl_M4B_III` 提出的所有 Blocking 要求，且未引入新的架構矛盾或 regression。Reviewer 判定審查通過（PASS）。

單據正式標記為 **Resolved** 並歸檔至 `docs/reviews/history/AR_impl_M4B_III.md`。後續由 **Designer** 確認收斂架構並推進 foundation-contract implementation design 規劃。
