# core/display/

顯示裝置的硬體抽象層。此模組僅提供**低階原語**（畫 pixel、寫 buffer、更新畫面），不涉及畫面內容或狀態語意——那些屬於 `sbd/adaptor/display/`。

---

## 設計原則

1. **每個顯示型號一個獨立子目錄**：可以拿到新硬體就開一個目錄試，移除也沒成本，重新編譯不影響其他型號。
2. **統一 Protocol**：所有 driver 實作 `base.py` 定義的 `DisplayDevice` Protocol。
3. **C driver 隔離**：Waveshare/廠商官方 C code 只在該型號目錄內出現，不外洩。
4. **Python 端只用 ctypes**：不寫 CPython 擴充；每個 driver 一個 wrapper 檔載入 `.so`。
5. **Lazy import**：`__init__.py` 的 factory 只在被選中時才 import 該 driver，其他 `.so` 沒 build 也不影響。

---

## 目錄結構

```
core/display/
├── README.md                     ← 本檔
├── __init__.py                   ← factory：make_display(cfg) 依 config 選 driver
├── base.py                       ← DisplayDevice Protocol（統一介面契約）
│
├── mock/                         ← 開發機用（純 Python，無 .so）
│   ├── __init__.py
│   └── driver.py
│
├── ssd1306/                      ← 型號 A：SSD1306 單色 OLED
│   ├── __init__.py
│   ├── driver.py                 ← ctypes wrapper
│   ├── native/
│   │   ├── include/
│   │   │   ├── DEV_Config.h
│   │   │   └── ssd1306.h
│   │   ├── src/
│   │   │   ├── DEV_Config.c
│   │   │   └── ssd1306.c
│   │   ├── Makefile
│   │   └── build/libssd1306.so   ← gitignored
│   └── README.md                 ← 該型號的接線圖、SPI/pin 配置
│
├── oled_1in5_rgb/                ← 型號 B：1.5" RGB OLED（照這個範本複製）
│   ├── __init__.py
│   ├── driver.py
│   ├── native/{include,src,Makefile}
│   └── README.md
│
└── lcd_2in0_ips/                 ← 型號 C：2.0" IPS LCD
    ├── ...
```

**每個型號目錄自成一格**：官方 `DEV_Config.c` 直接放在該型號的 `native/src/`，不共用。理由——各廠商 `DEV_Config.c` 可能有微小差異（腳位、SPI mode、reset 時序），保持獨立可避免相互踩雷。

---

## 抽象契約（`base.py`）

```python
from typing import Protocol


class DisplayDevice(Protocol):
    def clear(self) -> None: ...
    def write_pixels(self, buf: bytes) -> None: ...
    def show(self) -> None: ...
    def close(self) -> None: ...
```

`buf` 的格式（單色 bit-packed / RGB565 / RGB888）由 driver 自行解讀。上層若需通用繪圖，透過 `adaptor/display/renderer.py` 做 pixel format 轉換。

---

## 新增一個顯示型號的步驟

假設你手邊拿到一個新的 `oled_new_model` 模組：

1. **複製骨架**：`cp -r ssd1306 oled_new_model`
2. **替換 C 檔**：把廠商官方 `.c/.h` 放進 `oled_new_model/native/src/` 與 `include/`
3. **調整 Makefile**：改 target 名稱為 `liboled_new_model.so`，確認 include path
4. **改 driver.py**：更新 ctypes 綁定的函式名稱與簽名
5. **編譯測試**：`make -C src/sbd/core/display/oled_new_model/native`
6. **加進 factory**：`__init__.py` 加一個 `elif driver == "oled_new_model": ...` 分支
7. **設定 config**：`config.local.yaml` 選用該型號

**移除只需 `rm -rf` 該目錄**，其他型號完全不受影響。

---

## Makefile 範本（每型號各自一份）

```makefile
CC       ?= gcc
CFLAGS   := -O2 -Wall -Wextra -fPIC -Iinclude
LDFLAGS  := -shared

BUILD    := build
TARGET   := $(BUILD)/libssd1306.so    # 依型號改名
SRC      := $(wildcard src/*.c)
OBJ      := $(patsubst src/%.c, $(BUILD)/%.o, $(SRC))

.PHONY: all clean
all: $(TARGET)

$(TARGET): $(OBJ)
	@mkdir -p $(BUILD)
	$(CC) $(LDFLAGS) -o $@ $^

$(BUILD)/%.o: src/%.c
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(BUILD)
```

---

## ctypes wrapper 範本（`<model>/driver.py`）

```python
from __future__ import annotations

import ctypes
from pathlib import Path

_LIB = Path(__file__).parent / "native" / "build" / "libssd1306.so"


class SSD1306:
    def __init__(self, spi_dev: str, dc_gpio: int, rst_gpio: int) -> None:
        if not _LIB.exists():
            raise RuntimeError(
                f"libssd1306.so not found. Run `make` under {_LIB.parent.parent}"
            )
        self._lib = ctypes.CDLL(str(_LIB))
        self._bind()
        self._ctx = self._lib.ssd1306_open(spi_dev.encode(), dc_gpio, rst_gpio)
        if not self._ctx:
            raise RuntimeError("ssd1306_open returned NULL")

    def _bind(self) -> None:
        self._lib.ssd1306_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        self._lib.ssd1306_open.restype = ctypes.c_void_p
        self._lib.ssd1306_close.argtypes = [ctypes.c_void_p]
        self._lib.ssd1306_clear.argtypes = [ctypes.c_void_p]
        self._lib.ssd1306_clear.restype = ctypes.c_int
        self._lib.ssd1306_write_pixels.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self._lib.ssd1306_write_pixels.restype = ctypes.c_int
        self._lib.ssd1306_show.argtypes = [ctypes.c_void_p]
        self._lib.ssd1306_show.restype = ctypes.c_int

    def clear(self) -> None:
        if self._lib.ssd1306_clear(self._ctx) != 0:
            raise RuntimeError("ssd1306_clear failed")

    def write_pixels(self, buf: bytes) -> None:
        if self._lib.ssd1306_write_pixels(self._ctx, buf, len(buf)) != 0:
            raise RuntimeError("ssd1306_write_pixels failed")

    def show(self) -> None:
        if self._lib.ssd1306_show(self._ctx) != 0:
            raise RuntimeError("ssd1306_show failed")

    def close(self) -> None:
        if self._ctx:
            self._lib.ssd1306_close(self._ctx)
            self._ctx = None
```

---

## Factory（`__init__.py`）

```python
from sbd.core.display.base import DisplayDevice


def make_display(cfg) -> DisplayDevice:
    driver = cfg.driver

    if driver == "mock":
        from sbd.core.display.mock.driver import MockDisplay
        return MockDisplay()

    if driver == "ssd1306":
        from sbd.core.display.ssd1306.driver import SSD1306
        return SSD1306(cfg.spi_dev, cfg.dc_gpio, cfg.rst_gpio)

    if driver == "oled_1in5_rgb":
        from sbd.core.display.oled_1in5_rgb.driver import OLED_1in5_RGB
        return OLED_1in5_RGB(cfg.spi_dev, cfg.dc_gpio, cfg.rst_gpio)

    raise ValueError(f"unknown display driver: {driver}")
```

**Lazy import** 是關鍵：不用該型號就不 import，該 `.so` 沒 build 也不影響其他 driver 運作。

---

## 編譯與測試

**開發機（Windows / 一般 Linux）**：預設用 `mock`，不編譯任何 C。

**RPi5**（首次部署）：
```bash
# 編譯需要用的型號
make -C src/sbd/core/display/ssd1306/native

# 或全部型號一次
for d in src/sbd/core/display/*/native/Makefile; do
    make -C "$(dirname "$d")"
done
```

`scripts/setup_rpi.sh` 會自動處理系統套件（`build-essential`）安裝與編譯。

---

## 效能考量

- ctypes 每次呼叫固定開銷 1–3 μs——**設計上讓 C 端做粗粒度工作**（一次寫整張 buffer，而不是逐 pixel 呼叫）
- 128×64 單色 OLED 每張畫面 1 KB buf，一次 `write_pixels` 呼叫就送完
- 狀態切換每秒最多 1–2 次重繪 → ctypes 開銷 <10 μs，完全可忽略
- 動畫（loading spinner）10 fps → 幾百 μs 級，也無感

若某天真的需要極高頻更新（>1000 fps），才需考慮 CFFI 或 pybind11。POC 用不到。

---

## 不做的事

- **不做 CPython 擴充**（`.pyd` / `.so` extension modules）——ctypes 已足夠
- **不整合到 `pyproject.toml` build**——手動 Makefile 更可控、debug 更容易
- **不做跨型號的 C 抽象層**（例如統一的 `dev_config.c`）——各型號獨立，避免共用 code 綁死彼此
- **不寫 pixel-level 高階繪圖**——那屬於 `adaptor/display/renderer.py`
