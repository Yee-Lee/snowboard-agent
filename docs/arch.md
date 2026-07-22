# Snowboard 架構設計

離線 AI 語音助理 POC，執行於 Raspberry Pi 5 (Pi OS)。
本文件描述目錄結構、模組職責與設計原則，作為後續實作依據。

> 狀態：POC 規劃階段，未實作。討論後會持續修正本文件。

---

## 1. 硬體與軟體堆疊

**硬體**
- I2S 麥克風
- I2S 喇叭
- SPI OLED
- 8MP CSI 相機
- GPIO（按鈕、LED、控制家電）

**軟體**
- ASR：離線語音辨識
- TTS：離線語音合成
- LLM：LiteRT-LM 執行 Gemma3:e2b
- Tools calling：本機工具註冊 + 執行
- 外部通訊：MQTT / UART / 其他 IPC
- Wake：wake word / GPIO 按鈕 / 外部訊息觸發

---

## 2. 設計哲學

### 2.1 事件驅動 + 星型解耦

**核心思想**：模組互不相識，全靠總線與狀態機溝通。

- **Event Bus**：全系統唯一神經網路。所有模組只對 bus 做 publish 或 subscribe。
- **StateManager (SM)**：系統的唯一協調者。訂閱事實通報、維護全局狀態、下達命令。
- **無狀態工作節點**：Wake / Perception / Brain / Action / Adaptor 皆為獨立協程，不知道彼此存在，只完成份內工作並回報結果。

### 2.2 生命週期分層

目錄結構直接對應對話生命週期，讀目錄就能理解對話流程：

```
wake → perception → brain → action
（觸發） （感知）    （思考） （行動）

adaptor：全程訂閱狀態，把系統狀態具現化到物理世界（顯示、燈號、對外訊息）
core：所有實作可能共享的基礎設施與硬體資源
```

### 2.3 抽象 + 多實作

每個生命週期層都遵循「抽象契約 + 多種實作」模式：

```
<layer>/
├── base.py              # 抽象契約
├── <impl-A>/            # 某種實作
└── <impl-B>/            # 另一種實作
```

SM 只認「抽象」不認實作。這使得 wake 可以有多種觸發來源、perception 可以有多種感知方式、action 可以有多種行動形式——皆不影響控制流。

### 2.4 硬體/軟體兩層分離

- **core/*** 提供硬體 HAL（audio、display、camera、gpio）——硬體資源的**單一 owner**
- **上層模組**（wake / perception / action / adaptor）跟 core **借用資源**，不直接碰硬體
- **HW driver 若換型號**，只改 core，上層一行不動

比喻：core 是**眼、耳、嘴的實體器官**；上層是**看、聽、說的能力**。

### 2.5 Adaptor 類比

Adaptor = 外部工具。想像一個人除了本體的看/聽/說之外，可以「手持工具、帶上望遠鏡、吹樂器」——這些工具擴展能力，但不是本體。

- **本體**：perception + action（內建的感知與行動）
- **Adaptor**：透過外部通道（MQTT、UART、LED、OLED）將狀態具現化或雙向溝通
- **損壞不影響本體**

---

## 3. 目錄總覽

```
Snowboard/
├── README.md
├── project.txt
├── requirements.txt
├── pyproject.toml
├── .gitignore
│
├── config.example.yaml
├── config.local.yaml                # gitignore
├── .env.example
├── .env                             # gitignore
│
├── src/sbd/
│   ├── __init__.py
│   ├── main.py                      # 進入點：組裝 + 啟動
│   │
│   ├── core/                        # 基礎設施 + 硬體 HAL
│   │   ├── config/
│   │   ├── logger.py
│   │   ├── event_bus/               # 本機 pub/sub（asyncio）
│   │   ├── state_manager/           # 全局狀態機
│   │   ├── audio/                   # HW: I2S mic/speaker driver
│   │   ├── display/                 # HW: SPI OLED driver
│   │   ├── camera/                  # HW: CSI camera driver
│   │   └── gpio/                    # HW: GPIO 存取
│   │
│   ├── wake/                        # 觸發層（常駐、低耗）
│   │   ├── base.py                  # WakeTrigger 抽象
│   │   ├── voice/
│   │   ├── button/
│   │   └── event/
│   │
│   ├── perception/                  # 感知層
│   │   ├── base.py                  # Perception 抽象
│   │   ├── listen/
│   │   ├── read/
│   │   └── look/
│   │
│   ├── brain/                       # 認知層
│   │   ├── reasoner.py
│   │   ├── llm_engine.py
│   │   └── prompt_builder.py
│   │
│   ├── action/                      # 行動層
│   │   ├── base.py                  # Action 抽象
│   │   ├── speak/
│   │   └── tool/
│   │
│   └── adaptor/                     # 外部工具 / 狀態具現化層
│       ├── base.py                  # Adaptor 抽象
│       ├── display/
│       ├── leds/
│       └── external_broker/
│
├── models/                          # 所有離線模型權重（gitignored）
├── scripts/                         # 人手動跑的工具
├── deploy/                          # systemd 上線設定
├── docs/                            # 設計與評估文件
└── tests/                           # 純邏輯單元測試
```

**文件約定**：`#` 之後為說明註解，非檔名；所有 Python 套件目錄需建立空的 `__init__.py`（未在樹狀圖列出）。

---

## 4. core/ — 基礎設施 + 硬體 HAL

### 4.1 定位

core 提供**多層共用的資源**。分兩類但同一目錄：

**軟體基礎設施**
- `config/`：設定管理（三層：預設 / local yaml / .env）
- `logger.py`：統一 logger
- `event_bus/`：pub/sub 匯流排（asyncio 純記憶體）
- `state_manager/`：全局狀態機、命令發送者

**硬體 HAL**
- `audio/`：I2S mic 與 speaker 驅動（單例，所有需要音訊 I/O 的模組共用）
- `display/`：SPI OLED 驅動（低階原語：畫 pixel、寫文字、清畫面）
- `camera/`：CSI 相機驅動（拍照、抽幀）
- `gpio/`：GPIO 存取（供 wake/button 監聽、tool 控制家電、adaptor/leds 驅動燈號）

### 4.2 core/audio 與上層的介面

`core/audio` 只提供**純 PCM 進出**：

```python
# core/audio/base.py
class AudioInput(Protocol):
    async def frames(self) -> AsyncIterator[bytes]: ...

class AudioOutput(Protocol):
    async def play(self, pcm: AsyncIterator[bytes]) -> None: ...
```

- **VAD、串流分段** 屬於軟體演算法，留在 `perception/listen/` 或 `wake/voice/`——不同上層可能有不同分段需求
- 上層向 core/audio 借麥克風串流，各自做加工

### 4.3 core/display 與 adaptor/display 的介面

- **core/display**：低階原語（畫 pixel、寫文字、清畫面）
- **adaptor/display**：訂閱 `StateChanged` 事件、決定要顯示什麼圖示/文字、呼叫 core/display 繪製

這樣：
- 換 OLED 型號 → 只改 core/display
- 改變顯示風格 → 只改 adaptor/display

### 4.4 core/gpio 的獨立性

`gpio/` 獨立而非藏在 `wake/button/`。理由：多個模組會用到 GPIO：
- `wake/button/`：按鈕輸入
- `adaptor/leds/`：LED 輸出
- `action/tool/`：控制家電

集中管理避免 pin 衝突與資源爭搶。

### 4.5 event_bus 與 SM 的技術細節

**event_bus**：
- 用 asyncio.Queue 或自訂 pub/sub dict
- 事件分兩類，用命名區分（見 §10）：
  - **事實通報**（過去式/狀態）：`WakeDetected`、`TranscriptReady`、`SpeechFinished`
  - **命令**（祈使句）：`StartListening`、`StopSpeaking`、`ExecuteTool`
- 未知型別或無 subscriber → log warning

**SM**：
- 訂閱**事實通報**、發布**命令**與 `StateChanged`
- 唯一持有 `state` 欄位的元件
- 用 guard 擋非法時序（如 speaking 狀態下的 `WakeDetected` 忽略）

---

## 5. wake/ — 觸發層

### 5.1 定位

**唯一 24 小時運作的極低耗模組**。責任是把系統從休眠中踢醒，發布 `WakeDetected` 事件。**絕不處理複雜邏輯**。

### 5.2 抽象契約

```python
# wake/base.py
class WakeTrigger(Protocol):
    """所有 wake 實作都是常駐 async task，偵測條件成立就 publish WakeDetected。"""
    async def start(self, bus: EventBus) -> None: ...
    async def stop(self) -> None: ...
```

### 5.3 共同輸出

`WakeDetected(source, payload)`

- `source` 供 log / metrics 使用，SM 不依此分支
- `payload` 可帶額外資訊，供後續 perception 選型參考

---

## 6. perception/ — 感知層

### 6.1 定位

Wake 之後啟動的情報收集區。把物理世界的訊號**翻譯成內部可用資料**（文字或結構化資訊）。

### 6.2 抽象契約

```python
# perception/base.py
class Perception(Protocol):
    async def perceive(self) -> PerceptionResult: ...
```

每個 perception 實作**自己知道從哪拿輸入**——listen 拉 audio、read 訂閱事件、look 拉 camera。對外統一「呼叫 perceive() → 得到結果」。

### 6.3 實作

| 實作 | 輸入來源 | 輸出 |
|---|---|---|
| `perception/listen/` | core/audio 麥克風串流 | 文字（ASR 結果） |
| `perception/read/` | 內部事件 payload | 文字 |
| `perception/look/` | core/camera 抽幀 | 視覺結果 |

### 6.4 SM 選擇 perception 的策略

依 `WakeDetected` 事件的 `source` 或 `payload` 決定該啟動哪個 perception。決策集中在 SM，不下放到 perception 層。

---

## 7. brain/ — 認知層

### 7.1 定位

**語意與感知的協調者**。與 SM 分工：
- **SM**：系統協調者（小腦——反射、狀態、時序）
- **brain/reasoner**：語意協調者（大腦——理解、推論、決策）

### 7.2 結構

```
brain/
├── reasoner.py         # 訂閱 PerceptionResult；組 prompt；解析 LLM 意圖；派發 action
├── llm_engine.py       # LLM driver
└── prompt_builder.py   # system prompt 模板、tool schema 格式化
```

### 7.3 職責

1. 訂閱 `PerceptionResult` 事件
2. 呼叫 `prompt_builder` 組 prompt（含 tool schemas）
3. 呼叫 `llm_engine.chat()` 推論
4. 解析回應：
   - 有 tool_calls → publish `ExecuteTool` 命令
   - 有 text 回應 → publish `SpeakRequested` 命令
5. 收到 `ToolExecuted` 結果 → 塞回 messages 再次呼叫 LLM

---

## 8. action/ — 行動層

### 8.1 定位

將數位意圖轉化為實際行動。

### 8.2 抽象契約

```python
# action/base.py
class Action(Protocol):
    async def execute(self, request: ActionRequest) -> ActionResult: ...
```

### 8.3 實作

| 實作 | 職責 |
|---|---|
| `action/speak/` | TTS 合成 + 交給 core/audio 播放 |
| `action/tool/` | 註冊表 + dispatcher，執行 LLM 決策的 tool_call |

---

## 9. adaptor/ — 外部工具 / 具現化層

### 9.1 定位

把系統內部狀態**具現化**到物理世界，或作為與外部世界雙向溝通的通道。

**特徵**：
- 純訂閱者或雙向翻譯者
- 損壞不影響主流程
- 「內部狀態 → 外部具現化」或「外部訊息 → 內部事件」

### 9.2 抽象契約

```python
# adaptor/base.py
class Adaptor(Protocol):
    async def start(self, bus: EventBus) -> None: ...
    async def stop(self) -> None: ...
```

### 9.3 實作

| 實作 | 方向 | 職責 |
|---|---|---|
| `adaptor/display/` | 純輸出 | 訂閱 `StateChanged`，繪製圖示/文字到 core/display |
| `adaptor/leds/` | 純輸出 | 訂閱 `StateChanged`，透過 core/gpio 閃燈 |
| `adaptor/external_broker/` | 雙向 | 訂閱內部事件轉 MQTT 外送；訂閱 MQTT 訊息轉內部事件 |

---

## 10. 事件模型

### 10.1 三類事件

| 類別 | 命名風格 | 誰發布 | 誰訂閱 |
|---|---|---|---|
| **事實通報** | 過去式或狀態（`WakeDetected`、`TranscriptReady`、`SpeechFinished`） | 工作節點（wake / perception / brain / action） | SM、adaptor、log / metrics |
| **命令** | 祈使句（`StartListening`、`StopSpeaking`、`ExecuteTool`） | SM | 工作節點 |
| **狀態變化** | `StateChanged(old, new)` | SM | adaptor、metrics |

### 10.2 事件型別清單

**事實通報**
- `WakeDetected(source, payload)`
- `UtteranceCaptured(pcm, duration_ms)`
- `PerceptionResult(kind, text, extra)`
- `LLMResponse(text, tool_calls)`
- `ToolExecuted(name, result)`
- `SpeechStarted(text)`
- `SpeechFinished()`
- `TurnCompleted()`
- `ErrorOccurred(where, error)`

**命令**
- `StartListening()`
- `StartPerception(kind)`
- `StartReasoning(input)`
- `ExecuteTool(call)`
- `SpeakRequested(text)`
- `StopSpeaking()`
- `GoIdle()`

**狀態**
- `StateChanged(old, new)`

### 10.3 未知事件處理

- **Adapter 層過濾**：無法翻譯的外部訊息 → adapter 內 log warning，不進 bus
- **Bus 層兜底**：已知型別但沒 subscriber → log warning

---

## 11. 狀態機

### 11.1 狀態集合

| 狀態 | 意義 |
|---|---|
| `IDLE` | 等待 wake 觸發 |
| `WAKE` | 已被喚醒，準備啟動 perception |
| `PERCEPTION` | 感知進行中（listen / read / look） |
| `THINK` | brain 推論中（含 LLM + tool 執行） |
| `ACTION` | 執行行動（speak / tool） |
| `ERROR` | 錯誤處理中（短暫停留後回 IDLE） |

### 11.2 狀態轉移表

| 目前狀態 | 觸發事件 | 動作 | 下一狀態 |
|---|---|---|---|
| IDLE | WakeDetected | 依 source 選 perception，publish StartPerception | WAKE → PERCEPTION |
| IDLE | 其他事件 | 忽略 | IDLE |
| PERCEPTION | PerceptionResult | publish StartReasoning | THINK |
| PERCEPTION | Timeout | 提示訊息 | ACTION |
| THINK | LLMResponse(tool_calls) | publish ExecuteTool | THINK |
| THINK | ToolExecuted | 塞回 messages，再次呼叫 LLM | THINK |
| THINK | LLMResponse(text only) | publish SpeakRequested | ACTION |
| THINK | LLMResponse(empty) | 無回應 | IDLE |
| ACTION | SpeechFinished | publish TurnCompleted | IDLE |
| ACTION | InterruptRequested | publish StopSpeaking | IDLE |
| ERROR | timeout | 回歸 | IDLE |
| 任意 | ErrorOccurred | 停手邊動作 | ERROR |
| 任意 | ShutdownRequested | 收尾 | (終止) |

### 11.3 感知模型

- **外部訊息**由常駐 adaptor / wake 感知，翻譯為內部事件送 bus
- **SM 只訂閱內部事件**，不感知外部
- 對話狀態機（六種狀態）與外部連通性（常駐服務）**解耦**：狀態機忙不忙不影響訊息接收，訊息接收不擾亂狀態機

---

## 12. 執行模型

### 12.1 執行緒模型

- **1 個主 thread 跑 asyncio event loop**，協調所有 async task
- **N 個 worker thread**（via `asyncio.to_thread`）跑 CPU 密集推論（ASR、LLM、TTS）
- **部分第三方 lib** 可能自起 thread——透過 `loop.call_soon_threadsafe` 收斂回主 loop

### 12.2 async 介面規則

所有跨模組介面用 async：

```python
class ASREngine(Protocol):
    async def transcribe(self, pcm: bytes) -> Transcript: ...
```

driver 內部決定是否 `to_thread`：

```python
async def transcribe(self, pcm):
    return await asyncio.to_thread(self._blocking_transcribe, pcm)
```

上層永遠 `await`——不管底下是純 async 還是被 to_thread 包裝。

### 12.3 常駐 async task 清單

系統啟動後常駐：
- event_bus 分派 loop
- SM
- 各 wake/* 實作
- 各 adaptor/* 實作

按需啟動（state 驅動）：
- perception/*（收到 `StartPerception` 才啟動）
- brain/reasoner（收到 `StartReasoning` 才動作）
- action/*（收到 `SpeakRequested` / `ExecuteTool` 才動作）

### 12.4 併發保護

- 單 event loop 下無 race，但邏輯錯亂可能——handler 首行用 guard 擋非法時序
- 非法時序 → log warning + 忽略，不拋錯

---

## 13. 設定分層

| 層 | 檔案 | 進 git？ | 內容 |
|---|---|---|---|
| Schema / 預設 | `src/sbd/core/config/` | ✅ | dataclass 定義、預設值、載入邏輯 |
| 本機覆寫 | `config.local.yaml` | ❌ | pin 腳、ALSA card、模型路徑 |
| 祕密 | `.env` | ❌ | MQTT 密碼、API key |
| 範本 | `config.example.yaml`、`.env.example` | ✅ | 使用者複製後改名 |

**載入順序**：預設 → local yaml 覆寫 → env 覆寫。
**格式**：YAML。

---

## 14. models/、scripts/、deploy/、docs/、tests/

### 14.1 models/（gitignored）
```
models/
├── README.md
├── llm/
├── asr/
├── tts/
├── wake/
└── vision/
```
`scripts/fetch_models.sh` 下載；config 只需一個 `MODELS_DIR`。

### 14.2 scripts/（人手動跑）
```
scripts/
├── setup_rpi.sh
├── fetch_models.sh
├── run.sh
├── record_sample.py
├── benchmark_asr.py
└── benchmark_llm.py
```

### 14.3 deploy/（systemd 上線）
```
deploy/
├── snowboard.service
├── install-service.sh
└── uninstall-service.sh
```

### 14.4 docs/
```
docs/
├── arch.md                  # 本文件
├── hardware.md
├── interfaces.md            # 各 base.py 精確 Python signature
├── decisions.md             # ADR
├── protocol.md              # 外部契約（MQTT topic schema 等）
└── evaluation/
    ├── asr_benchmarks.md
    ├── llm_latency.md
    └── end_to_end.md
```

### 14.5 tests/（純邏輯）
```
tests/
├── conftest.py
├── fixtures/
├── test_event_bus.py
├── test_state_manager.py
├── test_prompt_builder.py
├── test_tool_registry.py
├── test_config.py
└── test_vad.py
```

---

## 15. 設計原則速覽

| 原則 | 體現 |
|---|---|
| 生命週期分層 | wake → perception → brain → action + adaptor 全程訂閱 |
| 抽象 + 多實作 | 每層 `base.py` + 多個實作子目錄 |
| HW / SW 分離 | core/ 提供硬體 HAL；上層做軟體演算法 |
| 事件驅動 | event_bus 是唯一神經；模組不直接互相呼叫 |
| 星型解耦 | SM 集中控制流；工作節點無狀態 |
| 事實通報 vs 命令 | 命名區分（過去式 vs 祈使句），同一 bus |
| 邊界抽象一致 | wake 和 adaptor 都是「協定/來源多樣，內部語意統一」 |
| 感知模型 | 外部由常駐服務感知；SM 只認內部事件 |
| main 與 pipeline 分工 | main.py 只組裝與啟動；SM 才有執行時邏輯 |
| 開發機可跑 | 每個 driver / 實作子目錄配 mock 版本 |
| 測邏輯不測硬體 | tests/ 只測純軟體 |
