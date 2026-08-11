# PM Handoff (產品團隊需求與反饋) 管理總覽

本目錄放置產品團隊（PM Team）提供的產品規劃方向、需求反饋與建議。

---

## 1. 進行中 / 待處理 Handoffs (Active Handoffs)

| Handoff ID | 標題 / 範疇 | 關聯 Feedback ID | 對應 Milestone | 狀態 | 對應 Response 路徑 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [`PM-OUT-260805-002-m3-m4-poc-planning`](PM-OUT-260805-002-m3-m4-poc-planning/brief.md) | Audio / Display / LLM 設計與 POC 接合準備 | `OUT-FB-2026-002-R1` | M3 / M4 | **Blocked（整體 handoff）**：M3 等 Display v0.3 收斂；Audio 已 Accepted with Conditions；LLM 不阻擋 M3，改列 M4b entry blocker | `docs/outsource/responses/OUT-FB-2026-002-R1.md` (尚未產出) |

---

### Milestone gate 判讀（Core Team，2026-08-09）

| Gate | 目前狀態 | 外部 contract 影響 |
| :--- | :--- | :--- |
| **M3 POC contract readiness** | **Blocked by Display only** | Audio contract 已可作 M3 設計／開發輸入；Display v0.2 經 `DELIVERY-004-poc_display-m3-v0.2-review` 判定 `Needs Revision`，須先完成 D1–D5；LLM 不在 M3 scope。 |
| **M3 開發進場** | **Not Ready** | 採單一整合 gate，不先開 Audio-only 或其他部分實作。Display contract 收斂後，Core 仍須完成 `display_spec.md` Baseline、M3 Design Ready、test spec 簽核與 Developer 工作包，才正式開始 M3；此順序不依賴 LLM contract。 |
| **M3 最終 delivery / acceptance** | **Pending** | Audio contract 的 P1/P2 條件及 Display hardware/evidence contract 必須在 M3 delivery SHA 前完成；LLM 仍非此 gate。 |
| **M4 / M4b 開發進場** | **Blocked by LLM/model gate** | 必須先有 `model_spec.md` 的 M4 baseline（含 LiteRT-LM artifact、版本、checksum、license、Pi benchmark）及已 review 的 `docs/protocol.md`；目前尚未收到 LLM POC contract。 |
| **本 PM handoff 結案** | **Blocked** | 本 handoff 同時涵蓋 M3 與 M4，須完成 Display 收斂、LLM POC intake、requirement mapping 與 `OUT-FB-2026-002-R1` response；其整體 Blocked 不代表 M3 必須等待 LLM。 |

判讀依據：`docs/milestones/M3.md` §5.3 明確排除真實 ASR / TTS / LLM；`docs/milestones/M4.md` §6.2 才將 model baseline 與 LiteRT-LM child protocol 列為進場相依。

---

## 2. 已結案 / 歸檔 Handoffs (Completed & History Handoffs)

結案或已被取代之 PM Handoff 歸檔於 [`history/`](history/) 目錄：

| Handoff ID | 標題 / 範疇 | 原 Legacy ID | 結案狀態 | 回覆 / 交付對照 |
| :--- | :--- | :--- | :--- | :--- |
| [`PM-OUT-260805-001-m1-carryover-feedback`](history/PM-OUT-260805-001-m1-carryover-feedback/brief.md) | M1 完成後 Carry-over Feedback | `PM-OUT-2026-001-R1` | **Superseded**（由 003 取代） | 被 `PM-OUT-260806-003` 取代並收斂 |
| [`PM-OUT-260806-003-m1-test-platform-scope`](history/PM-OUT-260806-003-m1-test-platform-scope/brief.md) | M1 測試平台矩陣與交付證據澄清 | `PM-OUT-2026-001-R2` | **Resolved**（全數驗收 PASS） | Response: [`CR-M1-II.md`](../responses/CR-M1-II.md) |
| [`PM-OUT-260806-004-m3-target-device-test-ack`](history/PM-OUT-260806-004-m3-target-device-test-ack/brief.md) | M3 目標裝置測試方式確認 | 無 | **Resolved**（已回覆 ACK） | Response: [`OUT-M3-TEST-2026-001.md`](../responses/OUT-M3-TEST-2026-001.md) |
| [`PM-OUT-260806-005-gpio-button-semantics`](history/PM-OUT-260806-005-gpio-button-semantics/brief.md) | M3 單一 GPIO Button 開發前設計 Gate | 無 | **Resolved**（設計已定稿） | Response: [`OUT-M3-DESIGN-2026-001.md`](../responses/OUT-M3-DESIGN-2026-001.md) |
| [`PM-OUT-260807-006-m2-tester-verification`](history/PM-OUT-260807-006-m2-tester-verification/brief.md) | M2 Tester 驗證與修復 | 無 | **Resolved**（003/004/005 已修復） | 無要求書面回覆 |

---

## 3. 目錄結構規範

```text
docs/outsource/pm_handoff/
├── README.md                                  # 本管理總覽表
├── history/                                   # 已結案 / 已取代 Hand-offs 歸檔目錄
│   ├── PM-OUT-260805-001-m1-carryover-feedback/
│   ├── PM-OUT-260806-003-m1-test-platform-scope/
│   ├── PM-OUT-260806-004-m3-target-device-test-ack/
│   ├── PM-OUT-260806-005-gpio-button-semantics/
│   └── PM-OUT-260807-006-m2-tester-verification/
└── PM-OUT-260805-002-m3-m4-poc-planning/       # [Active] M3/M4 POC 規劃
```
