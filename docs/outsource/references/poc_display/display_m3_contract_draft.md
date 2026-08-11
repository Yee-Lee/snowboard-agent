# Display Contract & Spec Draft v0.2

此文件為 POC 團隊交付給核心團隊 (Core Team) 的底層驅動規範與渲染架構草案。核心團隊將基於此草案撰寫正式的產品 `display_spec.md`。

本草案嚴格遵守**「技術輸入限制在 HAL 層級以內」**且**「不採用 IPC、Queue 或 Service 架構」**之原則，並說明底層架構如何支援從 M3 (基礎) 到 M7 (完整動畫 UX) 的擴充。

---

## 1. 架構原則與技術限制
* **無 IPC / 無 Queue / 無獨立 Service**：HAL (Hardware Abstraction Layer) 採用純同步、阻擋式的函數呼叫。不維護自己的背景執行緒或訊息佇列。
* **狀態無涉 (Stateless)**：HAL 不知道 UI 畫面的內容，也不負責管理 UI 優先權。
* **單一控制流**：上層的 Renderer / Arbiter 必須自行負責 Thread-safety，並在單一控制流中呼叫 HAL。

---

## 2. Python HAL Protocol (DisplayDevice)
**所在位置**: `src/sbd/core/display/hal/protocol.py`

```python
class DisplayDevice(Protocol):
    info: DisplayInfo

    def start(self) -> None:
        """初始化硬體資源 (SPI/GPIO)。支援 Lazy Loading。"""

    def stop(self) -> None:
        """安全釋放所有硬體資源。"""

    def clear(self) -> None:
        """將記憶體中的 Back Buffer 填滿黑色，不觸發硬體 I/O。"""

    def write_pixels(self, frame: Rgb565Frame) -> None:
        """將完整的 Rgb565 畫面寫入 Back Buffer (長度需等於 w * h * 2)。"""

    def show(self) -> None:
        """(Atomic Flush) 將 Back Buffer 透過 SPI 完整寫入實體螢幕。"""

    def size(self) -> tuple[int, int]:
        """回傳 (width, height)。"""
```

---

## 3. 渲染機制與擴充性 (M3 to M7)

雖然 POC 團隊不負責實作產品端的 Renderer 與 Arbiter，但以下提供基於本 HAL 的渲染機制建議，以確保架構可順利從 M3 擴充至 M7：

### 階段 M3：基礎渲染 (Baseline)
*   **Arbiter 機制**：透過簡單的同步鎖 (Mutex) 或單一主執行緒控制。當觸發事件 (如按鈕按下) 時，Arbiter 決定要顯示的內容。
*   **Renderer 行為**：使用 Pillow 組合文字與圖形。
*   **HAL 互動**：
    1. 呼叫 `clear()`
    2. 呼叫 `write_pixels(frame)`
    3. 呼叫 `show()` (畫面一次性更新，無閃爍)
*   **特性**：低更新率，事件驅動 (Event-driven)。

### 階段 M4~M6：局部更新與過場
*   **Arbiter 機制**：引入簡單的 State Machine 管理畫面層級。
*   **Renderer 行為**：優化渲染邏輯，計算出差異畫面，但對於 HAL 依然傳遞完整 Frame (維持架構簡單)，或未來擴充 `write_rect_pixels()` (若效能遇瓶頸)。
*   **HAL 互動**：維持 `write_pixels()` + `show()` 的 Atomic Flush。由於底層 C ABI 使用 DMA/高速 SPI，全螢幕 Flush 在 60MHz 下延遲極低 (<20ms)，通常無需妥協於複雜的局部 I/O。

### 階段 M7：完整動畫 UX (60fps)
*   **Arbiter 機制**：具備 60fps 的 Render Loop (Game Loop)。Arbiter 負責計算每幀的動畫插值 (Interpolation)。
*   **Renderer 行為**：可能從 Pillow 升級為更高效的圖形引擎 (如 LVGL 綁定或其他 C-based renderer) 以產生 RGB565 buffer。
*   **HAL 互動**：
    *   在 Render Loop 中，每秒 60 次以同步方式呼叫 `write_pixels()` + `show()`。
    *   由於 HAL 不包含任何 Queue 或 IPC 的 Overhead，`show()` 的延遲直接等於 SPI 傳輸時間。只要上層的 Render 夠快，HAL 完全能支撐 M7 的流暢動畫需求。

---

## 4. Native C ABI Contract (硬體基準)
**所在位置**: `src/sbd/core/display/native/include/display.h`

```c
// 傳入完整的 SPI 與 GPIO 腳位設定 (取代環境變數)
int display_open(const DisplayConfig *config);
// 寫入 RGB565 Buffer
int display_present_rgb565(int handle, const char *buffer, int length);
// 清除實體面板畫面
void display_clear(int handle);
// 釋放資源
void display_close(int handle);
```
*   **硬體防呆**：底層 C 代碼負責攔截所有錯誤狀態（如 SPI 斷線、GPIO 佔用），並安全地釋放資源避免死鎖，提供堅固的硬體操作基準。

---

## 5. 硬體基準與測試規格 (Hardware Gate)
為確保 Core Team 能在 Raspberry Pi 5 上建立與 POC 團隊完全一致的測試環境 (Fixture)，以下為明確的硬體與配線規格：

### 支援面板規格
1. **OLED 面板 (主要測試對象)**
   * **型號**: Waveshare 1.5-inch RGB OLED Module
   * **控制器**: SSD1351
   * **解析度**: 128x128
   * **Pixel Format**: RGB565 (16-bit)
2. **LCD 面板 (備用驗證)**
   * **型號**: Waveshare 2-inch LCD Module
   * **控制器**: ST7789
   * **解析度**: 320x240 (可縮放至邏輯 128x128)

### 通訊與接線規格
* **通訊介面**: SPI0
* **SPI 速率 (Driver Config)**: 60 MHz (`speed_hz = 60000000`)
* **GPIO BCM 接線 (對應 Pi 5)**:
  * `VCC`: 3.3V (Pin 1或17)
  * `GND`: Ground (Pin 6, 9, 14, 20...)
  * `DIN` (MOSI): GPIO 10 (Pin 19)
  * `CLK` (SCLK): GPIO 11 (Pin 23)
  * `CS` (CE0): GPIO 8 (Pin 24)
  * `DC` (Data/Command): GPIO 24 (Pin 18)
  * `RST` (Reset): GPIO 25 (Pin 22)
  * `BL` (Backlight, 僅 LCD 需接): GPIO 18 (Pin 12)

---

## 6. 整合契約與交付邊界 (Integration Contract)
明確定義 POC 團隊與 Core Team 雙方的交付責任與交接點。

### POC 團隊交付物 (POC Deliverables)
1. **軟體層**: 穩定的 `.so` 驅動 (Native C ABI) 以及無狀態的 Python HAL Adapter (`src/sbd/core/display/hal/`)。
2. **硬體驗證證據 (Evidence)**: 在 Pi 5 上通過 Diagnostics (`test_ssd1351_present.py`) 的執行 Logs、效能數據 (P50/P95)，以及硬體運行影片或照片 (存於 `poc_display/evidence/`)。
3. **交付清單**: 包含環境參數與 SHA 的 `manifest_001.md`。

### Core Team 驗收與回傳物 (Core Team Requirements)
1. **前置放行**: Core Team 需審閱此 Contract v0.2，並將其標記為 `v1.0 / Accepted`。
2. **M3 實作整合**: Core Team 基於本契約的 `DisplayDevice` 介面，開發 M3 的 `DisplayRenderer` 與 `DisplayArbiter`。
3. **交付 M3 SHA (Integration Handoff)**: Core Team 完成 M3 後，需回傳整合測試分支的 **Exact Commit SHA**。
4. **POC 最終驗證**: POC 團隊將拉取該 SHA，在實體 Pi 5 測試夾具上進行運行，若 M3 畫面可正確渲染且不發生 Crash，即代表 **POC 任務圓滿結束**，完全移交給主線。

---
**核准狀態**: [ ] Draft v0.2 (等待 Core Team 升級為 v1.0 / Accepted)
