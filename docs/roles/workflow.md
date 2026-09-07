# 工作流程入口

本文件是角色啟動時的短路由，不承載各階段的完整操作細節。

## 讀取原則

1. 先確認使用者任務與當前角色，只讀直接相關的現行文件。
2. 權威順序為：USER 指示 → `AGENTS.md`／角色規則 → architecture／design／milestone／test spec。
3. progress、review、delivery、response 與 history 是狀態或證據，不得自行改寫產品契約。
4. 不因角色啟動而預讀整套 architecture、implementation、test、handoff 或歷史文件。

## 接手方法

1. **Orient**：只有「接手／繼續」任務才讀 `docs/status/current.md`。
2. **Gate**：確認 current stage、next owner 與角色 entry；未開放就回報 blocker 並停止。
3. **Load**：依 current handoff 只讀指定文件與章節；歷史只用 ID/SHA/Test ID 查詢。
4. **Work**：只修改本角色 authority 與 active scope，驗證直接影響面。
5. **Handoff**：各角色只更新下表允許的既有文件；由 Designer 在已確認的 gate transition 後
   更新 `current.md`。對 USER 的回覆就是一般交接，不另建摘要文件。

## 寫入矩陣

| 角色 | 可更新的現行狀態 | 不直接更新 |
|---|---|---|
| Architect | `arch.md`、自己負責的 active review | `status/current.md`、design/development status |
| Designer | `status/current.md`、`status/design.md`、Designer-owned authority/review | Developer status、Tester spec/evidence |
| Developer | `status/development.md`、`src/`、`tests/`、自己負責的 active review | `status/current.md`、design/test authority |
| Reviewer | 指定的 active review | `status/current.md` 與被審 authority（由 owner 修） |
| Tester | current test spec、指定 active review、正式 evidence | `status/current.md`、design/development status |

新檔只允許三種情況：新 authority 已由上游核准、`review-process.md` 要求的新 review round，
或 USER／外部契約明確要求具唯一 ID 的交付物。其他 checkpoint、交接與結果更新既有文件；
不得為同一狀態再建立 `*_summary`、`*_handoff`、`*_progress` 或另一份 ACK。

## 任務路由

| 任務 | 必要時才讀 |
|---|---|
| 建立、回覆或結案 review | [`review-process.md`](review-process.md) |
| 實體／人工驗收、candidate、freeze、acceptance | [`candidate-process.md`](candidate-process.md) |
| 準備 commit、tag 或其他 Git 交付 | [`git.md`](git.md) |
| PM handoff／外部 delivery | [`../outsource/README.md`](../outsource/README.md) 與該筆 active 文件 |
| 接手目前工作 | [`../status/current.md`](../status/current.md) 後再依角色路由 |
| 一般實作／設計／測試 | 指定工作包、當前 milestone 章節與其直接引用 |

## 權責與主要產出

| 角色 | 主要權威範圍 |
|---|---|
| Architect | `docs/arch.md` |
| Designer | `docs/implement/`、`docs/milestone.md`、`docs/milestones/` |
| Tester | `docs/test_spec/`、正式驗收 evidence |
| Developer | `src/`、`tests/`、`docs/status/development.md` |
| Reviewer | architecture／design／milestone 的跨文件審查 |

`docs/reviews/` 只放進行中的跨角色 review；結案移至 `history/`。操作指令放
`docs/runbooks/`。動態接手狀態放 `docs/status/`；外部往返與證據依
`docs/outsource/README.md` 分流。

## Pipeline

Architecture → design → milestone/test planning → development → verification/acceptance。
每一任務只執行所處階段；遇到上游矛盾，依 `review-process.md` 回到權威 owner，
不得由下游角色私自改契約。沒有實體／人工 gate 時，Tester PASS 後由 Designer 做
最終對齊確認；有此類 gate 時改走 `candidate-process.md`。
