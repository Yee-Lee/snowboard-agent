# Snowboard 實作里程碑 ( milestone.md )

本文件回答 WHEN + VERIFY：定義實作順序、每階段範圍、相依、排除項目與可重複驗收。架構原則以 `arch.md` 為準；Python 契約與演算法以 `implement.md` 及 `implement/` 各定稿章節為準。Display 內容 profile 見 `display_spec.md` ；runtime 模型選型 gate 見 `model_spec.md` 。本文件只維護穩定原則與規劃；階段狀態、定案 gate、跨角色阻擋與下一動作摘要見 `reviews/milestone_progress.md` 。Developer 明細見 `reviews/dev_progress_M{x}.md` ；Tester 明細見 `reviews/test_progress.md` 。Implement 章節狀態與跨章 gate 另見 `reviews/impl_progress.md` 。

---

## M4 MVA revision（2026-09-05）

USER確認M4以最小可行語音架構為目標：M4B完成最小Reasoner與session內連續對話，
M4整合驗speech-end到meaningful audible onset；ALPHA擴大品質/穩定性，實際tool在M5。
2秒目標／3秒上限、10秒恢復是可修訂目標，不是整個計畫no-go條件；
保留原目標、實測、調整理由與新目標，不重標historical result。
[新M4規劃](milestones/M4.md)、[M4B-MVA設計](implement/ch_m4b_llm_production.md)尚待
Architecture/Reviewer/Tester與量測profile，不因USER產品方向確認直接宣告Development Ready。

## 1. 規劃基準

### 1.1 規劃前提

* Core 正式支援 CPython 3.11、3.12、3.13；Developer fast loop 使用團隊指定的單一主要版本，candidate portable gate 必須覆蓋三個 minor。Pi 只跑該 milestone 固定的正式部署 runtime，不將 Python matrix 乘到實體測試。
* Linux / Raspberry Pi OS / Raspberry Pi 5 是 POSIX process signal (`SIGINT` / `SIGTERM`)、native lifecycle、runtime 與硬體驗證的權威平台。
* Windows 僅驗證純 Python、mock / null、config 與 portable subprocess 測試（如 pipe/stream readiness）；明確排除 POSIX process signal 節點驗證，且不得為此修改 production signal architecture。
* 所有文件與驗收命令均使用啟用虛擬環境後的 python 。

### 1.2 階段定案原則

階段從規劃進入實作前，必須同時滿足：

1. 該階段的範圍、相依、排除項目與驗收條件已由使用者確認。
2. Tester 依 `arch.md` 、 `implement/` 、適用的 `display_spec.md` / `model_spec.md` 與本文件產出 `docs/test_spec.md` ，且至少完成該階段的需求──測試對照。
3. 該階段引用的上游契約不存在未解矛盾或無法實作 / 驗證的缺口。
4. Developer 已提供必要估點；估點只影響排程，不改變契約或驗收門檻。
5. 若階段依賴外部 POC，所有會影響開發介面、硬體 fixture 或 artifact provenance 的輸入，必須已有 Core Team 採用紀錄；開發阻擋條件與只阻擋最終驗收的 pending condition 必須分級記入 `reviews/milestone_progress.md`。Developer 工作包須引用已採用的 contract 版本、ACK / Delivery ID、artifact SHA/checksum/license 與已知限制，不得以 POC branch HEAD、自驗結果或未核准 draft 作為 baseline。

各條件的當前完成狀態只記於 `reviews/milestone_progress.md` 。條件未完成前，不得以「已有 milestone 規劃」推定 Developer 已獲准開始該階段。

### 1.3 階段依賴

```text
M1 純軟體核心
 └── M2 Mock 對話垂直切片
      └── M3 Raspberry Pi HAL 與硬體 bring-up
           └── M4 本機 AI 語音主線（M4a + M4b + M4c 同 SHA 通過）
                └── ALPHA Voice-only 產品化收斂 Gate
                     └── M5 外部訊息與工具
                          └── M6 語音喚醒、視覺輸入與整體收斂
                               └── M7 Display UX 完整化
                                    └── BETA 全能力產品收斂 Gate
```

> `ALPHA` 與 `BETA` 為產品成熟度 Gate，不是功能 milestone。`M4 Accepted` 不推定 `ALPHA Accepted`；`M7 Accepted` 不推定 `BETA Accepted`。詳見 `docs/milestones/ALPHA.md` 與 `docs/milestones/BETA.md`。

ASR Product R1 若由 User 開線，使用獨立但不取代原線的條件式產品路徑：

```text
shared Core fork SHA
 ├── original: M4 → ALPHA ──┐
 └── R1: M4a.R1 → M4b.R1 → M4c.R1 → M4.R1 → ALPHA.R1 ──┴── M5 baseline selection → M5
```

R1 branch 可在原 `ALPHA Accepted` 前建立與前進，但只能從已 commit 的明確 Core fork
SHA 開始，且不得取得原線的 gate credit。M5 工作包前必須依
`docs/milestones/ALPHA_R1.md` 完成唯一 baseline selection；`ALPHA` 與 `ALPHA.R1`
不得同時進入 M5。

每條已開立的產品線內，後一階段必須在該線前一階段驗收通過後開始。若前一階段只完成部分功能，不以 feature flag 或「已知失敗」跳過其 gate。

### 1.4 共同完成條件

每個 milestone 除本章特定驗收外，皆須滿足：

* 新增或修改的契約行為有自動化測試；async race 使用 `asyncio.Event` / 明確 barrier，不以 wall-clock sleep 猜時序。
* `python -m pytest -v` 全數通過，且不得刪除、skip 或 xfail 先前 milestone 的驗收來 取得綠燈。
* 測試與 log 不包含 credential、prompt、完整 payload、transcript、音訊或影像內容。
* Windows 可執行的 pure-Python / mock 測試不得意外 import Pi-only dependency。
* Pi-only 驗收明確標記，且在 Raspberry Pi 5 上保存命令、版本、config 與結果摘要。
* 含 Pi 或人工驗收的 milestone 自 M4 起依 `docs/roles/workflow.md` §4 執行 portable-first candidate gate：三版本 portable matrix 全綠後才 review / freeze；target preflight 與正式 acceptance 只接受同一外部指定 SHA，debug evidence 不得混入。
* 若實作發現定稿契約不可落實，停止該項實作並交回 Designer；涉及架構邊界時再交 Architect，不在 code 中自行發明另一套契約。

### 1.5 Designer 輔助規格文件產出時機

以下兩份文件由 Designer 產出，不在 implement/ 章節範圍內，但為後期里程碑的進場 gate 所需：

* `docs/display_spec.md`：最晚於 **M2 驗收期間**完成。M3 進場 gate 要求 selected profile 已納入 Tester 的 test spec 與 Developer 工作包（§5.2）。M1 / M2 不依賴本文件。

* `docs/model_spec.md`：M3驗收期間先建立schema與未定欄位。M4 generic protocol / fake scaffold不等待runtime baseline；Audio M2B reviewed selection後才可填入candidate-specific provisional設定，Audio M3 target/HAL qualification後才可準備產品exact-SHA acceptance，Gate 2B final handoff後才固定ASR / TTS production baseline。LiteRT-LM依M4b gate另行固定；M6進場仍依賴M6 baseline（§8.2）。M1 / M2 / M3不依賴本文件。

兩份文件均不阻擋 M1 / M2 立即啟動。

---

## 2. 階段總覽

| 階段 | 主要成果 | 主要平台 | 契約來源 |
| :--- | :--- | :--- | :--- |
| **M1** | 基礎契約、事件、Bus、SM、RM、三級收斂、config、logging 的純軟體核心 | 開發機 | `Ch 1 / 2 / 3 / 4 / 5 / 6 / 10 / 11` |
| **M2** | 使用 mock / null 完成可啟動、可對話、可收斂的垂直切片 | 開發機 | `Ch 2a / 2b / 7 / 9` |
| **M3** | Raspberry Pi 5 真實 HAL、null fallback 與 selected Display profile | Raspberry Pi 5 | `Ch 2a / 5 / 8 / 10 / 11`、`display_spec.md` selected profile、Core 已採用的 Audio / Display POC contract |
| **M4** | M4a Audio、M4b LLM、M4c Session Display 全數通過的本機語音主線 | Raspberry Pi 5 | `Ch 2b / 4 / 5 / 6 / 9 / 10 / 11`、M2B後的provisional model recipe與Gate 2B後的final model baseline |
| **ALPHA** | Voice-only 產品化收斂 Gate：固定 hardware / config / model / dependency / manifest，驗證可重現 session / soak / failure / recovery / shutdown / resource / privacy | Raspberry Pi 5 | `docs/milestones/ALPHA.md`；M4 Accepted exact SHA |
| **ALPHA.R1** | 條件式 ASR Product R1 Voice-only 收斂 Gate；不改寫或取代原 ALPHA 結論 | Raspberry Pi 5 | `docs/milestones/ALPHA_R1.md`；M4.R1 Accepted exact SHA |
| **M5** | 依 baseline selection 選定的唯一 ALPHA 或 ALPHA.R1 Accepted exact SHA 擴充 MQTT、read 與 tool dispatch | Raspberry Pi 5 | `Ch 2b / 7 / 9 / 10 / 11` |
| **M6** | Wake daemon、voice-wake IPC、Vision/look 與全能力驗收 | Raspberry Pi 5 | `Ch 2a / 2b / 4 / 5 / 6 / 8 / 10 / 11`、`model spec M6 baseline` |
| **M7** | 正式 Display 版面、資產、動畫與視覺 UX 完整化 | Raspberry Pi 5 | `Ch 8`、M7 開發前核准的 `display_spec.md` revision |
| **BETA** | 全能力產品收斂 Gate：在同一 Beta 候選 SHA 重跑 M4 ~ M7 regression，涵蓋長時間穩定、診斷、manifest inventory | Raspberry Pi 5 | `docs/milestones/BETA.md`；M7 Accepted exact SHA |

---


> **注意**：各階段詳細規劃已拆分至 `docs/milestones/M{x}.md`；產品收斂 Gate 另見 `ALPHA.md`、`ALPHA_R1.md` 與 `BETA.md`。Agent 只應讀取當前進行中或任務直接影響的檔案。

## 10. 規劃維護原則

### 10.1 估點與範圍調整

工期與估點由 Developer 提供，統一記於 `reviews/dev_progress_M{x}.md` ，不寫回本文件。Designer 只把因此產生的 gate、跨角色阻擋或階段影響摘要到 `reviews/milestone_progress.md` 。估點變更不直接修改驗收條件；若估點顯示單一階段範圍過大，由 Designer 拆分階段並重新確認其相依與驗收。只有階段切分、穩定範圍或驗收原則改變時才修改本文件。

### 10.2 docs/protocol.md 動筆 gate

`docs/protocol.md` 不在 M1 / M2 預先展開；以下任一階段開始前必須先完成對應章節：

* **M4** : LiteRT-LM child process wire schema。
* **M5** : 公開 MQTT topic / payload schema。
* **M6** : wake daemon IPC schema。

每個 wire schema 必須先於其 producer / consumer code，並明列版本與 breaking-change 政策；內部 Event dataclass 不因此增加 version 欄位。
