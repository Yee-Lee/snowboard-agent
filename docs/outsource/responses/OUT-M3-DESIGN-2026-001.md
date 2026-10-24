# Response: OUT-M3-DESIGN-2026-001

* **Handoff ID**: `PM-OUT-260806-005-gpio-button-semantics`
* **Finding ID**: `OUT-M3-DESIGN-2026-001`
* **Status**: `Resolved`
* **Comparison baseline**: `7bc694d3edd2d06657c1081cb5f12a4dae13b554`
* **Delivery commit SHA**: TBD（提交後更新）
* **Architecture change**: `Yes`

---

## 逐項 ACK

本 response 逐項確認 PM-OUT-260806-005 §「必須固定的架構語意」六條：

| # | 條文 | 確認 |
|---|---|---|
| 1 | 裝置只有一個 conversation button；按法分類由 `input_events/button` 負責，GPIO HAL 只提供低階能力 | ✅ 已於 arch.md §5.4、ch02_contracts.md §2.2 固定 |
| 2 | App READY 且 IDLE 時短按 → WAKE，首 turn `[listen]` | ✅ 已於 arch.md §4.4、§4.5 固定 |
| 3 | WAKE / listen / think / speak / rest 時短按 → `InterruptRequested`，乾淨返回 IDLE | ✅ 已於 arch.md §4.5 wake 類 Signal 雙態行為、ch04 §5.1 固定 |
| 4 | 任何狀態長按 → graceful App shutdown（`ShutdownRequested`），exit code 正常；不觸發 reboot / poweroff | ✅ 已於 arch.md §3.3、§5.4、ch02_contracts.md §2.2 固定 |
| 5 | `recovery` / `error` 時短按：recovery 進行中 → 忽略；recovery 已完成或無 recovery → 清錯誤狀態，直接進 WAKE | ✅ 已於 arch.md §4.7、ch04 §5.1 固定（與 PM 確認：recovery 進行中忽略，比強制進 WAKE 更安全） |
| 6 | 短按 / 長按門檻（≥ 50 ms / ≥ 1500 ms）固定於 arch.md，`input_events/button` 只對上層輸出分類結果 | ✅ 已於 arch.md §5.4、ch10 ButtonInputConfig 固定 |

---

## Requirement Traceability

| Req ID | 行為 | arch.md | implement | milestone |
|---|---|---|---|---|
| **BTN-001** | IDLE 短按 → WAKE + `[listen]` | §4.4 wake mapping、§4.5 雙態行為 | ch04 §5.1 whitelist、§6.1 IDLE handler | M3.md §5.4 驗收第 4 點 |
| **BTN-002** | 非 IDLE session 中短按 → `InterruptRequested` 行為 | §4.5 雙態行為 | ch04 §5.1 drop rule | M3.md §5.4 驗收第 4 點 |
| **BTN-003** | 長按任意狀態 → `ShutdownRequested`，exit 0 | §3.3 Signals、§5.4 GPIO 分流 | ch02_contracts §2.2 InputSource 表 | M3.md §5.4 驗收第 4 點 |
| **BTN-004** | ERROR + recovery 進行中 → 忽略短按 | §4.7 若已在 ERROR | ch04 §5.1 ERROR ButtonPressed rule | M3.md §5.4 驗收第 4 點 |
| **BTN-005** | ERROR + recovery 完成或無 recovery → 短按直接進 WAKE | §4.7 若已在 ERROR | ch04 §5.1 ERROR ButtonPressed rule | M3.md §5.4 驗收第 4 點 |
| **BTN-006** | 短按門檻 ≥ 50 ms；長按門檻 ≥ 1500 ms；config 可覆寫 | §5.4 GPIO 分流 | ch10 ButtonInputConfig | — |
| **BTN-007** | 按法分類由 `input_events/button` 負責；GPIO HAL 只提供 pin/edge/duration | §5.4 GPIO 分流 | ch02a §2a.5 GPIO Protocol、ch02_contracts §2.2 | — |

---

## 修改文件定位

| 文件 | 章節 / 位置 | 修改摘要 |
|---|---|---|
| `docs/arch.md` | §3.3 Signals | `ButtonPressed` 加語意說明；`ShutdownRequested` 標注為長按產生 |
| `docs/arch.md` | §4.4 wake mapping | `ButtonPressed` 限定為 IDLE 下，加「短按」說明 |
| `docs/arch.md` | §4.5 wake 類 Signal 雙態行為 | 細化 `ButtonPressed` 四種狀態下行為（IDLE / 非 IDLE session / ERROR recovery 中 / ERROR recovery 完成） |
| `docs/arch.md` | §4.7 若已在 ERROR | 補充 `ButtonPressed` 在 ERROR 狀態的兩條處理規則 |
| `docs/arch.md` | §5.4 GPIO 分流 | 範例改為新語意（長按 → `ShutdownRequested`）；補充按法分類責任與門檻預設值 |
| `docs/implement/ch02_contracts.md` | §2.2 InputSource 事件對照表 | button 欄位改為短按 `ButtonPressed` / 長按 `ShutdownRequested` |
| `docs/implement/ch02a_core_hal.md` | §2a.5 GPIO 設計要點 | 長按門檻說明更新 |
| `docs/implement/ch04_state_manager.md` | §5.1 公共事件白名單 | ERROR 狀態加入 `ButtonPressed`；更新各狀態 drop/ignore 規則 |
| `docs/implement/ch10_config.md` | ButtonInputConfig | 新增 `short_press_min_ms`（50）、`long_press_min_ms`（1500）欄位 |
| `docs/milestones/M3.md` | §5.4 可重複驗收 | 新增第 4 點 Button 語意驗收項（四條場景） |

---

## 未完成事項 / 待 PM 或內部決策

- **App 未執行時的長按啟動**：由外部 launcher 處理，不屬 Snowboard App 本輪開發範圍，已於 arch.md §5.4 聲明；具體 launcher 實作不在本文件定義。
- **`docs/implement/` 其他章節**（ch01_events.md、ch07、ch09 等）未修改：檢查後確認這些章節未對 button 行為作獨立規定，無需同步修訂。

---

## Architecture Change 聲明

**Architecture change: Yes**

修改涉及 §3.3 Signal 語意定義、§4.5 / §4.7 狀態機行為矩陣、§5.4 GPIO 分流範例，屬架構行為改變。但 `ButtonPressed(button_id, duration_ms)` dataclass 定義不變；`InterruptRequested` / `ShutdownRequested` dataclass 不變；僅修改了「哪個模組在何時 publish 哪個 Signal」的語意責任歸屬。
