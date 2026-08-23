# Audio POC 最終繳交清單

對象：Audio POC 團隊
Owner：內部 Designer
狀態：Ready for PM delivery；不代表 PM 已交付

## 結論

交付必須包含可重現程式、候選比較、Pi 5 證據、cleanup 證據與產品化建議。Demo、簡報或只有摘要數字不能進入正式 review。

## 1. Delivery manifest

- [ ] Delivery ID：`POC-audio-DEL-YYYY-NNN-RN`
- [ ] POC repo、branch、完整 40 字元 commit SHA 與 baseline SHA。
- [ ] 環境、硬體、執行命令、結果與 evidence 路徑。
- [ ] 已知限制；若回覆 finding，列出原 Finding ID、修訂位置與驗證命令。

Manifest 放在 `poc_audio/deliveries/`；evidence 索引放在 `poc_audio/evidence/`

## 2. 可重現程式

- [ ] Python 3.11 以上的 lockfile / container 或完整 setup。
- [ ] Benchmark harness、result schema、fixture catalog 與 deterministic fake。
- [ ] VAD、ASR、TTS candidate wrapper 與必要 tests。
- [ ] Smoke、單項 benchmark、M3 HAL integration 組合測試命令。

## 3. Candidate manifest 與結果

每個執行過的 candidate 都必須提交：

- [ ] Engine、精確版本、model / voice、quantization、checksum 與來源。
- [ ] Engine license 與 model / voice license；標明商用及再散布限制。
- [ ] Platform、PCM format、threads、參數、fixture 與執行命令。
- [ ] Cold / hot、p50 / p95、RTF、peak RSS、disk、CPU 與結果索引。
- [ ] `advance` 或 `reject` 及理由；失敗結果不得省略。

License 不明、artifact 無法固定、aarch64 無法安裝或不能離線者，不得成為 winner。

## 4. 功能與品質證據

- [ ] VAD：speech start / end、首尾音節、停頓、靜音 / 噪音、endpoint 參數與 reset。
- [ ] ASR：台灣華語 CER、整句正確率、中英混說、數字日期、產品詞典 normalization。
- [ ] TTS：指定使用者品質確認、誤讀、first-chunk latency、生成時間與原生 PCM sequence。
- [ ] Timeout、error、cancel、force-abort 與 completion / exit proof。
- [ ] 每次測試後 orphan process、iterator、thread、stream 與 device owner 均為 0。

## 5. Raspberry Pi 5 與 M3 HAL 驗證

- [ ] 使用的 M3 Audio HAL 產品 repo 與完整 SHA。
- [ ] Pi 5 型號 / RAM、OS、kernel、mic / speaker、driver、外殼與測試環境。
- [ ] VAD / ASR finalist 使用真實 mic fixture 重跑。
- [ ] TTS finalist 經真實 AudioOutput 播放原生 PCM iterator。
- [ ] Start、stop、reopen、device failure、backpressure、underrun / overflow 與 cleanup。
- [ ] Pi 5 latency、RTF、RSS、CPU、temperature 與 thermal throttling；Ubuntu 結果不得取代此項。

## 6. 組合測試

- [ ] VAD、ASR、TTS 同時常駐，完成至少 20 個固定 pipeline sessions。
- [ ] 記錄總 RSS、threads、load time、端到端 latency、溫度與資源累積。
- [ ] 在 VAD、ASR、TTS 分別注入 timeout / cancel，且無資源殘留。
- [ ] 停用網路後主要 pipeline 仍可完成。

## 7. Winner / No-go 與產品化資料

- [ ] VAD、ASR、TTS 各指定唯一 winner；無候選達 gate 時明確 no-go。
- [ ] 固定 winner 的 artifact、license、PCM format、VAD endpoint、language / normalization、threads 與 timeout。
- [ ] 列出 rejected candidates、已知風險及不可採用原因。
- [ ] 說明可產品化的 wrapper / protocol、execution-container 建議與待辦工作。
- [ ] ASR 產品化建議須從 M2 evidence 列出 systematic semantic-mishearing patterns 與
  頻率、fixed-prompt benefit/regression，以及 decoder bias 或 context-aware correction
  方向；排除 LLM 可理解的純格式 normalization，且 POC 不實作 static lexicon。
- [ ] 明確區分可重用 source 與不可進入主線的 benchmark / demo code。

## 8. 資料安全

- [ ] Git 不含模型、大型 raw result、私有語音、敏感 transcript、API key 或 secret。
- [ ] 未進 Git 的 artifact 提供受控位置、checksum 與內部重複驗證方式。
- [ ] 提交的 log 與 summary 已去除 raw PCM、完整私人 transcript 及完整 TTS text。

## 驗收狀態

提交完整 SHA 只代表 `Ready for internal review`。Tester / Reviewer 關閉 blocking findings，且 Designer 確認 winner 或 no-go 後，才是 `POC Accepted`；主線產品化仍須另立 OUT-TASK 驗收。
