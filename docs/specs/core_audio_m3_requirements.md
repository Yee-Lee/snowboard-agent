# 核心主線 M3 Audio 開發要求

對象：核心主線產品開發團隊
Owner：內部 Designer
狀態：Ready for PM delivery；不代表 PM 已交付

## 結論

M3 開始前固定 Audio 契約；M3 完成前交付 Raspberry Pi 5 真實 Audio HAL。M3 不導入真實 VAD、ASR 或 TTS。

POC 可先以固定 WAV / text 比較候選；只有接上 M3 Audio HAL 並完成 Pi 5 驗證後，才能完成 Audio POC。

## M3 開始前

### AUDIO-M3-01：固定 Audio API 與設定

- AudioInput 與 AudioOutput 分別設定 driver、device 及 PCM format。
- PCM format 明確包含 sample rate、channels、16-bit little-endian。
- AudioInput baseline 為 16 kHz、mono、20 ms frame。
- AudioOutput sample rate 可與 input 不同，由 TTS POC winner 決定。
- AudioOutput 接受任意合法 PCM chunk sequence；Speak / Listen 不得隱式 resample。

驗收：權威文件、strict config、factory、validator、example config 與測試使用同一契約。

### AUDIO-M3-02：固定責任與 lifecycle

- Audio HAL 只負責 PCM capture / playback、裝置 lifecycle 與錯誤回報。
- VAD、endpoint、ASR 位於 Listen 邊界，不進 Audio HAL。
- 固定資料流：`AudioInput` -> `rechunker` -> `VAD / endpoint` -> `bounded utterance` -> `ASR` -> `PerceptionResult`
- VAD 不持有 AudioInput、不發布產品事件；Listen 擁有 timeout、cancel、cleanup 與 terminal result。
- Adapter 必須支援 start / READY、stop / completion proof、cancel，以及失敗時的 force-abort。
- 若 native inference 無可靠 cancel，產品設計必須允許 persistent child process 與 exit proof。

驗收：權威文件與測試能定位各層責任，並可觀察取消及資源釋放結果。

## M3 完成前

### AUDIO-M3-03：交付 Pi 5 真實 Audio HAL

- AudioInput 從目標 mic 產生格式、frame bytes 與時序正確的 PCM。
- AudioOutput 依指定格式完整播放 PCM iterator。
- Input / output 可獨立 start、stop、reopen，不殘留 stream、task 或 device owner。
- 無效 input / output device 各自產生規格定義的錯誤、fallback 與 capability 結果。
- 可將 mic 輸入保存為合法 WAV，供 POC 建立受控 fixture。

### AUDIO-M3-04：提供 POC 整合基線

- Audio HAL source、tests、權威文件與完整 commit SHA。
- Pi 5 OS、audio device、driver、PCM format、安裝及執行命令。
- Mic fixture capture 與 PCM iterator playback 的可重現入口。
- Start / stop / reopen、device failure、fallback 與 cleanup 證據。
- 已知的硬體、driver、buffering 與 sample-rate 限制。

POC 團隊只依完整 SHA 整合；branch 名稱或聊天說明不能取代固定基線。

## M3 不包含

- 選定或產品化真實 VAD、ASR、TTS。
- 決定最終 model、voice 或 VAD endpoint 參數。
- Barge-in、AEC、wake word / KWS 或跨 process mic handoff。
- 將 POC harness 接入 production composition root。
