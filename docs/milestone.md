# Snowboard 實作里程碑

依 `arch.md` 的架構分階段推進，採用 **Skeleton First、Mock 測試驅動** 策略——先讓系統在沒有硬體、沒有 AI 的情況下跑通，再逐步替換底層實作。

---

## 開發原則

1. **降低同時卡關風險**：不同時打硬體、驅動、模型、系統邏輯
2. **介面先於實作**：`base.py` 與事件型別穩定後，各實作可獨立替換
3. **每階段有明確驗收**：跑得起來 ≠ 完成，需符合該階段的可觀察行為
4. **常駐骨架不動**：從 M1 到 M4，`core/event_bus` 與 `core/state_manager` 只增加事件與轉移規則，不重構

---

## M1：神經中樞與介面契約

> **The Backbone & Interfaces**——完全不碰硬體、不載入 AI 模型

### 範圍

**1. Event Bus**（`core/event_bus/`）
- 基於 `asyncio.Queue` 或 dict-based pub/sub 的最小實作
- `subscribe(event_type, handler)`、`publish(event)`
- 已知型別但無 subscriber → log warning
- 錯誤隔離：一個 handler 拋錯不影響其他 handler

**2. 事件型別**（`core/event_bus/events.py`）
- 用 `@dataclass(frozen=True)` 定義 arch.md §10.2 全部事件
- 分三類：事實通報、命令、狀態變化

**3. 抽象契約**（各層 `base.py`）
- `wake/base.py`：`WakeTrigger`（start / stop）
- `perception/base.py`：`Perception`（perceive）
- `action/base.py`：`Action`（execute）
- `adaptor/base.py`：`Adaptor`（start / stop）
- `core/audio/base.py`：`AudioInput`、`AudioOutput`
- 全部用 `Protocol`；不含實作邏輯；不 import 第三方 lib

**4. StateManager (SM)**（`core/state_manager/`）
- 訂閱事實通報、發布命令與 `StateChanged`
- 完整實作 arch.md §11.2 狀態轉移表
- Guard 擋非法時序（log warning + 忽略）

**5. 骨架程式**
- `main.py` 完成組裝：讀 config → 建 bus → 建 SM → 掛 subscriber → `asyncio.run()`
- `core/config/`、`core/logger.py` 最小可用版本

### 驗收條件

- 跑 `py -3.11 -m sbd.main`（RPi 上為 `python3.11 -m sbd.main`），能啟動 event loop 且不 crash
- 用 `py -3.11 -m pytest` 測 SM 的所有轉移：合法轉移走通、非法轉移被 guard 擋掉並 log
- 測 event bus：多 subscriber、handler 錯誤隔離
- **不需要**任何實作能真的動作——所有實作類都不存在

### 不做

- 任何硬體 I/O、任何 AI 模型、任何 mock 實作
- Adaptor 具體實作（display/leds/external_broker）

---

## M2：Mock Pipeline 走通全流程

> **The Dummy Pipeline**——驗證事件流與狀態機在完整生命週期下正確運作

### 範圍

為每一層寫一個極簡 mock，讓 `py -3.11 -m sbd.main` 能跑一次完整的 IDLE → WAKE → PERCEPTION → THINK → ACTION → IDLE。

**Mock 實作**
- `wake/manual/`：讀 stdin，使用者按 Enter → publish `WakeDetected(source="manual")`
- `perception/mock/`：收到 `StartPerception` 後 `asyncio.sleep(1)`，publish `PerceptionResult(text="今天天氣如何")`
- `brain/reasoner.py`：先寫死邏輯（不接 LLM），收到 `PerceptionResult` → `asyncio.sleep(2)` → publish `SpeakRequested(text="這是一段測試回應")`
- `action/speak/mock/`：收到 `SpeakRequested` → print `[SPEAK] ...` → publish `SpeechFinished`
- `action/tool/`：註冊表骨架 + 一個 `time_tool` 供未來測試 tool_call 流程

**Adaptor 骨架**
- `adaptor/display/mock/`：訂閱 `StateChanged`，print `[DISPLAY] state=...`
- `adaptor/leds/mock/`：同上，print `[LED] state=...`

### 驗收條件

- 手動觸發 wake，log 顯示完整事件流與六狀態轉移
- 中斷測試：ACTION 狀態下再觸發 wake → guard 擋掉 + log warning
- 錯誤測試：mock 內主動 `raise` → SM 進 ERROR → 超時回 IDLE
- 一次跑完不 crash、記憶體不漲

### 不做

- 真實 ASR / LLM / TTS
- 真實麥克風 / 喇叭 / OLED / GPIO
- Tool calling 完整流程（M4 才做）

---

## M3：接上硬體 HAL

> **Hardware HAL**——mock 逐步換成真硬體，AI 仍為 mock

### 範圍

**1. 音訊 I/O**（`core/audio/`）
- I2S mic 讀 PCM 串流實作
- I2S speaker 播 PCM 串流實作
- 獨立測試腳本：`scripts/record_sample.py`、`scripts/play_sample.py`
- 驗證無底噪、無 buffer underrun

**2. Wake 硬體實作**
- `wake/button/`：GPIO 按鈕短按 → `WakeDetected(source="button")`
- 保留 `wake/manual/` 作為開發用備選

**3. OLED**（`core/display/` + `adaptor/display/`）
- `core/display/`：SPI OLED 低階原語
- `adaptor/display/`：訂閱 `StateChanged` → 繪製對應圖示

**4. LED**（`core/gpio/` + `adaptor/leds/`）
- `core/gpio/`：GPIO 存取封裝（避免 pin 衝突）
- `adaptor/leds/`：訂閱 `StateChanged` → 燈號變化

**5. Perception 半實作**
- `perception/listen/`：從 core/audio 拉 PCM，但 ASR 仍為 mock（回傳寫死文字或音檔長度）
- VAD 演算法可先接上（判斷段落結束）

### 驗收條件

- 按按鈕 → OLED 切 listening 圖示 → 錄音 → 播放 mock 回應 → 回 idle → OLED 切 idle 圖示
- 音訊測試腳本能獨立跑通，PCM 品質可接受
- GPIO 資源集中管理，button/led 無衝突
- SM 邏輯與事件型別**零改動**

### 不做

- 真實 ASR / LLM / TTS 推論
- MQTT / 外部整合（`adaptor/external_broker/` 保留骨架）
- CSI 相機（`core/camera/`、`perception/look/` M4 後）

---

## M4：注入 AI 模型

> **AI Models Integration**——mock 換成真實推論引擎

### 範圍

依相依關係與感知延遲影響順序推進：

**1. ASR**（`perception/listen/` 完整版）
- 接入 ASR 引擎（暫不指定型號）
- `core/audio` 麥克風串流 → VAD 切段 → ASR → publish `PerceptionResult`
- Benchmark：RTF、WER（`scripts/benchmark_asr.py`）

**2. TTS**（`action/speak/` 完整版）
- 接入 TTS 引擎
- 串流輸出：邊生成邊播（降低感知延遲）
- 常用短語預生成快取（如「好的」「請稍等」）

**3. LLM + Tool Calling**（`brain/reasoner.py` 完整版）
- 接入 LiteRT-LM + Gemma3:e2b
- `prompt_builder.py`：system prompt、tool schema 格式化
- `llm_engine.py`：async chat 介面（內部 `to_thread` 跑推論）
- Tool calling 完整迴圈：LLM → `ExecuteTool` → `ToolExecuted` → 再次 LLM
- Benchmark：TTFT、tokens/sec（`scripts/benchmark_llm.py`）

**4. 內建工具**（`action/tool/builtin/`）
- 至少一個實用工具（如 `time_tool`）
- Tool 註冊表 + schema 自動生成

### 驗收條件

- 按按鈕 → 說「現在幾點」→ 助理語音回答當前時間
- 端到端延遲拆解記錄於 `docs/evaluation/end_to_end.md`
- 三個 benchmark 腳本可重複跑，結果穩定
- Tool calling 流程正確：LLM 決策、dispatcher 執行、結果餵回

### 不做（延後至 M5+）

- Wake word 引擎（`wake/voice/`）
- CSI 相機與視覺（`core/camera/`、`perception/look/`）
- MQTT 整合（`adaptor/external_broker/`、`wake/event/`）
- 多輪對話 memory
- systemd 上線部署（`deploy/`）

---

## M5+：擴充功能

以下按需求優先權排序，各自獨立可插拔：

| 項目 | 主要工作 | 依賴 |
|---|---|---|
| Wake word 引擎 | `wake/voice/` 實作、常駐低耗監聽 | M4 完成 |
| 相機與 YOLO | `core/camera/`、`perception/look/`、`action/tool/builtin/vision_tool` | M4 完成 |
| MQTT 整合 | `adaptor/external_broker/`、`wake/event/`、共享 MQTT client | M4 完成 |
| 多輪對話 | `brain/` 引入 memory / session | M4 完成 |
| 上線部署 | `deploy/snowboard.service` + install script | M4 穩定後 |
| 延遲優化 | 量化、模型 prewarm、串流優化 | M4 完成 |

---

## 階段對照表

| 階段 | 目標 | 硬體 | AI |
|---|---|---|---|
| M1 | Event Bus + Protocol + StateManager | ❌ | ❌ |
| M2 | Mock Pipeline 走通六狀態 | ❌ | ❌ |
| M3 | 硬體 HAL 上線 | ✅ | ❌ |
| M4 | 真實 AI 模型接入 | ✅ | ✅ |
| M5+ | 擴充功能 | ✅ | ✅ |

---

## 貫穿全期的紀律

- **不跳階段**：M2 未跑通不進 M3；M3 未跑通不接 AI
- **介面不動**：M1 定下的 `base.py` 與事件型別，除非有本質理解錯誤，否則不改
- **每階段留一段回歸時間**：換實作後重跑上一階段的驗收
- **測試同步累積**：M1 起 `tests/` 就開始長；每加一個實作，補一組 mock-based 測試
- **文件同步更新**：`docs/decisions.md` 記錄關鍵取捨；`docs/evaluation/` 記錄 benchmark 結果
