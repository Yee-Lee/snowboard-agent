# M7D1 — Display UX discovery design

- Status: IN PROGRESS; decision scope recorded, candidate design not yet complete.
- Authority: [Core request](../pm_handoff/REQUEST-DISPLAY-POC-M7-UX-DISCOVERY-001.md).
- Formal stages: M7D1–M7D6; D1–D6 are abbreviations within the M7 context.
- USER decision: tool-oriented interface is the primary direction.
- USER confirmed nine scenario categories, formally numbered SCN-01–SCN-09 below.
- USER reviewed the first sketch sheet without requested changes and named the initial theme **baseline** (THM-baseline).
- Purpose: select a small useful candidate set and the risks to resolve in M7D2–M7D4.
- This document contains discovery proposals, not adopted Core product requirements or integration evidence.

## 本次討論紀錄停點

前次 USER 要求記錄到 ANI 語意決定；2026-10-09 USER 指示恢復討論，先將全部走完一輪，
不先深入沙漏細節。M7D1 仍為 IN PROGRESS。

已確定：

- 任務正式編號 M7D1–M7D6，M7 語境中簡稱 D1–D6。
- 工具型介面為主；九類場景正式編號 SCN-01–SCN-09。
- 設計階層 Style → Theme → Scene；STYLE-01 純文字與 STYLE-02 圖示＋文字目前皆為候選。
- 主題正式 ID 為 THM-baseline。USER 看過第一批 PNG 草圖，沒有提出修改。
- 可替換的視覺設定用變數記錄；StatusBar 與 Main 的背景、前景、字級、行高等各自獨立。
- 預留打字機效果能力；這與接收 raw model streaming 不同，預設仍直接顯示合法文字。
- SCN-05 狀態列使用「思考中」搭配沙漏動畫；baseline 選擇翻轉循環、不做落沙。
- ANI-001 唯一代表動畫項目「思考沙漏」；跨主題維持此 ID，各 Theme 可分別設計其外觀及動態。
- Animation 在 Theme 下先以描述記錄，需要時才提取參數；Scene 控制開始、停止與取消。

已產出與限制：

- 九類場景首稿、22 張 128×128 靜態 PNG、兩張比較圖及方法說明。
- 第二批草图尚未記錄 USER 看圖結論；思考的三點舊圖尚未改為沙漏，沒有動畫預覽。
- 靜態首稿時尚未實作主題切換、打字機或沙漏；本輪共用 review 工具現已實作原型並在 Pi／OLED 執行，詳見下方工具紀錄。尚非 Core production 支援。
- 主畫面思考時保留內容、沙漏造型與節奏、唯一 Style 選擇及其他未決設計仍待討論。
- 沒有將這些決定視為 Core 採用、M7 驗收或實機證據；前次紀錄與草圖已以 4353fbc 提交並 push。

本輪接續：先看九類場景與共用項目的整體選擇，沙漏外觀／節奏延後，不阻擋第一輪設計討論。
不用重新討論已確定的編號、階層或 ANI 語意。

## 全部走完一輪：場景與共用項目總覽

以下起始提案尚未作為 USER 決定；已確定項目另行標明。不要求本輪定字級、動畫週期或資源預算。

| 場景 | 第一輪起始方向 | 決策狀態 |
|---|---|---|
| SCN-01 開機 | 簡單開機動畫為方向；本輪先做靜態標誌，全黑為 fallback | USER 已決定；標誌內容待定 |
| SCN-02 待機 | StatusBar「待命」、Main 空白；閒置一段時間後熄屏，時間與恢復機制待確認／映射 | USER 已決定方向 |
| SCN-03 喚醒 | 光芒 icon 緩慢明暗呼吸＋「準備中」，文字穩定，Main 空白 | USER 已決定方向；動態細節延後 |
| SCN-04 感知 | StatusBar「感知中」＋多來源 icon 群，固定順序緊排；Main 更新草案沿用當前有效文字 | USER 已接受文案與圖示排列方向；Main 待確認 |
| SCN-05 思考 | StatusBar「思考中」＋ANI-001；Main 保留當前有效感知文字，無文字則空白 | USER 已確認第一輪方向；沙漏細節延後 |
| SCN-06 執行 | 工具：扳手＋「執行中」；Speak：喇叭＋「回應中」；Main 顯示安全動作名或 actual Speak | USER 已確認狀態列方向；打字機能力預留、細節延後 |
| SCN-07 打斷 | 系統接受打斷後 Main 顯示「已中止」、停止原文字效果；回到 IDLE 清空 | USER 已確認；StatusBar 跟隨實際狀態 |
| SCN-08 錯誤 | 警告三角形＋「錯誤」；Main 以獨立錯誤色顯示安全類別／摘要，靜態不閃爍，恢復待機後清空 | USER 已確認第一輪方向；未完成實體驗證 |
| SCN-09 關機 | 先顯示與開機相同的簡單標誌，再回全黑；未來可加短動畫，不拖延關機 | USER 已確認第一輪方向 |

共用項目仍需第一輪討論：

- Style：兩份稿目前只是比較。起始提案為一個工具型 Style，圖示／動畫依 Scene 使用；是否收斂尚未決定，不先改寫既有 Style 編號或草圖。
- 輔助資訊：volume、connection、capability 均需有呈現安排。提案使用 StatusBar 輔助位置，優先保障狀態可讀；一次顯示多少、精確圖示與合法來源待核對，不加入 OSD 或輪播新能力。
- 長文字：先沿用固定字級、pixel-width wrapping 與 ellipsis；是否需要捲動、分頁或標點規則留為聚焦問題，不先加入新產品能力。
- 全部動態：普通狀態／內容先直接切換；已選沙漏及預留打字機列入後續原型；其他動畫先說明價值再保留。
- 隱私與錯誤降級：保留既有要求，跨 Style／Theme 一致，不用每個主題重設。
- 渲染／整合：程序繪製為簡單畫面起點，不在這輪定 production 技術；後續補 Core mapping、依賴及最小實驗選擇，才能完成 D1。

先收齊本表的方向性回饋，再返回需要比較的視覺細節；不將總覽或延後細節當成 D1 已完成。

### 共用主題 review 工具

USER 要求建立可持續沿用的典範，之後主題設計開發使用同一套腳本驗證，並包含動畫／動態。
本輪已建立 [工具與操作說明](../../poc_display/review/README.md)、
[播放入口](../../poc_display/tools/m7_review.py)、[共用場景](../../poc_display/review/scenes.json)
與 [THM-baseline 設定](../../poc_display/review/themes/THM-baseline.json)。

- 共用 14 個合成 review 畫面涵蓋九類場景；Theme 可替换視覺設定與圖示 PNG，場景 ID／測試入口共用。
- 支援準備光芒呼吸、思考沙漏翻轉及可開關的文字逐步揭露；ANI-005 在工具中標識逐步揭露能力，尚未選為預設产品效果。
- Theme 保留動畫描述；現有 preview 設定只為可執行效果服務，不強迫所有設計先參數化。新增效果需擴充 renderer／tests。
- 瀏覽器 GIF／PNG 預覽、mock RGB565 播放與 Pi HAL 路徑共用 renderer；可自動輪播或 terminal 手動切換、暫停、重播。
- Logo 使用暫定 Snowboard 文字，輸入色／回覆色及動態時間是工具預覽值，不記作 USER 的正式主題選色／節奏決定。
- 工作站適用檢查目前 12 passed，完整 mock 輪播及 interactive 操作已執行；Pi／OLED 已連線完成首輪同 bytes 播放與控制操作，兩項 review 修正的最後一輪驗證另記於 evidence summary。
- 這是 D1 討論用的範圍明確 review 工具，不代表 D2、完整 D3 或 D4 已完成，也不是 Core 整合證明。
- USER 要求完成後 commit/push 並結束當日工作；提交內容仍須按 AGENTS.md 展示後批准，不將此工具里程碑視為 M7D1 全部完成。

本輪 USER 觀察到「回應中＋已中止」不直覺，且回覆文字色沒有明顯改變。工具修正版先使用
停止 icon＋「中止中」、Main「已中止」，並以輸入白色／回覆淡綠色做可比較預覽。
這些是針對回饋的 prototype 修正，尚未取得正式 Theme 色值選擇或 Core adoption；
interrupt StatusBar 投影須返回 focused finding，不新增 State Manager state。

### 第一輪 StatusBar icon 方向

USER 已確認以下 icon 意象；準備中與思考中使用動態，其餘第一輪為靜態，不先細設造型。
圖示位於狀態文字旁，依所選 Theme 呈現，與 Main 圖文設定分開。

| 狀態／場景 | Icon 意象 | 第一輪動態 |
|---|---|---|
| IDLE／SCN-02 | 空心圓 | 靜態 |
| WAKE／SCN-03 | 簡單光芒，ANI-003 | 緩慢明暗呼吸，文字穩定 |
| PERCEPTION／SCN-04 | 接收訊號 | 靜態 |
| THINK／SCN-05 | 沙漏，ANI-001 | 翻轉循環、不落沙 |
| ACTION／SCN-06 Tool | 扳手 | 第一輪靜態 |
| ACTION／SCN-06 Speak | 喇叭 | 第一輪靜態 |
| ERROR／SCN-08 | 警告三角形 | 靜態 |

SCN-07 仍使用當前 authoritative state 的圖示；SCN-01／SCN-09 是 Fullscreen，不顯示 StatusBar。
這次確認使圖示＋文字成為第一輪產品探索方向；STYLE-01 純文字稿保留為比較基準，
是否整併 Style 編號仍待整理，不能把兩者視為已採用的使用者切換功能。

## 已確定的邊界

- Raspberry Pi 5、實體 SSD1351 128×128 RGB OLED；1:1 canvas、20 px StatusBar、108 px Main、互斥 Fullscreen。
- 黑色背景、既有高對比前景／錯誤角色、安全區、離線 Noto Sans TC；繁體中文優先。
- 狀態維持 IDLE、WAKE、PERCEPTION、THINK、ACTION、ERROR，不增加 State Manager 狀態。
- Main 是當前有效內容，不是歷史紀錄；保留隱私、清空、stale filtering 與降級要求。
- runtime 離線；推薦須映射既有 Core flow、ownership、lifecycle 與 failure contract。
- 不自行加入 Progress UI、OSD、touch、LED、fullscreen preemption 或 runtime 音量按鍵。

## 場景清單與下一步

以下是 USER 確認的九類探索場景，不是九個 State Manager 狀態，也不限定為九張獨立畫面。
同一場景可有必要的內容版本；共用版式與靜態／動態處理待後續決定。

| ID | 場景 | 必須涵蓋的內容／行為 |
|---|---|---|
| SCN-01 | 開機 | 啟動呈現；可靠的 fullscreen.blank fallback；不得延後 readiness |
| SCN-02 | 待機 IDLE | 正常待機；長時間待機的 OLED 保護與恢復 |
| SCN-03 | 喚醒 WAKE | 已被喚醒的辨識 |
| SCN-04 | 感知 PERCEPTION | 感知狀態；當前有效且 validated 的 Perception 文字 |
| SCN-05 | 思考 THINK | 思考狀態的辨識；不暗示虛構進度 |
| SCN-06 | 執行 ACTION | 安全 Tool 名稱、actual Speak 內容；必要時使用不同內容版式 |
| SCN-07 | 打斷回饋 | 已接受的 interrupt feedback；不新增系統狀態 |
| SCN-08 | 錯誤 ERROR | sanitized error 類別／摘要 |
| SCN-09 | 關機 | graceful shutdown 呈現；收斂至 fullscreen.blank；不得延後 cleanup／shutdown |

跨場景事項：volume、connection、capability 的位置；show_session_content=false；empty／stale
content、長文字、missing glyph／asset 與 renderer／HAL failure。這些不自動增加獨立場景。

下一步先逐一填寫「場景卡」：

1. 使用者需要理解什麼。
2. 顯示哪些合法內容；哪些內容不顯示。
3. StatusBar、Main 或 Fullscreen 的位置與版式需求。
4. 進入、更新、離開與取消條件，以指定 Core baseline 的既有語意為依據。
5. 空內容、隱私設定與失敗時如何呈現。
6. 必要的內容版本、靜態／短促轉場候選，以及實機要解決的疑問。

先做 SCN-02 待機與 SCN-06 執行的場景卡及共用版式草案，作為 StatusBar／Main 的設計基礎；
再展開其他場景與 Fullscreen。此順序是 Display team 的起始工作提案，尚非 USER 選定的版式。

## 第一批場景卡：SCN-02／SCN-06／SCN-08

本批為草案，尚未由 USER 選定版式或取得實體 OLED 證據。
已核對 Core `80d79d6c74ff93a40a018a03529c275287f2693e` 的 `docs/display_spec.md`
§§2–5；以下保留其文案、固定字級、安全區、內容有效期及 fallback。
其他 architecture／implementation baseline 來源仍待後續映射，不能宣稱已完成全部核對。

### 共用版式

USER 同意先以語意色彩代號記錄，方便後續主題色探索。場景與版式引用代號；
下表是 Core 既有基準的映射，不代表替代配色已獲採用。黑色背景仍為既有要求。

| 代號 | 用途 | Core baseline token／值 |
|---|---|---|
| COLOR-BG | 畫布基礎背景／Blank | color.background／#000000 |
| COLOR-FG | 一般前景角色的基準值 | color.foreground／#FFFFFF |
| COLOR-STATUS-BG | StatusBar 專用背景 | #000000；獨立設定，不隨 Main 改動 |
| COLOR-STATUS-FG | StatusBar 專用文字／圖示 | #FFFFFF；獨立設定，不隨 Main 改動 |
| COLOR-MAIN-BG | Main 專用背景 | #000000；獨立設定，不隨 StatusBar 改動 |
| COLOR-MAIN-FG | Main 專用一般文字 | #FFFFFF；獨立設定，不隨 StatusBar 改動 |
| COLOR-INPUT-FG | Main 的有效感知文字；包含思考時保留的輸入 | 色值待選；須與回覆色可辨識且保持黑底可讀 |
| COLOR-REPLY-FG | Main 的實際回覆／Speak 文字 | 色值待選；須與輸入色可辨識且保持黑底可讀 |
| COLOR-DIVIDER | StatusBar 與 Main 分隔線 | color.divider／#30343A |
| COLOR-ERROR-FG | Main 的安全錯誤類別／摘要 | color.error／#FFB000 |

- SCN-02、SCN-06：StatusBar 使用 COLOR-STATUS-BG／COLOR-STATUS-FG；Main 使用 COLOR-MAIN-BG／COLOR-MAIN-FG。
- SCN-08：StatusBar 使用 COLOR-STATUS-BG／COLOR-STATUS-FG；Main 背景 COLOR-MAIN-BG，error 文字 COLOR-ERROR-FG。
- 所有 Normal 場景的 divider 使用 COLOR-DIVIDER。
- USER 明確要求 StatusBar 與 Main 的主題設定獨立。TEXT-STATUS-*／FONT-STATUS 只影響狀態列，TEXT-MAIN-*／FONT-MAIN 只影響主區。
- USER 決定輸入與回覆使用不同 Main 文字色；不加內容標籤，不使用左右對齊區分。兩者沿用同一靠左正文版式，Theme 分別提供 COLOR-INPUT-FG／COLOR-REPLY-FG；實際色值待選。
- SCN-04 及 SCN-05 保留的感知文字用 COLOR-INPUT-FG；SCN-06 Speak 用 COLOR-REPLY-FG。Tool 暫沿用 COLOR-MAIN-FG，Error 使用 COLOR-ERROR-FG；Tool 是否另設文字色尚未選定。
- 保留單一 Main 內容、有效更新取代的既有模型；本次不增加上下分區、歷史或保留兩份內容。舊 PNG 尚未顯示輸入／回覆的分色。
- Renderer 需能以合法內容角色選擇顏色，不可由文字本身猜測。現有 main.text 路徑是否保留來源／內容角色需核對；必要時返回最小 focused finding，不能宣稱現有 Core 已支援。
- 相同初始色值不代表綁定變數；Core 基準的兩區背景皆黑，替代狀態列底色可記為主題探索差異，不改 Blank 全黑語意。

### Style → Theme → Scene

USER 指示：可替換的主題設計項目以變數記錄，方便後續設計更替。
USER 確認正式設計階層為 **Style → Theme → Scene**。
以下為設計記錄／原型的變數約定，尚非 Core configuration API 或 runtime reload 功能。

```text
STYLE-01 文字優先／純文字狀態列
└─ THM-baseline
   ├─ SCN-02 待機
   ├─ SCN-06 執行（Tool／Speak）
   └─ SCN-08 錯誤
STYLE-02 文字優先／圖示＋文字狀態列
└─ THM-baseline（共用定義）
   ├─ SCN-02 待機
   ├─ SCN-06 執行（Tool／Speak）
   └─ SCN-08 錯誤
```

兩個 Style 是探索候選，尚未選定最終推薦；所有九類場景的行為定義共用，
以上是第一批示例；目前九類場景皆有第一版場景卡與靜態草圖。
Theme 定義可共用引用，不為每個 Style 複製相同值。
完整設計定位使用 `STYLE-ID / THEME-ID / SCN-ID`；Tool／Speak 是 SCN-06 的內容版本。

| 層級 | 責任 | 本輪初始設計 |
|---|---|---|
| Style | 共用視覺結構、區域內排列、圖文組合；定義可用的主題變數角色 | STYLE-01 純文字；STYLE-02 小圖示＋文字；兩者 Main 均文字優先 |
| Theme | 提供 Style 所引用的色彩、字體、字級、行距、間距、圖示資源 | THM-baseline，名稱 baseline，使用 Core 基準；圖示相關值僅供 STYLE-02 使用 |
| Scene | 定義合法內容、觸發、更新、清空及離開；在所選 Style／Theme 下呈現 | SCN-01–SCN-09 共用產品行為，不因主題不同而改變 |

| 分類 | 變數／ID | 意義／初始值 |
|---|---|---|
| 風格 | STYLE-ID | STYLE-01 或 STYLE-02 |
| 主題 | THEME-ID／THEME-NAME | THM-baseline／baseline |
| 場景 | SCN-ID | SCN-01–SCN-09 |
| 色彩 | COLOR-* | 沿用上表語意角色 |
| 字體 | FONT-STATUS／FONT-MAIN／FONT-ERROR | Noto Sans TC Medium／Regular／Medium 2.004 |
| 字級 | TEXT-STATUS-SIZE／TEXT-MAIN-SIZE／TEXT-ERROR-SIZE | 12／14／14 px |
| 行高 | TEXT-STATUS-LINE-HEIGHT／TEXT-MAIN-LINE-HEIGHT／TEXT-ERROR-LINE-HEIGHT | 16／20／20 px |
| 對齊 | TEXT-STATUS-ALIGN／TEXT-MAIN-ALIGN／TEXT-ERROR-ALIGN | 靠左；Status 垂直置中 |
| 圖示 | ICON-STATUS-SIZE／ICON-STATUS-GAP | STYLE-02 草案為 12 px／4 px |
| 圖示資源 | ICON-IDLE／ICON-TOOL／ICON-SPEAK／ICON-ERROR | 空心圓／扳手／喇叭／警告三角形；USER 已確認意象，造型細節待定 |
| 思考圖示 | ICON-THINK | USER 選定沙漏；外觀由 Theme 提供 |
| 思考動畫 | ANI-001 | 沙漏翻轉；設計描述見下方 Theme 動畫項目，先不強制定義時間參數 |
| 分隔線 | DIVIDER-THICKNESS | 1 px；顏色引用 COLOR-DIVIDER |
| 文字效果預設 | TEXT-REVEAL-MODE | instant；預留 typewriter |
| 逐字速度 | TEXT-REVEAL-INTERVAL-MS | 待原型／量測決定；不等於 SPI flush interval |
| 揭露時間上限 | TEXT-REVEAL-MAX-DURATION-MS | 待原型／量測決定；超出時直接呈現最終可見內容 |
| 區域約束 | PROFILE-ID／STATUS-RECT／MAIN-RECT／CONTENT-RECTS | 引用既有 DSP-PROFILE-OLED-128 與安全區；不當成任意主題參數 |

- 場景記錄「顯示什麼、何時顯示」；Style 記錄「圖文如何組合」；Theme 變數記錄「字體、大小、顏色、間距、圖示資源」。
- 各草案使用一組明確主題值；不同字級／行高需要重新計算文字容量及換行，不沿用五行等舊結果。
- 既有 profile、黑底、安全區、sanitization、stale filtering、ownership 及 fallback 不隨主題任意切換。
- 可用變數記錄替代設計；改動 Core 固定字級等既有要求時明確標成探索候選，向 Core 返回差異與證據。
- 舊 L0／L1 僅為 StatusBar 局部草案代號，分別收進 STYLE-01／STYLE-02；後續統一使用 STYLE-ID，不維持另一套選擇 ID。
- STYLE-03 僅在有第三個結構不同且有比較價值的整體風格時新增，不預先擴充。
- 原型可用 STYLE-ID 與 THEME-ID 選擇組合以比較；目前尚未實作切換。
- 最終推薦可以只保留一種版式。產品是否提供多版式／多主題選擇及 runtime 切換，仍由 Core 決定；本記錄不新增設定頁、按鍵或控制能力。

### THM-baseline 動畫項目

USER 確認主題 ID 為 **THM-baseline**；動畫內容在 Theme 底下設計，以文字描述起步，
不要求每項效果先參數化。**ANI ID 唯一識別動畫項目的語意，跨 Theme 保持不變**。
ANI-001 固定代表「思考沙漏」；不同 Theme 各自描述其造型、動態與節奏，不因換主題或
重新設計同一項目的呈現而分配新 ID。不同語意的動畫項目才使用新 ID。
具體主題實作以 `Theme ID / ANI ID` 定位；描述／版本記錄追蹤同一主題內的修改。
已交付內容後續 append fix，不重寫交付版。

| 欄位 | ANI-001 |
|---|---|
| 主題 | THM-baseline |
| 名稱 | 思考沙漏 |
| 使用位置 | STYLE-02／SCN-05 StatusBar，位於「思考中」左側 |
| 設計描述 | 小沙漏停留後翻轉，再停留，持續循環；不做落沙 |
| 視覺要求 | 與狀態文字協調，不搶 Main 注意力；不表示百分比、剩餘時間或真實推理進度 |
| 行為引用 | SCN-05 決定開始、停止與取消；不由主題改變權威狀態或 lifecycle |
| 未決內容 | 沙漏造型、翻轉呈現與節奏，預覽後再調整；先前 1.5 秒週期／0.3 秒翻轉只是未採用的討論提案 |
| 狀態 | 方向已選定，尚未實作／預覽／實機驗證 |

Scene 使用穩定的 ANI-001 選擇「思考沙漏」，所選 Theme 提供其具體設計；不用再增加語意動畫 ID 層。
其他尚未設計的動畫不預先大量編號；打字機效果保留能力，具體主題效果定義時再分配 ANI ID。

| 欄位 | ANI-002 |
|---|---|
| 名稱 | 開機標誌 |
| 主題／場景 | THM-baseline／SCN-01 |
| 設計描述 | 未來為簡單啟動動畫；本輪先做靜態標誌，Fullscreen 中央呈現 |
| 未決內容 | 標誌使用品牌圖形或產品名稱；造型、尺寸及動畫細節延後 |
| 限制 | 不延後 readiness；缺件、timeout、cancel、failure 收斂至 Blank |
| 狀態 | USER 選定方向；尚未繪製或實作 |

| 欄位 | ANI-003 |
|---|---|
| 名稱 | 準備光芒 |
| 主題／場景 | THM-baseline／SCN-03 StatusBar |
| 設計描述 | 光芒 icon 緩慢明暗呼吸，表示正在處理；「準備中」文字保持穩定，Main 空白 |
| 行為引用 | 跟隨 authoritative WAKE 開始，離開 WAKE 停止；不表示完成進度或剩餘時間 |
| 未決內容 | 造型、亮度範圍、週期與影格，留待後續預覽與實機比較 |
| 狀態 | USER 已選定呼吸方向；尚未實作或驗證 |

ANI-003 跨 Theme 仍代表「準備光芒」，各 Theme 描述自己的外觀與動態，沿用既定 ANI 語意規則。

| 欄位 | ANI-004 |
|---|---|
| 名稱 | 關機標誌 |
| 主題／場景 | THM-baseline／SCN-09 |
| 設計描述 | 先呈現與開機相同的簡單靜態標誌，再回全黑；未來可加短動畫 |
| 行為引用 | SCN-09 lifecycle；bounded best effort，不拖延關機，沒有可用時間則直接 Blank |
| 未決內容 | 共用開機標誌的造型、後續動畫方向與具體時序 |
| 狀態 | USER 已確認方向；尚未繪製或實作 |

### 基準版式數值

- Normal layout：StatusBar 20 px，Main 108 px；沿用既有 divider 與安全區。
- Status：12 px Medium、16 px line height；Main：14 px Regular、20 px line height、最多五行。
- Error：14 px Medium、20 px line height、最多五行；error 色 `#FFB000`，status 仍白色。
- 文字靠左；使用實際 glyph pixel width 換行，overflow 以 `…` 截斷，缺字用 `□`。
- 以下文字線框只表示內容位置，不代表精確像素、換行結果或字型實測。
- 候選 A 直接更新靜態畫面；候選 B 僅比較少量狀態轉場，內容更新不等待動畫。
  B 尚無具體效果與時長，本批先建立 A，不為了比較而在每個場景加入動畫。

### SCN-02 — 待機

USER 已確認第一輪方向：StatusBar 顯示「待命」、Main 空白，閒置一段時間後熄屏。
具體時間、恢復觸發與 ownership 機制待後續設計，不新增 State Manager state。

| 場景卡欄位 | 草案 |
|---|---|
| 目的 | 使用者知道系統目前待命；長期閒置時降低固定亮像素暴露 |
| 內容與位置 | StatusBar 顯示既有文案「待命」；Main 清空，不放邀請文字、時鐘或上一輪內容 |
| 進入／更新 | 啟動時投影初始 IDLE；其後跟隨有效 StateChanged。真正回到 IDLE 時清除 Main |
| 離開 | 下一個有效狀態／內容依既有 owner 規則更新；保護呈現不能阻擋更新 |
| 隱私／失敗 | content setting 不影響 State；renderer／HAL failure 沿用 disabled rendering，不改 session |
| 保護方向 | 正常待命後延後熄屏已由 USER 選定；降低亮度不是本輪已選方向。具體時間與恢復路徑待映射，不建立新 state |
| 動態 | 不做持續裝飾動畫；待機不重複刷新相同畫面作為視覺效果 |
| 待解問題 | 「待命」是否足夠清楚？全黑是否被誤認為關機？低亮度是否仍可讀？保護機制是否符合 ownership？ |

```text
┌────────────────┐
│ 待命           │ ← StatusBar
├────────────────┤
│                │
│    黑色空白    │ ← Main
│                │
└────────────────┘
```

### SCN-06 — 執行

USER 討論結論：Main 的感知輸入與實際 Speak 回覆先以不同文字色辨識，
不加「輸入／回覆」標籤，不改為左／右對齊。兩者仍為单一目前內容，替換行為不變。
實際配色留待 Theme 設計。
USER 已確認 ACTION 的兩種狀態列呈現：Tool 使用扳手＋「執行中」，Speak 使用喇叭＋「回應中」；
第一輪 icon 靜態，造型細節延後。不新增 State Manager state，也不使用「播報中」。
工具文案「執行中」與 action 類型投影是相對 Core baseline ACTION 一律「回應中」的探索差異，
需核對 hint/model/StatusBar owner 的資料流並返回 Core 決定；不得從 Main 文字猜測類型。
尚無可靠 action 類型時沿用 baseline「回應中」，通用圖示待後續映射，不默認顯示扳手或喇叭。
原有 PNG 的執行箭頭仍是舊稿，尚未依此次決定更新。

| 場景卡欄位 | 草案 |
|---|---|
| 目的 | 使用者知道正在回應，並看見當前動作或實際即將播報的文字 |
| 內容與位置 | Tool：StatusBar 扳手＋「執行中」；Speak：喇叭＋「回應中」。Main 使用同一文字版式，Tool 與 Speak 不疊加 |
| Tool 版本 | 顯示 registry 提供的安全動作名稱；不顯示 tool arguments、內部識別碼或猜測的執行結果 |
| Speak 版本 | 顯示已驗證且準備交给 speak action 的實際文字；使用 COLOR-REPLY-FG，不顯示 raw model output，不推定音訊已開始或完成 |
| 進入／更新 | Tool 在已驗證、正規化且準備執行時更新；Speak 在 dispatch 前更新。狀態與 Main 分別跟隨各自權威資料 |
| 離開／清空 | 下一輪 PERCEPTION 或真正回到 IDLE 時清除；已接受 interrupt 的取代行為由 SCN-07 設計 |
| 空／stale／隱私 | 有效新內容為空則清 Main；stale 資料丟棄且不清現有畫面；content setting 關閉時不顯示 Tool／Speak，State 照常 |
| 動態 | 起始版不捲動、不加進度；長文 deterministic 截斷，是否需要其他閱讀方案依證據決定 |
| 待解問題 | 五行是否足以理解短／長 Speak？安全動作名稱是否可辨識？快速內容替換是否造成閱讀困難？ |

下列內容是合成 fixture，不代表已採用的 tool registry 名稱或實際對話。

```text
Tool                        Speak
┌────────────────┐          ┌────────────────┐
│ 回應中         │          │ 回應中         │
├────────────────┤          ├────────────────┤
│ 查詢天氣       │          │ 今天下午可能   │
│                │          │ 下雨，出門請   │
│                │          │ 記得帶傘。     │
└────────────────┘          └────────────────┘
```

### SCN-08 — 錯誤

USER 已確認第一輪方向：StatusBar 警告三角形＋「錯誤」，Main 以 COLOR-ERROR-FG
呈現安全類別／摘要；靜態不閃爍，恢復待機後清空。錯誤色仍由 Theme 管理。

| 場景卡欄位 | 草案 |
|---|---|
| 目的 | 使用者辨認產品進入 ERROR，並理解可安全顯示的錯誤類別／摘要 |
| 內容與位置 | StatusBar 白色「錯誤」；Main 以既有 amber error style 顯示 category／summary，不重複「錯誤」標題 |
| 進入／更新 | 依 StateChanged.new == ERROR 與 error owner 的 sanitized category／summary；缺少摘要時不自行編造原因 |
| 離開 | recovery 完成且真正回到 IDLE 時清 Main；不由 Display 自行決定恢復 |
| 隱私 | content setting 不抑制 Error；禁止 exception detail、stack trace、secret 或內部路径 |
| 空內容 | 不為空／sanitized 後空的摘要補寫提示；缺欄位的完整組合行為待 renderer contract 核對 |
| Display 故障 | renderer／HAL failure 是停止後續實體 rendering 的路徑，不為此將 session 改為 ERROR，也不保證故障後仍可畫此畫面 |
| 動態 | 靜態呈現，不閃爍、不佔 Fullscreen；文字與 error 色共同表意 |
| 待解問題 | amber 小字是否可讀？類別和摘要是否清楚？長摘要截斷是否丟失關鍵資訊？ |

下列 category／summary 為合成 fixture，實際文案須由 error owner 提供。

```text
┌────────────────┐
│ 錯誤           │ ← 白色 StatusBar
├────────────────┤
│ 連線           │
│ 暫時無法連線   │ ← amber Main
│                │
└────────────────┘
```

本批完成的是三張場景卡及靜態文字線框；D1 仍待輔助資訊配置、B 轉場設計、
IDLE 保護 ownership、實驗淘汰依據及完整 Core 映射，不標為完成。

### 第一批 Style 比較

以下為起始提案，USER 尚未選定最終 Style。這是靜態結構比較，與前述 A/B 轉場比較分開。
本輪先使用同一 THM-baseline 與合成內容，避免同時更換主題造成比較不清楚。

| 版式 | SCN-02 | SCN-06 | SCN-08 |
|---|---|---|---|
| STYLE-01 純文字基準 | 待命 | 回應中 | 錯誤 |
| STYLE-02 小圖示＋既有文字 | 簡單空心圓＋待命 | 簡單執行箭頭＋回應中 | 警告三角形＋錯誤 |

- STYLE-02 的圖示置於 StatusBar 安全區左側、文字在其右側；尺寸引用 ICON-STATUS-SIZE，間距引用 ICON-STATUS-GAP。
- 不變更 StatusBar 高度、既有字級或安全區；圖示與文字使用 COLOR-STATUS-FG。
- 圖示為程序繪製幾何圖形的候選，不以 emoji 或 OS 字型提供，亦不宣稱已採用正式資產。
- Main 版式保持一致，不加大圖示；SCN-06 Tool／Speak 仍共用 Main 文字版式。
- 保留 STYLE-02 的前提是實體 OLED 上更易辨識且不影響文字／輔助資訊空間；無明顯收益則保留 STYLE-01。
- 下一步產出這三個場景的 STYLE-01／STYLE-02 等比例靜態草圖（SCN-06 分 Tool／Speak），再展開其餘六個場景。

第一批八張 128×128 靜態草圖已產出：[比較圖](m7_sketches/comparison.png)、[方法與限制](m7_sketches/README.md)。
目前觀察到 simple pixel-width wrapping 可使標點落在行首；標點避頭尾是否需要探索列為未決問題。
USER 已看過第一批草圖、沒有提出修改，並將 THM-baseline 命名為 baseline；尚未選定唯一 Style。
這是工作站設計回饋，不是實體 OLED 評估、Core 採用或 M7 驗收。
已預留打字機效果設計；其餘六類場景已補入下方第二批，尚待 USER 查看。

### 文字更新與 streaming

- 已核對的 Core baseline `display_spec.md` §4.1 指定 Speak 顯示已驗證且準備交給 speak action 的文字，在 dispatch 前取代 Main；不要求 Display 接收逐 token 模型串流。
- 上游模型是否 streaming 與 Display 是否逐字更新是兩個決策；Display 不直接接收 raw model output。
- 本輪靜態草圖起點為收到合法內容後直接更新，不加入打字機效果，也不宣稱音訊進度同步。
- 若未來 Core 採用經驗證的分段 Speak 更新，Display 須再評估更新頻率、freshness、內容切換與資源成本；這是內容／更新契約議題，不是單靠 Theme 切換就能提供的能力。
- 已取得完整合法文字後逐字揭露只是視覺動畫，與上游 streaming 不同；只有存在產品價值且不延遲有效內容呈現時才值得保留為實驗。

#### USER 指示：預留打字機效果能力

USER 已要求預留此能力。這是 D1 的設計要求，尚未實作或宣稱已通過實機驗證。
原型應可替換文字呈現策略，至少支援 `instant` 與 `typewriter`，預設 `instant`。

- Style 定義文字區域與組合；Theme 提供 TEXT-REVEAL-* 預設與速度參數；Scene 決定是否使用文字效果。
- SCN-06 Speak 預留選擇效果模式；SCN-06 Tool、SCN-08 Error、StatusBar 初始仍直接顯示。
- 文字效果只處理已驗證、sanitized 且 freshness 通過的合法內容，不接 raw token stream，也不改 action／audio 的啟動或完成時機。
- RenderModel 的目標內容仍是完整合法內容；原型效果僅管理可見範圍及節奏，具體 Core 接入位置在後續 ownership 映射中核對，不新增 State Manager state。
- 先對完整文字完成 glyph fallback、pixel-width wrapping 及 truncation，再逐步揭露可見文字，避免每新增一字都重排已顯示內容。
- 揭露單位以使用者可見字元為目標，不以 UTF-8 byte 切割，亦避免拆開組合字元；具體離線處理策略待 D3 決定。
- 新有效內容到達時取消舊效果並呈現新目標；stale 資料不得取消、取代或清除當前效果／畫面。
- 有效空內容立即清 Main；隱私設定關閉時不啟動受抑制內容的效果；已接受 interrupt、清空、ERROR 或 shutdown 依既有語意取消舊效果，不得再補寫舊文字。
- 僅針對可顯示範圍揭露，沒有 overflow 區域的隱藏動畫；到达時間上限收斂至最終可見文字。
- 字元揭露頻率與實體 frame flush 分離，允許一個 frame 揭露多字；每次呈現仍沿用完整 frame／atomic presentation，速度不宣稱由 SPI 能力支援。
- 若 Normal 被 Fullscreen 遮蔽，不做 Normal 實體 flush；release 後呈現最新有效 Normal 畫面，不重播舊效果。確切 scheduler／owner 行為待 Core contract 映射。
- 效果失敗但 renderer／HAL 可用時回到直接顯示；renderer／HAL failure 則沿用停止實體 rendering 的既有路徑。
- D2 加入最新內容取代、stale、空內容、interrupt、shutdown、Fullscreen、超時及 failure 檢查；D4 比較閱讀體驗與刷新成本。

不增加使用者設定頁或 runtime 按鍵；此預留方便原型選擇與後續整合推薦，產品採用與配置方式仍由 Core 決定。

## 第二批場景卡：其餘六類

沿用 THM-baseline、STYLE-01／STYLE-02 與前述 Core baseline `display_spec.md`。
新增 14 張 128×128 草圖：[第二批比較圖](m7_sketches/comparison_remaining.png)。
SCN-04 有空內容／有效文字兩版，其他場景各一版；文字皆為合成 fixture。
開機、關機的 Blank 在兩個 Style 下完全相同，不為風格增加產品內容。

### SCN-01 — 開機

- USER 決定：開機應有簡單動畫，本輪先做簡單靜態標誌，動畫細節延後。
- 目的／版式：Fullscreen 中央標誌；沒有狀態列或 divider。標誌內容、造型與尺寸待討論，尚未產出。
- 未來動畫項目登記 ANI-002「開機標誌」；THM-baseline 目前以靜態標誌作首稿，後續同一項目可設計簡單動畫。不因不同 Theme 更換 ANI ID。
- 進入／離開：Display lifecycle 啟動時由 `app.lifecycle.boot` 持有；建立第一個有效 Normal model 後 release。
- 故障：NullDisplay／failure 仍處理 ownership release；動畫未採用時不依賴素材。
- 全黑仍是可靠 fallback，不能以標誌取代 Blank 語意；asset absence、timeout、cancel、failure 都需收斂 Blank，再依 lifecycle 規則進 Normal，不延後 readiness。
- 既有第二批開機 PNG 是先前 Blank 基準，不代表新選定的靜態標誌；尚未改圖。
- 待解：短開機動畫是否有辨識價值；具體 owner／cancel 與 lifecycle 時序待 architecture mapping。

### SCN-03 — 喚醒

- USER 更新並確認：光芒 icon 緩慢明暗呼吸＋StatusBar「準備中」，文字保持穩定，Main 空白。
- 此決定取代先前「第一輪不加動畫／靜態光芒」方向；ICON-WAKE 的造型由 Theme 設計，動態引用 ANI-003，細節延後。
- 進入 WAKE 開始呼吸，離開 WAKE／shutdown／rendering disabled 時停止；Fullscreen active 時不做 Normal 實體 flush，具體 scheduler／owner 映射後續核對。
- 基準契約：WAKE 本身沒有清 Main 規則；從 IDLE 喚醒時 Main 已空，與所選畫面相符。若非 IDLE 路徑仍有合法 backing content，不默認新增 clear；後續映射須明列是否需要 focused finding，不能以此畫面決定改写 Core 行為。
- 進入／離開：跟隨有效 StateChanged.new == WAKE 與下一個權威狀態；不增加「已喚醒」新 state。
- 故障／隱私：State 不受 session-content setting 影響；failure 沿用既有路徑。
- 待解：短暫 WAKE 是否能辨識；圖示是否比單純文字更清楚。

### SCN-04 — 感知

- USER 接受 StatusBar 文案「感知中」，取代本輪先前的「接收中」提案。Core baseline 固定文案仍為「接收中」；此差異須返回 Core 採用，不默認已改產品權威。
- 已核對指定 Core baseline `docs/arch.md` §2.6：一個 turn 可平行啟動多個 perception module，SM 等全部完成／timeout 再進 THINK。因此不能把 SCN-04 設計為僅有單一來源，也不能以最新結果推定所有活躍來源。
- USER 已接受多來源 icon 第一輪排列：StatusBar 左側為來源圖示群，右側接「感知中」；麥克風→訊息框→相機固定順序，只顯示有可靠資訊的本回合啟動來源，靠左緊排。
- icon 群的尺寸／間距由 Theme 描述或變數提供；起始尺寸每個 12 px、間距 4 px、三個 icon 共 44 px，待草圖與實體可讀性驗證，不固定為產品要求。
- 若要逐一表達 working／done／timeout，還需要額外權威狀態及視覺設計，本轮未採用。沒有可靠 active-module 資料時用通用輸入圖示，不根據結果到達猜測模組啟動／結束。
- Core 顯示契約目前未確認可供 StatusBar 使用的 active-module 集合；來源來源映射／必要最小契約 delta 列為待解 focused finding。現有三線 icon PNG 是舊草案，尚未更新。
- 空內容版：新 turn 進入 PERCEPTION 時清除上一輪 Main；未有合法結果前 Main 黑色空白，不加 placeholder。
- 有效文字版：當前 session／turn 驗證通過的 PerceptionResult.text 取代 Main；不限定為語音來源。
- 更新／離開：依 observer 收到的有效結果順序取代，不合併；進 THINK 不為了轉場自行清 Main。
- 隱私／例外：設定關閉時不顯示感知文字；有效空內容清 Main；stale 資料直接丟棄，不影響當前畫面。
- 效果：本批直接顯示，不做打字機；未採用 streaming partial transcript。
- 待解：空內容畫面是否足以理解正在接收；文字更新是否易讀；圖示能否適用非語音輸入。

### SCN-05 — 思考

- USER 決定：StatusBar 顯示「思考中」並搭配小沙漏動畫；不選轉圈。
- 目的／內容：辨識正在思考且仍在處理；沙漏位於 StatusBar，外觀引用 ICON-THINK，大小／間距／色彩引用既有 StatusBar Theme 變數。
- 本輪沙漏配置適用 STYLE-02。STYLE-01 仍是純文字比較基準，不默認兩個 Style 都已選為最終方向。
- Main：保留當前有效內容，本批示例為 SCN-04 的已驗證文字；原本無內容則保持空白。
- 進入／離開：由權威 THINK state 更新 StatusBar；新合法 Tool／Speak 內容依各自觸發取代 Main。
- 隱私／例外：不顯示 prompt、推理過程、raw model output 或虛構進度；設定關閉時不因 THINK 恢復已抑制內容。
- USER 決定動態方式 B：沙漏只做翻轉循環，不做落沙；效果模式 hourglass-flip。週期、翻轉時長與影格待討論。不表示百分比、剩餘時間或真實推理進度。
- 有效進入 THINK 開始，離開 THINK／shutdown／Display rendering disabled 時停止；不自行變更 State。Fullscreen active 時不做 Normal 實體 flush，release 後投影最新狀態，具體 scheduling 待 Core mapping。
- USER 已確認 Main 保留當前有效感知文字；沒有文字時保持空白。隱私設定已抑制的內容不能因此恢復，不顯示內部推理或額外進度。
- 待解：沙漏如何動、速度及實體小尺寸辨識；動畫成本與取消行為。Main 保留方向已決定，不再作為未決選擇。
- 已生成的第二批草圖仍為三點靜態舊稿，未呈現此次沙漏決定；下次更新僅在外觀／動態細節收斂後產出。

### SCN-07 — 打斷回饋

- USER 已確認第一輪方向：系統接受打斷後 Main 顯示「已中止」、停止原文字效果；真正回到待機時清空。
- 目的／內容：SM 已接受 InterruptRequested 並開始 convergence 後，Main 取代為既有文案「已中止」。
- StatusBar：維持實際 authoritative state，不新增「中止中」state。本批用仍為 ACTION 的「回應中」及其圖示作時序示例，不代表固定組合。
- 進入／離開：不能在按鍵／請求尚未接受時提前顯示；真正回到 IDLE 時清 Main。
- 隱私：既有 session-content setting 只抑制 Perception／Tool／Speak，不能順便抑制已接受 interrupt feedback。
- 效果：直接呈現，取消舊 Speak 打字機效果，不能讓殘留更新覆蓋「已中止」。
- 待解：短暫回饋是否來得及看見；「回應中＋已中止」的合法短暫組合是否造成誤解。若需要改動狀態文案，返回 focused finding，不自行新增語意。

### SCN-09 — 關機

- USER 已確認：先顯示與開機相同的簡單標誌，再回全黑；未來可加短動畫，但不能拖延關機。
- 目的／版式：Fullscreen 標誌，沒有狀態列或 divider；回到全黑作可靠結束。標誌圖形與 SCN-01 共用，尚未設計。
- ANI-004「關機標誌」標識這項主題呈現，與 ANI-002 開機標誌共用圖形但有不同 lifecycle；Theme 各自描述，ID 不因换主題改變。
- Ownership：由 `app.lifecycle.shutdown` 使用既有 fullscreen 規則；不得強制 preempt 或釋放別人的 owner。
- 結束：維持至 Display stop；real SSD1351 釋放 transport 前 best-effort 最終全黑 frame。
- 故障：最終 present 失敗仍繼續 cleanup，不延後 shutdown、不改 exit code；不保證硬體故障時面板必然變黑。
- 標誌／後續動畫皆 bounded best effort；若 lifecycle 沒有可用呈現時間，直接走 Blank，不新增等待。完成／timeout／cancel／failure 收斂 Blank，最終 present 失敗仍繼續 cleanup。
- 舊第二批關機 PNG 仍是 Blank 基準，尚未更新為標誌。
- 待解：關機動畫是否有價值；取消、競爭 owner 與 reverse-stop 時序待 contract mapping。

### 本批主題變數增補

ICON-WAKE、ICON-PERCEPTION、ICON-THINK 納入 Theme 圖示資源變數，僅 STYLE-02 使用。
SCN-07 引用當前 authoritative state 的圖示，不額外建立假的 interrupt state 圖示。
以上圖示均為程序幾何草案，沒有加入正式資產或依賴。

九類場景的靜態首稿現已齊全，但 D1 尚未完成：輔助資訊、IDLE 保護、轉場／開關機候選、
效果參數、完整 Core mapping 及實驗選擇依據仍待整理。

## 要完成的設計決策

以下「起始提案」尚未定案；Core baseline 的細節須在指定 baseline 核對，不能以本表推定。

| 決策 | 要決定的內容 | 起始提案 | 必須解決的風險／後續證據 |
|---|---|---|---|
| 1. 視覺語言 | 字體層級、圖示風格、前景／錯誤角色、留白及密度 | 工具型、簡單圖示、文字優先；不以角色動畫為候選主線 | 128 px 上看不清、資訊過密；以實體閱讀觀察收斂 |
| 2. 區域與資訊優先級 | StatusBar 狀態及輔助資訊的空間配置；Main 文字和圖示比例；安全區 | 保留既有分區，Main 先給當前內容；不以圖示壓縮文字 | 狀態難辨、內容不足、輔助資訊互相擠壓 |
| 3. 六種狀態 | 每個 authoritative state 的短標籤、圖示、靜態／動態處理及狀態切換 | 短標籤加簡單圖示；動態只在有助辨識時保留 | 視覺相似造成誤判；動畫暗示虛構的進度或新狀態 |
| 4. 當前內容 | Perception、安全 Tool 名稱、actual Speak、已接受的 interrupt feedback、sanitized error 的版式與清空 | 沿用各內容的合法觸發與有效期，錯誤只呈現安全類別／摘要 | 漏掉必要內容、舊 turn 殘留、未接受的 interrupt 提前顯示 |
| 5. 文字策略 | 字級、行高、行數、pixel-width wrapping、ellipsis、缺字與空內容；是否需要閱讀動態 | 先採確定性換行／截斷；不先加入自動捲動 | 截斷失去關鍵意義、中文難讀；若需捲動須另列風險與測試 |
| 6. 輔助資訊 | volume、connection、capability 如何在既有 surface 呈現、資訊來源與更新條件 | 音量以 startup-static 為前提；連線／能力使用既有權威資訊 | 假設尚未採用的控制能力、顯示推測狀態、擠壓狀態標籤 |
| 7. 候選與轉場 | 靜態與短促轉場差異；哪些切換有價值；觸發、時長、pacing、連續更新和取消策略 | A：清晰靜態；B：相同內容版式加少量短促轉場 | 裝飾收益低、內容顯示延遲、動畫與較新有效內容競爭 |
| 8. 開關機 | 是否加入 bounded animation、素材／時長、owner、timeout、取消、release 和 Blank 收斂 | Blank 為基準；僅在收益明確時保留短動畫 | 延後 readiness／shutdown、素材缺失、owner 未釋放 |
| 9. IDLE／OLED 保護 | 低亮度靜態、延後 blank、可能的微位移；進入／恢復條件、設定與長期風險 | 優先比較低亮度靜態與延後 blank；確認既有能力再選機制 | 使用者誤以為離線、喚回延遲、固定像素風險；短測不宣稱壽命或 burn-in 已驗證 |
| 10. 渲染與資產 | 程序繪製、sprites、預製影格何者適合保留的視覺；dependency、offline、license 和 size | 靜態／簡單轉場先評估程序繪製；只為必要效果比較資產方案 | 技術比較失焦、儲存／解碼成本、依賴無法離線重現 |
| 11. 降級与隱私 | content switch、empty、stale、missing glyph／asset、unknown hint、NullDisplay、renderer／HAL failure 的推薦路徑 | 保留既有契約；UI 故障不影響 session、audio、lifecycle 或 exit | 洩露內容、故障阻斷主功能、錯誤 fallback 清掉當前有效畫面 |
| 12. Core 映射與選擇依據 | 每個畫面的 hint/model/render/arbiter/device 路徑、owner；各候選的保留／淘汰依據 | 完成指定 baseline 核對與映射；以可讀性、狀態辨識、內容時效和資源成本比較 | 獨立 demo 被誤當整合證明；偏離契約而未提出 focused finding |

## 決策分工與時間點

- USER 已決定工具型主方向。若兩個方向在證據之外仍有重大產品取捨，返回 USER 討論。
- Display team 可依既有授權決定日常版式、候選範圍、渲染比較與實驗方法。
- D1 決定候選和風險；D2 設計檢查；D3/D4 取得證據；D5 形成推薦，Core 決定是否採用。
- 精確字級、動畫時長／幀率、亮度與待機時間先列為候選參數，不在實測前宣稱產品預算。
- 實體 OLED 的可讀性、flicker、smoothness 與 product fit 保留人眼判斷。

## D1 完成產出

- [ ] 核對指定 Core baseline 的直接相關來源並記錄約束／疑點。
- [ ] 必要畫面清單與 A/B 候選版式，覆蓋各適用產品要求。
- [ ] 狀態／內容切換表，含取消、清空、隱私、錯誤與 Blank 路徑。
- [ ] 轉場、開關機及 IDLE 候選策略與參數範圍。
- [ ] 每個保留實驗的產品問題、失敗風險及淘汰依據。
- [ ] 初步渲染／資產策略與 Core ownership 映射。
- [ ] 未決事項清單，明確標示由 D2–D4 證據或 Core 決策解決。

D1 不需要量測結果或完整可執行原型；以上完成後直接進入 D2，不增加額外 sign-off gate。
