# Audio POC 團隊開發指引

對象：Audio POC 團隊
Owner：內部 Designer
狀態：Ready for PM delivery；不代表 PM 已交付

## 目標

在 M4a 前為 VAD、ASR、TTS 各選出唯一 baseline，並證明三者可在 Raspberry Pi 5 離線、可取消、可清理且同時常駐運作。

POC 使用獨立 repo，不接續 M2 code base，也不修改產品 repo。第一階段使用固定 WAV / text；第二階段接上指定 SHA 的 M3 Audio HAL。

## 開發階段

### 1. 建立共同測試基線

- 建立可重現環境、lockfile、benchmark harness、result schema 與 fixture catalog。
- 所有候選使用相同 fixture、命令、threads、warm-up、重複次數及量測方式。
- 先用 deterministic fake 驗證 success、timeout、error、cancel、force-abort 與 orphan-process 檢查。
- 正式比較前取得 Designer / Tester 凍結的品質與資源 gate；不得看完結果再調整門檻。

### 2. 比較候選

第一輪候選：

| 類別 | 候選 |
| --- | --- |
| VAD | Silero VAD ONNX、WebRTC VAD |
| ASR | sherpa-onnx SenseVoice int8、Paraformer small/int8、whisper.cpp tiny 或 base multilingual |
| TTS | sherpa-onnx VITS / MeloTTS voice、Piper 中文 voice |

每次執行必須固定 engine version、model / voice、quantization、checksum、license 與前後處理。版本或參數改變即視為新的 candidate run。

### 3. 整合 M3 Audio HAL

- 使用目標 I2S mic 重跑 VAD / ASR finalist。
- 使用真實 AudioOutput 播放 TTS finalist 的原生 PCM stream。
- 驗證 start、stop、reopen、backpressure、underrun / overflow、cancel 與 cleanup。
- 固定 WAV winner 若未通過真實裝置 gate，回到 finalist 比較，不得降低門檻放行。

### 4. 組合驗證

- VAD、ASR、TTS 同時常駐，至少執行 20 個固定 pipeline sessions。
- 在三個階段分別注入 timeout / cancel，確認無 child、iterator、stream 或 device owner 殘留。
- 停用網路重跑主要流程。
- 記錄總 latency、RSS、CPU threads、溫度及 thermal throttling。

## 最小 adapter 契約

POC 不必引用產品 class，但 wrapper 必須能映射以下語意：

- 共通：start / READY、stop / completion proof、cancel、force-abort；連續 session 不重載模型或累積資源。
- VAD：接收 PCM chunk、輸出 speech observation、每次 utterance 可 reset；endpoint state machine 與模型分離。
- ASR：消費 bounded PCM utterance，回傳 final transcript 或明確錯誤；固定 language 與 normalization。
- TTS：輸入 text、輸出有順序的 PCM iterator；回報原生 PCM format，cancel 後停止生成並關閉資源。
- Blocking native runtime 若無可靠 cancel，使用 persistent child process，證明 READY、cancel、shutdown 與 exit。

不得在 POC 改變產品事件語意、把 VAD 放進 Audio HAL，或在 Speak / Listen wrapper 隱式 resample。

## 必測項目

- VAD：speech start / end、首尾音節、自然停頓、靜音 / 噪音、最大 utterance 與 reset。
- ASR：台灣華語、中英混說、數字日期、產品詞、空白 / 噪音、CER 與整句正確率。
- TTS：中文可讀性、數字 / 縮寫 / 產品詞、first-chunk latency、完整生成時間與 PCM sequence。
- 共通：cold / hot、p50 / p95、RTF、peak RSS、disk、CPU、temperature、離線、cancel 與 cleanup。
- TTS voice 必須提供受控樣本供指定使用者確認品質。

## Repo 與資料規則

- 只修改 POC repo；交付以完整 commit SHA 為準。
- 模型、大型 artifact、私有語音、敏感 transcript 與 secret 不進 Git。
- Repo 保存來源、版本、checksum、license、受控資料與 sanitized results。
- Log 不得包含 raw PCM、完整私人 transcript 或完整 TTS text。

## 完成條件

依 Audio POC 最終繳交清單 提交後才進入內部 review。所有 blocking findings 關閉，且 Designer 決定 winner 或 no-go 後，才是 POC Accepted；不等於主線產品化完成。
