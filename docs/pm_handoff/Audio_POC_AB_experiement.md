# Audio POC A / B 分組觀察計畫

> **對象**：Audio POC Team
>
> **Owner**：內部 Designer
>
> **狀態**：Ready for PM；尚未交付

---

## 結論

保留現有 A+B 結果；只針對有產品潛力的 `small Q8`、`base Q8` 補做分組觀察。`medium Q5` 速度過慢，不列入產品候選；可零成本重算既有 evidence 作為品質天花板，不安排重新執行。

本輪只回答一個問題：在既有相同執行條件下，A 與 B 的辨識品質是否不同、差多少？唯一分析變因是 fixture group；不得同時改模型、decoder、prompt、frontend、endpoint 或 scoring。

---

## 背景與假設

- 現行 M2A 為 internal 8 加 Common Voice 12；`small Q8` 的 A+B sentence correctness 為 55%。
- `Small Q8` 過去 internal-only 50 筆為 full-input 28%、bounded/native 34%。因 fixture、build 與 method 不同，歷史值只作背景，不得與本輪合併計分。
- 本輪主要假設是 B 可能明顯優於 A；先量出差距，再以不改變輸入與模型的伴隨觀察，判斷下一輪應優先調查 frontend / endpoint、domain handling 或模型容量。

---

## 測試觀察

使用相同逐筆 report、fixture identity 與 scoring，分別輸出：

- **A**：internal recordings。
- **B**：Common Voice samples。
- **A+B**：保留現行固定 8:12 組合結果。

每個 candidate 並列表列：

- `exact correct / total`、`sentence correctness`、`CER`。
- `Sentence gap = B sentence correctness - A sentence correctness`；正值表示 B 較好。
- `CER improvement = A CER - B CER`；正值表示 B 的 CER 較低。
- `latency / RTF / RSS` 僅沿用既有數據作描述，不在本輪作優化變因。

不得丟棄或改寫既有 A+B evidence。只有逐筆 evidence 遺失、SHA / fixture identity 不符時才補跑，且只補缺項。

`Small Q8` 歷史 internal-50 結果（full input 28%、bounded/native 34%）只作跨 packet 參考，不與本輪不同 fixture / method 合併計分。

---

## 固定條件

- 使用現有 exact artifact、runtime、threads、decoder 與 20-item fixture lock。
- A 固定為現行 internal 8；B 固定為現行 Common Voice 12；A+B 固定為 8:12，不重新加權。
- 逐筆 evidence 必須對上既有 report SHA；不得排除錯誤樣本或新增樣本。

本 handoff 不授權新 microphone capture、acoustic replay、DSP、endpoint、prompt、keyword、normalization 或其他 tuning。A / B 結果確認後，優化方向另立 follow-up，避免混淆歸因。

---

## 次要觀察因子（只產生假設）

以下項目必須使用同一批 exact PCM / 逐筆結果計算，不得修改音訊或重新推論：

1. **訊號特徵**：每筆 duration、RMS dBFS、peak dBFS、DC offset、s16 saturation / clipping count。Silence ratio 或 SNR 只有已有凍結定義時才可列入，不得看到結果後自訂 threshold。
2. **錯誤型態**：每組 insertion / deletion / substitution totals；A 另列 Mandarin、code-switch、number/date、product term 的 `exact correct / total` 與 `CER`。完整 transcript 留在 controlled evidence，Git 只放 sanitized counts。
3. **同筆候選配對**：對 `small Q8` 與 `base Q8` 的相同 fixture，分 A、B 統計 `both correct`、`small-only correct`、`base-only correct`、`both wrong`，觀察容量差異是否集中於 A 或 B。
4. **關聯摘要**：分 A、B 比較 correct 與 incorrect items 的上述訊號特徵中位數 / 範圍。樣本只有 8 / 12，不做顯著性宣告、不新增 pass/fail threshold。

這些伴隨因子不改變本輪主結論；不得因相關性直接寫成錄音品質、endpoint 或 domain 的因果。

---

## 結果解讀與下一輪方向

- 若 `small Q8`、`base Q8` 都是 B 明顯高於 A，且 A 的錯誤與低 RMS、clipping、DC、長靜音或邊界特徵同向：下一輪優先提出一個 frontend / endpoint 單變因 probe。
- 若 A 的一般 Mandarin 接近 B，但 code-switch、number/date、product term 明顯較差，且訊號特徵沒有一致關聯：下一輪優先提出 prompt / keyword / normalization 單變因 probe；數字與控制值不得靜默猜測修正。
- 若 `small Q8` 在 A 的同筆配對明顯優於 `base Q8`，而兩者在 B 接近：記為模型容量 / domain robustness 假設。
- 若 A、B 都差：不要先做 frontend tuning，回報模型或 scoring / normalization 能力限制。
- 若 A、B 接近：55% 不可主要歸因於 Common Voice 混入；歷史差異另按 fixture / build / method 調查。

任何優化實驗都必須在本輪結果 review 後另立 handoff；一次只允許一個 named variable。

---

## 完成條件

- 一份 A / B / A+B 並列表與候選解讀。
- 一份 sanitized 次要觀察表，包含訊號特徵、錯誤型態及同筆候選配對；缺少凍結定義的欄位明確標示未計算。
- 保留 raw / sanitized 分離、evidence checksum 與執行 SHA。
- 清楚聲明 A / B 為不同語料 / 講者的分組觀察，不能單獨證明錄音品質因果，也不自行宣告 winner。

---

## 必須提交的實際數據

只提交文字結論或 aggregate 百分比不算完成。POC Team 必須在 repo 提交可供內部重新計算的 sanitized data：

1. `poc_audio/evidence/m2/M4A-M2A-AB-SPLIT-001/items.sanitized.json`
   - `small Q8`、`base Q8` 各 exact 20 筆，共 40 records。
   - 每筆至少包含 candidate ID、fixture ID、family、category、reference length、hypothesis length、edit distance、sentence correct、latency、RTF、peak RSS、hypothesis hash、原 formal-row SHA-256。
   - **禁止** reference text、hypothesis text、PCM、絕對 controlled path 或私人資料。
2. `poc_audio/evidence/m2/M4A-M2A-AB-SPLIT-001/summary.json`
   - A、B、A+B 的 numerator / denominator、sentence correctness、CER numerator / denominator、latency / RTF / RSS 與明確 delta。
   - A+B 必須精確重現既有 scorecard；包含重算命令與輸入 SHA-256。
3. `poc_audio/evidence/m2/M4A-M2A-AB-SPLIT-001/README.md`
   - Evidence identity、方法、缺失欄位、限制、結果解讀及 reproduction command。
4. 若有做訊號特徵，再提交 `signal_features.sanitized.json`；若沒有 exact PCM 或 frozen 定義，明確標示未執行，不得估造數值。

上述 committed sanitized data 是本輪 review 的必要輸入；只提供 Pi 私有路徑或未提交檔案的 hash，不足以完成內部 intake。

---

## 回覆

請在 POC repo 提交分組表、候選解讀、evidence path、branch 與完整 HEAD SHA；建議回覆路徑：`poc_audio/deliveries/RESP-AUDIO-M2A-AB-SPLIT-001.md`。
