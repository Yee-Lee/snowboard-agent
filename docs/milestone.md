# 軟體工程開發策略：Skeleton First，Mock 測試驅動

以軟體工程的最佳實踐來說，我們應該採用「**骨架優先（Skeleton
First），Mock 測試驅動**」的策略。

建議將開發分為四個明確的階段，從系統的「神經」開始搭建。

------------------------------------------------------------------------

## 第一階段：打造神經中樞與介面契約

> **The Backbone & Interfaces**

這是整個專案成敗的關鍵。在此階段，我們完全不碰任何硬體，也不載入任何 AI
模型。

### 1. 定義通訊協定：`event_bus/`

實作基於 `asyncio.Queue` 的 Event Bus。

在 `topics.py` 或 `events.py` 中，使用 `dataclass`
精準定義出架構文件中列出的所有事件 Payload，例如：

-   `WakeDetected`
-   `StateChanged`
-   `StartListening`

### 2. 定義抽象契約：`base.py`

寫出以下模組中的 `Protocol` 介面：

-   `wake/base.py`
-   `perception/base.py`
-   `action/base.py`

確定所有核心方法的介面與簽章，例如：

-   `start()`
-   `stop()`
-   `execute()`

### 3. 實作狀態機：`state_manager/`

完成 `StateManager` 的核心邏輯，包括：

-   訂閱事件
-   狀態切換
-   Guard 防呆邏輯

例如，系統狀態可以按照以下流程流轉：

``` text
IDLE → WAKE → PERCEPTION → BRAIN → ACTION → IDLE
```

同時需要處理非預期事件，例如：

> 在 `ACTION` 狀態下收到 `Interrupt` 時，應該如何處理？

### 第一階段目標

完成系統的「神經中樞」與所有介面契約，使後續的 Mock、硬體與 AI
模組都能透過穩定的介面接入。

------------------------------------------------------------------------

## 第二階段：建立假人測試管線

> **The Dummy Pipeline**

有了神經與介面之後，我們需要驗證各個元件是否能夠順暢運作。

請為每個層級寫一個極度簡陋的 Mock 實作。

### Mock Wake

每隔 10 秒自動發佈一次 `WakeDetected`。

或者，也可以提供一個簡單的 CLI 輸入介面，讓開發者手動觸發事件。

### Mock Perception

收到啟動命令後：

1.  `await asyncio.sleep(1)`
2.  發佈一組寫死的文字：

``` python
PerceptionResult(text="今天天氣如何")
```

### Mock Brain

收到感知結果後：

1.  等待 2 秒
2.  發佈：

``` python
SpeakRequested(text="今天天氣很好")
```

### Mock Action

收到說話命令後：

1.  在 Console 印出：

``` text
[Playing Audio]: 今天天氣很好
```

2.  等待 2 秒
3.  發佈：

``` text
SpeechFinished
```

### 階段里程碑

執行：

``` bash
python main.py
```

應該能在終端機看到乾淨的 Log，顯示：

-   事件在 Event Bus 上流動
-   狀態機在六個狀態間正常流轉
-   非預期事件能被 Guard 正確攔截
-   Mock Pipeline 能完成完整的一次互動流程

理想的狀態流程：

``` text
IDLE
  ↓
WAKE
  ↓
PERCEPTION
  ↓
BRAIN
  ↓
ACTION
  ↓
IDLE
```

------------------------------------------------------------------------

## 第三階段：打通硬體抽象層

> **Hardware HAL**

當系統邏輯已經透過 Mock Pipeline 跑通後，再開始對接實體世界。

這個階段的重點是建立 `core/` 底下的硬體驅動與抽象層。

### 1. 音訊管線：`core/audio/`

這是最容易卡關的部分。

需要實作：

-   I2S 麥克風驅動
-   I2S 喇叭驅動
-   PCM 串流讀取
-   PCM 音訊播放

建議寫一支獨立的硬體測試腳本，確認：

-   能正確讀取 PCM 串流
-   能將 PCM 資料推送至喇叭播放
-   沒有明顯底噪
-   沒有 `Buffer Underrun` 問題

例如：

``` text
Microphone → PCM Stream → Audio Processing
                              ↓
Speaker ← PCM Stream ← Audio Output
```

### 2. 視覺與燈號：`core/display/`、`core/gpio/`

實作：

-   OLED 的繪製原語
-   LED 閃爍邏輯
-   GPIO 控制

### 3. 掛上 Adapter

將以下 Adapter 接入 Event Bus：

-   `adaptor/display`
-   `adaptor/leds`

讓實體螢幕與 LED 燈號能隨著 Dummy Pipeline 的狀態切換而變化。

例如：

``` text
StateManager
     │
     ▼
 Event Bus
  ┌──┴──┐
  ▼     ▼
Display LEDs
```

------------------------------------------------------------------------

## 第四階段：注入靈魂

> **AI Models Integration**

最後一步，才是把 Mock 掉的假人換成真正的 AI 引擎。

因為前面的介面（`Protocol`）已經定義完成，這個抽換過程應該會非常順利。

------------------------------------------------------------------------

### 1. Wake & Listen

掛上真正的：

-   Wake Word 模型
-   ASR 引擎

例如：

-   Whisper.cpp
-   Sherpa-onnx

用真正的 Perception 實作取代 `Mock Perception`。

------------------------------------------------------------------------

### 2. Action：TTS

掛上：

-   Matcha-TTS
-   RVC

確保生成的音訊能順利交給：

``` text
TTS / Voice Conversion
          ↓
      PCM Audio
          ↓
      core/audio
          ↓
       Speaker
```

------------------------------------------------------------------------

### 3. Brain：LLM

最後掛上：

-   LiteRT-LM
-   Gemma 3

完成：

-   Prompt 封裝
-   LLM 推論
-   Tool Calling 邏輯
-   對話上下文管理

------------------------------------------------------------------------

## 最終整體架構

``` text
┌─────────────────────────────────────────────────────────┐
│                    AI Application Layer                 │
│                                                         │
│  Wake Word → Perception → Brain / LLM → Action / TTS   │
│                                                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                     Event Bus                            │
│                                                         │
│        asyncio.Queue + Typed Event Payloads             │
│                                                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    State Manager                        │
│                                                         │
│   IDLE → WAKE → PERCEPTION → BRAIN → ACTION → IDLE     │
│                                                         │
│                    + Guard Logic                        │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    Hardware HAL                         │
│                                                         │
│   Audio / I2S   Display / OLED   GPIO / LEDs            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

------------------------------------------------------------------------

## 開發順序總結

  階段       核心目標                                      是否使用真實硬體   是否使用真實 AI
  ---------- ------------------------------------------- ------------------ -----------------
  第一階段   建立 Event Bus、Protocol 與 State Machine                   ❌                ❌
  第二階段   使用 Mock 驗證完整 Pipeline                                 ❌                ❌
  第三階段   對接 Hardware HAL                                           ✅                ❌
  第四階段   注入真正 AI Models                                          ✅                ✅

------------------------------------------------------------------------

## 核心原則

> **先讓系統在沒有硬體、沒有 AI 的情況下跑通，再逐步替換底層實作。**

這樣做的好處是：

1.  **降低開發風險**：不會同時被硬體、驅動、模型與系統邏輯卡住。
2.  **快速驗證架構**：可以先確認 Event Bus、State Machine
    與各層介面是否合理。
3.  **容易測試**：所有核心邏輯都可以在沒有實體硬體的環境下測試。
4.  **容易替換實作**：只要遵守既定的 `Protocol`，Mock、真實硬體與 AI
    模組都可以互相替換。
5.  **降低整合成本**：當 AI
    模型最後加入時，系統骨架已經穩定，不需要重新設計整個架構。

**最重要的原則：不要一開始就追求「能聽、能看、能說」；先確保系統的神經、骨架與介面能夠穩定運作。**

