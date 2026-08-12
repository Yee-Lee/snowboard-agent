---
requestor: "Reviewer"
owner: "Designer"
status: "Resolved"
---

# 審查單：MR_review_II（Milestone 規劃審查 II）

## 審查目標

針對 Designer 新完成的 `docs/milestone.md`（M3–M7 細化版）、`docs/milestones/M3.md` – `M7.md` 分工與各 gate，審查規劃內部一致性、相依邏輯與可驗收性。以 `arch.md` 與 `implement/` 定稿契約為對齊基準。

審查基準版本：2026-08-12 快照

---

## Finding 清單

### 🔴 FIND-MR-01：M3 gate 表格「M3 Design Ready 前」Display 條件措辭缺少「排除 LLM POC」的正面宣告

**位置**：`docs/milestones/M3.md` §5.2.1 Checkpoint 表格，行「M3 Design Ready 前」

**問題**：

M3.md §5.1 排除項目已明確列「不等待 LLM POC contract 才開始或驗收 M3」，但 §5.2.1 的三欄 Checkpoint 表格「M3 Design Ready 前」一行中，Display 欄僅描述「必須取得可直接對齊 Ch 2a / Ch 8 / Ch 10 的 Accepted design input」，沒有正面宣告「LLM POC contract 不是此 gate 的 input 之一」。

與此同時，「放行規則」欄以「Designer 在 milestone_progress.md 記錄…整合 gate 結論」帶過，在 gate 本體內缺乏明確的排除聲明。這造成後續若 Display POC 遲延，有人可能誤解 gate 須等 LLM POC 一起收斂。

**契約依據**：`milestone.md` §1.3 & M3.md §5.3（排除項目）
**最低驗收條件**：在 §5.2.1「M3 Design Ready 前」Display 欄或「放行規則」欄明確補充「LLM POC contract 不在此 gate 範圍，不得列為 M3 Design Ready 阻擋條件」。

---

### 🔴 FIND-MR-02：M4 sub-gate M4c 的「Display POC 不重新定義產品內容」未說明 gate 責任歸屬

**位置**：`docs/milestones/M4.md` §6.2 Gate 表格，行「M4c Session Display」

**問題**：

M4c 放行條件包含「Display POC 不重新定義產品內容」，但文件未說明若 Display POC 試圖重新定義時，誰負責拒絕或調解，以及拒絕後走哪條升階路徑。此條件被列為 gate 要求，但缺乏可觀察的驗收動作（無人員、無審查單類型、無 milestone_progress.md 更新義務）。

若 Display POC 產出與 `display_spec.md` 有出入，M4c 無法確定 gate 是否通過，也無法確定由誰裁定。

**契約依據**：`milestone.md` §1.2 條件 3（引用上游契約不存在未解矛盾）
**最低驗收條件**：在 §6.2 M4c 放行條件中，補充「Display POC 若嘗試修改產品內容定義，由 Designer 以 `display_spec.md` 為準拒絕，並記錄於 `milestone_progress.md`，不阻擋 M4c 本身」，或等效的責任歸屬說明。

---

### 🟠 FIND-MR-03：M5 排除項目漏列「不把 broker 連線狀態寫入 startup-static capability map」

**位置**：`docs/milestones/M5.md` §7.3 排除項目

**問題**：

M5.md §7.4 驗收條件第 3 點要求「broker 斷線只使 `is_available()` / 連線狀態降級，主對話與 capability map 不變」。但 §7.3 排除項目未列此對應排除，Developer 若未注意到 §7.4，可能在實作中誤將連線狀態寫入 startup-static capability map，違反 `arch.md` §6.8。

**契約依據**：`arch.md` §6.8（capability map 為 startup static）
**最低驗收條件**：於 §7.3 補充「不把 broker 連線狀態寫入 startup-static capability map」作為明確排除項目。

---

### 🟠 FIND-MR-04：M6 可重複驗收缺少 Pi-only 測試指令（與 M3/M4/M7 不一致）

**位置**：`docs/milestones/M6.md` §8.4 可重複驗收

**問題**：

M6.md §8.4 第 1 點驗收指令只列 `python -m pytest -v`，未列帶 `-m rpi` 標記的 Pi 專屬測試指令。M3.md §5.4、M4.md §6.4、M7.md §9.4 均同時列出兩條指令。M6 涵蓋 wake daemon 麥克風互斥、Vision adapter 等 Pi-only 行為，缺少指令使 Tester 撰寫 `test_spec_M6.md` 時無從參照命名慣例。

**契約依據**：`milestone.md` §1.4（Pi-only 驗收明確標記）
**最低驗收條件**：在 §8.4 補充 `python -m pytest -v -m rpi tests/milestones/test_m6_full_session.py`（或等效命名），與其他 milestone 格式一致。

---

### 🟡 FIND-MR-05（Advisory）：M7 相依條件對字型變更路徑未說明

**位置**：`docs/milestones/M7.md` §9.2 相依

**問題**：§9.2 第 3 點補充「M3 固定的主字型若未變更則沿用」，但未說明「若 M7 修訂後 `display_spec.md` 改用新字型」時需更新 §2.3 Asset inventory 並取得授權與 SHA 的使用者確認。

**Advisory**：建議在 §9.2 補充「若 M7 修訂後字型異動，需同步更新 `display_spec.md` §2.3 Asset inventory，並取得使用者確認」。此 Advisory 不阻擋 Resolved。

---

## Designer 修訂說明（2026-08-12）

* **FIND-MR-01**：M3.md §5.2.1 Checkpoint 表格「M3 Design Ready 前」放行規則欄補充「LLM POC contract 不在此 gate 範圍，不得列為阻擋條件」。
* **FIND-MR-02**：M4.md §6.2 M4c 放行條件補充「Display POC 若提出不同產品內容，Designer 以 `display_spec.md` 為準拒絕或另開產品決策，並記錄於 `milestone_progress.md`。單純提案不阻擋 M4c；未解的技術契約矛盾仍依 `milestone.md` §1.2 阻擋」。
* **FIND-MR-03**：M5.md §7.3 補充「不把 broker connection 狀態寫入 startup-static capability map」。
* **FIND-MR-04**：M6.md §8.4 補充 `python -m pytest -v -m rpi tests/milestones/test_m6_full_session.py`。
* **FIND-MR-05**：Designer 選擇本輪不修訂（Advisory）。

---

## Reviewer 最終裁定（2026-08-12）

| Finding | 結果 | 驗收依據 |
|---|---|---|
| FIND-MR-01 🔴 | ✅ 通過 | M3.md §5.2.1「M3 Design Ready 前」放行規則欄已明確補充「LLM POC contract 不在此 gate 範圍，不得列為阻擋條件」 |
| FIND-MR-02 🔴 | ✅ 通過 | M4.md §6.2 M4c 已補充責任歸屬：Designer 以 `display_spec.md` 為準拒絕，並記錄 `milestone_progress.md`；單純提案不阻擋 M4c；技術契約矛盾仍依 §1.2 阻擋 |
| FIND-MR-03 🟠 | ✅ 通過 | M5.md §7.3 已補充「不把 broker connection 狀態寫入 startup-static capability map」 |
| FIND-MR-04 🟠 | ✅ 通過 | M6.md §8.4 已補充 `python -m pytest -v -m rpi tests/milestones/test_m6_full_session.py`，與 M3/M4/M7 格式一致 |
| FIND-MR-05 🟡 | ⚪ 略過（可接受） | Advisory；Designer 本輪選擇不修訂，可接受 |

**結論：Milestone M3–M7 規劃審查通過。**

本單據狀態設為 `Resolved`，依照流程移至 `docs/reviews/history/`。
