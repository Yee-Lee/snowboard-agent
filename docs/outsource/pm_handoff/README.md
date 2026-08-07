# PM Handoff (產品團隊需求與反饋) 管理總覽

本目錄放置產品團隊（PM Team）提供的產品規劃方向、需求反饋與建議。

---

## 1. 進行中 / 待處理 Handoffs (Active Handoffs)

| Handoff ID | 標題 / 範疇 | 關聯 Feedback ID | 對應 Milestone | 狀態 | 對應 Response 路徑 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [`PM-OUT-260805-002-m3-m4-poc-planning`](PM-OUT-260805-002-m3-m4-poc-planning/brief.md) | Audio / Display / LLM 設計與 POC 接合準備 | `OUT-FB-2026-002-R1` | M3 / M4 | `Ready for PM` (待回覆) | `docs/outsource/responses/OUT-FB-2026-002-R1.md` |
| [`PM-OUT-260806-004-m3-target-device-test-ack`](PM-OUT-260806-004-m3-target-device-test-ack/brief.md) | M3 目標裝置測試方式確認 | `OUT-M3-TEST-2026-001` | M3 | `Ready for PM` (待 ACK) | `docs/outsource/responses/OUT-M3-TEST-2026-001.md` |
| [`PM-OUT-260806-005-gpio-button-semantics`](PM-OUT-260806-005-gpio-button-semantics/brief.md) | M3 單一 GPIO Button 開發前設計 Gate | `OUT-M3-DESIGN-2026-001` | M3 | `Ready for PM` (待 Design Gate) | `docs/outsource/responses/OUT-M3-DESIGN-2026-001.md` |

---

## 2. 已結案 / 歸檔 Handoffs (Completed & History Handoffs)

結案或已被取代之 PM Handoff 歸檔於 [`history/`](history/) 目錄：

| Handoff ID | 標題 / 範疇 | 原 Legacy ID | 結案狀態 | 回覆 / 交付對照 |
| :--- | :--- | :--- | :--- | :--- |
| [`PM-OUT-260805-001-m1-carryover-feedback`](history/PM-OUT-260805-001-m1-carryover-feedback/brief.md) | M1 完成後 Carry-over Feedback | `PM-OUT-2026-001-R1` | **Superseded**（由 003 取代） | 被 `PM-OUT-260806-003` 取代並收斂 |
| [`PM-OUT-260806-003-m1-test-platform-scope`](history/PM-OUT-260806-003-m1-test-platform-scope/brief.md) | M1 測試平台矩陣與交付證據澄清 | `PM-OUT-2026-001-R2` | **Resolved**（全數驗收 PASS） | Response: [`CR-M1-II.md`](../responses/CR-M1-II.md) |

---

## 3. 目錄結構規範

```text
docs/outsource/pm_handoff/
├── README.md                                  # 本管理總覽表
├── history/                                   # 已結案 / 已取代 Hand-offs 歸檔目錄
│   ├── PM-OUT-260805-001-m1-carryover-feedback/
│   └── PM-OUT-260806-003-m1-test-platform-scope/
├── PM-OUT-260805-002-m3-m4-poc-planning/       # [Active] M3/M4 POC 規劃
├── PM-OUT-260806-004-m3-target-device-test-ack/# [Active] M3 實體裝置測試 ACK
└── PM-OUT-260806-005-gpio-button-semantics/   # [Active] M3 GPIO Button 語音設計 Gate
```
