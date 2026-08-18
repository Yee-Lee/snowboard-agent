# LLM POC readiness 與 Gate 對齊修正

- **Handoff ID** : `PM-POC-LLM-20260817-001`
- **Feedback ID** : `POC-LLM-READINESS-2026-001`
- **Status** : `On hold — pending Core handoff PM-OUT-260817-015`
- **Owner** : `LLM POC Team`
- **Reviewed repo** : `poc_llm/snowboard-agent`
- **Reviewed branch / SHA** : `llm` / `4ac7ba3941077babf34c7c575003a65f5c541009`
- **Internal review** : `poc_llm/feedback/active/POC-LLM-READINESS-2026-001/review_notes.md`

## 結論與影響

POC 的目標、Pi 5 驗證方向與 evidence 原則可接受，但目前 Gate 0 / M0 狀態、Gate 1 執行順序及交付追蹤尚未對齊。現有 Gate 0 receipt 尚不足以完成行政收件 / 登錄，也不得據此略過 Ubuntu 初篩或開始 Pi 5 Gate 2 驗證。

請先完成以下修訂，最後一次 commit/push 到約定 branch 並通知 PM 已可收件。POC 團隊不必在文件內預填或指向 commit SHA；PM 拉回後自行記錄收到的 branch HEAD，再交 Core Designer 登錄。

## Findings

### `POC-LLM-GOV-2026-001` — Blocking

**問題** : `docs/milestone/README.md` 將 Gate 0 / M0 標成 `IN_PROGRESS`，但 `poc_llm/README.md` 與 `m0_llm_readiness.md` 是 `NOT_STARTED`；Gate 0 receipt 又宣告 `COMPLETE`。Receipt 另保留無法在最後一次 commit 前自我解析的 `PENDING_OPERATOR_COMMIT` 欄位。外部 Contract Gate 與內部執行 milestone 也共用同一狀態。

**必做修訂** :

- 分開列示 External Gate 0 與 Internal M0，不再合併為 `Gate 0 / M0`。
- 指定一份權威狀態索引，其他文件只能引用或保持一致。
- 移除要求 POC 團隊預填 delivery commit SHA 的欄位。Gate 0 在 PM 收件、Core Designer 記錄前標示 `submitted`；完成收件 / 登錄後才由內部狀態記錄為 `complete`，不另增加一輪 Core 技術核准。
- 清楚記錄每個 Gate 的開啟與關閉權限；POC 團隊不得用自己的 ACK 取代 Core Designer ACK。

驗收方式：PM 拉回的 repo 內所有狀態一致；receipt 無 SHA placeholder 或自我引用要求；可由文件直接判斷 Contract Gate、Internal Milestone、owner、recorder/approver 與目前授權範圍。

### `POC-LLM-PLAN-2026-002` — High

**問題** : 合約 Gate 1 要求 candidate proposal 與 Ubuntu x86/arm64 pre-screening，但內部 M1 只定義 frozen contract/harness，M2 已直接進入 Raspberry Pi candidate evaluation，缺少可執行的 Ubuntu 初篩 gate。

**必做修訂** :

- 增列明確的 Ubuntu pre-screen 階段，定義 entry、exit、命令、metrics、evidence、淘汰理由及 approver。
- 先固定 runtime/model/quantization 的有效 pairing，完成 license、offline、artifact checksum 與 aarch64 compatibility preflight。
- Ubuntu 初篩後最多保留兩個 finalist；取得 Core Designer Gate 1 書面確認後才進 Pi 5 Gate 2。

驗收方式：milestone crosswalk 可逐項對應 Contract Gate 1；候選矩陣有固定 ID、淘汰規則與最多兩個 Pi finalist，且不以 Ubuntu 結果取代 Pi evidence。

### `POC-LLM-TRACE-2026-003` — High

**問題** : milestone index 使用 D1–D6，個別 M0–M4 文件與 delivery gate draft 使用 D1–D8，無法可靠追蹤 M4B-P1~P12、證據與結案條件。Gate 0 receipt 所稱 Initial Manifest 目前也只有預定目錄樹，沒有實際 manifest artifact。

**必做修訂** :

- 固定唯一 delivery taxonomy，並提供 External Gate、Internal Milestone、Delivery Area、M4B-P1~P12 的單一 crosswalk。
- 在 `poc_llm/deliveries/` 提交實際 Gate 0 initial manifest，至少包含 repo/branch、環境狀態、artifact/evidence 狀態、已知 blocker 與下一個獲准工作；未執行項目標為 `Pending` 或 `Blocked`。Delivery HEAD 由 PM 收件時另行記錄。
- 交付 ID 採 `POC-llm-DEL-YYYY-NNN-RN`，不得以規劃中的目錄樹代替 manifest。

驗收方式：任一 M4B test ID 均可唯一追溯到 milestone、delivery item、evidence 狀態與 owner；manifest 所列路徑在 PM 拉回的 repo tree 中真實存在。

### `POC-LLM-EXEC-2026-004` — High

**問題** : 目前 repo 是合理的 planning scaffold，但尚無可執行 M0 packet。若要把 M0 改為 `IN_PROGRESS`，仍缺 setup/lock、允許命令、timeout/cancel/cleanup、dummy child、evidence schema 與 resource schedule。

**必做修訂** :

- M0 未獲准且 packet 未完成前維持 `NOT_STARTED`。
- 開始 M0 前提交最小可執行 packet：Python 3.11+ setup/lock、deterministic dummy child、test request、命令與 expected output、timeout/cancel/cleanup、sanitized evidence schema。
- 登錄 owner、預估工期、Pi 5 4GB/8GB 可用性、儲存 / 下載需求與每階段重跑上限。

驗收方式：在不下載真實模型的條件下，可由 clean checkout 依固定命令執行 M0；失敗可被觀察，且 evidence 能定位 exact SHA、exit code、cleanup 與 raw artifact checksum。

### `POC-LLM-BOUNDARY-2026-005` — Medium

**問題** : 團隊 workflow 允許同一 agent session 依序擔任 Developer 與 Tester；這可作團隊自測，但不能取代內部 Tester 的正式驗收。此外，repo 的 `docs/arch.md` 範圍包含大量產品架構內容，可能形成與正式產品架構競爭的權威來源。

**必做修訂** :

- 清楚區分 POC Team self-test、Technical Lead review、Internal Tester confirmation；只有後者可支撐正式 POC acceptance。
- 將 `docs/arch.md` 的權威範圍限定為 POC-specific wrapper、protocol、resource/evidence decisions；產品架構只引用 Core 指定的 exact SHA，不自行宣告為產品權威。

驗收方式：workflow 明列三種審查角色與各自可簽核狀態；架構文件能明確辨認 POC 決策與產品權威來源。

## 回覆與提交要求

請 LLM POC Team 在自己的 repo 提交：

1. `docs/response/RESP-POC-LLM-READINESS-2026-001.md` : 逐項回覆上述 Finding ID，列出修改路徑與剩餘限制。
2. 修訂後的 Gate 0 receipt，以及 `poc_llm/deliveries/POC-llm-DEL-2026-001-R1.md` initial manifest。
3. 全部修訂完成後一次 commit/push 到約定 branch，僅通知 PM 已可收件；不必在回覆文件中填寫 commit SHA。

PM 收到通知後應拉回約定 branch，自行記錄實際 HEAD，再次交 Core Designer 登錄 Gate 0 receipt。`Team revised` 不等於 finding 已關閉；Blocking finding 關閉前不得啟動 Gate 1，Gate 1 未取得 Core Designer 書面確認前不得啟動 Pi 5 Gate 2。
