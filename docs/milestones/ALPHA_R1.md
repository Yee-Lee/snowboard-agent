# ALPHA.R1 條件式規劃 ── ASR Product R1 平行線與 M5 Baseline Selection

## 定位

`ALPHA.R1` 是使用新 ASR pipeline 候選的條件式 Voice-only 產品收斂 Gate。它與既有
`M4 → ALPHA` 是兩條獨立產品候選線，不回頭改寫原 M4 / ALPHA 結論，也不拼接兩條線
的 acceptance evidence。

R1 產品版本與既有 `POC-audio-DEL-2026-001-R1` 的 delivery revision 不同。本文一律使用
`ASR Product R1`、`M4a.R1`、`M4b.R1`、`M4c.R1`、`M4.R1` 與 `ALPHA.R1` 指稱產品線。

本規劃目前狀態為 `PLANNED / CONDITIONAL`；不宣告 Design Ready、Developer Ready 或 POC
Accepted。

---

## 1. 兩種 R1 工作區的邊界

| 工作區 | Git branch | 歷史 / 責任 | 允許輸出 |
| :--- | :--- | :--- | :--- |
| `asr-r1/` | `audio` | Audio POC 獨立歷史；研究 ASR、適合的 VAD / endpoint 與 evidence-backed postprocess / second-pass scorer | POC plan、code、sanitized evidence、final outcome handoff |
| `core/` | `core` | 唯一永久 Core 開發分支；現行 `M4 → ALPHA` 線 | 原始 ALPHA 候選與後續被選定的唯一 M5 歷史 |
| `core-r1/` | `candidate/asr-r1` | Core 同一歷史上的短期產品候選分支 | `M4a.R1 → M4b.R1 → M4c.R1 → M4.R1 → ALPHA.R1` |

Audio POC history 不得 merge 或 cherry-pick 進 Core。Core 只收取 contract、committed full SHA、
manifest、artifact / license identity、sanitized evidence、conformance assets 與產品 delta
建議；Core 產品實作必須留在 Core history。

### 1.1 目標 workspace layout

```text
snowboard-agent/
├── .git/       # common / bare Git directory；本身不是 worktree
├── core/       # linked worktree → core
├── asr-r1/     # linked worktree → audio
└── core-r1/    # linked worktree → candidate/asr-r1（需要時才建立）
```

`core/.git`、`asr-r1/.git` 與 `core-r1/.git` 都是指向 common Git directory 下各自
worktree metadata 的 gitfile。搬移、建立、修復與移除 worktree 只使用標準 `git worktree`
命令；禁止直接編輯 `.git/` 內部。實體路徑是 operator workspace 細節，不是
candidate identity；所有 gate 仍綁定 branch 診斷資訊與完整 SHA。

---

## 2. Audio POC outcome contract 與收件

Core contract 為
`docs/outsource/deliveries/DELIVERY-AUDIO-POC-ASR-PRODUCT-R1-CONTRACT-001.md`。它只要求
Audio POC 回答：

> 是否有明確、可重現的證據，證明新 ASR pipeline 在產品相關限制下可行，且值得繼續
> 發展 `ALPHA.R1`？

ASR pipeline 可由 POC 自主納入適合的 VAD / endpoint、postprocess、second-pass scorer
或 rescoring。Core 不預先指定 candidate、方法、指標、threshold、runner、內部 gate 或排程，
也不因 POC 一般研究調整而重寫 contract。

### 2.1 最終回交

POC final handoff 必須使用以下一種 outcome：

| Outcome | Core 收件語意 |
| :--- | :--- |
| `SUPPORTED` | 證據支持繼續投入 Core R1；不自動取得產品 gate credit |
| `NOT_SUPPORTED` | 不建議繼續發展；不改變原 M4 / ALPHA 線 |
| `INCONCLUSIVE` | 證據無法回答 contract question；不可包裝為通過或產品輸入 |

Core 收件至少核對：

1. POC delivery path、`audio` branch 與完整 40-character SHA；
2. ASR / VAD / endpoint / postprocess / rescoring 中實際影響結論的 identity、license 與
   controlled artifact locator；
3. 可重現程序、sanitized evidence index、current Audio control 對照或無法直接對照的理由；
4. 收益、成本、失敗路徑、限制、剩餘風險與建議 Core product delta。

Core 對 final handoff 做 evidence intake，不回頭以方法偏好要求 POC 重排研究計畫。身份、
可重現性、privacy 或 conclusion support 不足時，結論維持 `INCONCLUSIVE`；是否投入新一輪由
User 另行決定。

---

## 3. `core-r1` 建立與同步

`core-r1` 不需等待原 `ALPHA Accepted` 或 POC `SUPPORTED` 才能建立。User 確認開線後，
Designer / Developer 可從當時明確、已 commit 的 Core fork SHA 建立
`candidate/asr-r1` linked worktree。建立紀錄必須包含：

- fork branch 與 full SHA；
- worktree path 與 candidate branch；
- fork 當下 `git status --porcelain`；
- 當時 POC outcome / evidence status；
- 允許先行的 branch-neutral 工作與仍被阻擋的 candidate-specific lock / acceptance。

POC input 未足時，`core-r1` 可進行文件、interface-preserving scaffold、fake、validator、
test seam 或不綁定 winner identity 的整合準備；不得以 POC branch HEAD、未定 artifact
或口頭結果固定 production model / dependency / config lock，也不得宣告 Design Ready 或
Accepted。

### 3.1 單向同步

- baseline selection 前只允許 `core → candidate/asr-r1` 同步；R1 產品變更不得提前
  merge 回 `core`。
- R1 分支以標準 merge 取得新 Core 進度，不使用 rebase 改寫歷史。同步後 `core`
  應成為 R1 HEAD 的 ancestor，以保留最終 fast-forward 可能性。
- 任何 candidate-affecting Core sync 都撤銷 R1 freeze，必須對新 exact SHA 重走受影響的
  portable / target gate。
- Candidate SHA 一旦 push、送驗或用於正式驗證，禁止 amend、rebase、reset 或
  force-push；Reject / Fail / Inconclusive 只能 append fix。

---

## 4. R1 產品 gate

| Gate | 直接範圍 | 繼承 / 重驗原則 |
| :--- | :--- | :--- |
| `M4a.R1` | R1 ASR pipeline；包含最終選定的 ASR、VAD / endpoint 與 postprocess / rescoring delta | 受影響的 protocol、adapter、config、lock、lifecycle、offline、resource 與 HAL wiring 全數重驗 |
| `M4b.R1` | LLM compatibility 與共同資源 | LLM behavior / protocol 未變時不重做 model selection；必須重驗 transcript compatibility、composition resource、privacy 與 regression |
| `M4c.R1` | R1 完整 session / display composition | 以 R1 exact SHA 重驗 Listen → ASR → LLM → TTS、failure / recovery 與 sanitized display |
| `M4.R1` | M4a.R1 + M4b.R1 + M4c.R1 結論 | 三個子 gate 必須在同一 Core product exact SHA 通過 |
| `ALPHA.R1` | R1 Voice-only 產品化收斂 | 依 ALPHA 同等類別固定 manifest、session / soak、failure / recovery、resource / thermal、offline、privacy 與 known limits，但使用 R1 identity |

未變的共通證據可以繼承，但每筆繼承必須記錄 source gate / exact SHA、identity
不變理由、R1 delta Test ID 與產品 exact-SHA regression locator。不得只寫「沿用 ALPHA」或
以 POC Pass 取代 Core Tester Pass。

若 POC 建議的 VAD / postprocess 引入新產品 owner、持久狀態、公開 protocol 或跨現有
module boundary，Designer 必須先提 `AR_impl` 交 Architect 裁決；不在 R1 branch 中默認
新架構。

---

## 5. M5 唯一 baseline selection

M5 只能從一個已 Accepted 的 Voice-only baseline 進場。Designer 必須在 M5 工作包前建立
`M5-BASELINE-SELECTION-R1` 紀錄，列出：

- `ALPHA` outcome 與 exact SHA；
- `ALPHA.R1` outcome 與 exact SHA（若該線已成立）；
- POC final outcome / handoff SHA；
- User 選定的唯一 baseline 與理由；
- M5 entry exact SHA 與未入選候選的 frozen / historical disposition。

| 情境 | M5 可用 baseline |
| :--- | :--- |
| POC `NOT_SUPPORTED` / `INCONCLUSIVE`，或 R1 停止 / 未 Accepted | `ALPHA Accepted exact SHA` |
| `ALPHA.R1` Accepted 且 User 選定 R1 | `ALPHA.R1 Accepted exact SHA` |
| 兩候選都 Accepted，User 選定原線 | `ALPHA Accepted exact SHA` |

禁止兩條線同時進入 M5、拼接不同 SHA / run ID / evidence，或先從一條線開始 M5
後再把另一條未驗收的 ASR delta 換入。

若選定 R1，選擇前必須確認當時 `core` HEAD 是 `candidate/asr-r1` 的 ancestor；Core 只能在
User 確認後以 fast-forward 進入已驗收歷史。若選定原 ALPHA，R1 branch 停止開發並保留
不可改寫的歷史與 evidence，不 merge 進 `core`。

---

## 6. 當前進場狀態

| 項目 | 狀態 | 下一動作 |
| :--- | :--- | :--- |
| Core outcome contract | `AUTHORED / AUDIO DELIVERY PENDING` | 完成 Core 紀錄後，將 contract 原樣交付 Audio `docs/pm_handoff/` |
| Audio `asr-r1` worktree | `CREATED ON audio / INTAKE NOT STARTED` | 完成 workspace hub 路徑決策與 contract delivery；POC team 自行 commit receipt |
| Core `core-r1` worktree | `NOT CREATED` | User 確認 fork checkpoint 後才使用標準 Git 命令建立 |
| `M4a.R1` 至 `ALPHA.R1` | `CONDITIONAL / NOT DESIGN READY` | 等待產品 delta 可定義，再完成 design / test coverage gate |
| M5 baseline selection | `PENDING` | M5 工作包前記錄唯一被選定的 Accepted SHA |
