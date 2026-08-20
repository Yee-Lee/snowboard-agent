# PM Handoff (產品團隊需求與反饋) 管理總覽

本目錄放置產品團隊（PM Team）提供的產品規劃方向、需求反饋與建議。

---

## 1. 進行中 / 待處理 Handoffs (Active Handoffs)

| Handoff ID | 標題 / 範疇 | 關聯 Feedback ID | 對應 Milestone | 狀態 | 對應 Response 路徑 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| — | 目前無 Open task / request | — | — | — | — |

---

### Milestone gate 判讀（Core Team，2026-08-20）

| Gate | 目前狀態 | 外部 contract 影響 |
| :--- | :--- | :--- |
| **M3 POC contract readiness** | **Ready** | Audio Accepted with Conditions；Display v0.3 已由 `DELIVERY-005-poc_display-m3-v0.3-ack` 接受為 design input；LLM 不在 M3 scope。 |
| **M3 開發進場** | **Development Ready / Approved** | PM-009 技術 finding 已收斂，`TR_spec_M3_I` coverage sign-off Resolved；Developer 可建立工作包後實作。 |
| **M3 最終 delivery / acceptance** | **Accepted** | Fixed implementation SHA `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`；USER核准transition direct review與免再次freeze；CR_M3_I及20張target cards已收斂。 |
| **M4a / M4b POC進場** | **M4a G1B focused scope accepted / M4b Gate 0 R2 accepted** | Audio `756ded69...`已完成focused intake。LLM `0d415d1...`已由`DELIVERY-LLM-POC-M4B-GATE0-R2-ACK-001`接受Gate 0 R2；Gate 1平台分流已核准修訂packet，但真實x86 / Pi執行仍未授權。017已收斂為Core Tester可在實測階段重跑的`M4-REG-001`，不新增Gate或POC combined執行責任。 |
| **歸檔狀態** | **目前所有已收件要求均已裁決並歸檔** | Audio Option A已由`DELIVERY-AUDIO-POC-M3-P4-ACK-004`接受；PM-014已由PM-018在`f87c5e6`收斂；LLM平台變更已核准packet revision，但Gate 1真實執行仍未授權。 |

2026-08-20 補充：PM-019 已以 `DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002`
授權 whisper.cpp small Q8_0 primary 與受條件 Q5_1 fallback；本 ACK 不等於
Gate 2A PASS。PM-019 本身的 ACK request 已完成，後續執行由 ACK-002 / Gate 2A
追蹤。

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
| [`PM-OUT-260805-002-m3-m4-poc-planning`](history/PM-OUT-260805-002-m3-m4-poc-planning/brief.md) | Audio / Display / LLM 設計與 POC 接合準備 | `OUT-FB-2026-002-R1` | **Resolved** | Response: [`OUT-FB-2026-002-R1.md`](../responses/OUT-FB-2026-002-R1.md) |
| [`PM-OUT-260811-008-m3-display-spec-design`](history/PM-OUT-260811-008-m3-display-spec-design/brief.md) | M3 Display Spec 與 Design Ready | `OUT-M3-DISPLAY-SPEC-2026-001` | **Resolved** | Response: [`OUT-M3-DISPLAY-SPEC-2026-001.md`](../responses/OUT-M3-DISPLAY-SPEC-2026-001.md) |
| [`PM-OUT-260813-009-m3-display-test-spec-feedback`](history/PM-OUT-260813-009-m3-display-test-spec-feedback/brief.md) | M3 Display / Test Spec 收斂 | `OUT-M3-REVIEW-2026-001` | **Resolved** | Response: [`OUT-M3-REVIEW-2026-001.md`](../responses/OUT-M3-REVIEW-2026-001.md) |
| [`PM-OUT-260817-013-m3-morning-retest-audit`](history/PM-OUT-260817-013-m3-morning-retest-audit/brief.md) | M3早晨重測與zero-debounce稽核 | `OUT-M3-AUDIT-2026-001` | **Resolved — fixed SHA accepted** | Response: [`OUT-M3-AUDIT-2026-001.md`](../responses/OUT-M3-AUDIT-2026-001.md) |
| [`PM-OUT-260814-010-m4a-audio-poc-contract-gate`](history/PM-OUT-260814-010-m4a-audio-poc-contract-gate/brief.md) | M4a Audio POC Contract / Gate 協調 | `OUT-M4A-2026-001` | **Resolved** | Response: [`OUT-M4A-2026-001.md`](../responses/OUT-M4A-2026-001.md) |
| [`PM-OUT-260814-011-m4b-llm-poc-contract-gate`](history/PM-OUT-260814-011-m4b-llm-poc-contract-gate/brief.md) | M4b LLM POC Contract / 002 結案移交 | `OUT-M4B-2026-001` | **Resolved** | Response: [`OUT-M4B-2026-001.md`](../responses/OUT-M4B-2026-001.md) |
| [`PM-OUT-260814-012-alpha-beta-product-convergence`](history/PM-OUT-260814-012-alpha-beta-product-convergence/brief.md) | M4後ALPHA / M7後BETA產品收斂Gate | `OUT-ROADMAP-2026-001` | **Resolved** | 待產出 |
| [`PM-OUT-260817-016-m4a-poc-core-evidence-handoff`](history/PM-OUT-260817-016-m4a-poc-core-evidence-handoff/brief.md) | M4a Audio POC evidence inheritance與產品化交接 | `OUT-M4A-2026-002`～`005` | **Resolved — G1A durable intake complete** | Response: [`PM-OUT-260817-016-m4a-poc-core-evidence-handoff.md`](../responses/PM-OUT-260817-016-m4a-poc-core-evidence-handoff.md)；G1B: [`DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001.md`](../deliveries/DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001.md) |
| [`PM-OUT-260817-015-llm-poc-contract-plan-review`](history/PM-OUT-260817-015-llm-poc-contract-plan-review/brief.md) | M4b LLM POC contract與執行規劃補強 | `OUT-M4B-2026-002`～`007` | **Resolved — Gate 0 R2 accepted at `0d415d1...`** | Response: [`PM-OUT-260817-015-llm-poc-contract-plan-review.md`](../responses/PM-OUT-260817-015-llm-poc-contract-plan-review.md)；ACK: [`DELIVERY-LLM-POC-M4B-GATE0-R2-ACK-001.md`](../deliveries/DELIVERY-LLM-POC-M4B-GATE0-R2-ACK-001.md) |
| [`PM-OUT-260818-017-m4b-early-memory-preflight`](history/PM-OUT-260818-017-m4b-early-memory-preflight/brief.md) | M4b Pi 5 4GB early memory preflight與跨POC資源預算 | `OUT-M4B-2026-007` | **Resolved — post-POC Core integration preflight implemented** | Response: [`PM-OUT-260818-017-m4b-early-memory-preflight.md`](../responses/PM-OUT-260818-017-m4b-early-memory-preflight.md)；Test: [`test_spec_M4.md`](../../test_spec/test_spec_M4.md) |
| [`PM-OUT-260818-018-m4-portable-gate-cost-correction`](history/PM-OUT-260818-018-m4-portable-gate-cost-correction/brief.md) | M4 candidate gate簡化與執行成本修正 | `OUT-PROCESS-2026-001` | **Resolved — implemented at `f87c5e6`** | 無需response；實作與流程文件已收斂至minimal gate |
| [`PM-OUT-260817-014-local-hardware-test-gate-reform`](history/PM-OUT-260817-014-local-hardware-test-gate-reform/brief.md) | 本機／實體測試順序與candidate gate改革 | `OUT-PROCESS-2026-001` | **Resolved / superseded by PM-018** | Original response：[`OUT-PROCESS-2026-001.md`](../responses/OUT-PROCESS-2026-001.md)；最終minimal gate依PM-018於`f87c5e6`收斂 |
| [`DELIVERY-AUDIO-POC-M3-OPTION-A-VALIDATION-001`](history/DELIVERY-AUDIO-POC-M3-OPTION-A-VALIDATION-001.md) | Audio POC M3 Option A P4-A01～A10完整回交 | 無 | **Resolved — Option A final selection accepted** | ACK：[`DELIVERY-AUDIO-POC-M3-P4-ACK-004.md`](../deliveries/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) |
| [`DELIVERY-002-PM-LLM-POC-GATE1-PLATFORM-CHANGE-REQUEST`](history/DELIVERY-002-PM-LLM-POC-GATE1-PLATFORM-CHANGE-REQUEST.md) | M4b Gate 1 x86完整初篩＋產品Pi compatibility平台分流 | 無 | **Resolved — packet revision authorized / real execution not authorized** | Contract：[`DELIVERY-LLM-POC-M4B-CONTRACT-001.md`](../deliveries/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)；ACK已直接交付POC incoming |
| [`CR-AUDIO-M3-P4-REPRO-002.md`](history/CR-AUDIO-M3-P4-REPRO-002.md) | Restore reproducible P4-A10 dependency artifacts | 無 | **Resolved** | Response: [`RESP-AUDIO-M3-P4-REPRO-002.md`](../responses/RESP-AUDIO-M3-P4-REPRO-002.md) |
| [`PM-OUT-260819-019-audio-asr-recovery-gate`](history/PM-OUT-260819-019-audio-asr-recovery-gate/brief.md) | whisper.cpp small Q8_0/Q5_1 ASR recovery與real-time hard gate | `CR-AUDIO-M4A-G1B-ASR-SCOPE-001` | **Resolved — recovery rows ACKed** | ACK: [`DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002.md`](../deliveries/DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002.md) |

---

## 3. 目錄結構規範

```text
docs/outsource/pm_handoff/
├── README.md                                  # 本管理總覽表
└── history/                                   # 已結案 / 已取代 Hand-offs 歸檔目錄
    ├── CR-AUDIO-M3-P4-REPRO-002.md
    ├── DELIVERY-AUDIO-POC-M3-OPTION-A-VALIDATION-001.md
    ├── DELIVERY-002-PM-LLM-POC-GATE1-PLATFORM-CHANGE-REQUEST.md
    ├── PM-OUT-260805-001-m1-carryover-feedback/
    ├── PM-OUT-260805-002-m3-m4-poc-planning/
    ├── PM-OUT-260806-003-m1-test-platform-scope/
    ├── PM-OUT-260806-004-m3-target-device-test-ack/
    ├── PM-OUT-260806-005-gpio-button-semantics/
    ├── PM-OUT-260807-006-m2-tester-verification/
    ├── PM-OUT-260811-008-m3-display-spec-design/
    ├── PM-OUT-260813-009-m3-display-test-spec-feedback/
    ├── PM-OUT-260814-010-m4a-audio-poc-contract-gate/
    ├── PM-OUT-260814-011-m4b-llm-poc-contract-gate/
    ├── PM-OUT-260814-012-alpha-beta-product-convergence/
    ├── PM-OUT-260817-015-llm-poc-contract-plan-review/
    ├── PM-OUT-260817-016-m4a-poc-core-evidence-handoff/
    ├── PM-OUT-260817-013-m3-morning-retest-audit/
    ├── PM-OUT-260817-014-local-hardware-test-gate-reform/
    ├── PM-OUT-260818-017-m4b-early-memory-preflight/
    ├── PM-OUT-260818-018-m4-portable-gate-cost-correction/
    └── PM-OUT-260819-019-audio-asr-recovery-gate/
```
