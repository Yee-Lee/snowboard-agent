# Display HAL Contract Draft v0.3

狀態：**Draft / Needs Core Team re-review**  
範圍：POC native driver、Python HAL adapter、selected hardware fixture 與 evidence contract。  
非範圍：產品 Renderer、DisplayArbiter、UI priority、Display profile 與 M3–M7 產品行為；上述內容以 Core Team 權威文件為準。

本版回覆 `DELIVERY-004-poc_display-m3-v0.2-review` 的 D1–D5。此文件不得由 POC 自行標記為 Accepted，也不得單獨作為最終 M3 integration acceptance。

---

## 1. Ownership 與呼叫模型

- POC HAL 不建立 IPC、Queue、背景 Service、Renderer 或 Arbiter。
- Core `DisplayDevice` 是唯一 Python contract；POC 不建立第二套 Protocol。
- `start()` / `stop()` 是 async lifecycle，供 Core Resource Manager 統一 `await`。
- `clear()` / `write_pixels()` / `show()` / `size()` 是同步 render primitives，只能由 Core 指定的 event-loop thread 呼叫。
- `clear()` 與 `write_pixels()` 只改 Python adapter 的 back buffer，不做 SPI/GPIO I/O。
- `show()` 是唯一 flush boundary；每次呼叫最多對 native ABI 做一次 full-frame present。
- `single-flush / non-interleaved update` 只保證同一 display intent 不交錯，不宣稱面板掃描為 hardware atomic 或絕對無 tearing。

Renderer、Arbiter、Pillow/LVGL、animation loop、partial update 與 milestone fps 均為產品端決策，不屬於本契約的 normative 要求。

---

## 2. Python HAL adapter contract

權威 Protocol 位於 Core Team 指定的 `src/sbd/core/display/base.py`。POC adapter 預期位於 `src/sbd/core/display/<chip>/driver.py`，native artifacts 位於該 chip 的 `native/`。若 Core repository 的實際路徑調整，由 Core delivery 記錄；POC 不另建 `hal/protocol.py`。

```python
class DisplayDevice(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def clear(self) -> None: ...
    def write_pixels(self, buf: bytes) -> None: ...
    def show(self) -> None: ...
    def size(self) -> tuple[int, int]: ...
```

### 2.1 Lifecycle 與錯誤語意

- `start()` 成功後才建立固定長度 back buffer；重複 start 應拒絕或由 Core lifecycle 防止，結果不得假成功。
- `stop()` 必須冪等。未 start、start 部分失敗或已 stop 時再次呼叫都不得洩漏 native handle、SPI 或 GPIO ownership。
- `.so` 載入、ABI mismatch、invalid config、GPIO/SPI open 與 panel init 失敗，必須 raise，讓 Resource Manager 啟用 NullDisplay fallback。
- `write_pixels()` 僅接受 `bytes`；長度必須精確等於 `width * height * 2`，否則 raise `ValueError` 且不得改動現有 back buffer。
- `show()` 在未啟動時 raise `RuntimeError`；native present 失敗映射為 `DisplayNativeError`，供 Core 進入 rendering-disabled degradation。

### 2.2 Native status 到 Python exception

| Native status | Python boundary |
|---|---|
| `DISPLAY_OK` | 正常返回 |
| `DISPLAY_E_INVALID_ARGUMENT` / `DISPLAY_E_BAD_CONFIG` / `DISPLAY_E_BUFFER_SIZE` | `ValueError` |
| `DISPLAY_E_ABI_MISMATCH` | `DisplayAbiError` |
| `DISPLAY_E_NOT_OPEN` / `DISPLAY_E_ALREADY_OPEN` / `DISPLAY_E_WRONG_THREAD` | `RuntimeError` |
| `DISPLAY_E_GPIO` / `DISPLAY_E_SPI` / `DISPLAY_E_PANEL` / 其他 native failure | `DisplayNativeError` |

---

## 3. Native C ABI v1

Normative public header：`src/sbd/core/display/native/include/display.h`。

### 3.1 穩定型別與版本

- ABI version：`DISPLAY_ABI_VERSION == 1`。
- 所有跨 ABI 整數使用 `<stdint.h>` 固定寬度型別。
- `DisplayConfig` 必須帶 `abi_version` 與 `struct_size`；不相符回傳 `DISPLAY_E_ABI_MISMATCH`。
- `DisplayHandle` 的 invalid value 為 `0`；handle 只在 successful open 後有效。
- 所有 functions 回傳 `DisplayStatus`，不得以 `void` 吞掉錯誤。

Normative functions：

```c
uint32_t display_abi_version(void);
DisplayStatus display_open(const DisplayConfig *config,
                           DisplayHandle *out_handle);
DisplayStatus display_get_info(DisplayHandle handle,
                               DisplayInfo *out_info);
DisplayStatus display_present_rgb565(DisplayHandle handle,
                                     const uint8_t *buffer,
                                     uint32_t length);
DisplayStatus display_close(DisplayHandle handle);
```

### 3.2 Buffer 與 thread ownership

- RGB565 是 row-major、左到右／上到下，每 pixel 兩 bytes，**MSB first / big-endian**；例如 red `0xF800` 傳為 `F8 00`。
- Full-frame buffer 長度固定為 `width * height * 2`；native 必須在任何 I/O 前拒絕錯長度或 NULL buffer。
- Native 僅在 `display_present_rgb565()` call 期間借用 buffer；返回後不持有、不修改 buffer。
- open/get-info/present/close 必須在同一 OS thread。錯誤 thread 應回傳 `DISPLAY_E_WRONG_THREAD`（若目前 backend 無法辨識，必須由 adapter 保證並在 known limits 記錄）。
- Python adapter owns back buffer；native ABI 不提供 `display_clear()`，避免 `clear()` 提前 flush。
- `display_close()` 釋放已取得的所有資源。Python `stop()` 只對有效 handle 呼叫一次 close，藉此提供冪等 lifecycle；直接對無效／已關閉 handle 呼叫 native close 回傳 `DISPLAY_E_NOT_OPEN`。

---

## 4. Hardware Gate

### 4.1 Primary M3 fixture

| 欄位 | 固定值／狀態 |
|---|---|
| Host | Raspberry Pi 5；實際 board revision 待 evidence 記錄 |
| Module | Waveshare 1.5-inch RGB OLED Module；實際 module/revision 由 config 與 operator attestation 確認，不要求照片 |
| Controller | SSD1351 |
| Interface | 4-wire SPI |
| Physical / logical size | 128 × 128 / 128 × 128 |
| Pixel format | RGB565, MSB first |
| Rotation | 0°（若實體 fixture 不符，須先更新 config 與 evidence，不得 silent transform） |
| Supply | 模組 VCC 依 Waveshare module 規格接 3.3 V；GPIO logic 為 Raspberry Pi 3.3 V |
| SPI | SPI0, mode 0, CE0 |
| Requested speed | 4,000,000 Hz；不得以 requested speed 當 effective throughput |

Primary pin map：

| Signal | BCM | Board pin | 備註 |
|---|---:|---:|---|
| VCC | — | 1 或 17 | 3.3 V |
| GND | — | 6 | Ground；可使用其他等效 GND pin，但 evidence 必須記錄 |
| DIN / MOSI | 10 | 19 | SPI0 MOSI |
| CLK / SCLK | 11 | 23 | SPI0 SCLK |
| CS | 8 | 24 | SPI0 CE0 |
| DC / D/C | 25 | 22 | 官方 Raspberry Pi 範例 |
| RST / RES | 27 | 13 | 官方 Raspberry Pi 範例 |
| BL | 不適用 | 不適用 | OLED 無 backlight pin |

SSD1351 Rev 1.5 的 4-wire serial clock minimum cycle 為 220 ns（約 4.55 MHz 上限）。本契約選擇 4 MHz 作為未超規的 requested baseline；仍須由實機記錄 effective speed 與 latency。

### 4.2 Optional fixture

Waveshare 2-inch LCD / ST7789 僅為 optional、unverified fixture，不得替代 primary SSD1351 的 M3 通過證據。它必須使用獨立 config、pin table、module revision 與 evidence；在這些資料完成前不屬於本版 acceptance 範圍，亦不得沿用 OLED 的 BL、orientation 或 latency 結論。

### 4.3 Local config

- Schema：`poc_display/config/display_config.schema.json`
- Sanitized example：`poc_display/config/ssd1351_pi5.example.json`
- Evidence 必須保存實際使用的 config copy 與 SHA-256。
- Primary fixture 的 bus、CE、speed、DC/RST/BL、resolution、rotation、pixel format、byte order 與 gpiochip 必須來自該 local config；不得依賴環境變數或未記錄的 source defaults。
- `gpiochip` 範例保留 `auto`；實際 run 前必須複製為 local config、解析成整數 chip index，並在 evidence 保存該檔案與 hash。Reference adapter 不接受未解析的 `auto`。

---

## 5. Performance contract

本契約不承諾 60 fps、`<20 ms` full-frame latency、DMA、局部更新需求或任何超出 datasheet 的 SPI clock。

Primary SSD1351 的單幀 payload 為 `128 * 128 * 2 = 32768 bytes`。4-wire clock cycle 220 ns 時，僅 payload 理論下限約 57.7 ms，尚未包含 command、DC/CS GPIO、syscall、driver 與 scheduling overhead。

Pi evidence 必須至少記錄：

- sample count、warm-up count；
- latency measurement boundary；
- P50、P95、max；
- resolution、pixel format、config SHA-256；
- requested speed 與可取得時的 effective speed；
- Pi model/revision、CPU、OS/kernel、Python、compiler、lgpio、driver/source SHA；
- target Pi 上由登入使用者執行的 clean build、`ldd -r libdisplay.so` 完整輸出；`make` 成功但有任何 `undefined symbol` 仍為 FAIL；
- color、orientation、readability 與 flicker 的人工觀察。

完成實機測試前，performance disposition 為 `IN_PROGRESS`，不得推導 M7 fps 或排除 partial update／更換硬體。

---

## 6. Artifact provenance 與 integration acceptance

### 6.1 POC delivery manifest

Manifest 必須包含：

- Tracked delivery 使用 POC candidate full 40-character SHA 作整包識別，不要求逐檔 checksum；
- target-Pi user reproducible build command、compiler/toolchain、target OS/arch，以及無 unresolved runtime symbol 的 `ldd -r` 證據；
- vendor source revision、license/notice；
- 無法納入 Git 提交包的 `.so`、actual config 或 raw evidence 才另記整包 SHA-256／custody reference；
- primary hardware、evidence index、known limits。

Dirty worktree、branch HEAD、聊天訊息或只有照片不可視為 Accepted artifact。

### 6.2 兩階段 gate

1. **Accepted as M3 design input**：POC 發布修正版後，由 Core Team 另行建立 ACK；POC 不修改外部 reference 為 Accepted。
2. **Final M3 integration acceptance**：Core 回交 full 40-character integration SHA、source/tests/權威文件範圍、環境/config 與 evidence index；Core Tester acceptance 與 POC fixture verification 分開記錄，兩者不得互相取代。

POC fixture verification 至少覆蓋：start、present、stop、reopen、錯 buffer length、invalid config/device、startup fallback、重複 lifecycle、P50/P95，以及沒有殘留 handle/SPI/GPIO owner。「看得到且不 crash」只作人工補充。

---

## 7. v0.3 delivery index

- Contract：本文件
- Public C header：`src/sbd/core/display/native/include/display.h`
- Python adapter contract：本文件 §2；POC reference adapter 以 manifest 定位
- Manifest：`poc_display/deliveries/manifest_001.md`
- Finding disposition：`poc_display/deliveries/finding_disposition_v0.3.md`
- Local config schema/example：`poc_display/config/`
- Hardware runbook：`poc_display/README.md`
- Read-only workstation/Pi pre-test：`poc_display/tools/environment_pre_test.sh`
- Pi-local capability packet：`poc_display/tools/m3_ssd1351_capability.sh`
- Evidence schema/index與 sanitized summary template：`poc_display/evidence/`

---

## 8. References

- Core review：`docs/pm_handoff/DELIVERY-004-poc_display-m3-v0.2-review.md`
- Waveshare 1.5-inch RGB OLED Module wiki：https://www.waveshare.com/wiki/1.5inch_RGB_OLED_Module
- SSD1351 Rev 1.5 datasheet：https://files.waveshare.com/upload/a/a7/SSD1351-Revision_1.5.pdf

**核准狀態：Draft v0.3；等待 Core Team re-review。**
