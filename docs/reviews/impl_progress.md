# Implement Progress ( impl_progress.md )

本文件用於追蹤 `docs/implement.md` 所列各章節的撰寫進度與跨章節依賴 (gate)。

## 章節進度

| 章節 | 標題 | 狀態 | 負責人 | 備註 |
| :--- | :--- | :--- | :--- | :--- |
| **Ch 01** | [ch01_events.md](../implement/ch01_events.md) | Done | Designer | 事件 dataclass 定義 |
| **Ch 02** | [ch02_contracts.md](../implement/ch02_contracts.md) | Done | Designer | 跨層貫穿契約 |
| **Ch 02a** | [ch02a_core_hal.md](../implement/ch02a_core_hal.md) | Done | Designer | core HAL Protocol |
| **Ch 02b** | [ch02b_workers.md](../implement/ch02b_workers.md) | Done | Designer | worker 契約與 library adapter |
| **Ch 03** | [ch03_event_bus.md](../implement/ch03_event_bus.md) | Done | Designer | Event Bus 實作 |
| **Ch 04** | [ch04_state_manager.md](../implement/ch04_state_manager.md) | Done | Designer | State Manager 實作 |
| **Ch 05** | [ch05_resource_manager.md](../implement/ch05_resource_manager.md) | Done | Designer | Resource Manager 實作 |
| **Ch 06** | [ch06_cancel.md](../implement/ch06_cancel.md) | Done | Designer | Cancel 三級收斂實作 |
| **Ch 07** | [ch07_external_message.md](../implement/ch07_external_message.md) | Done | Designer | External message buffer |
| **Ch 08** | [ch08_display_arbiter.md](../implement/ch08_display_arbiter.md) | Done | Designer | Display 仲裁層協定 |
| **Ch 09** | [ch09_action_payload.md](../implement/ch09_action_payload.md) | Done | Designer | LLMResponse action_payload schema |
| **Ch 10** | [ch10_config.md](../implement/ch10_config.md) | Done; M4a extension reviewed | Designer | 基礎Config schema與M4a real ASR/TTS strict profile已獲Reviewer核准 |
| **Ch 11** | [ch11_error_logging.md](../implement/ch11_error_logging.md) | Done | Designer | 錯誤處理與 logging 慣例 |
| **M4a production** | [ch_m4a_audio_production.md](../implement/ch_m4a_audio_production.md) | Accepted | Designer | Core candidate `6c3ba95455dc5c2a152aa230b8ae5915887fe6a9`已完成Tester exact-SHA驗收與Designer final confirmation |
| **M4b production** | [ch_m4b_llm_production.md](../implement/ch_m4b_llm_production.md) | Design review approved；Tester coverage pending | Designer | `IR_review_M4B_I` Blocking 0／Resolved；WP-01～06須等`TR_spec_M4B_I`，尚未宣告Development Ready或Gate 3 PASS |
| **Child Protocol v1** | [protocol.md](../protocol.md) | Audio approved；LLM `snowboard.llm/1` design approved | Designer | LLM winner lifecycle、pre-warm與exact wire schema已由`IR_review_M4B_I`核准 |

## 跨章節 Gate 與備註

* 需確保 `ch01` 中定義的欄位能支援 `ch04` SM 的 Guard 邏輯。
* M4a production design與test-spec coverage sign-off均已完成；Accepted Audio POC evidence仍不取代Core exact-SHA驗收。
* Gate 2A的Gemma R1 P2/P8 FAIL與Qwen exclusion維持immutable history；Gate 2B後User以known resident-retention defect waiver選定Gemma POC winner。此waiver不等於Core Gate 3 PASS；若runtime偏離LiteRT-LM仍須先處理change request／`AR_impl`。

## M4b Designer post-Gate-2B design approval（2026-08-30）

### Current decision

Gate 2B final winner ACK已固定POC baseline；Designer的post-Gate-2B planning已完成，Reviewer亦已在
`IR_review_M4B_I`以Blocking 0／`Resolved`核准完整設計。但在Tester coverage 100%前，不宣告Core
M4b Development Ready、Gate 3 PASS或Accepted。已核准的single-review scope包含：

1. `docs/implement/ch_m4b_llm_production.md` 的process ownership、lifecycle、config、packaging、
   inheritance、coverage與work-package gates；
2. `docs/protocol.md` §4／§6的`protocol_version="snowboard.llm/1"` lifecycle、wire schema與tests；
3. `docs/milestones/M4.md` 的Gate 2A / provisional / Gate 2B / Gate 3順序；
4. `docs/implement/m4b_gate2a_intake.md`的historical identity、Gemma/Qwen decision與evidence lineage；
5. 與Ch 2b、Ch 5、Ch 6、Ch 9、Ch 10及`model_spec.md` §6 winner baseline的一致性。

依USER減少多輪的決策，本輪未開generic-only review。Reviewer已用單一`IR_review_M4B_I`完成Phase A、
DELIVERY-019 adaptation、selected baseline、protocol/driver/config/lock/packaging、structured Reasoner
seam、planned recycle與WP-01～06審查，並保持POC waiver與Core product PASS分離。下一個owner是Tester：
一次補完整M4B test spec，Designer以`TR_spec_M4B_I`確認下列15項coverage 100%後才交Developer：
`M4B-CFG`、`M4B-LOCK`、`M4B-IPC`、`M4B-RDY`、`M4B-GEN`、
`M4B-OUT`、`M4B-P5`、`M4B-CAN`、`M4B-REC`、`M4B-HIST`、`M4B-PRIV`、`M4B-OFF`、
`M4B-RES`、`M4B-PKG`、`M4B-INH`。

### Fixed design disposition

- Architecture change：`No`。沿用`arch.md`既有persistent child、Reasoner與RM recovery barrier；不開
  `AR_impl`。
- Child wire只接受structured `ReasoningInput`並回單一structured `RESULT`；沒有raw prompt、
  parent-visible `CHUNK`或跨operation history。
- Gate 2B real marker harness的`listen -> speak -> listen`窄化面只作winner evidence；Core renderer固定
  generic canonical JSON prompt與capability-bound`speak/tool/rest` constrained schema，列為M4B-OUT/INH
  product delta，不把POC結果重標。
- 每child最多8次inference attempt，或post-prewarm owner PSS增量`>=48 MiB`，或target
  `MemAvailable <768 MiB`時，在terminal cleanup後排程planned recycle。缺少target sample為
  preflight failure。
- Planned recycle只走`backend.cognition.reasoner.llm`同key `RecoveryTicket`；replacement完成exact-lock
  authentication、Engine load、pre-warm與cleanup並達`INFERENCE_READY`前，下一次admission保持阻擋；
  main常駐監督`rm.wait_fatal()`，故沒有下一request時的recovery failure仍立即Level 3；沒有alternate
  model/profile fallback。
- 20-session不因recycle分段重算：combined PSS與system-used仍各自套r14 slope`<=4 MiB/session`及
  late-minus-early delta`<=64 MiB`，每generation owner PSS delta亦`<=64 MiB`。

### Remaining Development Ready blockers

- Reviewer gate已完成：`IR_review_M4B_I`為Blocking 0／`Resolved`，並已歸檔；
- Tester尚未將15項coverage落入`docs/test_spec/test_spec_M4.md`並由`TR_spec_M4B_I`確認100%；
- Developer WP-01～06、machine-readable lock、offline package closure與Core exact-SHA Gate 3均尚未開始。

Gate 2A provisional ACK、Gate 2B final review與final winner ACK均保留為append-only lineage。下一步
是Tester完成M4B test spec，再由Designer執行`TR_spec_M4B_I` coverage sign-off。

### Reviewer approval confirmation（2026-08-30）

- `docs/reviews/history/IR_review_M4B_I.md`：YAML `status: "Resolved"`。
- Reviewer結論：十項§13核對全部通過，Blocking findings為0，architecture change維持`No`。
- 唯一Advisory不影響Resolved；Ch 5 §6.5原已定義`prepare_shutdown()`，本輪在M4b §0.1補上其
  RM surface交叉引用。
- 此核准只關閉設計審查，不取代Tester coverage、Developer implementation或Core exact-SHA Gate 3。

### Post-Gate-2B Reviewer delivery self-check（2026-08-30）

- `git diff --check`：PASS；touched design Markdown heading-separation scan無輸出。
- Stale-seam scan對deprecated async/raw-prompt/pending-ID/text-result seam、old request ID與generic
  protocol digest均無輸出。
- Gate 2B execution Git object可讀；逐檔`git show ... | shasum -a 256`確認prompt、response、selected
  Pi protocol、strict config schema與product config，再以exact renderer bytes計算fixed pre-warm prompt；六個digest分別為
  `aca834...`、`4be45e...`、`e1af3b...`、`ce8fa4...`、`c4557b...`、`4f3bc3...`，與設計全文一致。
- Mechanical coverage：15個M4B Test ID、6個Developer WP、10列Designer requirement-closure matrix，
  數量均exact；沒有修改Tester-owned test spec或Developer-owned progress。
- 本輪是Designer docs delivery，現有`src/`仍保留pre-M4b text seam，預期由WP-01～06修改；因此沒有
  用舊source pytest宣稱新設計已實作或Gate 3 PASS。正式portable/Pi evidence仍屬後續role gate。
- PM handoff檢查：active=0；022／023／024維持Resolved/final ACK，025 hardware diagnostic已在history
  標Resolved且與本M4b delivery無關。工作樹中025索引／script為其他變更，本輪未改寫或納入scope。

### Phase A self-check evidence（2026-08-29）

- `git diff --check`：PASS；touched Markdown trailing-whitespace scan無輸出。
- `python`不可用；system與`.venv`的`python3`皆為unsupported Python 3.14.6，故不宣稱正式
  3.11／3.12／3.13 portable result。
- `.venv/bin/python -m pytest -q tests/test_m2_wrk_003.py tests/test_contracts.py`：
  `20 passed in 0.03s`，證明本設計引用的Reasoner P5/stateless/cancel與LLM adapter contract seam
  在目前source存在。
- 加跑`tests/test_m4a_ipc_001.py`的組合結果為總計`43 passed, 6 failed`；6個failure全在既有
  process-group exit proof，因macOS無`/proc`且Python 3.14不在支援矩陣。這不是本輪文件造成的
  regression，也不是M4A重驗PASS；Phase A因此明確禁止重構`FramedProcess`，後續正式驗證仍須在
  支援Python與Linux執行。
- 本輪Core working tree只含Designer-owned docs與PM handoff歸檔；沒有`src/`、`tests/`、dependency、
  config、candidate runner或formal evidence變更，未建立real adapter或production model/runtime lock。

## M4a Designer handoff（2026-08-26）

### Reviewer — approval complete

Review scope固定為：

1. `docs/model_spec.md` Audio baseline / provenance / license / product commands；
2. `docs/protocol.md` Audio Protocol v1；
3. `docs/implement/ch_m4a_audio_production.md`；
4. `docs/implement/ch10_config.md` M4a extension；
5. 上述文件對Ch 2b / Ch 5 / Ch 6與`docs/milestones/M4.md`的直接一致性。

Reviewer 已完成複審，並於 `IR_review_M4A_I.md` 中明確核准了完整 M4a handoff scope (包含 `model_spec.md`、`protocol.md`、`ch_m4a_audio_production.md` 與 `ch10_config.md`)，該審查單已 Resolved 並歸檔。

### Test spec — coverage resolved

`docs/reviews/TR_spec_M4_I.md`已Resolved。Tester第二次submission後，USER明確指示Designer
接手剩餘修訂；Designer已直接補齊runner lifecycle/schema、READY identity、fixed runtime、
real-child recovery、composition/RM與product preflight，並完成T1～T12終局核對。

### Developer — active：建立M4A-WP-09～13

Developer現在更新`docs/reviews/dev_progress_M4.md`，估點並執行`M4A-WP-09`～
`M4A-WP-13`。首個production implementation仍只跑主要Python minor與affected tests；
建立provisional candidate commit前另依workflow取得USER確認。
