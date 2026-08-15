---
handoff_id: "PM-OUT-260814-012-alpha-beta-product-convergence"
finding_id: "OUT-ROADMAP-2026-001"
delivery_id: "DELIVERY-ALPHA-BETA-ROADMAP-001"
status: "Delivered"
date: "2026-08-15"
owner: "Designer"
---

# DELIVERY-ALPHA-BETA-ROADMAP-001

## 1. Comparison Baseline

| 項目 | 修訂前 | 修訂後 |
| :--- | :--- | :--- |
| 依賴鏈 | M3→M4→M5→M6→M7（功能串行） | M3→M4→**ALPHA**→M5→M6→M7→**BETA** |
| M5 entry baseline | M4 Accepted exact SHA | **ALPHA Accepted exact SHA** |
| 產品成熟度 gate | 無 | ALPHA（M4後）、BETA（M7後） |

## 2. Candidate SHA（規劃 commit）

本輪為 Design Ready 規劃，不提前建立 Developer 工作包或實作 Alpha / Beta code。  
Candidate SHA 待本輪文件修訂 commit 後由 PM 以 branch / 完整 HEAD SHA 通知。

## 3. Architecture Change Declaration

**Architecture change: No**

| 項目 | 聲明 | 理由 |
| :--- | :--- | :--- |
| systemd / supervisor | 不引入 | 操作部署外部獨立處理，不在 Core 文件範圍 |
| deployment / persistent config | 不引入 | ALPHA 固定化只記錄文件與 manifest，不實作新部署機制 |
| process ownership | 無變更 | 沿用 `arch.md` 現有定義，ALPHA / BETA 不新增 process 角色 |
| update / rollback | 不引入 | 外部獨立處理 |

## 4. 修改定位（逐項）

| 文件 | 修改說明 |
| :--- | :--- |
| `docs/milestones/ALPHA.md` | **新建**：ALPHA scope（Voice-only）、排除項目、entry/exit gate、Requirement mapping（M4→ALPHA trace）、test spec gate（Tester 建立 `test_spec_ALPHA.md`，Designer TR_spec_ALPHA_I 簽核）、evidence index |
| `docs/milestones/BETA.md` | **新建**：BETA scope（M4~M7 regression）、排除項目（≠ GA）、entry/exit gate、Requirement mapping（M7→BETA trace）、test spec gate（Tester 建立 `test_spec_BETA.md`，Designer TR_spec_BETA_I 簽核）、evidence index |
| `docs/milestone.md` §1.3 | 依賴樹插入 ALPHA / BETA gate；加入「M4 Accepted ≠ ALPHA Accepted」聲明 |
| `docs/milestone.md` §2 | 階段總覽表新增 ALPHA / BETA 兩列；M5 欄位更新為引用 ALPHA Accepted exact SHA |
| `docs/milestones/M4.md` §6.2 | Gate table 新增 ALPHA entry 與 M5 entry 說明（ALPHA Accepted 為 M5 entry 前提） |
| `docs/milestones/M5.md` §7.2 | entry 依賴從「M4 exact SHA」改為「ALPHA Accepted exact SHA」 |
| `docs/milestones/M7.md` §9.2 | 新增 BETA entry 說明（M7 Accepted ≠ BETA Accepted） |
| `docs/reviews/milestone_progress.md` | 新增 ALPHA / BETA Gate Forward Planning 區段（四列狀態 + Architecture Change Declaration） |

## 5. 文件檢查結果

* ALPHA / BETA 分開記錄，不以 M4 / M7 功能通過推定產品 gate 通過 ✅
* M5 entry 依賴已改為 `ALPHA Accepted exact SHA` ✅
* systemd / deployment 明確排除（外部獨立）；Architecture change: No 已逐項聲明 ✅
* ALPHA / BETA 各自設有 Tester test spec gate（TR_spec_ALPHA_I / TR_spec_BETA_I），走完整五階段管線 ✅
* 本輪只做 Design Ready 規劃，未提前建立 Developer 工作包或實作 code ✅
* `BETA ≠ GA / production release` 已明確記入 BETA.md 排除項目 ✅

## 6. Requirement / Future Test ID Trace

### M4 → ALPHA

| Requirement | Future Test ID |
| :--- | :--- |
| Voice-only 離線完整 session | `ALPHA-T-001` |
| 重複 session / soak | `ALPHA-T-002` |
| failure / recovery / shutdown | `ALPHA-T-003` |
| resource / thermal budget | `ALPHA-T-004` |
| log privacy（不含 transcript / prompt / raw output）| `ALPHA-T-005` |
| Manifest 全組件固定 | `ALPHA-T-006` |
| Session Display privacy mapping | `ALPHA-T-007` |

### ALPHA → M5

M5 entry 唯一依賴：`ALPHA Accepted exact SHA`（見 `docs/milestones/M5.md` §7.2）

### M7 → BETA

| Requirement | Future Test ID |
| :--- | :--- |
| M4 ~ M7 regression 全數通過（同一 SHA）| `BETA-T-001` |
| M5 MQTT / tool regression | `BETA-T-002` |
| M6 wake / Vision regression | `BETA-T-003` |
| M7 Display UX regression + human checklist | `BETA-T-004` |
| 長時間 soak：無 orphan child / 資源洩漏 | `BETA-T-005` |
| log privacy（全 M4 ~ M7 範圍）| `BETA-T-006` |
| Beta manifest 全組件固定 | `BETA-T-007` |

## 7. 尚待決定的門檻（Open Items）

| 項目 | Owner | 說明 |
| :--- | :--- | :--- |
| ALPHA soak session 數量與 thermal 門檻 | Designer + User | ALPHA.md 僅列佔位，Tester 建立 test spec 時需與 User 確認具體數值 |
| BETA regression 的 scope 是否包含 Pi-only 硬體 checklist 的全部項目 | Tester + Designer | test_spec_BETA.md 建立時確認 |
| Beta manifest 路徑 | Designer | 建議 `docs/milestones/BETA.md` Evidence 欄填入；若採其他路徑，response 說明唯一權威位置 |

## 8. 未完成事項

* `test_spec_ALPHA.md`：待 ALPHA Design Ready 後由 Tester 建立
* `test_spec_BETA.md`：待 BETA Design Ready 後由 Tester 建立
* ALPHA / BETA 的 Developer 工作包：待各 gate Design Ready 後建立
