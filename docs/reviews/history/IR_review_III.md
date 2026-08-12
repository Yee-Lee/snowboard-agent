---
requestor: "Reviewer"
owner: "Designer"
status: "Resolved"
---

# 審查單：IR_review_III（Display spec 與 Ch 8 / Ch 10 架構一致性審查）

## 審查目標

針對 Designer 新完成的 `docs/display_spec.md`（DSP-PROFILE-OLED-128），審查其與 `docs/implement/ch08_display_arbiter.md`、`docs/implement/ch10_config.md` 及 `docs/arch.md` 的架構一致性。以 `arch.md` 為頂層對齊基準，以 IR-Final 通過的 Ch 8 / Ch 10 為實作契約基準。

審查基準版本：2026-08-12 快照

---

## Finding 清單

### 🔴 FIND-IR-01：Ch 10 `DisplayConfig` 預設尺寸（64）與 display_spec 選定 Profile（128×128）不一致

**位置**：`docs/implement/ch10_config.md` §7 `DisplayConfig`

**問題**：

`DisplayConfig` 的欄位預設值為：
```python
width: int = 128
height: int = 64      # ← 不一致
pixel_format: Literal["mono1", "rgb565", "rgb888"] = "mono1"  # ← 不一致
```

但 `display_spec.md` §1.2 明確選定 Profile 為「128×128 RGB OLED / SSD1351」。`height` 預設為 `64`（SSD1306 mono OLED 的常見尺寸），`pixel_format` 預設 `"mono1"` 與 SSD1351 RGB 硬體不符。在 mock backend 以預設 config 啟動時，render / pixel buffer 測試將在錯誤前提下通過，形成假綠燈風險。

**契約依據**：`display_spec.md` §1.2 `canvas.rect = (0,0,128,128)`；色彩欄位均為 RGB
**最低驗收條件**：將 `DisplayConfig` 預設值修正為 `height=128`、`pixel_format="rgb565"`；或在 Ch 10 §7 cross-validation 中明確記錄「selected profile 必須使用 128×128 與 rgb565，不得以 driver 差異放寬」。

---

### 🔴 FIND-IR-02：display_spec.md §3.2 `CMP-ANIMATION` 列為初版組件，但 §1.3 明確排除 animation asset

**位置**：`docs/display_spec.md` §3.2 Components 表格

**問題**：

§3.2 Components 表格將 `CMP-ANIMATION` 列為正式組件，但 §1.3 排除項目明確宣告「正式 icons、animation asset 本體與 idle burn-in timeout；animation 的共同 lifecycle 原則仍由 §4.3 定義」，同時補充「Animation asset 尚未納入 selected profile 時，Boot / shutdown 只使用 Blank」。`CMP-ANIMATION` 既列入 Components 表格（暗示屬於 selected profile），又同時宣告「asset 尚未納入」，形成正面矛盾。

**契約依據**：`display_spec.md` §1.1
**最低驗收條件**：移除 `CMP-ANIMATION` 於 §3.2 Components 表格，並在 §3.2 表格後補充說明「Animation component / asset 尚未進入 selected profile；lifecycle 原則見 §4.3」；§4.3 保留 animation lifecycle 原則供未來使用。

---

### 🟠 FIND-IR-03：display_spec.md §4.1 `SCN-PERCEPTION` 的「清除」時機語意與 Ch 8 backing model 行為不完全對齊

**位置**：`docs/display_spec.md` §4.1 Scenario matrix，行 `SCN-PERCEPTION`

**問題**：

`SCN-PERCEPTION` 原描述「下一輪接收開始時清除上一輪內容」，但未說明清除的發起者與 state machine 觸發機制，與 Ch 8 §5.2（`write_main(None)` 清除）對不齊，導致 Presenter 實作者對時機產生不同解讀。

**最低驗收條件**：明確說明 Presenter 在收到 `StateChanged.new == PERCEPTION` 時先以 `write_main(None)` 清除上一輪，再開始接收新一輪內容。

---

### 🟠 FIND-IR-04：display_spec.md §6 Requirement traceability 漏掉 `SET-SHOW-SESSION-CONTENT` 的 startup-static / no-reload 語意

**位置**：`docs/display_spec.md` §6 Requirement traceability

**問題**：

`DSP-REQ-004` 原標記為「Perception / Tool / Speak 目前內容，預設開啟並可關閉」，但未包含 `SET-SHOW-SESSION-CONTENT` 的 startup-only / no-runtime-reload 語意，與 Ch 10 §7 cross-validation 的對應條目缺乏 Requirement ID 引用，造成可追溯性不完整。

**最低驗收條件**：在 §6 `DSP-REQ-004` 中補充「startup-static，不支援 runtime reload」語意，並在 Ch 10 §7 cross-validation 引用該 Requirement ID。

---

## Designer 修訂說明（2026-08-12）

* **FIND-IR-01**：Ch 10 §7 `DisplayConfig` 預設值修正為 `height=128`、`pixel_format="rgb565"`；Ch 10 §7 cross-validation 補充「selected `DSP-PROFILE-OLED-128` 必須使用 `128×128` 與 `rgb565`，不得以 mock / real driver 差異放寬；未來 profile 必須另定 profile-specific validation」。
* **FIND-IR-02**：`display_spec.md` §3.2 移除 `CMP-ANIMATION` 表格行；在表格後補充說明「Animation component / asset 尚未進入 selected profile；若未來核准，必須遵守 §4.3」；§4.3 標題補充「Animation 尚未進入 selected profile」並保留 lifecycle 原則。
* **FIND-IR-03**：`display_spec.md` §4.1 `SCN-PERCEPTION` 的「Replace / clear」欄改為「Presenter 收到新 turn 的 `StateChanged.new == PERCEPTION` 時，先以 `write_main(None)` 清除上一輪內容；其後每個有效結果依 observer 收到順序取代，不合併」。
* **FIND-IR-04**：`display_spec.md` §6 `DSP-REQ-004` 補充「`SET-SHOW-SESSION-CONTENT` 預設開啟，只控制 Perception / Tool / Speak；startup-static，不支援 runtime reload」；Ch 10 §7 cross-validation 引用 `DSP-REQ-004`。

---

## Reviewer 最終裁定（2026-08-12）

| Finding | 結果 | 驗收依據 |
|---|---|---|
| FIND-IR-01 🔴 | ✅ 通過 | Ch 10 §7 `DisplayConfig` 預設值已修正為 `height=128`、`pixel_format="rgb565"`；cross-validation 補充 profile 強制規則，假綠燈風險消除 |
| FIND-IR-02 🔴 | ✅ 通過 | §3.2 已移除 `CMP-ANIMATION` 表格行，改以表格後注釋說明「Animation component / asset 尚未進入 selected profile」；§4.3 保留 lifecycle 原則並加「尚未進入 selected profile」標示，§1.3 與 §3.2 不再矛盾 |
| FIND-IR-03 🟠 | ✅ 通過 | §4.1 `SCN-PERCEPTION`「Replace / clear」欄已明確以 `StateChanged.new == PERCEPTION` 為觸發點，Presenter 先以 `write_main(None)` 清除，再接收新一輪，與 Ch 8 §5.2 語意對齊 |
| FIND-IR-04 🟠 | ✅ 通過 | `DSP-REQ-004` 補充 startup-static / no-reload 語意；Ch 10 §7 cross-validation 引用 `DSP-REQ-004`，可追溯性完整 |

**結論：Display spec 與 Ch 8 / Ch 10 架構一致性審查通過。**

本單據狀態設為 `Resolved`，依照流程移至 `docs/reviews/history/`。
