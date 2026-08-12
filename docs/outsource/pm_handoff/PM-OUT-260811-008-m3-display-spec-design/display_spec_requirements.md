# Snowboard Display 產品規格需求

| 狀態：規範性Handoff附件；`Ready for PM`；須與008 brief一併交付。

本文件是 `PM-OUT-260811-008-m3-display-spec-design` 的完整規範性附件。PM須與brief及Milestone附件一併交付；Core Team Designer須依本文件在活動產品repo建立並維護權威 `docs/display_spec.md`，內部團隊不代寫外包repo。

## 1. 範圍、權威與選定 Profile

### 1.1 權威邊界

- 本文件定義使用者可觀察的Display內容、版面、文字、lifecycle、privacy及fallback。
- Display HAL、Renderer / Arbiter API、resource ownership與threading以產品 `docs/arch.md`、Ch 2a及Ch 8為準，本文件不重複定義。
- SPI / GPIO、native ABI、pixel byte order、driver build與Pi診斷屬Ch 10、POC contract及delivery evidence，本文件只引用核准profile。
- Milestone文件定義何時實作；test spec定義如何驗證；本文件不保存進度、測試命令或結果。

### 1.2 納入與排除

| Included | Excluded |
| --- | --- |
| OLED 128×128 logical UI、Normal / Fullscreen、State / Main Text / Error / Blank、M7動畫原則、內容開關、privacy及fallback | ST7789產品layout、responsive / scaling政策、progress UI、SPI / GPIO / ABI細節、詳細test steps、完成進度 |

### 1.3 選定產品 Profile

| Field | Requirement | Owner / evidence |
| --- | --- | --- |
| Profile ID | `DSP-PROFILE-OLED-128` | Core Team Designer |
| Primary candidate | Waveshare 1.5-inch RGB OLED / SSD1351 | Accepted Display POC exact SHA |
| Logical canvas | 128×128、1:1 | Fixed product input |
| Orientation | `TBD-POC`；依機構安裝與Accepted POC evidence核准 | Display POC / Tester |
| Baseline blank | 沒有產品內容可見，logical frame為全黑 | Core mock / Pi evidence |
| Animation performance | 不預設FPS；依Pi latency及flicker evidence另定 | Display POC / M7 review |

Waveshare 2-inch LCD / ST7789為未選定backup，native 320×240且有獨立backlight及pin限制。目前不建立LCD layout、mock、blank/backlight或驗收規格；未來若採用，另開產品決策及OUT-TASK。

## 2. 視覺基礎

### 2.1 畫布與視覺 Token

| Token | Requirement | Status |
| --- | --- | --- |
| `canvas.size` | 128×128 | Confirmed |
| `color.background` | 全黑 | Confirmed |
| `color.foreground` | 高對比前景色 | `TBD-CORE-MOCK` |
| `color.error` | 可讀且可與一般內容區分 | `TBD-CORE-MOCK` |
| `status.rect` | StatusBar座標與高度 | `TBD-CORE-MOCK` |
| `main.rect` | Main座標、padding與可用行數 | `TBD-CORE-MOCK` |
| `text.ellipsis` | 固定且由選定字型支援的省略提示 | `TBD-CORE-FONT` |
| `text.missing_glyph` | 固定替代glyph | `TBD-CORE-FONT` |

### 2.2 字型與資產清單

| Asset ID | Purpose | Required metadata | Status |
| --- | --- | --- | --- |
| `FONT-UI-PRIMARY` | 繁中、ASCII、數字及基本標點 | repo path、family、version、license、checksum、支援字元、字級與line height | `TBD-CORE` |
| `ANIM-BOOT` | M7啟動動畫 | repo path、format、dimensions、duration、license、checksum | Deferred to M7 |
| `ANIM-SHUTDOWN` | M7關機動畫 | repo path、format、dimensions、duration、license、checksum | Deferred to M7 |

產品必須使用固定、離線、可追溯的字型，不得依賴Raspberry Pi OS現有字型。M3 Design Ready需提供一份128×128 mock contact sheet，至少涵蓋State、Perception短 / 長文、Tool、Speak及Error；Blank不需要獨立mock文件。

## 3. UI 組成

### 3.1 版面清單

| Layout ID | Regions | Normative behavior | Status |
| --- | --- | --- | --- |
| `LYT-NORMAL` | StatusBar + Main | 兩區同時存在；各Component不得越界；確切geometry引用Visual Tokens | Geometry `TBD-CORE-MOCK` |
| `LYT-FULLSCREEN` | 完整128×128 | 互斥覆蓋Normal；release後回到最新Normal model | Behavior confirmed |

### 3.2 元件清單

| Component ID | Region / layout | Input | Required behavior | Status |
| --- | --- | --- | --- |
| `CMP-STATE` | StatusBar / Normal | 核准的產品state | 顯示最新狀態；確切繁中文案待mock核准 | Copy `TBD-CORE-MOCK` |
| `CMP-MAIN-TEXT` | Main / Normal | 已核准的display text | pixel-width換行、超高截斷、缺字fallback；不保存歷史 | Confirmed ; geometry待mock |
| `CMP-ERROR` | Normal中的核準位置 | sanitized error category / summary | 不顯示技術細節或敏感payload；位置與clear規則待提案 | `TBD-CORE` |
| `CMP-BLANK` | Fullscreen | 無 | 以全黑frame隱藏Normal內容 | Confirmed |
| `CMP-ANIMATION` | Fullscreen | 核准的boot / shutdown asset | M7啟用；bounded、cancelable；失敗回Blank；不得阻擋lifecycle | Deferred to M7 |

### 3.3 Main 文字共通規則

- 產品UI文案以繁體中文為主，並支援ASCII、數字及基本標點。
- 文字依實際glyph pixel width換行，不以字數估算。
- 超出Main可用高度時deterministic截斷，最後一行顯示核准的省略提示。
- emoji、罕見字或特殊符號缺字時顯示固定替代glyph；不得造成render、Display或session失敗。
- Main只保存目前要顯示的內容，不保存或呈現完整對話歷史。
- 目前沒有progress產品需求；`main.progress` 若仍存在於技術契約，只能標示為未啟用預留，不得成為milestone或驗收gate。

## 4. 情境與生命週期

| Trigger / Authoritative data 表示觸發畫面更新的已驗證事件 / 資料，不代表來源module可直接操作Display。Core Team Designer必須由Presenter / observer等既有邊界完成mapping，不得讓Listen、Agent或Action直接依賴panel或Display HAL。

| Scenario ID | Trigger / Authoritative data | Layout / Component | Content | Replace / clear | Product profile |
| --- | --- | --- | --- | --- | --- |
| `SCN-BOOT` | App / Display lifecycle啟動 | Fullscreen / Blank | 無文字 | 第一個有效Normal render後release；確切boundary待Core定位 | M3 / M4c |
| `SCN-STATE` | 已核准的 `stateChanged.new` | Normal / State | 目前狀態文案 | 下一個有效state取代 | M3+ |
| `SCN-PERCEPTION` | 本回合驗證通過的 `PerceptionResult.text` | Normal / Main Text | 語音辨識、外部訊息或視覺文字摘要 | 多結果排序 / 合併及phase exit規則 `TBD-CORE` | M4c+ |
| `SCN-ACTION-TOOL` | 已驗證、正規化且準備執行的tool決定 | Normal / Main Text | 使用者可理解的安全動作說明 | 取代時點及session exit規則 `TBD-CORE` | M4c+ |
| `SCN-ACTION-SPEAK` | 已驗證且準備交給speak action的內容 | Normal / Main Text | 實際說出的文字 | 取代tool / perception及完成後規則 `TBD-CORE` | M4c+ |
| `SCN-ERROR` | Error owner提供的sanitized摘要 | Normal / Error | 簡短錯誤類別或摘要 | recovery / 下一內容的clear規則 `TBD-CORE` | M4c+ |
| `SCN-SHUTDOWN` | App進入graceful shutdown | Fullscreen / Blank | 無文字 | 立即覆蓋Normal，維持至Display stop | M3 / M4c |
| `SCN-BOOT-ANIMATION` | M7 app startup lifecycle | Fullscreen / Animation | 核准啟動動畫 | 完成 / timeout / cancel後進Normal；失敗回Blank | M7 |
| `SCN-SHUTDOWN-ANIMATION` | M7 graceful shutdown lifecycle | Fullscreen / Animation | 核准關機動畫 | bounded best effort；完成 / timeout / 失敗後 Blank，不延後shutdown | M7 |

Fullscreen active時，Normal的State / Main model仍可更新但不得render；Fullscreen release後只render一次最新Normal model。不同fullscreen owner的競爭及release語意沿用Ch 8，不在本文件另建preemption。

## 5. 內容、設定與失敗處理

### 5.1 內容政策

| Allowed | Prohibited |
| --- | --- |
| 本回合已驗證的Perception文字、tool安全動作說明、speak實際內容、產品state、sanitized error摘要 | credential、內部prompt、hidden context、原始tool arguments、未處理模型輸出、過期session / turn資料、完整對話歷史 |

### 5.2 內容顯示設定

- 使用者內容顯示預設開啟，必須可由產品設定關閉。
- 設定範圍至少涵蓋Perception、Tool與Speak內容；State、Blank及系統必要錯誤是否受此設定影響，由Core Team Designer明列並提案。
- 關閉後不得改變session、action、audio、exit code或Display resource lifecycle。

### 5.3 降級與 fallback

| Condition | Observable result |
| --- | --- |
| 空白或sanitization後無內容 | 不顯示敏感或空白placeholder；保留 / 清除政策 `TBD-CORE` |
| 缺字 | 使用固定替代glyph |
| Renderer / HAL runtime failure | Display latch disabled；不改session、state或exit code |
| Real backend startup failure | 依產品契約使用NullDisplay / capability false |
| Animation缺件、失敗、timeout或cancel | 顯示Blank或直接完成lifecycle，不得無界重試 |
| OLED長時間待命 | 原則採idle blank保護；timeout及恢復條件 `TBD-POC / CORE` |

## 6. 核准與追溯

### 6.1 需求追溯表

| Requirement ID | Requirement | Design deliverable | Milestone reference | Review / approval |
| --- | --- | --- | --- | --- |
| `DSP-REQ-001` | OLED 128×128 selected profile；LCD不在本輪 | Profile table + Accepted POC SHA | M3 | Tester / Internal Designer |
| `DSP-REQ-002` | 固定離線繁中字型與高對比tokens | Font inventory + mock contact sheet | M3 Design Ready | User / Internal Designer / Engineering Reviewer |
| `DSP-REQ-003` | Normal / Fullscreen與State / Main / Blank | Layout / Component tables + mock | M3 | Internal Designer / Tester |
| `DSP-REQ-004` | Perception / Tool / Speak目前內容，預設開啟可關閉 | Scenario mapping + config boundary | M4c | User / Internal Designer / Engineering Reviewer |
| `DSP-REQ-005` | sanitized error與privacy | Error mapping + content policy | M4c | Internal Designer / Engineering Reviewer / Tester |
| `DSP-REQ-006` | Boot / Shutdown Blank baseline | lifecycle mapping | M3 | Internal Designer / Tester |
| `DSP-REQ-007` | Boot / Shutdown animation及Blank fallback | storyboard / asset manifest / timing proposal | M7 | User / Internal Designer / Tester |
| `DSP-REQ-008` | missing glyph、NullDisplay及runtime failure不阻斷主流程 | fallback mapping | M3 / M4c | Engineering Reviewer / Tester |
| `DSP-REQ-009` | 目前沒有progress產品需求 | Spec / milestone明確排除 | M3 / M4c | Internal Designer |

## 6.2 Design Ready 必要交付

Core Team Designer須在同一產品commit提交：

1. 權威 `docs/display_spec.md`，使用本文件的精簡結構與stable IDs。
2. 128×128 mock contact sheet：State、Perception短 / 長文、Tool、Speak及Error。
3. Font / Visual Token inventory與license / checksum。
4. Ch 2a / Ch 8 / Ch 10及M3 / M4c / M7 milestone的定位與一致性修訂。
5. Scenario / requirement traceability、architecture-change聲明及所有 `TBD-CORE` disposition。
6. Accepted Display POC exact SHA或清楚標示仍阻擋real-backend integration的缺件。

Design Ready只核准設計；通過後才建立詳細test spec、Developer工作包及implementation delivery。Display POC另以exact SHA提交硬體能力與evidence，不能由本文件或Core mock取代。
