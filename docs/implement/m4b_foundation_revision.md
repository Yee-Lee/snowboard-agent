# M4B foundation contract revision

狀態：**Designer complete / Tester coverage approved / Developer entry open for
M4B-FOUNDATION-REVISION only**。

本文件是 `M4B-FOUNDATION-REVISION` 的 implementation-design authority，只把已核准的
[`AR_impl_M4B_III`](../reviews/history/AR_impl_M4B_III.md) 轉成可實作的 Core foundation delta。
它不定義 replacement M4B 的 prompt、token/KV 數值、LLM child wire、模型輸出 parser、Display
畫面或產品驗收門檻。上述 cognition/product 設計須等本 revision 驗證完成後另行建立。

若本文件與 generic Ch 1/2/4/5/6/9/10 內標為 M4B-MVA legacy 的段落衝突，以本文件為準；
Developer 在 foundation package 內同步更新那些直接受影響的 generic authority。Accepted M1/M2
只提供 regression baseline，從未驗證本文件新增的行為。

## 1. Scope and preserved invariants

### 1.1 Included delta

- `LLMResponse` 新增 primary action 之後的 route contract。
- State Manager 在 WAKE 內追蹤 Conversation readiness，且保持 inbox 可消費。
- 同一 Product Session 內的 sequential Conversation replacement barrier。
- ACTION 內互斥的 `primary` 與 `post_action_rest` phase。
- Conversation open/close 的 private completion、identity、cleanup proof 與 Level 1/2/3 收斂。
- Resource Manager 對 Conversation control 的 required late-fill wiring。
- M1/M2 deterministic fake、event construction 與受影響 regression 的遷移。

### 1.2 Preserved without reopening

- Public state 集合與正常觀察順序仍是
  `IDLE -> WAKE -> PERCEPTION -> THINK -> ACTION`；replacement/rest phase 不新增 public state。
- SM 仍是 Product Session、turn、transition、dispatch、buffer policy 與 in-flight owner。
- EventBus 三類事件、SM 只 publish `StateChanged`、Fact/task-done join 與 stale-ID guard 不變。
- 一 turn 只有一個 cognition Fact 與一次 Reasoner inference。
- Resource Manager recovery、process isolation、privacy 與 Level 1/2/3 proof boundary 不變。
- Normal rest、interrupt、error、shutdown 才是 Product Session end；replacement 不是 session end。

### 1.3 Explicit non-scope

- 不選定真實 Conversation class、LiteRT-LM API、child protocol command 或 timeout 數值。
- 不建立 application preparation UX port；foundation 可沒有該 UX。WAKE `StateChanged` 保留未來
  Display observer seam，但 UX 不構成 readiness proof。
- 不修改/驗收 prompt、semantic JSON、incremental extraction、admission equation 或 memory/timing
  dashboard。
- 不把 legacy M4B production/tests 標為可重用或通過；foundation 只允許必要的 event-schema
  compile migration，不能產生 M4B product PASS。

## 2. Public Fact contract

### 2.1 Route type and `LLMResponse`

`src/sbd/core/events.py` 與 Ch 1 定義：

```python
PostActionRoute: TypeAlias = Literal[
    "KEEP_NEXT",
    "REPLACE_NEXT",
    "END_SESSION",
]

@dataclass(frozen=True, slots=True)
class LLMResponse:
    action_kind: Literal["speak", "tool", "rest"]
    action_payload: dict[str, Any]
    post_action_route: PostActionRoute
    next_perceptions: tuple[str, ...]
    session_id: SessionId = ""
    turn_id: TurnId = 0
    correlation_id: CorrelationId = 0
```

`post_action_route` 沒有 default，且位於 `action_payload` 與 `next_perceptions` 之間。所有 production、
fake 與 test call site 改用 keyword construction；不得提供 legacy-compatible default，避免舊三欄
constructor 靜默產生錯誤 route。

`ActionCompleted` schema 不變。兩個 action phase 以不同 `correlation_id` 與 private
`InFlightRecord.phase` 區分，不把 phase 加進 public event，也不接受一個 Fact 完成兩個 phase。

### 2.2 THINK Exit validation

SM 依固定順序驗證：

1. `action_kind` 必須為 `speak | tool | rest`。
2. 共用 `ActionPayloadValidator` 驗證 payload，不 mutation Fact。
3. `post_action_route` 必須為 `KEEP_NEXT | REPLACE_NEXT | END_SESSION`。
4. `rest` 僅能搭配 `END_SESSION`；`speak`/`tool` 可搭配三種 route。
5. continuing route 對 `next_perceptions` 剔除未註冊 kind、依首次出現順序去重；結果必須非空。
6. `END_SESSION` 完全忽略 `next_perceptions`；canonical Reasoner 仍必須產空 tuple。

任何 schema、payload、action/route 組合或 continuing-empty 違約，均為 SM self-check E1：直接
`StateChanged(->ERROR)`，不由 SM fabricate `ErrorOccurred`，也不因違約本身直接進 Level 3。

### 2.3 Canonical outcomes

| Intent/outcome | Canonical Fact | Ownership |
| :--- | :--- | :--- |
| normal answer then listen | `speak + KEEP_NEXT + non-empty next_perceptions` | model speech；keep Conversation |
| application retry | `speak + KEEP_NEXT + non-empty next_perceptions` | application speech；no second inference |
| answer then replace | `speak + REPLACE_NEXT + non-empty next_perceptions` | action first；replacement second |
| final non-empty speech | `speak + END_SESSION + ()` | model speech completes before rest |
| empty end intent | `rest + END_SESSION + ()` | one rest phase；no fabricated speech |
| tool then end | `tool + END_SESSION + ()` | tool completes before rest |

## 3. Private Conversation lifecycle contract

### 3.1 Narrow required port

`src/sbd/core/state_manager/ports.py` 定義 required runtime-checkable port：

```python
ConversationGeneration: TypeAlias = int

@dataclass(frozen=True, slots=True)
class ConversationReady:
    session_id: str
    generation: int

@dataclass(frozen=True, slots=True)
class ConversationOpenRejected:
    session_id: str
    generation: int
    cleanup_proven: bool
    engine_usable: bool

@dataclass(frozen=True, slots=True)
class ConversationCloseProof:
    session_id: str
    generation: int
    request_terminal_proven: bool
    cleanup_proven: bool
    engine_usable: bool

@runtime_checkable
class ConversationLifecycleControl(Protocol):
    async def open_conversation(
        self, session_id: str, generation: int
    ) -> ConversationReady | ConversationOpenRejected: ...

    async def close_conversation(
        self, session_id: str, generation: int, reason: str
    ) -> ConversationCloseProof: ...

    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
```

這些 return object 是 SM inbox 的 private completion data，不是 Event、Worker Fact 或產品輸出。
Control 同時只允許一個 lifecycle operation；wrong session/generation、重入或回傳其他型別是
wiring/contract E1。

### 3.2 Proof semantics

- `ConversationReady` 只可在 clean Conversation 已被該 `(session_id, generation)` 唯一 claim、且
  可接受 admission 時回傳。
- `ConversationOpenRejected` 只有 `cleanup_proven=True` 且 `engine_usable=True` 才是 R2；SM 可在
  WAKE 內配置下一個 generation 並重試。任一 false 是 E1。
- `ConversationCloseProof` 只有三個 proof flag 全為 true，才可完成 replacement。Session-end close
  若 Engine 被 Level 2 破壞，後續仍須等待既有 RM recovery boundary；shutdown 不 rebuild。
- `request_terminal_proven` 包含 active native request 的 terminal/join；Python outer task done
  不能替代 native/child proof。
- `cleanup_proven` 表示 Conversation-local history/KV/reference 已不可再被使用；不要求 allocator
  立即把全部 PSS 歸還 OS。
- Control 不保存跨 Product Session 記憶，也不得 replay rejected input。

### 3.3 In-flight representation

`InFlightRecord.phase` 擴充為：

```text
perception | think | action_primary | action_rest |
conversation_open | conversation_close
```

並新增 `completion_mode: Literal["worker_fact", "private_result"]`、`private_result` 與
`cleanup_proven` tracking。Worker phases 仍要求 terminal Fact + task done；Conversation phases 要求
matching private result + task done + required proof。Conversation record 的 `kind` 固定為
`conversation.open` 或 `conversation.close`，既有 cancel timeout policy 可使用 per-kind override，
未配置時使用 default；本 revision 不新增 timeout config。

若 lifecycle task 已 done 但 result 缺 proof，SM 不得先移除 record。該 record 保留為 E1
convergence target；Converger 對 `cleanup_proven=False` 的 lifecycle record 仍須呼叫
`abort()`/`force_abort()`，不得因 outer task done 略過 cleanup。完成 proof 或 Level 2 report 後才可
移除；Level 2 無法證明則 Level 3。

Done callback 對 lifecycle task enqueue 單一 `_ConversationLifecycleCompleted` private notice，攜帶
`(operation, session_id, generation, correlation_id, task identity)`；dispatch loop 只在確認 task done
後呼叫 `task.result()` 取得上述 typed result。不得另發第二個 result notice。任一 identity 不匹配為
stale notice，log sanitized context 後 drop，不得改變新 generation/session。

對 done-but-unproven record，成功的 Level 1 `abort()` return 依既有 worker contract 成為 cleanup
proof；Level 2 則以 `force_abort()` return、outer task done 與 `ForceAbortReport` 共同成 proof。完成後
由 SM 標記 `cleanup_proven` 並移除 record；任一 timeout/exception 仍是 Level 3。

## 4. State Manager data model

`SessionContext` 至少新增/調整：

```python
conversation_generation: int = 0
conversation_state: Literal["none", "opening", "ready", "closing"] = "none"
wake_ack_ready: bool = False
model_admission_blocked: bool = True
post_action_route: PostActionRoute | None = None
normalized_next_perceptions: tuple[str, ...] = ()
action_phase: Literal["none", "primary", "post_action_rest"] = "none"
```

既有 `turn_id` 在 Product Session 內單調遞增；replacement 不歸零、不復用。`action_completed` 不再
作為可跨 phase 重用的單一完成旗標；完成資料歸屬 matching in-flight record，phase 結束即清除。

StateManager 增加 one-shot `set_conversation_lifecycle(control)`：

- 只能在 SM start 後、任何 input producer arm 前，由 RM late-fill 一次。
- `worker.cognition.reasoner` 的 `control` property 或 instance 本身必須實作該 Protocol。
- 缺失、None、重複填入或 producer 已 arm 才填入為 `StateManagerWiringError`，startup fail closed。
- M1/M2 composition 注入 deterministic fake；real M4B control 要等 cognition/product design。
- 不提供 Null/optional bypass，因沒有 Conversation readiness 就不能合法進 PERCEPTION。

Reasoner `reason()` 呼叫新增 keyword-only `conversation_generation`。SM 只在 session 的 generation
仍為 `ready` 且未 blocked 時啟動 THINK；control/Reasoner 可用該值拒絕 generation mismatch。

## 5. WAKE readiness algorithm

### 5.1 Entry

1. 建立 Product Session，`turn_id=0`、`conversation_generation=1`、admission blocked。
2. 保留既有 wake-source assignment 與 microphone release proof。
3. transition 至 WAKE 並 publish `StateChanged`。
4. 分別建立 wake acknowledgement timer 與 `open_conversation(session_id, 1)` task；兩者都只將
   private notice enqueue，callback 不直接 transition。
5. 可選 preparation UX 可由 WAKE observer 並行，但不是 gate、Fact、turn 或 Conversation content。

SM dispatch loop 不 await open task，因此 WAKE 中仍可處理 interrupt、shutdown、error、button 與
external-message pending ownership。任何 perception worker、listen/ASR 或 Reasoner generation 都
不能在 readiness 前啟動。

### 5.2 Progress gate

只有以下條件同時成立才進 PERCEPTION：

```text
state == WAKE
AND wake_ack_ready
AND conversation_state == ready
AND matching open record fully joined and removed
AND no convergence/end intent
```

Timer 先到只設 `wake_ack_ready=True`；open 先到只設 Conversation ready。兩者皆不得單獨轉移。

### 5.3 Failed open

- Matching `ConversationOpenRejected(True, True)`：保留 Product Session，完成失敗 object cleanup
  後遞增 generation，啟動另一個 clean open。不得依失敗次數升 E1/R3，也不得 reset turn identity。
- Proof 缺失、Engine 不可用、exception、protocol desync 或 invalid result：E1。
- WAKE 中 interrupt/error/shutdown：取消 timer、block admission，對 open record走 §8 收斂；取得
  termination/cleanup proof 前不得清 session 或接受新 wake。

## 6. THINK and ACTION algorithms

### 6.1 THINK

PERCEPTION 完整 join 後，SM 再確認 active Conversation generation ready，才呼叫 Reasoner。Reasoner
回一個 `LLMResponse`；Fact/task join 後套用 §2.2。通過才保存 route/normalized perceptions並進
ACTION，違約走 E1。

R1 application retry 的必要條件是 rejected input 未改動 Conversation；它是正常
`speak + KEEP_NEXT` cognition Fact。`UNSUPPORTED_INPUT`、wiring failure 或無法證明未 mutation
不得假裝 R1，必須走 E1。

### 6.2 ACTION phases

| Current phase/result | Route | Next operation |
| :--- | :--- | :--- |
| primary speak/tool `ok` | `KEEP_NEXT` | keep Conversation；用 normalized perceptions 進下一 turn |
| primary speak/tool `error` | `KEEP_NEXT` | keep Conversation；用 `default_perceptions` 進下一 turn |
| primary speak/tool `ok` | `REPLACE_NEXT` | 用 normalized perceptions；執行 replacement barrier |
| primary speak/tool `error` | `REPLACE_NEXT` | 用 `default_perceptions`；執行 replacement barrier |
| primary speak/tool any | `END_SESSION` | 啟動唯一 `post_action_rest`；不進 perception |
| rest any | `END_SESSION` | 此次 rest 即唯一 rest phase；開始 session convergence |
| post-action rest any | inherited `END_SESSION` | 開始 session convergence；status 不改 end intent |

`speak/tool + END_SESSION` 的 primary 與 rest 使用不同 correlation/record，且不並存。Primary record
完整 join/remove 後才建 rest record。SM 保持 public state `ACTION`，不重複 publish
`StateChanged(ACTION, ACTION)`。Final primary error 仍 rest/end，不使用 `default_perceptions`。

### 6.3 Sequential replacement barrier

ACTION primary 完整 join 後依序：

1. `model_admission_blocked=True`；拒絕任何新 Reasoner/generate admission。
2. 確認本 turn THINK record 已有 terminal/task join proof。
3. 啟動 old generation close；等待 matching `ConversationCloseProof` 與 task done。
4. 只有 request terminal、cleanup、Engine usable 三項 proof 都成立，才清 old generation claim。
5. 遞增 generation，啟動 clean open；只有 matching `ConversationReady` 完整 join 後才 unblock。
6. 使用步驟前已選定的 normalized/default perceptions 進下一 PERCEPTION；此時 `turn_id += 1`。

Barrier 全程保持同一 Product Session，不清 session/turn tracking、不執行 `flush_to_wake` 或
`discard`、不自動 replay rejected input。Close/open 任一步缺 proof 或 Engine unusable 立刻離開 R2
進 E1；不得先 claim 新 Conversation。

## 7. Session end and recovery

`_PendingConvergence` 增加 private phase：

```text
workers -> conversation_close -> recovery -> complete
```

所有 rest/R3 interrupt/E1/shutdown 先登記 end intent、block admission、取消 wake timer，再對
active perception/think/action/open/replacement work走現有 SessionConverger。In-flight work有 proof 且
清空後：

- 若有 ready Conversation，啟動一次 session-end close，等待 matching cleanup proof。
- 若 open 尚未 claim 成功且其 cleanup 已由 abort/force proof涵蓋，不額外 close。
- close 缺 proof 轉 E1/Level 2；Level 2 破壞 backend 時使用既有 RM recovery barrier。
- 只有 lifecycle proof、in-flight empty 與必要 recovery barrier 全成立後，才清 session tracking、
  resume wake、回 IDLE 或結束 process。

Buffer policy 仍依最初 session-end trigger：normal rest `flush_to_wake`；interrupt/error/shutdown
`discard`；replacement 永遠 `none`。Error 疊加或 shutdown 可依既有 precedence 升級 policy。

## 8. R1/R2/R3/E1 implementation classification

| Class | Implementable minimum | SM result |
| :--- | :--- | :--- |
| R1 | input 未 mutation；canonical application `LLMResponse` | keep generation，normal ACTION |
| R2 | request terminal/join + old/failed Conversation cleanup + Engine usable | same session sequential replacement |
| R3 | explicit USER end/reset or interrupt | close active generation and end Product Session |
| E1 | illegal outcome、wiring/protocol failure、worker crash、backend unusable 或 proof 缺失 | ERROR + Level 1/2/3 |

R3 的 explicit USER end/reset 不新增 foundation Signal：Reasoner 判定明確使用者結束/reset 意圖時，
依 §2.3 產出內容相符的 canonical `speak | tool | rest + END_SESSION`；interrupt 則由
`InterruptRequested` 進入同一正常收斂分類。`ShutdownRequested` 也會結束 Product Session，但屬
shutdown boundary，不是 R3。

重複 R2 不因 count 變成 E1，也不自動成 R3。Level 2 或 recovery 無 proof 才進 Level 3。

## 9. Direct implementation inventory

### 9.1 Required source/docs delta

- `docs/implement/ch01_events.md`, `src/sbd/core/events.py`：route type 與四欄 Fact。
- `docs/implement/ch02_contracts.md`：Reasoner generation input、Action error route boundary。
- `docs/implement/ch04_state_manager.md` 與
  `src/sbd/core/state_manager/{manager,session,inflight,notices,ports,guards,exceptions}.py`：本文件
  §§3–7。
- `docs/implement/ch05_resource_manager.md`, `src/sbd/core/resource_manager/manager.py`：required
  Conversation control late-fill 與 startup fail-closed。
- `docs/implement/ch06_cancel.md`, `src/sbd/core/state_manager/convergence.py`：done-but-unproven
  lifecycle target 不得被略過。
- `src/sbd/core/{m1_composition,m2_composition}.py` 與 deterministic fakes：explicit route、required
  lifecycle control。
- `src/sbd/cognition/reasoner.py`：只做 event signature/generation seam 的 compile migration；不據此
  宣稱 legacy cognition policy 被採用或產品通過。

### 9.2 Expected test impact

- `tests/test_events.py`, `tests/test_state_manager.py`, `tests/test_m2_sm_flows.py`,
  `tests/test_m2_flows.py`, `tests/test_m2_wrk_003.py`。
- `tests/milestones/test_m1_foundation.py`, `tests/milestones/test_m2_mock_pipeline.py` 與所有直接建構
  `LLMResponse` 的 fixtures/call sites。
- Tester 必須新增 foundation coverage；更新既有 assertions 只能證明 regression，不能代替新增
  readiness/replacement/rest/error cases。

### 9.3 Explicitly excluded from foundation package

- `src/sbd/cognition/{llm,llm_child_protocol,prompt_builder}.py`、`scripts/m4b_*`、
  `requirements/m4b/` 與 M4B-specific product/target tests。
- prompt/profile、token/KV admission、memory/timing instrumentation 與 real Pi candidate。

若實作發現必須改動上述 excluded surface，Developer 先開 `IR_dev`，不得擴大 package 或借用
legacy design 自行決定。

## 10. Minimum coverage request

Tester 的新 spec 至少須獨立覆蓋：

1. Event schema fail-closed migration與所有 call site explicit route。
2. WAKE ack/open兩種先後、不得提前 perception，以及 open 中 interrupt/error/shutdown。
3. `KEEP_NEXT`、`REPLACE_NEXT`、final speak、empty end、tool end 的唯一 ACTION route。
4. Primary/rest phase correlation，final/continuing action error 的不同結果。
5. Replacement close-before-open、generation/turn continuity、no overlap/no replay/no buffer exit policy。
6. R1 clean retry、R2 proof、repeated R2、R3 explicit end與E1 missing-proof boundary。
7. stale lifecycle notice、wrong generation/result type、lifecycle task done但proof缺失。
8. Level 2 destroyed backend/recovery與Level 3 proof failure。
9. 全部既有 M1/M2 entrypoint與full regression，不刪除、skip或xfail歷史 acceptance tests。

測試以 `asyncio.Event`/barrier 控制順序，不用 wall-clock sleep 猜 race；不需 real LLM、Pi、Audio
device、網路、credential 或 legacy M4B fixtures。

## 11. Gate and Developer package boundary

本設計完成只允許 Tester 建立/核准 coverage，不開 Developer entry。當 Tester response 為
`Revised` 後，Designer只核對 coverage 是否完整映射 §10 與本文件直接影響面；Resolved 後才可
開一個 `M4B-FOUNDATION-REVISION` Developer package。

該 package 必須一次遷移 event schema、SM algorithms、lifecycle fakes/control、generic authority 與
受影響 M1/M2 regression，保持 full suite green。它不包含 M4B cognition/product rewrite；foundation
驗證完成後，Designer才填寫 `ch_m4b_llm_production.md` 的 replacement product design。
