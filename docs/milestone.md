# Snowboard 實作里程碑 ( milestone.md )

本文件回答 WHEN + VERIFY：定義實作順序、每階段範圍、相依、排除項目與可重複驗收。架構原則以 `arch.md` 為準；Python 契約與演算法以 `implement.md` 及 `implement/` 各定稿章節為準。Display 內容 profile 見 `display_spec.md` ；runtime 模型選型 gate 見 `model_spec.md` 。本文件只維護穩定原則與規劃；階段狀態、定案 gate、跨角色阻擋與下一動作摘要見 `reviews/milestone_progress.md` 。Developer 明細見 `reviews/dev_progress_M{x}.md` ；Tester 明細見 `reviews/test_progress.md` 。Implement 章節狀態與跨章 gate 另見 `reviews/impl_progress.md` 。

---

## 1. 規劃基準

### 1.1 規劃前提

* Python 最低版本為 3.11。
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
           └── M4 本機 AI 語音主線
                └── M5 外部訊息與工具
                     └── M6 語音喚醒、視覺輸入與整體收斂
                          └── M7 Display UX 完整化
```

後一階段必須在前一階段驗收通過後開始。若前一階段只完成部分功能，不以 feature flag 或「已知失敗」跳過其 gate。

### 1.4 共同完成條件

每個 milestone 除本章特定驗收外，皆須滿足：

* 新增或修改的契約行為有自動化測試；async race 使用 `asyncio.Event` / 明確 barrier，不以 wall-clock sleep 猜時序。
* `python -m pytest -v` 全數通過，且不得刪除、skip 或 xfail 先前 milestone 的驗收來 取得綠燈。
* 測試與 log 不包含 credential、prompt、完整 payload、transcript、音訊或影像內容。
* Windows 可執行的 pure-Python / mock 測試不得意外 import Pi-only dependency。
* Pi-only 驗收明確標記，且在 Raspberry Pi 5 上保存命令、版本、config 與結果摘要。
* 若實作發現定稿契約不可落實，停止該項實作並交回 Designer；涉及架構邊界時再交 Architect，不在 code 中自行發明另一套契約。

### 1.5 Designer 輔助規格文件產出時機

以下兩份文件由 Designer 產出，不在 implement/ 章節範圍內，但為後期里程碑的進場 gate 所需：

* `docs/display_spec.md`：最晚於 **M2 驗收期間**完成。M3 進場 gate 要求 selected profile 已納入 Tester 的 test spec 與 Developer 工作包（§5.2）。M1 / M2 不依賴本文件。

* `docs/model_spec.md`：最晚於 **M3 驗收期間**完成。M4 進場 gate 要求 ASR / TTS / LiteRT-LM 的 M4 baseline 已固定（§6.2）；M6 進場 gate 同樣依賴 M6 baseline（§8.2）。M1 / M2 / M3 不依賴本文件。

兩份文件均不阻擋 M1 / M2 立即啟動。

---

## 2. 階段總覽

| 階段 | 主要成果 | 主要平台 | 契約來源 |
| :--- | :--- | :--- | :--- |
| **M1** | 基礎契約、事件、Bus、SM、RM、三級收斂、config、logging 的純軟體核心 | 開發機 | `Ch 1 / 2 / 3 / 4 / 5 / 6 / 10 / 11` |
| **M2** | 使用 mock / null 完成可啟動、可對話、可收斂的垂直切片 | 開發機 | `Ch 2a / 2b / 7 / 9` |
| **M3** | Raspberry Pi 5 真實 HAL、null fallback 與 selected Display profile | Raspberry Pi 5 | `Ch 2a / 5 / 8 / 10 / 11`、`display_spec.md` selected profile、Core 已採用的 Audio / Display POC contract |
| **M4** | M4a Audio、M4b LLM、M4c Session Display 全數通過的本機語音主線 | Raspberry Pi 5 | `Ch 2b / 4 / 5 / 6 / 9 / 10 / 11`、`model spec M4 baseline` |
| **M5** | 依 Accepted M4 exact SHA 擴充 MQTT 外部訊息、read 流程與實際 tool dispatch | Raspberry Pi 5 | `Ch 2b / 7 / 9 / 10 / 11` |
| **M6** | Wake daemon、voice-wake IPC、Vision/look 與全能力驗收 | Raspberry Pi 5 | `Ch 2a / 2b / 4 / 5 / 6 / 8 / 10 / 11`、`model spec M6 baseline` |
| **M7** | 正式 Display 版面、資產、動畫與視覺 UX 完整化 | Raspberry Pi 5 | `Ch 8`、M7 開發前核准的 `display_spec.md` revision |

---


> **注意**：各階段詳細規劃已拆分至 `docs/milestones/M{x}.md`，Agent 只應讀取當前進行中 Milestone 的檔案。

## 10. 規劃維護原則

### 10.1 估點與範圍調整

工期與估點由 Developer 提供，統一記於 `reviews/dev_progress_M{x}.md` ，不寫回本文件。Designer 只把因此產生的 gate、跨角色阻擋或階段影響摘要到 `reviews/milestone_progress.md` 。估點變更不直接修改驗收條件；若估點顯示單一階段範圍過大，由 Designer 拆分階段並重新確認其相依與驗收。只有階段切分、穩定範圍或驗收原則改變時才修改本文件。

### 10.2 docs/protocol.md 動筆 gate

`docs/protocol.md` 不在 M1 / M2 預先展開；以下任一階段開始前必須先完成對應章節：

* **M4** : LiteRT-LM child process wire schema。
* **M5** : 公開 MQTT topic / payload schema。
* **M6** : wake daemon IPC schema。

每個 wire schema 必須先於其 producer / consumer code，並明列版本與 breaking-change 政策；內部 Event dataclass 不因此增加 version 欄位。
