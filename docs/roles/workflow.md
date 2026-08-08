# 開發工作流程與協議 (AI 執行標準)

- **Git 操作與版控原則**：禁止任何 AI 角色直接修改、建立或寫入 `.git/` 目錄內部的檔案與結構；所有 Git 版本控制與異動操作必須一律透過標準 CLI `git` 命令執行。執行 `git commit` 前，必須先向使用者（USER）確認，獲得同意後方可執行提交。

- **Git Commit Message 規範**：

  **標題格式**：`[work_type][milestone]: [title]`

  | work_type | 用途 |
  |---|---|
  | `feat` | 新功能、新模組 |
  | `fix` | Bug 修正 |
  | `docs` | 文件新增或修改 |
  | `test` | 測試新增或修改 |
  | `refactor` | 重構（不改行為） |
  | `chore` | 建置、工具、設定類 |

  範例：`feat[M3]: add GPIO button InputSource with debounce`、`docs[M2]: restore §3.4 required_kinds derivation`

  **內容（Body）規範**：
  - 使用英文條列式（`-`）描述修改內容或緣由。
  - 全文 60 words 以內。
  - 引用相關 Handoff ID / Finding ID（如 `OUT-M2-2026-005`）或 Review 單號。

1. 目錄與權責映射


docs/arch.md : [Architect] 架構契約與邊界

docs/implement/ : [Designer] 技術設計與介面

docs/model_spec.md & docs/display_spec.md : [Designer] 軟硬體能力基準與顯示規範

docs/milestone.md : [Designer] 開發里程碑總覽與基礎原則

docs/milestones/M{x}.md : [Designer] 各開發里程碑詳細規劃 (按階段拆分)

docs/test_spec/test_spec_M{x}.md : [Tester] 各里程碑測試規範與驗收標準

docs/reviews/dev_progress_M{x}.md : [Developer] 各階段估點拆包與進度 (舊有單據歸檔至 history/)

docs/reviews/ : 跨角色審查單 (結案移至 history/)

docs/outsource/pm_handoff/ : [Product Team] PM 提供的產品規劃方向、需求反饋與建議

docs/outsource/references/ : [All Roles] 外部團隊（POC / 硬體廠商等）主動交付給 Core Team 的技術參考文件（contract、spec draft、capability matrix 等）；按團隊分子目錄（poc_audio/ poc_display/ poc_llm/）存放。Core Team 採用決定記錄於 deliveries/ ACK 文件，不在此修改原始內容。

docs/outsource/deliveries/ : [All Roles] 開發團隊完成後交付給產品團隊的產出物

docs/outsource/responses/ : [All Roles] 開發團隊針對 PM 需求的回應

docs/outsource/evidence/ : [Tester] 驗收測試的日誌與證據

src/ & tests/ : [Developer] 軟體代碼與自動化測試

2. 產品需求與外部溝通 (PM Interaction)

- 產品團隊負責審核與建議產品規劃方向，透過 `docs/outsource/pm_handoff/` 提供反饋，不會介入實際開發流程。
- 團隊角色（如 Architect 或 Designer）需定期檢視 `pm_handoff/` 中的建議，以調整架構或規劃。
- 當開發團隊完成需求或里程碑後，應將交付物、回應文件及測試證據分別放置於 `docs/outsource/deliveries/`、`docs/outsource/responses/` 與 `docs/outsource/evidence/` 供產品團隊查閱。
- 內部開發依然遵循原有的五階段流水線（Pipeline）與審查單（Review）生命週期約束，確保獨立性與品質。

3. 審查單 (Review) 生命週期約束

檔案命名：docs/reviews/{Type}_{Round}.md (例: AR_review_I.md) 或含有階段的單據 (例: TR_dev_M1_I.md)

AR_review: Reviewer -> Architect (架構審查)

AR_impl: Designer -> Architect (架構無法實作)

IR_review: Reviewer -> Designer (設計審查)

IR_dev: Developer -> Designer (設計無法開發)

MR_review: Reviewer -> Designer (Milestone 規劃審查)

TR_spec_M{x}: Designer -> Tester (測試規範涵蓋率審查)

TR_dev_M{x}: Tester -> Developer (測試驗收未通過，退回開發)

CR_M{x}: Designer -> Developer (Tester 通過後，最終代碼對齊設計審查)

YAML 標頭與狀態機：

---
requestor: "[發起角色]"
owner: "[負責修訂角色]"
status: "[Open | Revised | Rejected | Resolved]"
---


流轉規則：Requestor 發起 (Open) -> Owner 修訂主文件並回覆 (Revised) -> Requestor 審核若不通過 (Rejected) -> Owner 再修訂 (Revised)，如此反覆。直到 Requestor 通過 (Resolved) 後該輪結束，整輪單據移至 docs/reviews/history/ 歸檔。若日後有全新議題，再開立下一輪 (如 _III.md)。

審查收斂規則：

- Finding 必須分為 `Blocking` 與 `Advisory`。只有違反已核准契約／acceptance criteria、具安全或資料風險、造成跨模組不一致、假綠燈或高回歸風險者可阻擋；純風格、個人偏好、可選重構與非必要的重複測試不得阻擋。
- 每個 Blocking finding 首次提出時，必須完整提供：契約或 test spec 依據、可驗證證據或最小重現、預期／實際結果、影響、建議修正方向與最低驗收條件。建議方向用來降低來回成本，但除非契約指定，不得限制 Owner 採用唯一實作。
- Requestor 應盡量在首輪完成同一審查範圍內的問題盤點。複審以既有 finding、直接影響範圍與新 regression 為主，不得逐輪加入無關偏好或提高門檻。新 Blocking finding 僅能在有明確契約依據與風險時追加，並須記錄先前未能辨識的原因。
- 通過標準以行為與風險覆蓋為準，不以 finding、test function、assertion 或文件篇幅數量判定。允許參數化、table-driven、既有測試擴充及其他等價證據；同一風險已被有效覆蓋時，不要求重複測試。
- Advisory 應清楚標記且不得影響 `Resolved`。Owner 可選擇本輪處理或另行記錄；不得因未採用 Advisory 而將狀態改為 `Rejected`。

3. 五階段流水線 (Pipeline)

[A] 架構：Architect 寫 arch.md -> Reviewer 審查通過 (AR_review)。

[B] 設計：Designer 寫 implement/ (若架構矛盾發起 AR_impl) -> Reviewer 審查通過 (IR_review)。

[C] 規劃：Designer 寫 milestone.md -> Reviewer 審查通過 (MR_review) -> Tester 依此寫 docs/test_spec/test_spec_M{x}.md -> Designer 審查 (TR_spec_M{x})，確認測試 100% 覆蓋設計並簽核後進入 [D]。

[D] 開發：Developer 寫 docs/reviews/dev_progress_M{x}.md 估點拆包 -> 撰寫 src/ 與 tests/ (若遇阻發起 IR_dev)。

[E] 驗收與提交：Tester 以 test spec 實際執行並審核 src/ & tests/（功能驗收、揪出假綠燈）-> 若未通過開立 TR_dev_M{x}，依審查收斂規則提供建議方向與最低驗收條件，直到 Tester PASS -> Designer 最終 Code/Test Review（聚焦設計對齊及高風險 regression protection，不重做全面測試驗收；若有 Blocking 偏離則開立 CR_M{x}）-> Blocking 全數解決後才提交；Advisory 不阻擋提交。
