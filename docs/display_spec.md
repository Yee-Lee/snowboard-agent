# Snowboard Display 產品規格

本文件是 Snowboard Display 使用者可觀察行為的設計權威，定義產品 profile、版面、視覺規則、元件、情境、內容安全與 fallback。Display 的 HAL、Renderer、Arbiter、resource ownership 與 threading 契約分別以 `docs/arch.md`、`docs/implement/ch02a_core_hal.md`、`docs/implement/ch08_display_arbiter.md` 與 `docs/implement/ch10_config.md` 為準。

* **Profile ID**：`DSP-PROFILE-OLED-128`
* **產品語言**：繁體中文優先

任何未在本文件定義的畫面、元件或內容都不屬於目前產品行為。

---

## 1. 範圍與 Profile

### 1.1 權威邊界

本文件負責：

* 使用者看見的 Display layout、component、文案與狀態投影。
* 畫面內容何時顯示、取代、清除或被 Fullscreen 覆蓋。
* 字型、visual token、privacy 與 observable fallback。

本文件不重新定義：

* `DisplayDevice`、Renderer、Arbiter 或 Resource Manager API。
* SPI / GPIO、native ABI、pixel byte order、driver build 或硬體接線。
* State Manager、worker、Event Bus 或 action 的 domain contract。

Listen、Reasoner、Action、Adaptor 與硬體 driver 都不得直接操作產品畫面。它們只能提供已驗證的權威資料，由 Presenter、StatusBar 或 lifecycle fullscreen client 經 `DisplayArbiter` 提交完整 intent。

### 1.2 選定 Profile

| Field | Product requirement |
| :--- | :--- |
| Display class | 128×128 RGB OLED |
| Primary controller | SSD1351 |
| Logical canvas | 128×128、1:1、不縮放 |
| Logical orientation | 使用者觀看時文字保持正向；實體 rotation 由 driver / device profile 映射 |
| Baseline blank | logical frame 全黑，沒有產品內容可見 |
| Normal layout | StatusBar + Main |
| Fullscreen layout | 互斥覆蓋完整畫布 |

ST7789 / LCD 不屬於本 profile。若產品未來選用另一種 panel 或解析度，必須建立新的 profile，不得讓本 profile 隱含縮放或改變 layout。

### 1.3 排除項目

目前不定義：

* Progress UI。
* 觸控、LED、OSD overlay 或跨 owner fullscreen preemption。
* Display process、service、queue 或 IPC。
* 完整對話歷史、debug console 或 raw model output。
* 正式 icons、animation asset 本體與 idle burn-in timeout；animation 的共同 lifecycle 原則仍由 §4.3 定義。

`main.progress` 即使存在於技術 template registry，也不是產品元件，產品 owner 不得提交此 intent。

---

## 2. 視覺基礎

### 2.1 Visual tokens

所有座標以左上為原點，rectangle 使用 `(x, y, width, height)`；右、下邊界不包含在 rectangle 內。

| Token | Value | Requirement |
| :--- | :--- | :--- |
| `canvas.rect` | `(0, 0, 128, 128)` | 1:1 logical canvas |
| `status.rect` | `(0, 0, 128, 20)` | 固定於頂部、單行，不得被 Main 覆蓋 |
| `status.content_rect` | `(4, 2, 120, 16)` | State 文字安全區 |
| `main.rect` | `(0, 20, 128, 108)` | 使用 StatusBar 以下的剩餘畫布 |
| `main.content_rect` | `(4, 24, 120, 100)` | Main Text 與 Error 共用文字安全區 |
| `fullscreen.rect` | `(0, 0, 128, 128)` | Active 時完全遮蔽 Normal |
| `divider` | `y=20`、1 px | StatusBar 與 Main 的固定分隔線 |
| `color.background` | `#000000` | 全畫面背景 |
| `color.foreground` | `#FFFFFF` | State 與一般內容 |
| `color.divider` | `#30343A` | Normal layout 分隔線 |
| `color.error` | `#FFB000` | Main Error 摘要；Status state 仍使用 `color.foreground` 並顯示「錯誤」，不得只以顏色表意 |

同一 profile 不得依內容動態縮放版面、字級或安全邊距。

### 2.2 Typography

| Token | Requirement |
| :--- | :--- |
| `FONT-UI-FAMILY` | Noto Sans TC 2.004；Regular 與 Medium 固定、離線並隨產品提供 |
| `font.status` | `FONT-UI-MEDIUM`，12 px、weight 500、line height 16 px、單行 |
| `font.main` | `FONT-UI-REGULAR`，14 px、weight 400、line height 20 px、最多 5 行 |
| `font.error` | `FONT-UI-MEDIUM`，14 px、weight 500、line height 20 px、最多 5 行 |
| `text.ellipsis` | `…`，必須由 `FONT-UI-REGULAR` 提供 |
| `text.missing_glyph` | `□`，必須由 `FONT-UI-REGULAR` 提供 |
| `text.language` | 繁體中文、ASCII、數字及基本標點 |

換行必須使用實際 glyph pixel width，不得以 Unicode code point、UTF-8 byte 或字數估算。內容超出 Main 高度時 deterministic 截斷，最後一行保留足夠寬度顯示 `…`。不支援的字元逐一替換成 `□`，不得使整個 render 失敗。

### 2.3 Asset inventory

| Asset ID | Family | Repository path | License | Required metadata |
| :--- | :--- | :--- | :--- | :--- |
| `FONT-UI-REGULAR` | Noto Sans TC Regular 2.004 | `src/sbd/core/display/assets/fonts/NotoSansTC-Regular.otf` | `src/sbd/core/display/assets/fonts/OFL-1.1.txt` (SIL OFL 1.1) | SHA-256 `5bab0cb3c1cf89dde07c4a95a4054b195afbcfe784d69d75c340780712237537`；fontversion `131334`；language coverage 含 `zh-tw`、ASCII、數字及基本標點 |
| `FONT-UI-MEDIUM` | Noto Sans TC Medium 2.004 | `src/sbd/core/display/assets/fonts/NotoSansTC-Medium.otf` | 同上 | SHA-256 `bf206dca0975779bac71cb49a037a364156ca98a0c431b1b7d6b29fb8952ac7e`；fontversion `131334`；用於 Status 與 Error |

不得依賴 Raspberry Pi OS 或開發機已安裝的字型。兩個 Noto Sans TC weight 均取自官方 `notofonts/noto-cjk` 的固定 tag `Sans2.004`：`Sans/SubsetOTF/TC/`；授權檔 SHA-256 為 `6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2`。

---

## 3. UI 組成

### 3.1 Layout

| Layout ID | Regions | Normative behavior |
| :--- | :--- | :--- |
| `LYT-NORMAL` | StatusBar + Main | 兩區同時存在、不得越界；每次 intent 產生一個完整 frame |
| `LYT-FULLSCREEN` | Fullscreen | 互斥覆蓋 Normal；active 時 Normal model 可更新但不得 render；release 後只 render 一次最新 Normal model |

StatusBar 與 Main 是兩個同時可見的 region；Fullscreen 是互斥的 composition surface，不是第三個同時顯示的區域。

### 3.2 Components

| Component ID | Region | Input / template | Required behavior |
| :--- | :--- | :--- | :--- |
| `CMP-STATE` | StatusBar | `status.state {state}` | 顯示最新狀態文案；單行、垂直置中、靠左 |
| `CMP-MAIN-TEXT` | Main | `main.text {text}` | Pixel-width 換行、overflow 截斷、missing-glyph fallback；只保存目前內容 |
| `CMP-ERROR` | Main | `main.error {category, summary}` | 顯示安全的錯誤類別與摘要；使用 error style，但不重複 Status state 已顯示的「錯誤」 |
| `CMP-BLANK` | Fullscreen | `fullscreen.blank {}` | 產生全黑 frame，不含文字 |
| `CMP-ANIMATION` | Fullscreen | 核准的 Boot / shutdown asset | **M7 Deferred**；bounded、cancelable，失敗回 `CMP-BLANK`；不屬 M3 selected profile 或 test gate |

`fullscreen.text` 只供診斷或已另行定義的產品情境使用，不得取代 Boot / shutdown 的 Blank fallback。Animation component / asset 尚未進入 selected profile；若未來核准，必須遵守 §4.3。在此之前 Boot / shutdown 只使用 Blank。

### 3.3 State 文案

| Authoritative state | 顯示文案 |
| :--- | :--- |
| `IDLE` | `待命` |
| `WAKE` | `準備中` |
| `PERCEPTION` | `接收中` |
| `THINK` | `思考中` |
| `ACTION` | `回應中` |
| `ERROR` | `錯誤` |

Interrupt、recovery、startup 與 shutdown 不是新的 `status.state`。Display 不得為了文案擴充 State Manager state。

---

## 4. 情境與 Lifecycle

### 4.1 Scenario matrix

| Scenario ID | Trigger / authoritative data | Layout / component | Content | Replace / clear |
| :--- | :--- | :--- | :--- | :--- |
| `SCN-BOOT` | App Display lifecycle 啟動 | Fullscreen / Blank | 全黑 | owner `app.lifecycle.boot`；建立第一個有效 Normal model 後 release；failure / NullDisplay 仍須 release ownership |
| `SCN-BOOT-ANIMATION` | M7 app startup lifecycle | Fullscreen / Animation | 核准啟動動畫 | **M7 Deferred**；完成 / timeout / cancel 後進 Normal；失敗回 Blank |
| `SCN-SHUTDOWN-ANIMATION` | M7 graceful shutdown lifecycle | Fullscreen / Animation | 核准關機動畫 | **M7 Deferred**；bounded best effort；完成 / timeout / failure 後 Blank，不延後 shutdown |
| `SCN-STATE` | 初始 state `IDLE`，其後使用 `StateChanged.new` | Normal / State | §3.3 文案 | StatusBar 啟動時投影一次 `IDLE`；其後每次有效 transition 取代 |
| `SCN-PERCEPTION` | 本回合、目前 session / turn 驗證通過的 `PerceptionResult.text` | Normal / Main Text | 語音、外部訊息或視覺輸入的目前文字 | Presenter 收到新 turn 的 `StateChanged.new == PERCEPTION` 時，先以 `write_main(None)` 清除上一輪內容；其後每個有效結果依 observer 收到順序取代，不合併 |
| `SCN-ACTION-TOOL` | 已驗證、正規化且準備執行的 tool decision | Normal / Main Text | Tool registry 提供的安全動作名稱 | Action 開始時取代；下一輪接收或回到 IDLE 時清除 |
| `SCN-ACTION-SPEAK` | 已驗證且準備交給 speak action 的內容 | Normal / Main Text | 實際要說出的文字 | Dispatch 前取代；下一輪接收或回到 IDLE 時清除 |
| `SCN-INTERRUPT` | SM 已接受 `InterruptRequested` 並開始 convergence | Normal / Main Text | `已中止` | 取代目前 Main；真正回到 IDLE 時清除 |
| `SCN-ERROR` | `StateChanged.new == ERROR` 加上 error owner 提供的 sanitized category / summary | Normal / State + Error | `錯誤`與安全摘要 | 進入 ERROR 時取代 Main；recovery 完成並真正回到 IDLE 時清除 |
| `SCN-SHUTDOWN` | App 進入 graceful shutdown | Fullscreen / Blank | 全黑 | owner `app.lifecycle.shutdown`；維持至 Display stop；M4c起real SSD1351在釋放transport前best-effort present最終全黑frame，使stop後面板仍保持黑；present失敗不得阻止cleanup或延後shutdown |

State Manager 初始 state 為 `IDLE` 且不發布虛構的 `None -> IDLE`，所以 StatusBar 的初始投影不是新增 Event。Presenter 不保存列表、不建立對話歷史，也不自行等待或合併多個結果。

### 4.2 Normal / Fullscreen model

1. Fullscreen active 時，State 與 Main intent 仍更新 backing model，但不得觸發 HAL flush。
2. Fullscreen release 後只 render / flush 一次，內容為當下最新 State 與 Main。
3. 不同 fullscreen owner 競爭時拒絕且不排隊；產品情境不得依賴 retry loop。
4. 同一 owner 可更新目前 fullscreen intent；成功取得 ownership 後必須以 `finally` release。
5. Shutdown 不改寫 Arbiter preemption 契約，也不得強制釋放其他 owner。

### 4.3 Animation extension policy

Animation 尚未進入 selected profile。任何未來核准的 Boot / shutdown animation 都必須使用 Fullscreen stable owner，不得直接呼叫 HAL 或繞過 Arbiter。Animation 必須有明確 duration 上限、可取消，並由 owner 在 `finally` release；asset 缺件、render failure、timeout 或 cancel 時回到 `CMP-BLANK`。Boot animation 不得延後主流程 ready，shutdown animation 不得延後 resource reverse-stop 或改變 exit code。不同 fullscreen owner 的競爭仍依 §4.2 拒絕且不排隊，不為 animation 建立 preemption。

---

## 5. 內容、設定與失敗處理

### 5.1 Content policy

| Allowed | Prohibited |
| :--- | :--- |
| 本回合已驗證的 Perception 文字、tool 安全動作名稱、實際 speak 內容、產品 state、sanitized error category / summary | credential、secret、內部 prompt、hidden context、原始 tool arguments、未處理模型輸出、exception detail、stack trace、過期 session / turn 資料、完整對話歷史 |

Presenter 提交 hint 前必須完成 session / turn freshness 驗證、正規化與 sanitization。過期資料直接丟棄，不得清除或取代目前畫面。

若一筆權威新內容為空字串、只含空白，或 sanitization 後為空，必須清除 Main；不得顯示 placeholder，也不得保留上一筆內容。

### 5.2 Session content setting

產品設定 `SET-SHOW-SESSION-CONTENT`：

* 預設開啟。
* 控制 Perception、Tool 與 Speak 內容。
* State、Error、Blank 與 lifecycle 畫面不受此設定影響。
* 關閉時不得改變 session、action、audio、exit code、resource lifecycle 或 logging policy。
* 設定在 process 啟動時生效，不支援 runtime reload。

### 5.3 Failure 與 fallback

| Condition | Observable result |
| :--- | :--- |
| Missing glyph | 逐字使用 `□`，其餘內容照常 render |
| 空白或 sanitization 後無內容 | 清除 Main，不顯示 placeholder |
| 未知 template / 欄位 | 忽略該次顯示意圖並記錄安全摘要，不影響 session |
| Renderer / HAL runtime failure | 停止後續實體 rendering；仍維持 model / ownership；不改變 session state 或 exit code |
| Real backend startup / config failure | 使用 `NullDisplay`，主流程繼續 |
| `NullDisplay` | 不產生實體畫面，但 ownership 與 backing model 規則仍成立 |

Display failure 不得使 session 進入 ERROR，也不得改變既有 process exit code。

---

## 6. Requirement traceability

| Requirement ID | Requirement | 本文件定位 | Milestone | Approval owner / evidence |
| :--- | :--- | :--- | :--- | :--- |
| `DSP-REQ-001` | OLED 128×128 selected profile；LCD 排除 | §1 | M3 | Designer + Tester；Accepted Display POC / M3 coverage sign-off |
| `DSP-REQ-002` | 固定離線繁中字型與高對比 visual rules | §2 | M3 Design Ready | User + Designer + Reviewer；approved mock / font inventory |
| `DSP-REQ-003` | Normal / Fullscreen 與 State / Main / Error / Blank | §3–§4 | M3 baseline；Error runtime M4c | Designer + Tester；M3 / M4c test spec |
| `DSP-REQ-004` | `SET-SHOW-SESSION-CONTENT` 預設開啟，只控制 Perception / Tool / Speak；startup-static，不支援 runtime reload | §4.1、§5.2 | M4c | User + Designer + Reviewer；M4c design / test approval |
| `DSP-REQ-005` | Sanitized error 與 privacy | §3.2、§4.1、§5.1 | M4c | Designer + Reviewer + Tester；M4c design / test approval |
| `DSP-REQ-006` | Boot / shutdown Blank | §4.1 | M3 baseline；M4c補stop後保持全黑 | Designer + Tester；M3 coverage / Pi evidence；M4c lifecycle regression |
| `DSP-REQ-007` | Boot / shutdown animation 原則與 Blank fallback | §3.2、§4.1、§4.3 | M7 Deferred | User + Designer + Tester；M7 spec-first approval |
| `DSP-REQ-008` | Missing glyph、NullDisplay 與 runtime failure 不阻斷主流程 | §2.2、§5.3 | M3 baseline；session mapping M4c | Reviewer + Tester；M3 / M4c evidence |
| `DSP-REQ-009` | Progress UI 不屬目前產品行為 | §1.3 | M3 / M4c exclusion | Designer；milestone / test-spec exclusion review |
