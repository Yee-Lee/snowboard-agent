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
| **M4b production** | [ch_m4b_llm_production.md](../implement/ch_m4b_llm_production.md) | Gemma POC winner baseline integrated；Core Gate 3 pending | Designer | Final winner ACK與R3 identity已固定；single design/test review、implementation與exact-SHA acceptance未完成 |
| **Child Protocol v1** | [protocol.md](../protocol.md) | Audio approved；LLM `snowboard.llm/1` Designer draft complete / queued for review | Designer | LLM winner lifecycle、pre-warm與exact wire schema已納入，待`IR_review_M4B_I`審查 |

## 跨章節 Gate 與備註

* 需確保 `ch01` 中定義的欄位能支援 `ch04` SM 的 Guard 邏輯。
* M4a production design與test-spec coverage sign-off均已完成；Accepted Audio POC evidence仍不取代Core exact-SHA驗收。
* Gate 2A的Gemma R1 P2/P8 FAIL與Qwen exclusion維持immutable history；Gate 2B後User以known resident-retention defect waiver選定Gemma POC winner。此waiver不等於Core Gate 3 PASS；若runtime偏離LiteRT-LM仍須先處理change request／`AR_impl`。

## M4b Designer planning handoff（2026-08-29）

### Current decision

Gate 2B final winner ACK已固定POC baseline，但不宣告Core M4b Design Ready、Gate 3 PASS或Accepted。完整
review scope固定包含：

1. `docs/implement/ch_m4b_llm_production.md` 的process ownership、lifecycle、config、packaging、
   inheritance、coverage與work-package gates；
2. `docs/protocol.md` §4／§6的`protocol_version="snowboard.llm/1"` lifecycle、wire schema與tests；
3. `docs/milestones/M4.md` 的Gate 2A / provisional / Gate 2B / Gate 3順序；
4. `docs/implement/m4b_gate2a_intake.md`的historical identity、Gemma/Qwen decision與evidence lineage；
5. 與Ch 2b、Ch 5、Ch 6、Ch 9、Ch 10及`model_spec.md` §6 winner baseline的一致性。

依USER減少多輪的決策，不開generic-only review。現在由Reviewer以單一
`IR_review_M4B_I`一次審Phase A、DELIVERY-019 adaptation、selected baseline、protocol/driver/config/
lock/packaging與WP-01～06；Tester再一次補完整M4B test spec，Designer以`TR_spec_M4B_I`確認100%
覆蓋後才交Developer。

### Remaining Core entry blockers

- `ch_m4b_llm_production.md`的Gate 2A Phase A seam尚未完全收斂到`protocol.md` §4.4 winner schema；
- persistent child的mandatory pre-warm、bounded recycle、typed cancellation與recovery barrier需完成review；
- machine-readable Core lock、offline install closure、license/notices與4 GB defect delta需固定；
- Tester完整coverage sign-off、Developer implementation與Core exact-SHA Gate 3尚未開始。

Gate 2A provisional ACK、Gate 2B final review與final winner ACK均保留為append-only lineage。下一步
是以`model_spec.md` §6與`protocol.md` §4為authority收斂`ch_m4b_llm_production.md`，發起單一完整
`IR_review_M4B_I`，再由Tester完成`TR_spec_M4B_I` coverage sign-off。

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
