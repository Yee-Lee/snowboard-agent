# Ch 8. Display 仲裁層協定

本章定義 Display 技術契約；最低顯示內容、lifecycle 與未來完整 UX profile 見 `../display_spec.md`。

屬於 implement.md 索引 | 對應 arch.md §2.3 / §5.3 / §6.8 | 狀態：定稿（IR-final 已通過（2026-08-01））

上游：Ch 2a、Ch 5。

## 0. 已確認判斷

| 編號 | 判斷點 | 已確認結論 |
| :--- | :--- | :--- |
| ch8-Q1 | 四動作是 sync 或 async | sync；HAL render primitives 皆 sync，方法中不可做等待型 I/O |
| ch8-Q2 | Fullscreen owner 如何識別 | request / release 都帶 stable `owner_id`；仲裁器保存 owner，避免非 owner 釋放 |
| ch8-Q3 | 同一 owner 重複 request | 視為更新目前 fullscreen hint 並回 `True` |
| ch8-Q4 | Fullscreen 期間 status/main 更新 | 更新 backing model 但不 render；release 後一次 render 最新常規畫面 |
| ch8-Q5 | Hint 是否走通用大 schema | 否；只固定 envelope `template + data`，template-specific 驗證交 renderer |
| ch8-Q6 | Renderer 落點 | 與 arbiter 同層 `core/display` HAL 上層薄殼；不放 adaptor |
| ch8-Q7 | NullDisplay 行為 | 仍執行 ownership / model 規則，但 size `(0, 0)` 時跳過 render/show |
| ch8-Q8 | Runtime display failure 是否中斷 session | 否；arbiter latch rendering-disabled 並 log error，主流程繼續 |
| ch8-Q9 | 呼叫執行緒 | 只允許 event-loop thread；native producer 先用 loop thread-safe scheduling 排回 |

## 1. 範圍與非目標

### 1.1 本章包含
• `DisplayArbiter` 四動作的具體 signature、owner 與同步語意。
• status / main / fullscreen backing model 與 atomic render。
• Renderer 窄契約、hint envelope 與 slot 清單。
• NullDisplay、runtime failure 與 resource injection 政策。
• Presenter / StatusBar / fullscreen client 的驗收條件。

### 1.2 本章不包含
• SPI / pixel encoding / frame buffer driver：Ch 2a。
• OLED 版面美術、字型資產與各 template 像素配置；內容 profile 由 `display_spec.md` 定義，不寫入本章 API 契約。
• Adjuster overlay、LED、touch：arch.md §8 未定案。
• StatusBar owner 的業務邏輯；本章只列 slot ownership / 輸入。
• 動態 capability map 更新；capability map 仍是 startup static。

## 2. 套件與依賴

```text
src/sbd/core/display/
├── base.py              # DisplayDevice ( Ch 2a )
├── arbiter.py           # DisplayArbiter
├── renderer.py          # DisplayRenderer / RenderModel
├── hints.py             # DisplayHint 與驗證錯誤
└── ...                  # null / mock / chip backends
```

雖位於 `core/display`，`arbiter.py` / `renderer.py` 是 HAL 上層薄殼，不擴充 `DisplayDevice` Protocol，也不讓底層 driver 知道 status/main/fullscreen。

Resource Manager 註冊關係：

`core.display.device` → `core.display.renderer` → `core.display.arbiter` → `observer.presenter` → `observer.status_bar` → optional fullscreen clients

Renderer / arbiter factory 失敗依 Ch 5 observer policy 處理：顯示能力不可用但主對話流程仍可啟動。底層 real display 失敗而換 NullDisplay 時，兩者仍可建立，`capability_of("display")=False`。

## 3. Hint 與 render model

```python
from dataclasses import dataclass, field
from typing import Any, Mapping

@dataclass(frozen=True, slots=True)
class DisplayHint:
    template: str
    data: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class RenderModel:
    status_slots: tuple[tuple[str, DisplayHint], ...]
    main: DisplayHint | None
    fullscreen: DisplayHint | None
```

規則：
• `template` 是非空 composition root / renderer 已註冊的名稱。
• `data` 只允許 JSON-compatible value，建立時 recursive copy 以脫離 caller 原物件，之後唯讀。
• Hint 不含 pixel bytes、callable、HAL object 或 owner reference。
• Template-specific required fields 由 `DisplayRenderer.validate(hint)` 驗證。
• Arbiter 保存最後一份 status slot 與 main hint；不保存歷史、不設 queue。

## 4. Renderer 契約

```python
class DisplayRenderer(Protocol):
    def validate(self, hint: DisplayHint) -> None: ...

    def render(
        self,
        *,
        size: tuple[int, int],
        model: RenderModel,
    ) -> bytes: ...
```

• `render()` 是純同步轉換，不直接呼叫 HAL。
• 回傳 bytes 必須符合選定 `DisplayDevice` 的 pixel encoding 與 buffer length。
• size `(0, 0)` 時 arbiter 不呼叫 renderer。
• 未知 template / 欄位錯誤 raise `DisplayHintError`。
• Renderer bug 或 buffer length 不合會在 arbiter render boundary 被捕捉，進 §8 operational degradation。

初版必備 templates：

| template | data schema |
| :--- | :--- |
| `status.text` | `data={"text": str}` |
| `status.state` | `data={"state": IDLE\|WAKE\|PERCEPTION\|THINK\|ACTION\|ERROR}` |
| `main.text` | `data={"text": str}` |
| `main.progress` | `data={"label": str, "value": float 0..1}` |
| `fullscreen.text` | `data={"title": str, "body?": str}` |
| `fullscreen.blank` | `data={}` |

沒有實際使用者的 template 不預先加入。

## 5. Arbiter public API

```python
class DisplayArbiter:
    def write_status_slot(
        self,
        slot_id: str,
        hint: DisplayHint | None,
    ) -> None: ...

    def write_main(self, hint: DisplayHint | None) -> None: ...

    def request_fullscreen(
        self,
        owner_id: str,
        hint: DisplayHint,
    ) -> bool: ...

    def release_fullscreen(self, owner_id: str) -> None: ...
```

`None` 代表清除指定 slot 或 main。Fullscreen 必須用 release，不接受 `request_fullscreen(..., None)`。

### 5.1 write_status_slot
1. 驗證 `slot_id` 已註冊、`hint` 合法。
2. 更新或刪除 backing slot。
3. 若無 fullscreen owner，render 常規畫面。
4. 若 fullscreen active，只保存，不 flush。

未知 slot 是啟動 / 程式錯誤，raise `UnknownDisplaySlot`；slot owner 不能在 runtime 動態註冊新名稱。

### 5.2 write_main
1. 驗證 `hint` 合法。
2. 更新或刪除 main backing model。
3. 若無 fullscreen owner，render 常規畫面。
4. 若 fullscreen active，只保存，不 flush。

### 5.3 request_fullscreen
1. 若目前已有非此 `owner_id` 的 fullscreen active，拒絕，回傳 `False`；不建立佇列。
2. 驗證 `hint` 合法。
3. 保存 `owner_id` 與 `hint`，以 `RenderModel(fullscreen=hint)` 執行 atomic render，回傳 `True`。
4. 若原本即為此 `owner_id` 佔有，覆寫 hint 並重新 render，回傳 `True`。

### 5.4 release_fullscreen
1. 若 `owner_id` 非目前 active owner，直接忽略 ( no-op )。
2. 若 `owner_id` 相符，清除 fullscreen，拿最新 status slots 與 main 重建 `RenderModel` 執行 atomic render。

## 6. Slot 註冊與靜態 registry

初版固定 slot：

| slot_id | owner | 資料來源 | template | 更新時機 |
| :--- | :--- | :--- | :--- | :--- |
| `clock` | StatusBar clock task | local wall clock | `status.text` | 分鐘變更 |
| `state` | StatusBar state observer | `StateChanged.new` | `status.state` | 每次狀態轉移 |
| `volume` | volume adjustment | Audio 設定值 | `status.text` | 音量變更 |
| `connection` | adaptor status observer | `is_connected()` | `status.text` | 連線變更 |
| `capability` | startup capability presenter | startup snapshot | `status.text` | startup 完成一次 |
| `error` | logging/error observer | sanitized 摘要 | `status.text` | error 顯示政策觸發 |

`capability` 是 startup snapshot，不代表 capability map runtime 改變。Recovery 成功 / 失敗不更新 map，也不改此 slot。

Slot 清單是 code-declared registry，不進 config。是否啟用某 slot 由對應 owner 是否建立決定；未建立的 slot 維持空白。

## 7. Render 與 atomic flush

每次需要畫面更新：
1. 呼叫 `device.size()`。
2. `(0, 0)` → return，不改 model / ownership。
3. 建 immutable `RenderModel` snapshot：
   - fullscreen active：`fullscreen=hint`，status/main 仍可保留但 renderer 忽略；
   - 常規：`fullscreen=None`，slots 依 registry order，main 為最新值。
4. `renderer.render(size, model)`。
5. `device.clear()`。
6. `device.write_pixels(buf)`。
7. `device.show()`。

步驟 4~7 是同一同步 call stack，沒有 `await`，所以主 loop 中不會被另一個 display intent 交錯。HAL 的 back buffer + `show()` 保證不顯示半熱畫面。

Display method 不得從任意 native thread 直接呼叫。需要跨 thread 更新時，owner 使用 `loop.call_soon_threadsafe()` 把完整 intent 排回主 loop。

## 8. Runtime degradation

```python
class DisplayArbiterError(RuntimeError): ...
class DisplayHintError(ValueError): ...
class UnknownDisplaySlot(DisplayHintError): ...
```

Hint validation error 是 caller contract error：
• 直接呼叫者收到 exception；
• Event Bus observer 必須在自身 handler boundary 捕捉、log warning，不讓顯示 hint 錯誤觸發系統 `ErrorOccurred`。

Renderer / HAL runtime exception：
1. 捕捉 root exception。
2. `_rendering_enabled=False`。
3. log `ERROR` 一次，含 component 與 exception type。
4. 後續 intent 仍更新 backing model / fullscreen ownership，但跳過 render。
5. 不 publish `ErrorOccurred`、不進 SM `ERROR`、不更新 capability map。

理由：Display 是觀察 / 表達通道，arch.md 規定其損壞不應中斷主要對話流程。Runtime 自動 rebuild 不在現有架構；新 process startup 會重新嘗試 real/null 建立。

## 9. Lifecycle

Arbiter 本身無背景 task：

```python
async def start(self) -> None:
    self._assert_loop_thread()
    self._started = True
    self._render_current()

async def stop(self) -> None:
    if not self._started:
        return
    if self._rendering_enabled:
        self._device.clear()
        self._device.show()
    self._started = False
```

• start 前 public write raise `RuntimeError`。
• stop 後 write 為 no-op + `DEBUG`，避免 reverse shutdown 中的 late observer 造成 fatal。
• stop 不呼叫 `device.stop()`；RM 依 reverse order 另行停止底層。

## 10. 驗收與測試

最低純軟體測試：
1. status 與 main 各自更新且共同出現在常規 `RenderModel`。
2. fullscreen active 時 status/main 只更新 model、不呼叫 show。
3. release 後只 render 一次且包含 fullscreen 期間最新 model。
4. 不同 owner request 被拒絕且不排隊。
5. 相同 owner request 更新並回 `True`。
6. 非 owner release 不清除 fullscreen。
7. `None` 清除 slot/main。
8. slot 順序由 registry 固定，不因更新順序改變。
9. NullDisplay size `(0, 0)` 時不呼叫 renderer 但 ownership 規則仍成立。
10. 一次更新只做一組 clear/write/show，無半熱 flush。
11. 未知 slot / template 可區分並不污染既有 model。
12. renderer / HAL 第一次 runtime failure 後 latch disabled，後續不重試、不發 `ErrorOccurred`。
13. stop 清畫面且不重複停止底層 device。
14. native thread 直接呼叫被 thread-affinity guard 拒絕。

Mock renderer 保存 `RenderModel`；MockDisplay 保存 clear / write / show call order 與 buffer，測試不依賴實體 OLED。

## 11. 對後續章節的輸入

• Ch 10：DisplayDevice backend / 解析度進 config；slot 與 template 清單不進 config。
• Ch 11：display operational degradation log 一次、不發布 `ErrorOccurred`。
