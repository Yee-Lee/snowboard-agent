# Display Milestone 需求

| 狀態：規範性Handoff附件；`Ready for PM`；須與008 brief一併交付。

## 文件定位

本文件是 `PM-OUT-260811-008-m3-display-spec-design` 的完整規範性Milestone附件。PM須與brief及Display Spec附件一併交付。內容提出M3 Baseline、M4c Session Display與M7 Complete的範圍，回答「哪個階段做到哪裡」：

- 文件 / 設計完成的內容；
- runtime 接線範圍；
- column / 測試範圍；
- delivery / evidence gate；
- 誰補規格、誰補證據、誰審查、誰決策。

本文件不定義畫面的最終產品內容，也不取代活動產品 repo 的 milestone、test spec、delivery、progress 或 evidence。

## Milestone 層級

| Milestone | 定位 | 狀態 |
| --- | --- | --- |
| M3 Baseline | Selected SSD1351 backend、最低可重現 Display 能力與硬體 bring-up | User方向已確認；待 Core設計與 POC gate |
| M4c Session Display | 接入實際 perception文字、action決定 / speak內容、error與 lifecycle資料 | User方向已確認；待 Core設計 |
| M7 Complete | 正式 assets、icons、animation、完整 StatusBar、OLED保護與 UX polish | 範圍方向已確認；細節後決 |

## 責任原則

| 內容 | 補件者 | 決策 / 核准者 |
| --- | --- | --- |
| 產品內容與 UX requirement | Internal Designer整理；Core Team Designer寫入產品文件 | User / Product Owner；Internal Designer作 Design Ready |
| OLED硬體事實、限制與 POC evidence | Display POC Team | Tester確認；Internal Designer決定是否作為 M3 design input |
| Core設計、實作、tests與 integration evidence | Core Team Designer / Core Team | Engineering Reviewer / Tester；Designer作 milestone整合判定 |
| 公開契約、ownership、lifecycle或跨模組架構變更 | Core Team Designer提出 | Architect僅在確有架構變更時核准 |
| Handoff交付與 repo收件 | PM | PM不作產品或技術簽核 |

## M3 Baseline 建議

### Design Ready

- Core Team Designer於同一產品 SHA建立權威 `docs/display_spec.md`，採Scope / Profile / Visual Foundation / UI Building Blocks / Scenario / Lifecycle / Content / Failure / Traceability六區塊，並同步 Ch 2a / 8 / 10與M3 / M4c / M7 milestone。
- 提交 128×128 mock、固定離線字型提案、license / checksum、pixel geometry、palette與 strict SSD1351 config mapping。
- Core設計維持 chip-independent Display層；SSD1351-specific內容限制於 backend / factory / profile。
- Display real-backend產品化必須引用未來 Accepted SSD1351 POC exact SHA、artifact checksum、license與硬體限制；目前 POC candidate不得直接操作產品基線。
- Design Ready只核准設計；通過後才寫詳細test spec、拆Developer工作包及進入implementation。

### 實作與 runtime

- 完成 SSD1351 real backend、共用 Renderer / Arbiter、NullDisplay fallback、failure latch及 reverse lifecycle。
- 一般畫面採 StatusBar + Main，另保留互斥 Fullscreen能力。
- Runtime先接實際 state顯示；啟動期間保持黑畫面，關機時清為黑畫面。
- 完成目前產品需要的靜態文字 / 狀態 / fullscreen渲染能力及固定 fixture測試。
- 目前沒有進度條產品需求；不要求 `main.progress` UI、真實資料接線或進度條驗收。若技術契約保留名稱，須標示為未啟用預留，不得擴張 M3 scope。
- 排除動畫、捲動、正式 icons、完整對話歷史及 ST7789 backend。

### 測試與認證

- 純軟體測試覆蓋 deterministic render、pixel-width換行 / 截斷 / 缺字 fallback、ownership、single flush、NullDisplay及 failure degradation。
- Raspberry Pi 5驗證方向、顏色、可讀性、flicker、full-frame latency、repeated open / close、invalid config及資源清理。
- Tester只接受產品 delivery exact SHA與對應 config / artifact checksum的認證。

## M4c Session Display 建議

- 接入本回合 PerceptionResult文字：語音辨識、外部訊息及視覺文字摘要。
- ACTION/tool顯示經清理、使用者可理解的動作說明；ACTION/speak顯示實際說出內容。
- 內容顯示預設開啟，並提供可關閉的產品設定；關閉後不得影響 session主流程。
- 接入 sanitized error類別 / 摘要，不顯示 credential、內部 prompt、hidden context、原始 tool arguments或未處理模型輸出。
- 保持靜態畫面，不要求進度條、動畫或正式 icons。

## M7 Complete 建議

- 完成正式字型、assets、icons、完整 StatusBar、啟動 / 關機動畫及狀態轉場。
- 依 POC長時間實機結果完成 OLED idle blank / burn-in保護政策。
- 啟動 / 關機動畫使用Fullscreen；必須有owner、timeout、cancel與finally release，失敗回Blank，不能繞過Arbiter或阻擋startup / shutdown。
- 若未來 Accepted LCD POC促成產品切換或新增 ST7789支援，另開產品決策及 OUT-TASK；不得回寫為 M3已驗收內容。
