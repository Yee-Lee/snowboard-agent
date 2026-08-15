# PM Handoff (產品團隊需求與反饋) 管理總覽

本目錄放置產品團隊（PM Team）提供的產品規劃方向、需求反饋與建議。

---

## 1. 進行中 / 待處理 Handoffs (Active Handoffs)

| Handoff ID | 標題 / 範疇 | 關聯 Feedback ID | 對應 Milestone | 狀態 | 對應 Response 路徑 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [`PM-OUT-260805-002-m3-m4-poc-planning`](PM-OUT-260805-002-m3-m4-poc-planning/brief.md) | Audio / Display / LLM 設計與 POC 接合準備 | `OUT-FB-2026-002-R1` | M3 / M4 | **Resolved（已完成移交）**：各領域責任已移交 008/010/011，Response 已產出；可歸檔 | [`OUT-FB-2026-002-R1.md`](../responses/OUT-FB-2026-002-R1.md) |
| [`PM-OUT-260811-008-m3-display-spec-design`](PM-OUT-260811-008-m3-display-spec-design/brief.md) | M3 Display Spec 與 Design Ready | `OUT-M3-DISPLAY-SPEC-2026-001` | M3 / M4c / M7 | **Resolved**：Display POC Accepted；spec / mock / trace 已收斂，Response 已完成；可歸檔 | [`OUT-M3-DISPLAY-SPEC-2026-001.md`](../responses/OUT-M3-DISPLAY-SPEC-2026-001.md) |
| [`PM-OUT-260813-009-m3-display-test-spec-feedback`](PM-OUT-260813-009-m3-display-test-spec-feedback/brief.md) | M3 Display / Test Spec 收斂 | `OUT-M3-REVIEW-2026-001` | M3 / M4c / M7 | **Resolved**：四項 finding 已修訂，Response 已完成；可歸檔 | [`OUT-M3-REVIEW-2026-001.md`](../responses/OUT-M3-REVIEW-2026-001.md) |
| [`PM-OUT-260814-010-m4a-audio-poc-contract-gate`](PM-OUT-260814-010-m4a-audio-poc-contract-gate/brief.md) | M4a Audio POC Contract / Gate 協調 | `OUT-M4A-2026-001` | M4 / M4a | **Resolved**：Contract `DELIVERY-AUDIO-POC-M4A-CONTRACT-001` 已產出；Response `OUT-M4A-2026-001` 已完成；可歸檔 | [`OUT-M4A-2026-001.md`](../responses/OUT-M4A-2026-001.md) |
| [`PM-OUT-260814-011-m4b-llm-poc-contract-gate`](PM-OUT-260814-011-m4b-llm-poc-contract-gate/brief.md) | M4b LLM POC Contract / 002 結案移交 | `OUT-M4B-2026-001` | M4 / M4b | **Resolved**：Contract `DELIVERY-LLM-POC-M4B-CONTRACT-001` 已產出；Response `OUT-M4B-2026-001` 已完成；可歸檔 | [`OUT-M4B-2026-001.md`](../responses/OUT-M4B-2026-001.md) |
| [`PM-OUT-260814-012-alpha-beta-product-convergence`](PM-OUT-260814-012-alpha-beta-product-convergence/brief.md) | M4後ALPHA / M7後BETA產品收斂Gate | `OUT-ROADMAP-2026-001` | Roadmap / M4+ | **Ready for PM**：規劃 M4→ALPHA 與 M7→BETA 產品收斂 Gate | 待產出 |

---

### Milestone gate 判讀（Core Team，2026-08-15）

| Gate | 目前狀態 | 外部 contract 影響 |
| :--- | :--- | :--- |
| **M3 POC contract readiness** | **Ready** | Audio Accepted with Conditions；Display v0.3 已由 `DELIVERY-005-poc_display-m3-v0.3-ack` 接受為 design input；LLM 不在 M3 scope。 |
| **M3 開發進場** | **Development Ready / Approved** | PM-009 技術 finding 已收斂，`TR_spec_M3_I` coverage sign-off Resolved；Developer 可建立工作包後實作。 |
| **M3 最終 delivery / acceptance** | **Pending** | External design/test delivery尚待 user-approved exact-SHA commit；產品實作、Audio P1/P2 與所有 RPI-NATIVE cards仍待完成。 |
| **M4 / M4b 開發進場** | **Contract Issued / Blocked by POC Gate 1** | Contract `DELIVERY-LLM-POC-M4B-CONTRACT-001` 已發出；待 PM relay 轉交 LLM POC Team 並回交 Gate 1 candidate 清單。 |
| **本 PM handoff 結案** | **Resolved for 002/008/009/010/011** | 002、008、009、010、011 之 Core 端 Response 均已完成產出，各項責任已全數明確對接。 |

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
├── PM-OUT-260805-002-m3-m4-poc-planning/       # [Resolved/Archive-ready] M3/M4 POC 規劃
├── PM-OUT-260811-008-m3-display-spec-design/    # [Resolved/Archive-ready] Display Spec / Design Ready
├── PM-OUT-260813-009-m3-display-test-spec-feedback/ # [Resolved/Archive-ready] M3 design / test-spec feedback
├── PM-OUT-260814-010-m4a-audio-poc-contract-gate/   # [Resolved/Archive-ready] M4a Audio POC Contract
├── PM-OUT-260814-011-m4b-llm-poc-contract-gate/     # [Resolved/Archive-ready] M4b LLM POC Contract
└── PM-OUT-260814-012-alpha-beta-product-convergence/# [Active] ALPHA / BETA Roadmap
```
