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
| **Ch 10** | [ch10_config.md](../implement/ch10_config.md) | Done; M4a extension draft | Designer | 基礎Config schema已定稿；M4a real ASR/TTS fields與strict profile待同production design審查 |
| **Ch 11** | [ch11_error_logging.md](../implement/ch11_error_logging.md) | Done | Designer | 錯誤處理與 logging 慣例 |
| **M4a production** | [ch_m4a_audio_production.md](../implement/ch_m4a_audio_production.md) | Designer complete — Reviewer next | Designer | `audio_m4` Accepted reference已固定；Core Gate 3 ASR/TTS、runtime isolation、recovery與evidence mapping |
| **Audio Protocol v1** | [protocol.md](../protocol.md) | Designer complete — Reviewer next | Designer | ASR/TTS private child framing、identity、cancel、terminal與cleanup schema；LLM部分仍Pending |

## 跨章節 Gate 與備註

* 需確保 `ch01` 中定義的欄位能支援 `ch04` SM 的 Guard 邏輯。
* M4a production implementation須等待本章Reviewer通過，且Tester修訂`test_spec_M4.md`後由Designer完成coverage sign-off；Accepted Audio POC evidence不取代Core exact-SHA驗收。

## M4a Designer handoff（2026-08-26）

### Reviewer — next owner

Review scope固定為：

1. `docs/model_spec.md` Audio baseline / provenance / license / product commands；
2. `docs/protocol.md` Audio Protocol v1；
3. `docs/implement/ch_m4a_audio_production.md`；
4. `docs/implement/ch10_config.md` M4a extension；
5. 上述文件對Ch 2b / Ch 5 / Ch 6與`docs/milestones/M4.md`的直接一致性。

Reviewer依workflow建立下一輪`docs/reviews/IR_review_IV.md`（requestor Reviewer、owner Designer）。Exit是Blocking全數Resolved並歸檔該輪；不得把M4b/LLM或M4c內容加入本次Audio design gate。

### Tester — queued after IR resolution

`docs/reviews/TR_spec_M4_I.md`已Open但entry dependency尚未滿足。IR resolved後，Tester保留既有`M4-REG-001`並修訂`docs/test_spec/test_spec_M4.md`，覆蓋該單列出的13個M4A Test ID；完成後將TR狀態改`Revised`交Designer作100% coverage sign-off。

### Developer — queued after TR resolution

只有`TR_spec_M4_I`由Designer標`Resolved`後，Developer才更新`docs/reviews/dev_progress_M4.md`，估點並執行`M4A-WP-09`～`M4A-WP-13`。首個production implementation仍只跑主要Python minor與affected tests；建立provisional candidate commit前另依workflow取得USER確認。
