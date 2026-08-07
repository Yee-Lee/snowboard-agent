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
| **Ch 10** | [ch10_config.md](../implement/ch10_config.md) | Done | Designer | Config schema |
| **Ch 11** | [ch11_error_logging.md](../implement/ch11_error_logging.md) | Done | Designer | 錯誤處理與 logging 慣例 |

## 跨章節 Gate 與備註

* 需確保 `ch01` 中定義的欄位能支援 `ch04` SM 的 Guard 邏輯。
