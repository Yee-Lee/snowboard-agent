# Display Architecture

## 目的

Display 子系統提供一個穩定的展示服務，讓 AI worker、state machine、測試程式等外部來源可以顯示文字、狀態動畫與影片，而不需要知道面板型號、SPI、`ctypes` 或 `libdisplay.so`。

核心原則如下：

- 外部來源只描述「想展示什麼」；不直接操作 frame buffer 或硬體。
- `DisplayService` 是唯一可以將畫面送往硬體的擁有者。
- 同一時間只有一個 native I/O owner 可呼叫 HAL 與 `libdisplay.so`。
- 狀態、通知、警示與媒體播放有不同的產品語意，不能只用一個 FIFO queue 處理。
- Native driver 僅處理面板與通訊；文字、動畫、影片和產品 UI 留在上層。

## 分層

```text
外部 worker / state machine / test script
                    |
                    v
                  API
                    |
                    v
                 Service
                    |
                    v
                Rendering
                    |
                    v
                   HAL
                    |
                    v
                 Native
```

### API

API 是外部程式唯一需要接觸的入口。它將呼叫轉為 typed command，並立即回覆 request 已被接受或拒絕；不會等待動畫或影片播放結束。

```python
display.set_status("thinking")
display.notify("任務完成")
display.show_alert("網路中斷")
handle = await display.play_media("startup_animation")
```

API 不應暴露 SPI、Pillow、面板解析度、`.so` 檔案路徑，或 `push_frame()`。

同一 Python process 內可由 `DisplayClient` 直接呼叫 service。跨 process 時，`DisplayClient` 應透過 Unix domain socket 傳送相同的 command schema。HTTP/WebSocket 可作為除錯或遠端控制介面，但不應作為高頻影格傳輸通道。

### Service

`DisplayService` 負責同步與仲裁：

- 用單一 command queue 接收所有 source 的 command。
- 維護目前的 scene、layer、owner、優先權與生命週期。
- 決定內容是更新狀態、成為 overlay、立即取代畫面，或排入媒體序列。
- 執行 render scheduling、限幀與 frame dropping。
- 是唯一允許呼叫 `HAL.present()` 的元件。

Service 決定「現在該畫哪個 scene、何時送出下一幀」，但不負責星星位置、文字排版等畫面細節。

### Rendering

Rendering 將 service 提供的 scene 與時間轉換為 frame。

- 文字：字型、斷行、色彩、圖示、位置。
- 動畫：物件初始狀態、位置、速度、亮度、淡入淡出。
- 影片：解碼成連續 frame，交由 service 以適合面板的節奏呈現。
- Compositor：將背景、狀態與 overlay 合成一張 logical canvas。

例如星空動畫的每顆星位置由 rendering 決定：

```text
Star #17
  initial position: (30, 95)
  velocity:         (4, -8) pixels/sec

at t = 2.5 sec
  position:         (40, 75)
```

動畫應以固定 seed 與 `elapsed_time` 計算 frame，而不是只依賴逐幀累加狀態。若面板來不及刷新，service 可以丟棄舊 frame，下一張仍會對應正確的時間點。

### HAL

HAL 將 renderer 產生的 frame 交給目前選定的裝置實作。它處理面板能力、實際解析度、rotation、pixel format 和 native library 載入，但不知道產品 UI 或動畫內容。

建議 Python protocol：

```python
class DisplayDevice(Protocol):
    info: DisplayInfo

    async def open(self) -> None: ...
    async def present(self, frame: Rgb565Frame) -> None: ...
    async def present_rect(self, rect: Rect, frame: Rgb565Frame) -> None: ...
    async def clear(self) -> None: ...
    async def close(self) -> None: ...
```

初期實作：

- `MockDisplayDevice`：PC 與 CI 使用，可輸出圖片或 log。
- `CtypesDisplayDevice`：載入 `libdisplay.so`，定義 C signature，並呼叫 native ABI。

### Native

Native 層是每個實體面板控制器的 C driver，負責 GPIO、SPI、初始化序列、畫面傳輸與釋放資源。

它不處理文字、字型、影片解碼、動畫、logical resolution 或優先權。

建議穩定且版本化的 C ABI：

```text
display_open(config) -> handle
display_get_info(handle) -> DisplayInfo
display_present_rgb565(handle, buffer, length)
display_present_rect_rgb565(handle, x, y, width, height, buffer, length)
display_clear(handle)
display_close(handle)
```

應以回傳碼與可讀取錯誤取代只 `printf` 後繼續執行的行為。

## API 語意與排程政策

Caller 應表達產品語意，而不是自行選擇低階 queue 行為。建議 API 分為下列類型：

| API 類型 | 例子 | Service 預設行為 |
| --- | --- | --- |
| `set_status` | thinking、listening、idle | 持續狀態；同類內容採 latest-wins，不排隊 |
| `notify` | 任務完成、新訊息 | 短暫 overlay；同類內容可合併或 latest-wins |
| `show_alert` | 網路中斷、錯誤 | 立即顯示；必要時取代其他內容 |
| `play_media` | 開機動畫、教學、使用者選取影片 | 可按播放序列排隊，回傳 handle |

一般助理 UI 的背景狀態、聆聽與思考動畫，通常不需要 FIFO queue。它們代表「此刻系統狀態」，只保留最新值即可。

真正需要 queue 的情境較少，主要是：

- 開機流程或教學步驟必須依順序顯示。
- 使用者明確要求播放的影片或播放清單。
- 必須完成後才能進到下一個視覺步驟的流程。

### Overlay 與 exclusive

「任務完成」通常應疊加在星空等背景狀態上：

```text
背景 layer: 星空持續更新
overlay layer: 「任務完成」顯示 1.5 秒
```

兩者同時進入 renderer 進行合成，因此星空不需暫停或排隊。

小型面板或警示情境可能需要 exclusive 畫面：

```text
背景 layer: 暫時隱藏
exclusive layer: 高優先權警示
```

exclusive 結束後，service 根據目前狀態重新 render 背景；不應靠恢復陳舊 frame。

對明確的可暫停媒體，service 可以維護：

```text
state: queued | visible | suspended | completed | cancelled
priority
remaining_visible_duration
owner
interruption policy
```

其中 `duration` 預設表示「實際可見時間」，不包含排隊或被高優先權內容覆蓋的時間。若內容過時就沒有意義，才額外指定 wall-clock deadline 或取消政策。

## 同步、process 與 thread

多個 source 不可直接競爭 hardware lock。同步保護的核心不是讓 caller block，而是把 ownership 集中在 service。

```text
source A --\
source B ----> API -> single command queue -> DisplayService
source C --/                                  |
                                               v
                                     render scheduler / compositor
                                               |
                                               v
                                      native I/O owner -> HAL -> libdisplay.so
```

API 呼叫僅等待 command 被接受或拒絕，並快速回傳 handle。它不等待內容播放結束；需要等待完成的 caller 可顯式呼叫 `handle.wait()`。

建議最終部署為獨立 `display-service` process：

```text
display-service process
  |- API/event-loop task: 接收 command、更新 scene
  |- render task: 依目標 FPS 生成最新 frame
  `- native I/O thread: 唯一可呼叫 HAL / libdisplay.so 的 thread
```

所有 `open`、`present`、`clear`、`close` 都必須由同一 native I/O thread 執行，因為 driver、GPIO 與 SPI 應視為非 thread-safe。

render task 與 native I/O thread 之間採 latest-frame-wins：I/O 尚在寫入前一張 frame 時，新產生的舊 frame 不累積，只保留最新的一張。這避免低速面板使動畫延遲不斷累積。

初期可先在同一 process 實作 API、service 與 render；但一開始就要維持兩個邊界：只有 service 可碰 HAL，只有 HAL 可碰 native。之後拆為獨立 process 與 I/O thread 時，外部 API 不必變動。

## 建議目錄

目前實作位於 `src/sbd/core/display`。可逐步演進成：

```text
src/sbd/core/display/
├── api/
│   ├── client.py
│   ├── commands.py
│   └── server.py
├── service/
│   ├── service.py
│   ├── scene.py
│   ├── scheduler.py
│   └── policies.py
├── rendering/
│   ├── renderer.py
│   ├── text.py
│   ├── animation.py
│   ├── video.py
│   └── animations/
│       └── starry_night.py
├── hal/
│   ├── protocol.py
│   ├── factory.py
│   ├── mock.py
│   ├── ctypes_backend.py
│   └── profiles.py
├── native/
│   ├── include/display.h
│   ├── waveshare_ssd1351/
│   └── waveshare_st7789/
└── tests/
    ├── test_renderer_starry.py
    ├── test_service_policy.py
    ├── test_starry_night.py
    └── integration/
        ├── test_ssd1351_present.py
        └── test_st7789_present.py
```

每個 native 資料夾應只對應真實硬體：

- `waveshare_oled_1in5_rgb`：SSD1351、128 x 128。
- `waveshare_lcd_2in_rgb`：ST7789、320 x 240。

目前 `waveshare_lcd_2in_rgb_128` 是將 128 x 128 logical canvas 放大、置中到 320 x 240 LCD 的呈現策略；它不是另一種實體面板 driver，應逐步移為 `hal/profiles.py` 或 renderer 的 layout profile。

## 測試程式的定位

測試／示範程式不屬於五個架構層之一；它們是層外的 consumer，依測試目的從不同入口進入。

```text
完整星空展示測試:
test_starry_night.py -> API -> Service -> Rendering -> HAL -> Native

星空 renderer 單元測試:
test_renderer_starry.py -> Rendering

SSD1351 硬體診斷:
test_ssd1351_present.py -> HAL -> Native
```

目前的 `test_starring_night.py` 同時包含星空生成與直接 `ctypes` 呼叫。演進後，星空演算法應移至 `rendering/animations/starry_night.py`，而完整展示測試則只透過 Display API 發出播放請求。
