# LLM POC 工作流程與合作方式

狀態：Authoritative working process  
最後更新：2026-08-09

## 1. 目的與權威順序

本文件定義 LLM POC 從尚未開始 M0 到正式交付的工作方式。所有工作由 M4b
最終交付反推，每個 work item 都必須回答：

1. 它推進哪一個 delivery area 與 milestone exit condition？
2. 完成後產生什麼可重現 evidence？
3. 誰有權執行、判定與核准？
4. 若結果失敗或無法判定，最終目標是否仍可達？

無法回答以上問題的工作不進入目前範圍。

目前 repo 內的權威順序如下：

1. User 已明確給定的範圍、核准與外部限制。
2. 已正式交付的 PM/Designer Income 文件。
3. `docs/milestone/README.md` 的活動狀態、entry/exit gate 與風險。
4. 本 workflow 的角色、evidence、Git/Pi 與安全規則。
5. Repo-owned working drafts；它們不得自行降低外部 acceptance gate。

正式 LLM checklist/development guide 尚未交付時，可以維護計畫、schema 與不依賴
未決契約的 scaffold；不得假裝外部 gate 已批准。收到新 Income 後先做差異分析，
再更新 milestone/risk/change request。

## 2. 最終交付目標

POC 最終必須交付：

- 固定的 LiteRT-LM runtime、model artifact 與 quantization；若沒有候選達標，提交
  明確且有證據的 no-go。
- 固定 checksum、license、來源、strict config，以及 `docs/model_spec.md` 所需 handoff。
- Versioned child protocol，以及 `docs/protocol.md` 所需 handoff。
- Raspberry Pi 5 上的 cold READY、cold/hot generation、p50/p95、tokens/s、RSS、
  disk、CPU、threads/processes 與 thermal 證據。
- Reasoner/LLM boundary 能產生合法 `speak`、`tool`、`rest` action；model 不執行 tool。
- Single-turn history isolation、capability/payload validation、P5 fallback 與 log hygiene。
- Persistent child 的 timeout、cancel、terminate、kill、waitpid、crash/rebuild、shutdown
  與 orphan=0 證明。
- 與明確 Accepted 的 M4a Audio HAL 完整 SHA 整合，完成至少 20 個 combined
  sessions，且 offline/failure injection 後無資源殘留。

提交完整 SHA 只代表 `Ready for internal review`。Tester/Reviewer 關閉 blocking
findings 且 Designer 核准後，才是 `POC Accepted`。

## 3. 範圍與非目標

本 POC 專注於 LLM runtime/model、prompt/output boundary、child process 與 Pi 5
可交付性驗證。

不在範圍內：

- 修改產品 composition root 或 StateManager 主體。
- 重新選型 VAD、ASR、TTS 模型或重新定義 Audio 結果語意（屬 M4a）。
- 雲端 LLM、RAG、跨 session 記憶、Vision 或 wake daemon。
- 讓 LLM 模型直接執行 Python 或 tool handler。
- 未經 review 的 runtime、model、prompt、output schema 或 acceptance gate 變更。
- 把 POC wrapper、benchmark harness 或 fake 直接視為產品主線實作。

## 4. Milestone Lifecycle

活動狀態只由 [milestone index](milestone/README.md) 判定：

| Milestone | Gate purpose |
| --- | --- |
| M0 | Environment、exact SHA、remote command control 與 evidence chain readiness |
| M1 | Freeze contract、protocol、fixtures、metrics/gates；fake 驗證 harness |
| M2 | 在 frozen packet 下比較 runtime/model/quantization candidates |
| M3 | 固定 winner/no-go，驗證 persistent child 與 Pi integration baseline |
| M4 | Accepted M4a SHA 上完成 combined/offline/fault validation 與交付 |

允許的 milestone 狀態為：`NOT_STARTED`、`PLANNED / NEXT`、`IN_PROGRESS`、
`GATE_REVIEW`、`COMPLETE`、`BLOCKED`、`CHANGE_REQUESTED`。

撰寫或修正計畫文件不會自動開始 milestone。Milestone 只有在 entry review 完成、
下一個 test request 已獲准、索引明確改成 `IN_PROGRESS` 後才算開始。

任何 milestone 狀態變更，都必須同時在索引更新最終交付可達性、已取得 evidence、
未關閉 exit conditions、risk/blocker/change request，以及唯一下一個獲准工作。

不得因前一個 Audio POC milestone 名稱相同而轉移其 `COMPLETE` 或 `PASS`。可以引用
其通用 runbook/evidence 方法，但 LLM milestone 仍需自己的 test request、exact SHA、
result 與 review decision。

## 5. 角色與決策權

| 角色 | 責任與決策權 |
| --- | --- |
| Technical Lead（Assistant） | 規劃 work item、定義 test request/packet、審查 evidence、做技術 `PASS/FAIL/INCONCLUSIVE` 判定、維護風險並提出 change request。 |
| Developer（agent） | 只在 workstation 修改 POC source/tests/docs；先完成 local/fake tests，交付完整 SHA 與可執行 test request。不得直接宣告 hardware pass，不得在測試中修改 Pi worktree。 |
| Tester / Test Controller（agent） | 只對指定 exact SHA 做 Pi clean checkout、pre-test、test packet 執行與 evidence 回收；回報觀察結果，不改 gate、不挑選較好 run。 |
| User | 提供/控制目標硬體，核准 Pi 存取、下載/安裝、網路切換、特權、commit/push 與產品層決策。 |
| Designer | 凍結 Reasoner/prompt/output/protocol 與品質/資源 gate，核准 winner 或 no-go。 |
| Reviewer | 依 delivery checklist 審查可重現性、finding closure 與 acceptance readiness。 |

同一個 agent session 可以依序兼任 Developer 與 Tester，但必須在以下三個交接點
明確切換角色：

1. Developer 交付 exact full SHA 與 clean local evidence。
2. Technical Lead 發出 immutable test request/packet。
3. Tester 回收 evidence，Technical Lead 另行 review 後才判定結果。

## 6. Work Item and Test Packet

每個實作或測試 work item 至少記錄：

- Work/Test ID、milestone、delivery area、owner 與 approver。
- Baseline SHA、target full SHA、candidate/artifact/config/fixture/schema IDs。
- Entry conditions、允許命令、預期 output/exit code、timeout 與資源限制。
- Success criteria、failure criteria 與 `INCONCLUSIVE` conditions。
- Cancel/force-abort/cleanup/orphan 檢查與 completion/exit proof。
- Raw evidence 位置/checksum、sanitized output 與敏感資料規則。
- 重試規則；environment failure 與 candidate failure 必須分開。

Test packet 發出後不可在 run 中修改。任何會改變 acceptance semantics 的修訂都要
建立新 packet version，記錄理由並重新執行所有受影響 cases。

## 7. Result Semantics and Evidence Review

Hardware test 只能使用：

- `PASS`：所有 mandatory cases 由指定 packet 在有效環境下執行，evidence 完整，
  所有 gate 通過且 cleanup/exit proof 成立。
- `FAIL`：有效且完整的 evidence 顯示至少一項不可忽略的 gate 未通過。
- `INCONCLUSIVE`：evidence 缺失/損壞、環境不穩、SHA/fixture 不符、測試未完成，
  或無法區分 infrastructure failure 與 candidate failure。

`INCONCLUSIVE` 不等於 `PASS`，也不構成 candidate reject，除非 frozen gate 明確把
不可執行性定義為淘汰條件。重試必須保留原結果、記錄原因，禁止只發布最好一次。

Raw evidence 由 Tester 保存；repo 只存 sanitized index/summary。Technical Lead 應先
檢查 SHA、environment、packet version、exit code、artifact/fixture checksum 與 cleanup，
再審查 performance/quality result。

## 8. Git and Pi Workflow

POC repo 是 source、tests、harness、schemas、fixtures metadata、sanitized evidence index
與 delivery manifest 的唯一來源。Pi checkout 是受控 deployment/test worktree，不是
第二個開發來源。

日常流程：

1. Workstation edit/test，檢查沒有 model、large result、private content 或 secret。
2. 向 User/PM 說明 commit scope、tests 與 message，取得明確同意後才 commit。
3. Push feature branch/Draft PR；需要外部網路或外部狀態改變時依權限取得核准。
4. Tester 在 Pi `fetch` 並 checkout 指定完整 SHA，執行 clean check 與 pre-test。
5. 執行 immutable test packet；Pi worktree 不做 source edit 或臨時修補。
6. 回收 raw evidence/checksum，產出 sanitized index，Technical Lead review。

Commit message 格式：`[work_type][LLM-Mn]: concise title`。

未經 User 同意不得執行 commit。未 push、Pi 無法 fetch 的 local SHA 不得作為正式
hardware delivery SHA。若測試需要 artifact transfer，artifact checksum 與受控來源
必須獨立於 Git 記錄。

## 9. Data, Artifact and Offline Rules

- Model、大型 raw result、private prompt/perception/output/tool payload、secret、credential、
  endpoint、host fingerprint 與敏感資料不得進 Git。
- Repo 只保存 artifact source/version/license/checksum、受控取得方法與 sanitized result。
- 一般 log 不記錄完整 prompt、private perception、raw model output 或 tool payload。
- Offline gate 開始前先準備並驗證所有 artifacts；測試中不得 runtime download 或
  fallback 到 cloud/其他 model。
- Offline、網路切換、安裝、reboot、privilege 或可能影響其他 Pi workload 的動作
  必須獨立取得 User 核准。

## 10. Documents and Communication Channels

- **Income (`docs/pm_handoff/`)**：PM/外部團隊交付的 requirements、contracts 與 handoff messages，對開發團隊**嚴格唯讀 (Read-only)**。本團隊禁止在 `docs/pm_handoff/` 中直接編輯或撰寫回覆。
- **Income History (`docs/pm_handoff/history/`)**：已完成處理、被新合約取代或不再處於活動狀態的 handoff 訊息移至此目錄存檔，代表已完成不必重複追蹤。
- **Response (`docs/response/`)**：內部技術確認、評估結果或對 Income 的內部 ACK 記錄（命名規範 `ACK-{TargetID}.md`）。
- **Delivery (`docs/delivery/`)**：正式對外交付的文件，供 PM 轉交 Core Team/其他團隊，命名規範 `DELIVERY-{流水號}-{to_who}-{title}.md`。
- **Working plan (`docs/milestone/`)**：活動 milestone、repo-owned gate draft、風險與 evidence requirements。
- **POC assets (`poc_llm/`)**：source、tests、tools、fixtures metadata、evidence index 與 POC delivery package。
- `docs/DOCUMENT_INDEX.md` 追蹤 Income、Income History、Response、Delivery 與 Working Plan。

每次 milestone gate review 必須同步更新：狀態、交付可達性、取得的 evidence、未關閉
exit conditions、risk/blocker/change request，以及唯一下一個獲准工作。

## 11. Dependencies and Change Requests

以下情況必須提出 change request：

- Runtime/model 在 Pi 5 上無法滿足 frozen RSS/CPU/disk/latency/thermal gate。
- IPC、Reasoner、prompt/output 或 recovery contract 需要改變。
- Accepted M4a SHA、硬體、時間、人員或外部文件使 delivery gate 無法關閉。
- License、artifact 固定、aarch64 compatibility、offline 或 cleanup 無法證明。

未獲核准前，不降低 gate、不替換驗收語意、不把 `INCONCLUSIVE` 改寫為成功。

## 12. Session Start Checklist

每次新工作 session、context reset 或 milestone 狀態改變後：

1. 讀 `docs/milestone/README.md`。
2. 只讀目前活動或 next milestone 文件。
3. 讀本 workflow；同一 task 中未改變時不重讀。
4. 確認本次工作對應 delivery area、授權範圍與是否會改變外部狀態。
5. 若是測試，先確認 test request、exact SHA、artifact/fixture IDs 與 evidence path。
6. 若 entry review 尚未完成，保持 milestone `NOT_STARTED`，只進行獲准的準備工作。
