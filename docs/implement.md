# Snowboard 實作細節 ( implement.md )

本文件為 Snowboard 實作契約的索引：Protocol 方法簽名、事件 dataclass、SM 內部演算法、資源仲裁協定、config schema。回答「怎麼實作」。各章內容拆分於 `implement/` 子目錄。

本文件只寫設計架構本身──章節切分、章節分工、旁掛文件關係。動態進度（章節狀態、跨章 gate、章節備註）見 [reviews/impl_progress.md](reviews/impl_progress.md) ；Designer 的職責邊界、文件分工、工作流程與同步原則見 [roles/designer.md](roles/designer.md) 。

## 文件權責分界

| 文件 | 職責 |
| :--- | :--- |
| `arch.md` | WHAT + WHY──原則、邊界、契約存在性、事件語意 |
| `implement.md`（本索引 + `implement/` 各章） | HOW──具體 Python signature、dataclass 欄位、演算法、config schema |
| `display_spec.md` | Display 內容、lifecycle、Baseline / Complete UX profile |
| `model_spec.md` | Runtime 模型選型、版本 / 授權固定與階段 gate |
| `milestone.md` | WHEN + VERIFY──階段、範圍、驗收 |
| `protocol.md` | 對外 / 跨 process wire format；Audio Protocol v1 已定義，LLM 部分待 M4b final input |

`arch.md` 未明或無法落實的項目，依 [reviews/README.md](reviews/README.md) §2 以 `arch_review_impl_<round>.md` 交 Architect 裁定；Designer 不自行改寫 `arch.md`。既有 `history/arch_review_implement.md` 僅保留歷史追蹤。

---

## 章節總覽

| # | 檔案 | 章節 | 對應 arch.md |
| :--- | :--- | :--- | :--- |
| **1** | [ch01_events.md](implement/ch01_events.md) | 事件 dataclass 定義 | §3.2 / §3.3 |
| **2** | [ch02_contracts.md](implement/ch02_contracts.md) | 跨層貫穿契約 | §2.4 / §2.6 / §2.8 / §2.9 / §6.1 |
| **2a** | [ch02a_core_hal.md](implement/ch02a_core_hal.md) | core HAL Protocol | §2.3 |
| **2b** | [ch02b_workers.md](implement/ch02b_workers.md) | worker 契約與 library adapter | §2.4 / §2.6 / §2.7 / §2.8 |
| **3** | [ch03_event_bus.md](implement/ch03_event_bus.md) | Event Bus 實作 | §3.4 |
| **4** | [ch04_state_manager.md](implement/ch04_state_manager.md) | State Manager 實作 | §3.5 / §3.6 / §3.7 / §4 |
| **5** | [ch05_resource_manager.md](implement/ch05_resource_manager.md) | Resource Manager 實作 | §6.1 / §6.2 / §6.8 |
| **6** | [ch06_cancel.md](implement/ch06_cancel.md) | Cancel 三級收斂實作 | §6.4 / §6.5 |
| **7** | [ch07_external_message.md](implement/ch07_external_message.md) | External message buffer | §5.1 |
| **8** | [ch08_display_arbiter.md](implement/ch08_display_arbiter.md) | Display 仲裁層協定 | §5.3 |
| **9** | [ch09_action_payload.md](implement/ch09_action_payload.md) | LLMResponse action_payload schema | §2.7 / §4.6 |
| **10** | [ch10_config.md](implement/ch10_config.md) | Config schema | §7.1 |
| **11** | [ch11_error_logging.md](implement/ch11_error_logging.md) | 錯誤處理與 logging 慣例 | §3.4 / §6.6 / §6.7 |
| **M4a** | [ch_m4a_audio_production.md](implement/ch_m4a_audio_production.md) | Accepted Audio production adapter、runtime isolation、recovery 與 Gate 3 mapping | §2.4 / §2.8 / §6.4 / §6.8 |

各章目前狀態與備註見 [reviews/impl_progress.md](reviews/impl_progress.md) 。

---

## 章節分工原則

* **Ch 2 跨層貫穿契約**：對應 `arch.md`「有多實作需求即遵循 `base.py`」的層級── `InputSource` / `Perception` / `Action` / `Adaptor` 的 `base.py` Protocol ；共用 `start()` / `stop()` 、in-flight worker 的 `abort()` / `force_abort()` 、 `ForceAbortReport` 與 `Fact + task done` 雙完成契約
* **Ch 2a core HAL Protocol** ：`core/audio` / `core/display` / `core/camera` / `core/gpio` 的具體方法簽名、資料格式（PCM frame、pixel buffer 等）、null impl 語意（ `core/leds` 目錄不落地，見 `arch.md` §8.1 / AR-Impl-4 ；`core/gpio` 為純登錄型 HAL 例外，不提供 null，見 `arch.md` §6.8 / ARV-7 ）
* **Ch 2b worker 契約與 library adapter** ：每個 worker 種類的完整實作契約── `listen` / `read` / `look` 內的 ASR / 讀取 / 視覺 library adapter 介面；`speak` 內的 TTS library adapter ；`cognition` 內的 LLM engine（LiteRT-LM）adapter ；`tool registry` ；P5 降級策略；`worker execution container`（含 blocking backend 的 child process 隔離）
* **Ch 5 / Ch 6 責任分界**：Ch 5 Resource Manager 負責啟動、 `capability_of()` 查詢、recovery rebuild 與 recovery barrier ；Ch 6 Cancel 負責三級收斂機制本身（Level 1 / 2 / 3 定義、四條觸發路徑差異、per-worker 契約義務）── 兩章共享 `force_abort()` 動詞但不重複定義

---

## 相關導覽

* **Designer 職責 / 文件分工 / 工作流程 / 同步原則**： [roles/designer.md](roles/designer.md)
* **章節動態進度與跨章 gate** ： [reviews/impl_progress.md](reviews/impl_progress.md)
* **Display 內容與 UX profile** ： [display_spec.md](display_spec.md)
* **ASR / TTS / LLM / Vision / wake-word 選型 gate** ： [model_spec.md](model_spec.md)
* **跨 process child wire schema** ： [protocol.md](protocol.md)
* **設計與審查流程**： [reviews/README.md](reviews/README.md)
* **Reviewer 工作原則與新輪次紀錄**： [reviews/README.md](reviews/README.md) §3（既有 `history/implement_reviewer.md` 與 `history/impl_review_*` 僅保留歷史）
* **既有 Architect 審查紀錄**： `reviews/AR-Review-*.md`（新輪次見 [reviews/README.md](reviews/README.md) §1）
