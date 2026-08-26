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
| **M4a production** | [ch_m4a_audio_production.md](../implement/ch_m4a_audio_production.md) | Design + test-spec coverage approved — Developer active | Designer | `IR_review_M4A_I`與`TR_spec_M4_I`均Resolved；Developer可建立M4A-WP-09～13 |
| **Audio Protocol v1** | [protocol.md](../protocol.md) | Audio v1 Reviewer approved | Designer | ASR/TTS private child framing、identity、cancel、terminal與cleanup schema已核准；LLM部分仍Pending |

## 跨章節 Gate 與備註

* 需確保 `ch01` 中定義的欄位能支援 `ch04` SM 的 Guard 邏輯。
* M4a production design與test-spec coverage sign-off均已完成；Accepted Audio POC evidence仍不取代Core exact-SHA驗收。

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
