# Review Note — ASR Post-Correction Direction

**日期**：2026-08-23
**角色**：Reviewer
**依據 SHA**：`b21a8e9`（`audio` branch HEAD）
**主題**：ASR 輸出修正的 POC 邊界與產品化建議方向

---

## 背景

M2B 已提出 base Q8 primary + small Q8 fallback，兩者均使用 P0+greedy+fixed domain
prompt。M2A/M2B evidence 顯示 fixed prompt 改善 Internal 辨識但造成 Common Voice
+1 edit regression。ASR raw transcript 中仍存在 systematic mishearing patterns。

User 提出是否在 ASR 之後加入 lexicon post-correction 層，類似手機語音輸入的修正
機制。經討論後確認方向如下。

---

## 重點 1：POC Delivery 須記錄未來優化方向

Post-ASR correction 不改變 baseline 選擇，不屬於 POC scope，不排入任何新
milestone。但 **M4 delivery package §7（產品化建議）必須包含**：

- 從 M2A/M2B evidence 中提取的 systematic mishearing patterns 分類與出現頻率。
- 建議的 correction 架構位置（post-decoder、不進入 Audio HAL 或 ASR engine 內部）。
- 已驗證的 prompt-based bias 效果與侷限（Internal 改善、Common Voice regression）。
- 明確標示此為 Core 接手後的產品優化工作，POC 不做實作或驗證。

POC 的交付物是 **raw baseline + 觀察到的 error patterns + 建議方向**。Core 拿到後
自行決定實作方式與排程。

---

## 重點 2：只關注 LLM 無法自行解決的辨識錯誤

### 不需要 POC 處理的（downstream LLM 可自行理解）

數字、日期、百分比等 display normalization 差異：

| ASR 輸出 | 「正確」格式 | 理由 |
|----------|-------------|------|
| 二〇二六 | 2026 | LLM 理解無障礙 |
| 二十三度 | 23° | LLM 理解無障礙 |
| 一月十五號 | 1/15 | LLM 理解無障礙 |
| 百分之八十 | 80% | LLM 理解無障礙 |

這類差異是 format preference，不是辨識錯誤。在 ASR→LLM 的 pipeline 中，LLM 接收
的語意完全正確。投入資源做 number/date canonicalization 對最終產品品質無貢獻。

### 需要關注的（ASR 聽錯，LLM 無法還原原始語音）

同音、近音、聲調混淆導致的 **語意偏移**：

| ASR 輸出 | 實際說的 | 問題 |
|----------|---------|------|
| 確實 | 測試 | 近音混淆，語意完全不同 |
| 那個 | 哪個 | 聲調混淆，陳述 vs 疑問 |
| 適應 | 是硬（體） | domain 詞被拆解為通用詞 |

LLM 收到的文字語意已經偏移，無論模型多強都無法得知「使用者原本說了什麼聲音」。
這類錯誤只能在離聲音最近的地方（ASR 出口或 decoder 內部）處理。

### 對 Core 的建議方向

手機語音輸入的修正並非靜態字典替換，而是多層機制。手動編寫 lexicon dictionary
存在不完備、脆弱（換 model 即失效）、false correction 風險高、維護成本持續等
根本問題，不建議採用。

可行的產品方向（由 Core 評估與選擇）：

| 層級 | 方法 | 適用性 |
|------|------|--------|
| Decoder 內部 | N-best re-scoring with domain LM | 最有效，需自建 LM |
| Decoder 偏置 | Hotword / keyword boosting | whisper.cpp prompt 是弱版；可探索更強的 bias 機制 |
| Post-decoder | 結合對話 intent/state 的上下文修正 | 需要產品層 state 資訊，POC 無法模擬 |
| Personalization | 從用戶互動歷史學習 | 完全是產品層工作 |

POC 已驗證 decoder 偏置（fixed prompt）的效果與邊界。更深入的方向屬於產品工程。

---

## 結論

- POC 不新增 milestone，不延伸時程，不做 post-correction 實作。
- M4 delivery §7 須包含 error pattern report 與未來優化建議。
- 區分 LLM 可解決的格式差異與 LLM 無法還原的辨識錯誤，只記錄後者。
- 靜態 lexicon dictionary 不推薦；建議 Core 從 decoder bias 或 context-aware
  correction 方向評估。
