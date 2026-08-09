# LLM POC 工作流程與合作方式

狀態：Authoritative working process  
最後更新：2026-08-09

## 1. 目的

本文件定義 LLM POC 從環境就緒到正式交付的完整工作方式。所有工作以 M4b 最終交付為起點反推；每項工作都必須能回答：

1. 它推進哪一個最終交付項目？
2. 完成後產生什麼可重現證據？
3. 若結果失敗，最終目標是否仍可達？

無法回答以上問題的工作不進入目前範圍。

## 2. 最終交付目標

POC 最終必須交付：

- 固定的 LiteRT-LM runtime、model artifact (如 Gemma3:e2b)；若沒有候選達標，提交明確且有證據的 no-go。
- 固定 quantizations、checksum、license 與來源，以及建立 `docs/model_spec.md` 與 `docs/protocol.md`。
- Raspberry Pi 5 上的 cold/hot latency、p50/p95、tokens/s、RSS、disk、CPU 與 thermal 證據。
- 確立 Reasoner 與 LLM child process 之間的 IPC 通訊，保證產生合法的 `speak` / `tool` / `rest` action。
- 與 M4a Audio HAL 整合，進行至少 20 個 combined sessions，且離線與 failure injection 後無資源殘留。
- 確保 history isolation (單回合生成，無跨 operation 狀態) 與 strict config 限制。

提交完整 SHA 只代表 `Ready for internal review`。Tester/Reviewer 關閉 blocking findings，且 Designer 核准後，才是 `POC Accepted`。

## 3. 範圍與非目標

本 POC 專注於 LLM 的整合與效能驗證。

不在範圍內：
- 修改產品 composition root 或 StateManager 主體。
- 重新選型 VAD、ASR、TTS 模型 (屬 M4a)。
- 雲端 LLM、RAG、跨 session 記憶、Vision 整合。
- 讓 LLM 模型直接執行 Python 或 tool handler。
- 未經 review 的 runtime、model、prompt 或 output schema 變更。

## 4. 工作角色與分工

延續嚴謹的分工與推理配額：

| 角色 | 責任與決策權 |
| --- | --- |
| Technical Lead（Assistant） | 規劃工作、定義 test packet、審查 evidence、標記技術 pass/fail、追蹤風險、提出 change request。 |
| Developer（agent） | 只在工作站修改 POC source、tests 與文件；先完成 local/fake tests，交付完整 SHA、可執行 test request。**不得直接把 Pi 判定為 hardware pass，不得在測試中改動 Pi worktree**。 |
| Tester / Test Controller（agent） | 只對已指定 SHA 執行 Pi checkout、環境 pre-test、執行 test packet 並回收 evidence；保存 raw evidence 並回傳 sanitized index。 |
| User | 提供目標硬體、執行實體操作、核准有外部影響的動作與產品層決策。 |
| Designer | 凍結契約、品質/資源 gate，核准 baseline 或 no-go。 |

一個 agent session 可依序兼任 Developer 與 Tester，但必須在 commit SHA、test packet 與 evidence review 三個交接點明確切換角色。

## 5. 執行與 Git 流程

POC repo 是程式碼、測試 harness、schema、fixture 與 sanitized evidence 的唯一來源。
**Pi checkout 是受控的 deployment/test worktree，不是第二個開發來源**。

日常迭代使用 feature branch 與 Draft PR：
1. Workstation edit/test -> commit -> push feature branch。
2. Pi: `git fetch` -> checkout exact full SHA -> clean check -> pre-test -> test。
3. 收回 raw evidence，轉換為 sanitized evidence。

### Commit message convention
格式：`[work_type][milestone]: concise title`
例如：`[feat][LLM-M2]: implement LiteRT child process generation`

**⚠️ Git 提交規範**：
不要頻繁進行 `git commit`。每次執行 commit 前，**必須先向使用者 (PM) 確認並取得同意**。Commit 風格必須完全依照上述的既有規範 (與 Audio 團隊相同)。

## 6. 文件與狀態維護

除了 `poc_llm/` 內的程式碼，專案的文件狀態維持以下規定：
* **Income (`docs/pm_handoff/`)**：從 PM 或外部團隊接收的任務文件與需求（如 `core_llm_m4b_tasks.md`）。這些文件對開發團隊為**唯讀 (Read-only)**。
* **Outcome (`docs/delivery/`)**：對外正式交付的文件，命名規範為 `DELIVERY-{流水號}-{to_who}-{title}.md`。
* `docs/DOCUMENT_INDEX.md`：用於追蹤所有 Income 與 Outcome 文件的總索引。

## 7. 調整請求 (Change Request)

以下情況必須提出 change request：
- LLM runtime / model 在 Pi 5 上無法滿足資源 (RSS/CPU) 或 Latency 門檻。
- IPC 通訊或 Reasoner 契約需要改變。
- 時間、硬體或人員限制使 delivery checklist 無法完整關閉。

未獲核准前，不降低 gate、不替換驗收語意。
