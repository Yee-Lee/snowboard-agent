# VAD Labelling & Review Tool (Web-based)

這是一個專為 Audio POC 50 筆 M1 Fixture 音檔設計的互動式 Web 視覺化聲學標註與人工審閱工具。

---

## 🎯 功能特色

1. **實時聲學波形可視化（Waveform Display）**：
   - 繪製音訊實時振幅波形，直觀呈現音訊發音與靜音分佈。
   - 以半透明綠色高亮 `Speech 語音區間`、黃色高亮 `Pause 停頓區間`。
   - 支援滑鼠直接拖曳起訖邊界把手（圓點）進行微調（自動對齊 10ms 粒度）。

2. **多速播放與即時試聽**：
   - **慢速播放**：支援 `0.5x`、`0.75x`、`1.0x` 即時切換（預設 0.5x，方便聽辨子音與爆破音邊界）。
   - **暫停與續播**：按 <kbd>Space</kbd> 暫停在當前時間點，再按一次從暫停位置繼續播放。
   - **分段試聽**：一鍵只聽 Speech 語音段、Pause 停頓段、或起點/終點前後 350ms 邊界。

3. **規範防呆與一鍵產出**：
   - 自動確保 `clear_speech` 為單一區間、`pause` 為雙區間且停頓區間完全等於中間間隔。
   - 自動從 `fixture_manifest.json` 對齊 `native_sha256` 與 `source_manifest_sha256`。
   - 點擊「儲存」直接校驗並寫入符合 Schema 的 `vad-labels-v1.json`。

---

## ⌨️ 鍵盤快捷鍵

| 快捷鍵 | 動作說明 |
|---|---|
| <kbd>Space</kbd> | 播放整首 / 暫停 / 續播（Pause & Continue） |
| <kbd>S</kbd> | 只播放 Speech 語音區段（確認尾音/字首是否完整） |
| <kbd>P</kbd> | 只播放 Pause 停頓區段（確認停頓內是否乾淨） |
| <kbd>1</kbd> | 試聽起始邊界前後 350ms |
| <kbd>2</kbd> | 試聽結束邊界前後 350ms |
| <kbd>←</kbd> / <kbd>→</kbd> | 切換上一首 / 下一首音檔 |
| <kbd>Enter</kbd> | 標記為 `ACCEPTED_BY_HUMAN_REVIEW` 並自動跳至下一首 |

---

## 🚀 啟動與使用方式

### 1. 預設模式（使用標準 M1 fixture 目錄）
```bash
python3 poc_audio/tools/vad_labeling/vad_labeling_server.py
```
啟動後在瀏覽器開啟：`http://localhost:8765`

### 2. 指定自訂音訊目錄與輸出路徑
```bash
python3 poc_audio/tools/vad_labeling/vad_labeling_server.py \
  --port 8765 \
  --artifact-dir /path/to/artifacts \
  --output /path/to/vad-labels-v1.json
```

---

## 📄 輸出檔案格式

輸出檔案預設儲存於 `poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1/review/vad-labels-v1.json`，格式範例如下：

```json
{
  "schema_version": "1.0",
  "label_set_id": "m1-authorized-vad-labels-v1",
  "plan_id": "m1-authorized-zh-tw-v1",
  "source_manifest_sha256": "0072a95613d90664d09aa9e11274e3589d9dbcbb786047b060b420cebcddfabf",
  "annotation_method": "external_tool_then_human_review",
  "records": [
    {
      "fixture_id": "asr-clear-001",
      "class": "clear_speech",
      "native_sha256": "400d6ec64c810efa6d4c9737c9281b4ec4a71e65f08961712a2222e48e5e733f",
      "speech_intervals_ms": [[590, 2590]],
      "internal_pause_interval_ms": null,
      "review_status": "ACCEPTED_BY_HUMAN_REVIEW"
    },
    {
      "fixture_id": "asr-pause-026",
      "class": "pause",
      "native_sha256": "3cb49a46944e99ea5a1a1d95713437e95fc1506541f5348bbd6be1a0c436b761",
      "speech_intervals_ms": [[1170, 2500], [3340, 5270]],
      "internal_pause_interval_ms": [2500, 3340],
      "review_status": "ACCEPTED_BY_HUMAN_REVIEW"
    }
  ]
}
```
