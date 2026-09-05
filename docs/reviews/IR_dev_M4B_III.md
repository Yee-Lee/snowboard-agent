---
requestor: "Developer"
owner: "Designer"
status: "Revised"
severity: "Blocking"
---

# IR_dev_M4B_III — Product-session LLM lifecycle, Reasoner responsibility and performance boundary

## Current disposition — Designer response 2026-09-05

USER已確認M4 MVA與下列修訂；本單由Designer標Revised供Developer複審，未自標Resolved。
完整[M4B-MVA design](../implement/ch_m4b_llm_production.md)、[M4 scope](../milestones/M4.md)、
[architecture request](AR_impl_M4B_I.md)、[test-spec request](TR_spec_M4B_IV.md)已建立。
原下文為Developer發起時的證據與請求，保留不改写；新產品方向優先依本回覆。

| Finding | Verification / disposition | Direct fix / minimum closure |
| :--- | :--- | :--- |
| 1 session/history | fresh-per-turn事實成立；session定義原已在arch §4.1；USER並非禁止自然history | M4B-MVA §3/§4 session ports、same-session reuse、四路close與cross-session隔離；AR處理§8.3 |
| 2 prewarm | 原cold-first失敗有歷史依據；未證明每次replacement下一筆收益 | M4B-MVA §5/§6；same-boot預設none，冷啟動比較交POC；READY/profile/card同步 |
| 3 recycle | 原8來自POC斜率推算，Core適用性不足；sample注入證明capacity足夠也因150MiB delta回收 | M4B-MVA §5/§9；移除8/48/早期64/固定三generation；natural soak與受控recovery分開 |
| 4 Reasoner | full-envelope實作成立；LLM理解與SM驗證本來就符合架構，不採「因此失職」判法 | M4B-MVA §2最小text/end→Reasoner action/next_perceptions；M4不做task manager；tool留M5 |
| 5 performance | 有15秒watchdog，但缺caller/audible端點；internal TTFT不等於回應 | M4B-MVA §6；speech-end→meaningful onset，完整recovery；quality/manual與timing分欄 |

### Verified evidence and limits

本輪核對R1 source/design/test與指定上游文件；33項直接portable regression PASS（CPython3.12.3）。
命令（在清除USER允許捨棄的WIP以前執行）：

    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 timeout 60 .venv/bin/python -B -m pytest -p no:cacheprovider --capture=sys tests/test_m4b_hist_001.py tests/test_m4b_gen_001.py tests/test_m4b_out_001.py tests/test_m4b_rec_001.py::test_m4b_rec_001_rebuild_ready_timeout_starts_after_authentication

首次未關autoload因host ROS pytest plugin缺lark失敗；隔離該無關plugin後33 passed。
這是舊契約行为核實，非M4B-MVA測試／formal portable sign-off。
用tests.test_m4b_gen_001._adapter/_input在memory-only程序注入：
baseline1700MiB→1850MiB、MemAvailable1200MiB，第一request後
attempts=1/recycle_tickets=1/RECYCLE_PENDING。
另一個start+rebuild closure spy得到runtime/model-config verification各兩次，
配合lock.verify_config_paths直接完整hash，證明replacement critical path重新驗大model。
無Pi新run。新Pi 8.2秒/1.77–1.82GB原始腳本/逐次樣本未定位，只能列Developer摘要。
Developer可提供現成sanitized identity/commands/samples，無需為本核實另跑探索。
不要把41總decode tokens全稱為可省overhead，也不把Python驗證當成已證实性能瓶頸。

### Downstream scope and authority

應修改M4B-MVA §9列出的source/API/profile/card/catalog，不需重開M4A HAL、POC winner、
target ABI、license、歷史machine FAIL/waiver或generic M5 tool validator。
USER確認五個舊WIP無保留需要，已捨棄，不能以其存在阻擋新設計。
流程現依USER指定[M4B-MVA七步gate](../milestones/M4B_MVA.md)，
Reviewer審arch/design/POC計畫，Designer定版交付；POC結果經Designer審核解除gate前，
Developer／Tester不提前進場或準備spec draft，
不得建立耦合新candidate或用放寬READY deadline繼續舊target acceptance。
Performance target miss只發現差距，按USER決策可調整，不代表no-go；
原結果保留，未裁決前不假標PASS。

POC request：
[REQUEST-LLM-POC-M4B-MVA-MEASURE-001](../outsource/deliveries/REQUEST-LLM-POC-M4B-MVA-MEASURE-001.md)
prepared in Core，未交付外部／未授權實體執行。
Tester經TR_spec_M4B_IV寫自動/人工delta，Designer不修改Tester-owned spec。
本回覆一次列出五項與直接影響面；後續複審以本範圍及新regression收斂。

## Original decision requested

Please revise the M4b product design after the physical-Pi implementation diagnostics exposed five
coupled gaps in the approved lifecycle:

1. product session/context semantics are currently replaced by a mandatory fresh Conversation per
   operation;
2. inference pre-warm is mandatory without proof that it improves the following real request under
   the resulting product architecture;
3. planned replacement is driven by fixed attempt and premature PSS-delta gates that classify normal
   runtime allocation as a recycle trigger;
4. the implemented Reasoner does not yet perform all cognition/decision/context responsibilities
   assigned to it by `docs/arch.md`; and
5. performance ownership and acceptance endpoints are not defined separately for the LLM/runtime
   POC, the Core M4b subsystem and the complete M4 product.

These are Designer-owned contract questions. Developer will not select a new Conversation/context
architecture, remove required readiness work, weaken a resource gate, or change the Reasoner wire
shape without a revised design and corresponding Tester-owned specification delta. If the selected
Reasoner/context disposition changes `docs/arch.md`, Designer must open the appropriate `AR_impl`
rather than describe the change as implementation-only.

## Scope and evidence status

- The accepted model/runtime identity remains LiteRT-LM 0.16.0 and Gemma 4 E2B mobile. This request
  does not reopen model selection, artifact provenance, target CPython ABI or offline packaging.
- All measurements below are sanitized Developer diagnostics on the physical Pi. They are suitable
  for design feedback, but are not formal Gate 3 PASS evidence and are not merged into an acceptance
  run.
- No raw private prompt, model response, audio or credential is recorded. `Say hi.` and `Say ready.`
  are public diagnostic inputs.
- The immutable POC machine results and User waiver remain unchanged. In particular, historical P8
  and P9/P10B dispositions must not be relabelled by this review.
- USER direction recorded on 2026-09-05 is authoritative for the requested product semantics in this
  round. A new POC is not authorized by this review alone; Designer may request one when physical
  evidence is necessary for a design decision.

## Blocking finding 1 — Product context/session isolation is not defined independently of runtime construction

### Contract basis

- `docs/arch.md` §2.7 assigns the Reasoner understanding, inference, action selection, next-perception
  selection and normalization into one `LLMResponse`.
- `docs/protocol.md` §4.2 and `docs/implement/ch_m4b_llm_production.md` §§2 and 6 instead require every
  user operation to create and close a fresh single-turn LiteRT-LM Conversation and prohibit reuse.
- `M4B-HIST-001` makes distinct create/close counts part of acceptance, thereby fixing an
  implementation technique rather than first defining the allowed product context.

### Runtime research and observed evidence

LiteRT-LM documents `Conversation` as a stateful multi-turn API. It retains message history and an
incremental Session/KV state; callers normally send the new message to the same Conversation rather
than resending the complete transcript. The pinned source also shows that every new Conversation
calls `Engine.CreateSession()` and creates a model data processor and constraint provider:

- <https://github.com/google-ai-edge/LiteRT-LM/blob/main/docs/api/cpp/conversation.md>
- <https://github.com/google-ai-edge/LiteRT-LM/blob/924e79c91542761242244e4f1651851f822e4cbb/runtime/conversation/conversation.cc#L699-L738>

No public report was found for cross-session semantic leakage on the exact product combination of
Gemma 4 E2B, LiteRT-LM 0.16.0, Linux aarch64 Raspberry Pi and sequential reuse. Related reports are
not equivalent but show why the integration boundary should be explicit:

- LiteRT-LM issue 966 reports materially lower latency from Conversation reuse and asks whether the
  retained history affects accuracy: <https://github.com/google-ai-edge/LiteRT-LM/issues/966>.
- Issue 2807 reports loss of a suspended Conversation's own history when multiple Conversations are
  interleaved on the official 0.14.0 CPU wheel with Gemma 4 E2B; it is state loss, not proven
  cross-session leakage, and not the selected 0.16.0 runtime:
  <https://github.com/google-ai-edge/LiteRT-LM/issues/2807>.
- Issue 3184 reports retained prior thinking content and multi-turn drift on LiteRT-LM 0.15.0 with
  other thinking models; it demonstrates an explicit context-policy concern, not an exact-product
  defect: <https://github.com/google-ai-edge/LiteRT-LM/issues/3184>.

The project's own Gate 2 observations did not prove prior-state leakage. The old P8 result was
`FAIL / DEPENDENCY_LIMITED_BY_P2` with no observed history pollution; the later replacement pairing
passed its prior-state boundaries. Both used fresh Conversations, so they prove neither that reuse is
unsafe nor that reuse is safe.

### Expected product boundary and USER recommendation

USER does not require progress from a completed product session to be restored into a later session
at this milestone. The desired collaboration is:

- one active LiteRT-LM Conversation may retain dialogue history/KV within the same product session;
- the Reasoner records only product-significant context needed within that session, such as tool use,
  pending tool progress or other explicit task state;
- ending the product session clears that authority; M4b currently need not persist and reconstruct it
  for a future session;
- cross-session leakage, unintended prior-turn influence outside the allowed context, runtime state
  loss/corruption and unbounded context/KV growth are separate risks and must not be collapsed into
  the vague term `pollution`.

The design must define what constitutes one product session, which state is intentionally retained
inside it, which critical context the Reasoner owns, and the boundaries that require Conversation
replacement (at minimum session end and unrecoverable/cancelled runtime state as applicable). History
isolation acceptance must assert behavior against this allowed-context boundary; it must not require
fresh create/close on every turn unless Designer documents evidence that the selected runtime cannot
meet the required behavior by reuse.

### Impact

The current implementation pays the new-Conversation initialization cost on every turn, provides no
actual multi-turn dialogue memory, and treats the absence of any runtime history as the product
definition of isolation. Developer cannot safely optimize the lifecycle because reuse currently
fails the exact `M4B-HIST-001` structural oracle even if product-session behavior is correct.

## Blocking finding 2 — Pre-warm policy must follow the revised architecture and prove next-request gain

### Contract basis

`docs/protocol.md` §4.1, `docs/model_spec.md` §6 and `M4B-RDY-001` require a fixed disposable real
inference before every child publishes READY, including same-boot planned replacement. The pre-warm
Conversation is closed and discarded before the following product request.

### Evidence

The original lifecycle request recorded one identical full inference at `16.704 s` after reboot-cold
startup and `5.061 s` in a same-boot fresh process/Engine. That result establishes a cold-first-
inference effect, but does not directly compare the following user request with and without pre-warm.

Current same-boot replacement diagnostics used the same Pi, model/runtime and Core product path:

| Mode | Three replacement READY observations | Following `Say hi.` observations |
| --- | --- | --- |
| no inference pre-warm | `0.678 / 0.801 / 0.536 s` | `8.284 / 8.233 / 8.228 s` |
| real `Say hi.` inference pre-warm | `9.055 / 8.845 / 8.872 s` | `8.177 / 8.244 / 8.232 s` |

The pre-warm moved approximately eight seconds before READY but did not materially improve the next
request. One pre-warm also did not establish a stable PSS high-water mark.

### Required disposition

Do not decide the final pre-warm method or deadline before finding 1 and finding 4 establish the new
Conversation and Reasoner architecture. Under that architecture, pre-warm has one required product
justification: a measurable improvement to the following real request's TTFT or time-to-complete.

Designer may request a bounded physical POC if the historical cold observation is insufficient. Such
a request must separately compare cold boot and same-boot replacement, predeclare identical product-
representative input/output surfaces and repetitions, and measure the following request rather than
claiming the discarded pre-warm's own completion as gain. Current data do not support mandatory
inference pre-warm on same-boot replacement.

## Blocking finding 3 — Planned replacement must be limited to demonstrated memory pressure

### Contract basis

`docs/implement/ch_m4b_llm_production.md` §0.3 and `M4B-REC-001` currently schedule replacement after
eight inference attempts, after a post-pre-warm owner-PSS increase of at least 48 MiB, or when
`MemAvailable < 768 MiB`. Every replacement repeats authentication/load/pre-warm.

### Evidence and current risk inventory

Across three fresh-child diagnostic cycles, owner PSS behaved as an allocation warm-up rather than an
eight-turn failure:

- Engine-only READY was approximately 474 MB.
- The first real inference raised PSS to approximately 1.67–1.69 GB.
- Later turns rose in steps and converged around 1.77–1.82 GB, generally by attempt six.
- A baseline taken after the first inference still saw approximately 120–150 MB of normal later
  growth, so the 48 MiB delta trigger necessarily classifies normal allocation as a replacement
  condition.
- No corresponding turn-count latency degradation, functional degradation, OOM, swap or throttle
  evidence has been established.

The only demonstrated planned-replacement concern is memory capacity. Crash, protocol desynchrony,
cancel convergence failure and other destructive failures remain fault recovery; they must not be
mixed with a maintenance replacement policy.

### Required disposition

- Remove the fixed eight-attempt replacement trigger unless new evidence demonstrates a repeatable
  attempt-related correctness or performance failure.
- Do not use a premature post-pre-warm PSS delta as proof of abnormal growth. Establish a steady-state
  memory envelope before selecting an exact threshold.
- Use system `MemAvailable` as the primary capacity signal and owner PSS for attribution or a separately
  justified upper bound. The observed 1.8 GB plateau and a possible 2.0 GB bound are diagnostic inputs,
  not an authorized threshold.
- Do not perform a full 2.5 GB model rehash on every same-install replacement critical path. Preserve
  full digest verification at install/preflight/initial trust establishment, and define an immutable
  deployment or equivalent attestation boundary for replacement rather than silently dropping
  identity protection.
- Keep the policy minimal until physical evidence establishes another risk. Do not add speculative
  latency, age, attempt-count or multi-signal heuristics.

## Blocking finding 4 — Reasoner responsibilities are incomplete and duplicated in model output

### Contract basis and observed implementation

`docs/arch.md` §2.7 says Reasoner performs cognition and decision: it understands facts, selects the
action, decides the next-turn perceptions, normalizes model output and emits one `LLMResponse`.

The selected implementation instead prompts the LLM to generate the complete canonical object with
`action_kind`, `action_payload` and `next_perceptions`. The child constrains and validates it;
`Reasoner._normalize()` validates the same mapping, capability and tool boundaries and then wraps the
same values in `LLMResponse`; State Manager validates the result again. Reasoner has no documented
independent decision/context policy beyond availability projection and fixed fallback.

A public `Say hi.` physical diagnostic made the cost visible:

- actual speech text: `Hi!`;
- full model-generated envelope: 41 decode tokens;
- internal TTFT: `790.151 ms`;
- decode rate: `9.777 tokens/s`;
- runtime total init metric: `3758.580 ms`;
- caller-visible complete `generate()` wall time: `8109.691 ms`.

This does not prove one required replacement architecture, but it proves that fixed envelope syntax
and fresh Conversation setup are material product costs that the current design review did not
evaluate.

### Observed design insufficiencies for USER/Designer discussion

- No complete policy defines how Reasoner makes `speak/tool/rest` and `next_perceptions` decisions.
- No product-session context model defines dialogue continuity, critical tool/task state or context
  termination.
- The LLM generates fixed canonical field names and control structure that could potentially be
  constructed deterministically after a smaller semantic result.
- Tool selection/arguments, tool execution, canonical response construction and next-perception
  policy are separated operationally, but their decision ownership is not fully specified.
- Child, Reasoner and State Manager validations overlap without a documented risk/cost allocation for
  each layer.
- No comparison justifies full model-generated JSON against a smaller text/tool semantic output.
- Current fallback is bounded and safe, but fixed apology/rest fallback is not a complete Reasoner
  cognition or context strategy.

USER and Designer will own the complete Reasoner design discussion. Designer must specify the
semantic result expected from the LLM, canonical envelope construction, tool-intent ownership,
next-perception policy, product-session context responsibilities and the required validation layers.
Developer supplies implementation facts and physical measurements but will not choose these product
semantics unilaterally.

## Blocking finding 5 — Performance acceptance must be defined per layer and endpoint

### Gap

The accepted POC summary prominently records TTFT and token throughput. Core Gate 3 inherits P4 and
records runtime timing/token fields, but the current design does not state a complete caller-visible
time-to-complete target or clearly separate which layer owns each performance claim. Internal TTFT is
not user-visible in the current blocking full-result interface: the latest diagnostic produced its
first model token near 0.79 seconds, while Core received the validated complete result near 8.11
seconds.

### Required layered definition

Designer must define the performance object, start event, end event, threshold owner and inheritance
rule at each level:

1. **LLM/runtime POC** — the selected model/runtime on a product-representative inference surface.
   It owns internal TTFT and model-output time-to-complete. Token throughput and phase breakdown are
   diagnostic unless needed to compare or diagnose candidates.
2. **Core M4b subsystem** — from accepted `ReasoningInput` at the Core adapter boundary through IPC,
   runtime execution, parsing/validation and availability of the deliverable `LLMResponse`. It owns
   caller-visible completion time and only the integration delta introduced by Core. Internal TTFT is
   an M4b endpoint only if Core actually exposes usable incremental content.
3. **Complete M4 product integration** — the product interaction boundary selected by Designer, for
   example final ASR input through first audible response and terminal action. It owns user-visible
   end-to-end performance and must not be replaced by a raw model TTFT claim.

Core need not repeat an unchanged raw LLM benchmark when the POC proves exact equivalence of model,
runtime, target/backend, prompt/template, token envelope, Conversation lifecycle, output constraint
and cold/hot condition. When those surfaces differ, the POC number may be reference evidence but
cannot silently become a Core claim. Existing Gate 2A generic and Gate 2B narrow-marker surfaces must
therefore be identified explicitly when P4 measurements are inherited.

The durable minimum metrics should be TTFT and time-to-complete at the layer that can actually observe
them, plus correctness and the fixed input/output envelope. Init, prefill, decode, token counts/rates
and component timings should remain bounded diagnostic measurements when optimization or failure
analysis requires them, not automatically become product gates.

Designer may issue a POC measurement request when a layer cannot be specified from existing evidence.
The request must prove that the POC software simulates the relevant production flow closely enough
for its data to be inherited; otherwise Core measures only the changed integration boundary.

## Requested Designer response

Please provide one coordinated disposition that:

1. defines product session lifetime, intentional in-session Conversation memory, Reasoner-owned
   critical context and behavioral cross-session/error boundaries;
2. defers and then accepts, revises or removes pre-warm based on following-request gain under the
   selected architecture, requesting a predeclared physical POC only if needed;
3. replaces the current 8/48 planned-recycle policy with a minimal evidence-backed memory-capacity
   policy and separates it from destructive fault recovery;
4. completes the Reasoner responsibility design or opens `AR_impl` for any architecture change; and
5. defines per-layer performance objects, TTFT/time-to-complete endpoints, thresholds and valid POC
   inheritance conditions.

The response must identify affected Designer authorities and request the required Tester-owned
`TR_spec_M4B_IV` changes. It may choose any equivalent implementation that closes the stated behavior
and evidence gaps; this IR does not prescribe Conversation reuse, a context compression algorithm,
a fixed memory threshold, streaming, or a specific compact model-output encoding.

## Minimum acceptance for this review

- The design distinguishes product session/context semantics from LiteRT-LM Conversation/KV
  implementation and no longer uses per-turn create/close as the definition of isolation without
  evidence.
- Any retained pre-warm has a stated following-request benefit and a valid measurement plan; cold
  startup and same-boot replacement are not conflated.
- Planned replacement has only demonstrated triggers, uses a stable memory envelope and does not put a
  full model rehash in the replacement latency path; fault recovery remains fail-closed.
- Reasoner, LLM adapter/child and State Manager each have explicit semantic and validation ownership.
- POC, Core M4b and complete M4 performance claims have distinct observable start/end boundaries;
  TTFT never substitutes for caller-visible completion when no usable token is exposed.
- If Designer requests POC work, the request freezes the compared lifecycle/output surfaces,
  repetitions, metrics and validity criteria before execution. No POC is required merely to close a
  question that Designer can decide directly.

## Work blocked while Open

- Do not submit the current lifecycle as M4b Gate 3 PASS or continue full target acceptance merely by
  widening the 10-second replacement READY deadline.
- Do not create a new candidate for changes coupled to fresh Conversation, pre-warm, planned recycle,
  Reasoner output shape/context or performance evidence until the design and test-spec delta resolve.
- Preserve the existing candidate history, non-credit diagnostics and unrelated user work. Do not
  rewrite POC receipts or previously published candidate SHAs.
- Developer may perform read-only analysis and prepare bounded diagnostic methods, but does not run a
  new architecture POC until Designer requests it or USER separately authorizes it.
