# LLM POC 工作流程與合作方式

狀態：Authoritative cross-milestone process
最後更新：2026-08-20

## 1. 文件責任與權威順序

本文件只定義跨 milestone 長期不變的角色、evidence、Git/Pi、安全與溝通規則；不重複
目前狀態、個別 milestone scope、entry/exit gate、測試矩陣或 delivery mapping。

| 問題 | 唯一權威文件 |
| --- | --- |
| 現在做到哪、獲准做什麼、有哪些風險 | [Milestone index](milestone/README.md) |
| 當前 milestone 的目標、entry/exit、evidence、禁止事項 | 對應的 `docs/milestone/m*.md` |
| External Gate、M0–M4、D1–D8、P1–P12 映射 | [Traceability crosswalk](milestone/m4b_traceability_crosswalk.md) |
| Gate 1、2A、2B work package 與 result semantics | [Execution plan](milestone/m4b_execution_plan.md) |
| 外部 acceptance 與授權邊界 | 已交付的 PM/Core contract 與 ACK |
| 跨 milestone 工作方法 | 本文件 |

權威順序為：User 明確決策、PM/Core Income、milestone index、上述專責文件、repo working
draft。較低層文件不得自行降低 acceptance gate；收到新 Income 時先做差異分析，再更新
index、受影響 milestone、risk 與 change request。

## 2. 不變的交付邊界

- 每個 work item 必須推進明確的 delivery area 與 milestone exit condition，並產生可重現
  evidence；無法說明交付貢獻、判定者與失敗影響的工作不進入範圍。
- POC 僅處理 LLM runtime/model、prompt/output boundary、child process 與 Pi 5 可交付性；
  不修改產品 composition root、StateManager 主體或 Audio model selection。
- POC wrapper、benchmark harness、fake 與 self-test 不等於產品實作或正式 acceptance。
- 所有 hardware delivery 綁定可取得的完整 commit SHA、packet、artifact/config/fixture ID
  與 evidence checksum；branch HEAD、聊天摘要或最好一次結果不能替代。
- 完整 SHA 交付最多表示 `Ready for internal review`。Blocking findings 關閉且所需
  Tester/Reviewer/Designer approval 到位後，才可依合約標示 accepted outcome。

## 3. Gate 與 Milestone Lifecycle

External Contract Gate 是 PM/Core 的行政與授權狀態；Internal Milestone 是 POC 的
execution/readiness 狀態，兩者必須分開記錄，不得互相推導。External Gate 只能由 contract
指定的 recorder/approver 關閉；POC ACK、self-test 或 Technical Lead review 均不能代替。

Internal Milestone 狀態限於 `NOT_STARTED`、`PLANNED / NEXT`、`IN_PROGRESS`、
`GATE_REVIEW`、`COMPLETE`、`BLOCKED`、`CHANGE_REQUESTED`。計畫或 scaffold 編輯不會
啟動 milestone；entry review、test request 與所需授權完成，且 index 明確改為
`IN_PROGRESS` 後才算開始。只有 milestone 文件的 exit conditions、必要 evidence 與所需
approval 全部成立，index 才能改為 `COMPLETE`。

任何 Gate/Milestone 狀態變更必須同步更新 index 中的 delivery reachability、evidence、
open exit conditions、risk/blocker/change request 與唯一下一個獲准工作。具體 Gate/M0–M4
條件只保存在 index、active milestone、crosswalk 與 execution plan，不在本文件複製。

## 4. 角色與交接

| 角色 | 責任與邊界 |
| --- | --- |
| Technical Lead | 定義 packet、review evidence、提出 `PASS/FAIL/INCONCLUSIVE` 建議、維護 risk/change request；不能取代 Tester acceptance。 |
| Developer | 僅在 workstation 修改 source/tests/docs，完成 local/fake test，交付 exact SHA；不得宣告 hardware pass。 |
| POC Test Controller | 在 Pi 對指定 SHA 執行 immutable packet 並回收 evidence；不修改 Pi source、不改 gate、不挑最好 run。 |
| Internal Tester | 獨立確認 delivery SHA、packet 與 evidence；Developer self-test 不得冒充。 |
| User | 核准硬體存取、下載/安裝、網路/特權、commit/push/tag 與產品決策。 |
| Designer | 凍結 boundary 與 gates，依合約核准 finalist、winner 或 no-go。 |
| Reviewer | 審查重現性、finding closure 與 acceptance readiness。 |

同一 agent session 可依序兼任 Developer 與 Test Controller，但結果只能標為 POC Team
self-test。交接順序固定為：Developer 交付 clean exact SHA → Technical Lead 發 immutable
packet → Test Controller 回收 evidence → Technical Lead review → Internal Tester 獨立確認。

## 5. Work Item、Packet 與 Evidence

每個實作或測試 work item 至少記錄：

- Work/Test ID、milestone、delivery area、owner、approver、baseline 與 target SHA。
- Candidate/artifact/config/fixture/schema IDs、entry conditions 與允許命令。
- Expected output/exit、timeout、resource limit、success/failure/`INCONCLUSIVE` conditions。
- Cancel/force-abort/cleanup/orphan proof、raw evidence location/checksum 與 sanitization rule。
- 重試上限；environment failure 與 candidate failure 必須可區分。

Packet 發出後不得在 run 中修改；acceptance semantics 改變時建立新版並重跑所有受影響
cases。Hardware result 僅可依完整 evidence 判為：所有 mandatory gate 通過的 `PASS`、
有效 evidence 證明 gate 未通過的 `FAIL`，或 evidence/environment 不足的 `INCONCLUSIVE`。
重試必須保留原結果與理由，禁止只發布最好一次。

Technical Lead review 順序為 SHA/environment/packet、artifact/fixture checksum、exit/cleanup，
再審查品質與效能。Raw evidence 由 Tester 受控保存；repo 只保存 sanitized index/summary。

## 6. Git and Pi Workflow

本節承接 [`commit_workflow_update.md`](pm_handoff/commit_workflow_update.md)。POC repo 是
source 與 sanitized delivery record 的唯一來源；Pi 是受控 test worktree，不是開發來源。

- 唯一開發、驗證與 milestone 交付 branch 是 `llm`；不得建立或推送其他 POC branch，
  也不得 force-push `llm`。Workstation/Pi 均從 `origin/llm` 取得指定 exact SHA。
- Fast loop 原則上使用 working tree。必要的 WIP commit 必須保持 local、未 push、未送驗；
  在跨平台、硬體或 milestone review 前，將上一個 frozen SHA 之後的 WIP squash 成單一
  clean Candidate Commit。
- Candidate SHA 一旦 push 並送驗，其可達歷史永久凍結。Reject、`FAIL`、`INCONCLUSIVE`
  或後續缺陷只能保留 feedback 並在其上 append 修正；禁止 reset、rebase、amend、history
  filtering 或 force-push 改寫 frozen Candidate。
- Commit subject 為 `{work-type}{milestone/stage}: {title}`；body 使用 60–100 words 的
  英文 bullet list。提交集中於 milestone 或 remote verification，不為小文件頻繁 commit。
- 未經 User 核准不得 commit/push。未 push、Pi 無法 fetch 的 SHA 不得作 hardware delivery。

Internal Milestone 正式標為 `COMPLETE` 後，才建立對應的 immutable annotated tag：`m0`、
`m1`、`m2`，依此類推。Tag 指向 `llm` 上記錄 completion 的已 push exact SHA，message
記錄 decision 與主要 evidence/approval；push 後不得刪除、覆寫或移動。舊 milestone 補 tag
前須核對原 completion SHA 與 review record，不得使用目前 HEAD。Commit、branch push 與
tag push 均須 User 核准。

Pi 執行時必須 clean checkout exact SHA、先做 pre-test、再執行 immutable packet；不得在 Pi
臨時修補 source。回收 evidence/checksum 並完成 cleanup 後才進入 review。

## 7. Data、Artifact 與 Offline

- Model、large raw result、private prompt/perception/output/tool payload、secret、credential、
  endpoint 與 host fingerprint 不得進 Git 或 sanitized evidence。
- Repo 只保存 artifact source/version/license/checksum、受控取得方法與 sanitized result；
  artifact 本體與 raw evidence 依核准位置保存。
- Offline run 前先固定並驗證所有 artifacts；run 中不得下載或 fallback 到 cloud/其他 model。
- Artifact transfer、安裝、network switching、reboot、privilege 或影響其他 Pi workload 的
  動作必須另行取得 User 核准。

## 8. 文件與溝通

- `docs/pm_handoff/`：外部 Income，嚴格唯讀；完成、取代或不再追蹤時移至 `history/`。
- `docs/response/`：內部技術 ACK、assessment 與 finding response。
- `docs/delivery/`：由 PM 轉交外部的正式 delivery。
- `docs/milestone/`：index、active milestone、crosswalk 與 execution plan。
- `poc_llm/`：source、tests、tools、fixtures metadata、evidence index 與 delivery package。
- `docs/DOCUMENT_INDEX.md`：上述文件的索引；不得在 Income 內直接撰寫團隊回覆。

產品架構、model baseline、composition root 與產品 protocol 必須引用 Core 指定 SHA/ACK；
repo-owned architecture 文件只能描述 POC-specific wrapper、protocol、resource 與 evidence。

## 9. Change Requests

Runtime/model 無法滿足 frozen gate、IPC/Reasoner/protocol contract 需改變、M4a/hardware/資源
dependency 阻擋、或 license/artifact/offline/cleanup 無法證明時，必須提出 change request。
未獲核准前不得降低 gate、替換 acceptance semantics 或把 `INCONCLUSIVE` 改寫為成功。

Session/context/milestone 切換時的最小閱讀路由由 repository `AGENTS.md` 控制；本 workflow
只在任務涉及上述跨 milestone 規則或其他文件語意不明時按需讀取。
