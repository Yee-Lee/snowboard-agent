# REQUEST-VOICE-POC-RVC-MATCHA-001：角色音色 Audio Voice POC 任務規格

- **Delivery ID**: `REQUEST-VOICE-POC-RVC-MATCHA-001`
- **Date**: 2026-10-26
- **From**: Core Designer
- **Owner**: Voice POC (`voice` branch)
- **Status**: `OPEN — P0 / P2 / P3 READY TO START`
- **Source input**: [`docs/outsource/pm_handoff/proposal_voice_poc.md`](../../pm_handoff/proposal_voice_poc.md)
- **Fork baseline**: tag `core_alpha` (`9dd36c096e1670c49ce23c82c01b8002daef9971`) → branch `voice`
- **Execution platform**:
  - **P0 – P4（資料處理、RVC 訓練、Matcha-TTS 微調、ONNX 匯出與離線合成試聽）**：固定於 **Apple Silicon arm64 原生環境**（PyTorch `mps` 加速，啟用 `PYTORCH_ENABLE_MPS_FALLBACK=1`）；**不在 x86 虛擬機執行訓練或批次轉換**。
  - **P5（整機共存與實體喇叭驗證）**：固定於 **`Raspberry Pi 5`**（僅跑 `sherpa-onnx==1.13.5` CPU 推論，不在 Pi 訓練）。
- **Current TTS control baseline**: [`docs/model_spec.md` §2.3](../../../model_spec.md#23-tts) — `tts-sherpa-matcha-zh-en-1.13.5`（`sherpa-onnx==1.13.5`、`matcha-icefall-zh-en/model-steps-3.onnx`、`vocos-16khz-univ.onnx`、`sid=0`、CPU 2 threads、16 kHz mono S16_LE）
- **Product schedule boundary**: 與主線 `M5 MQTT → M6 Look → M7` 並行且不阻擋既有排程；於 `M7 Accepted` 後、`BETA` 設計前決定是否啟動正式 TTS baseline 變更。

---

## 1. 目標與研究問題

為雪板／Ollie 探索以 Anne Hathaway 聲音特徵為目標、能自然說中文（兼顧中英混說）、符合「精簡、幽默、帶點歪理」角色感的本機離線語音，並評估能否在 Raspberry Pi 5 現有完整離線語音 App 中以可接受的反應時間、音質與整機資源運作。

本階段為**獨立技術 POC**，不直接替換現有 M4a／ALPHA Matcha-TTS 產品鎖定，也不以素材使用範圍／授權作為本 POC 的技術阻塞項（未來若公開展示、分享模型或納入正式產品再單獨確認，不得於紀錄中寫成已取得授權）。

### 1.1 優先回答的三個問題

1. **跨語系 RVC 音色轉換（P2）**：以英文目標音源訓練的 RVC，能否將原本咬字與聲調清楚的中文女聲轉為「中文四聲自然、咬字清晰且音色值得繼續追求」的目標音色？
2. **少量轉換語料訓練與匯出 TTS（P3 → P4）**：能否打通上游 Matcha-TTS `.pt` 訓練與 ONNX 匯出閉環，並以少量 RVC 轉換後的中文語料微調／訓練出可由 `sherpa-onnx==1.13.5` 推論、兼顧中文清晰度與目標音色的模型？
3. **Pi 5 整機共存與體驗（P5）**：新模型能否在完整 Pi App 與 ASR／Gemma 4 E2B／Display 共存時，達到可接受的首段出聲延遲、整句合成時間與峰值記憶體（RSS）？

---

## 2. 技術基準與風險邊界

1. **推論規格 ≠ 可微調環境**：
   - 現有產品鎖定為 `sherpa-onnx==1.13.5` 推論產物（`model-steps-3.onnx` + `vocos-16khz-univ.onnx`，`sid=0`）。
   - 上游來源指向 ModelScope `dengcunqin/matcha_tts_zh_en_20251010`（[`model_spec.md` §2.3](../../../model_spec.md#23-tts) 記錄對照 commit 為 `f05803ec98df733d5775dfb0c40a919ae699cfb6`）。其 `.pt` checkpoint 與現行 ONNX 的結構對應、訓練 recipe、中英前端（`lexicon.txt`、`tokens.txt`、rule FSTs、`espeak-ng-data`）及匯出相容性，必須在 **P3** 實測確認。
2. **禁止未驗證假設**：
   - 不得預設「凍結 text encoder、只更新 speaker embedding 就能保證標準中文＋目標音色」（現有模型 `sid=0` 不代表可直接替換 speaker embedding）。
   - 不得預設「20 分鐘素材完美足夠」、「RVC 蒸餾徹底消除外國腔」、「一行秒級匯出 ONNX」或「Pi 上必然毫秒級延遲」。
   - RVC 轉換可能破壞中文四聲或帶入金屬音，TTS 二次訓練亦可能放大瑕疵；必須先通過小樣本驗證再決定是否擴充語料。
3. **驗證精簡原則**：
   - 實驗只針對可說明的產品失敗風險（聲調失真、金屬音、前端／ONNX 不相容、Pi 整機延遲與記憶體超限）。
   - 不在測試或啟動流程加入自動 SHA／digest 斷言、角色互簽、freeze 或行政 closure；試聽內容與音檔留於 private 環境判讀，公開紀錄只留必要的 boolean、count、時間／記憶體量測與具體失敗句編號。

---

## 3. 分階段執行計畫（P0 – P5）

`P2` 與 `P3` 可並行推進；**兩者皆通過前進條件後，才可啟動 `P4`**。

| 階段 | 最小工作／交付 | USER 人工工作 | 自動化與算力 | 前進條件（Gate） |
| :--- | :--- | :--- | :--- | :--- |
| **P0 目標與比較樣本** | 固定 8–12 句中文／中英混說雪板台詞（含四聲易混詞、短句、長句、幽默歪理語氣）；保存現有 Matcha `sid=0` 基準輸出 | 選台詞、說明「像」與「自然」的優先順序（中） | 生成基準音與紀錄可自動化；無訓練 | 具備可重播的同句比較基準與固定判讀項目 |
| **P1 20 分鐘素材盤點** | 記錄英文目標音源來源與可用時長；切句、去除重疊人聲／強背景音／過度戲劇化片段，保留未訓練參考片段 | 親聽、挑片段（中高） | 切句、格式統一、初篩可批次；本機 CPU／一般加速 | 得到單人、音色相對一致的英文訓練集與獨立參考集 |
| **P2 RVC 最小試驗** | 訓練第一版 RVC，只轉換 P0 的 8–12 句中文女聲；與中文原聲、P0 Matcha 基準、英文目標參考對照 | 逐句試聽中文聲調、清晰度、音色相似感、金屬音（中） | 訓練及批次轉換可腳本化；需可用加速資源，實測記錄耗時 | 中文可懂、四聲保留，且音色有值得追求的提升；否則先修資料／RVC 或停止本路徑 |
| **P3 TTS 路徑核查** | 清點上游 `.pt`、config、訓練 recipe、tokens／lexicon、16 kHz Vocos 與現有 ONNX 版本關係；用普通中文小資料完成「載入→短訓→匯出→離線合成」 | 聽一個技術 smoke 樣本；主要工程判讀（低） | 程式與環境核查為主，短訓需 GPU；在大批資料轉換前完成 | 確認可重現的訓練與 `sherpa-onnx==1.13.5` 輸出；若不相容，評估另一可訓練 TTS 與 Core adapter 影響 |
| **P4 小批 TTS** | 只轉換一小批中文訓練語料，保留未見測試句；訓練一版新音色 TTS，與 P0 基準及 P2 RVC 輸出對照 | 抽查轉換資料與 checkpoint、判斷未見句是否兼顧中文自然度與目標音色（中高） | 轉換與訓練可批次；依 P2/P3 實測成本決定規模，不預設數小時語料 | 未見句的中文仍清晰、自然且音色有價值；否則調整或停止，不直接擴充到數小時 |
| **P5 擴充與 Pi 整合** | 必要時擴充資料與模型；在 Pi 5 以現有完整 App 測首段出聲、整句時間、峰值 RSS、中英混說、中斷、重新使用及聽感 | 真人操作、聽感與採用判斷（中高） | 測量可自動化；Pi 5 CPU 推論（不在 Pi 訓練） | 對照 ALPHA 基準，產出 `SUPPORTED`／`NOT_SUPPORTED`／`INCONCLUSIVE` 結論供 BETA 前決策 |

---

## 4. 兩個最小實驗規格（P2 與 P3）

### 4.1 實驗一：P2 — RVC 跨語系音色轉換最小試驗

- **前置輸入**：
  1. P0 固定的 8–12 句雪板台詞清單（編號 `S01`–`S12`）與現行 Matcha `sid=0` 16 kHz 基準音檔。
  2. 一組咬字清楚、聲調自然、語氣貼近角色的中文女聲朗讀原音（同 `S01`–`S12`）。
  3. P1 清理後的 Anne Hathaway 英文單人訓練集（記錄實際可用分鐘數、採樣率、切句數）與保留未訓練的英文參考片段。
- **執行步驟**：
  1. 在核准的 arm64 原生訓練環境訓練第一版 RVC 模型，記錄訓練 epoch、耗時與記憶體／顯存峰值。
  2. 將 `S01`–`S12` 中文女聲原音經 RVC 轉換（測試必要之 f0 提取方法與 index rate 設定），輸出 16 kHz/原始採樣率對照音檔。
- **判讀基準（USER 主觀試聽 + 失敗句紀錄）**：
  對每句 `S01`–`S12` 獨立記錄三個面向（`PASS` / `BORDERLINE` / `FAIL` 與具體瑕疵描述）：
  1. **中文可懂度與四聲保持**：是否出現聲調扁平化、洋腔走調、吞字或子音模糊。
  2. **目標音色相似感**：相較中文原聲與 P0 Matcha 基準，是否具備可辨識的目標聲音特質，且無明顯金屬音／電音偽影。
  3. **雪板角色語氣**：短句俐落度、中英混說銜接與幽默歪理語氣是否自然。
- **Exit 判定**：
  - **PASS（可進 P4）**：多數固定句在三個面向達可接受水準，無系統性四聲崩壞或嚴重金屬音。
  - **ITERATE / STOP**：若出現系統性聲調跑掉或金屬音，先定位是中文底聲不合、英文素材混雜或 RVC f0/index 參數問題並做單輪修正；若仍無法兼顧中文四聲與目標音色，直接回報 `NOT_SUPPORTED` 並停止，不進入 P4。

### 4.2 實驗二：P3 — Matcha-TTS 上游訓練與 `sherpa-onnx` 匯出路徑核查

- **前置輸入**：
  1. 上游模型庫 `ModelScope dengcunqin/matcha_tts_zh_en_20251010`（核對 `f05803ec98df733d5775dfb0c40a919ae699cfb6` 與最新 revision）。
  2. 現行產品推論規格：`sherpa-onnx==1.13.5`、`matcha-icefall-zh-en.tar.bz2`（含 `model-steps-3.onnx`、`lexicon.txt`、`tokens.txt`、rule FSTs、`espeak-ng-data`）與 `vocos-16khz-univ.onnx`。
- **執行步驟（在批次轉換大量語料前完成）**：
  1. **清點與核對**：列出上游 `.pt` checkpoint 確切檔名、revision、模型結構／config、所需中英前端（phoneme/token 映射）與訓練 recipe；確認該 `.pt` 是否能直接匯出為與現行 `model-steps-3.onnx` 相同介面的 ONNX。
  2. **最小閉環 Smoke Test**：使用極小量普通中文女聲語料（如數十句乾淨樣本，不依賴 RVC 大量轉換），執行「載入上游 `.pt` → 短暫微調數步 → 匯出 ONNX（寫入 `sherpa-onnx` 所需 metadata）→ 搭配 `vocos-16khz-univ.onnx` 由 `sherpa-onnx==1.13.5` 合成 P0 中英混說句子」。
  3. **資源量測**：記錄微調單步／每百步耗時、GPU/統一記憶體峰值與匯出後 ONNX 檔案大小。
- **Exit 判定**：
  - **PASS（可進 P4）**：微調後匯出的 ONNX 可由 `sherpa-onnx==1.13.5` + `vocos-16khz-univ.onnx` 正常載入並輸出 16 kHz mono S16_LE 音訊，中英混說前端（tokens/lexicon）無缺字崩潰或採樣率／聲碼器錯配。
  - **BLOCKED / 替代評估**：若上游 `.pt` 與 `sherpa-onnx` 中英前端或 `vocos-16khz-univ.onnx` 不相容、或缺訓練／匯出關鍵腳本，立即記錄具體斷點，並評估替代可訓練中英 TTS 模型及其對 Core TTS adapter 的影響，不盲目啟動 P4。

---

## 5. 待定項目與立即下一步

1. **確認訓練路徑（P3 優先）**：列出 ModelScope `.pt` 的確切檔案、修訂版、模型結構／config、中英前端與訓練 recipe，實測能否重現 `sherpa-onnx==1.13.5` 相容之 ONNX。
2. **中文來源語料選型（P2 準備）**：挑選一個咬字與角色韻律合適的中文女聲來源（確認音檔品質與 transcript／切句對齊；AISHELL-3／DataBaker 等僅為公開資料集候選，先抽樣驗證 8–12 句，不預先假設需轉換 5–10 小時）。
3. **算力配置盤點（鎖定 Apple Silicon arm64）**：P0–P4 統一在 arm64 原生環境執行（配置 PyTorch `mps` 與 `PYTORCH_ENABLE_MPS_FALLBACK=1`，排除 x86 虛擬環境）；由 P2／P3 小試驗實測單步／每 epoch 時間與統一記憶體峰值後，再估算 P4 訓練成本。
4. **固定 P0 台詞與三軸試聽表**：與 USER 敲定 8–12 句雪板代表台詞，建立「中文可懂與聲調／音色相似感／雪板角色語氣」三軸評估紀錄表。
5. **產品納入分界**：若 POC 最終達標（`SUPPORTED`），於 M7 Accepted 後、BETA 設計前由 Core Designer 定義新的 TTS baseline（[`model_spec.md` §5](../../../model_spec.md#5-accepted-risk-and-change-control)）、artifact provenance 與 Core adapter delta，再依 `Design → Test Spec → Developer → Verify` 在 Pi 上以同 bytes 驗收。
