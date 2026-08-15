---
handoff_id: "PM-OUT-260814-012-alpha-beta-product-convergence"
finding_id: "OUT-ROADMAP-2026-001"
status: "Resolved"
date: "2026-08-15"
owner: "Designer"
---

# Response: OUT-ROADMAP-2026-001

## 結論

Core Team 已完成 `PM-OUT-260814-012` 必做修訂的全部 Design Ready 規劃。  
依賴鏈已更新為 `M3 → M4 → ALPHA → M5 → M6 → M7 → BETA`；ALPHA / BETA 各自分開記錄，M4 / M7 功能通過不推定產品 gate 通過。

Finding `OUT-ROADMAP-2026-001` 狀態：**Resolved**

---

## 必做修訂回應（逐項）

### ✅ 依賴鏈更新
`milestone.md` §1.3 已更新為 `M3 → M4 → ALPHA → M5 → M6 → M7 → BETA`，含「ALPHA / BETA 為產品成熟度 Gate，不是功能 milestone」聲明。

### ✅ ALPHA scope 固定
`docs/milestones/ALPHA.md` 新建：
- 納入：Button / Listen / ASR / Reasoner / LLM / Speak / TTS / M4c Session Display / 離線操作
- 排除：MQTT / external message / 實際 tool、voice wake / Vision、M7 正式動畫 / assets、systemd / deployment
- 固定化要求：hardware / config / model / runtime / dependency / license / checksum / manifest / privacy

### ✅ ALPHA 產品化可重現要求
`ALPHA.md` 已定義：重複 session / soak、failure / recovery / shutdown、resource / thermal、privacy、manifest、known limits 及 evidence index。

### ✅ M5 引用 ALPHA Accepted exact SHA
`docs/milestones/M5.md` §7.2 已改為 `ALPHA Accepted exact SHA`；`docs/milestones/M4.md` §6.2 gate table 已新增 M5 entry 規則。

### ✅ BETA scope 固定
`docs/milestones/BETA.md` 新建：
- 在同一 Beta 候選 SHA 重跑 M4 ~ M7 regression
- 涵蓋 M5 external message / tool、M6 wake / Vision、M7 完整 Display UX
- 長時間穩定、診斷、artifact / config / model / asset inventory 及 Beta manifest
- 明確聲明 `BETA ≠ GA / production release`

### ✅ M4 Accepted 與 ALPHA Accepted 分開記錄
`docs/milestones/M4.md`、`docs/milestones/ALPHA.md`、`docs/reviews/milestone_progress.md` 均分開列記，不以功能通過推定產品 gate。

### ✅ M7 Accepted 與 BETA Accepted 分開記錄
`docs/milestones/M7.md`、`docs/milestones/BETA.md`、`docs/reviews/milestone_progress.md` 均分開列記。

### ✅ Designer 定義 scope 與 Requirement mapping；Tester 在各 gate Design Ready 後建立 test spec
- ALPHA.md：Requirement mapping（ALPHA-T-001 ~ ALPHA-T-007）、test spec gate（`TR_spec_ALPHA_I`）
- BETA.md：Requirement mapping（BETA-T-001 ~ BETA-T-007）、test spec gate（`TR_spec_BETA_I`）

### ✅ Architecture change 聲明
**Architecture change: No**
- systemd / supervisor：不引入（外部獨立處理）
- deployment / persistent config：不引入（只記錄文件與 manifest）
- process ownership：無變更（沿用 arch.md）
- update / rollback：不引入（外部獨立處理）

---

## 權威文件位置

| 文件 | 路徑 |
| :--- | :--- |
| ALPHA 規劃 | `docs/milestones/ALPHA.md` |
| BETA 規劃 | `docs/milestones/BETA.md` |
| 里程碑總覽（含依賴鏈）| `docs/milestone.md` |
| Gate 進度狀態 | `docs/reviews/milestone_progress.md` |
| Delivery | `docs/outsource/deliveries/DELIVERY-ALPHA-BETA-ROADMAP-001.md` |

---

## PM 後續動作

PM 拉回最新 repo 後，以 branch / 完整 HEAD SHA 通知 Internal Designer 進行 intake。  
本輪 Core 不直接寄送、上傳或修改 Core repo 以外的任何管道。
