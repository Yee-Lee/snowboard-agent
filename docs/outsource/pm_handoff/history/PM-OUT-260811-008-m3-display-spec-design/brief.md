# M3 Display Spec 與 Design Ready

- Handoff ID : `PM-OUT-260811-008-m3-display-spec-design`
- Status : `Ready for PM`
- Requirement : `OUT-M3-DISPLAY-SPEC-2026-001`
- Related handoff : `PM-OUT-260805-002-m3-m4-poc-planning`
- Absorbed requirement : `PM-OUT-260810-007-m3-display-backend-boundary` / `OUT-M3-DISPLAY-2026-001`（未交付；內容已合併至本handoff）
- Reviewed Core candidate : branch `dev_agent_m2` , SHA `7b860e48a9e35abac027ddaaab1f94b1797a0fc6`
- Display POC reference : branch `display` , SHA `ecc6a6c81a82277eb7d06a22bc971914c25ffbd2` ; 目前尚未Accepted

## 結論

M3 Design Ready前，Core Team Designer須在活動產品repo建立唯一權威 `docs/display_spec.md`，把已核准的OLED 128×128產品方向、UI組成、情境 / lifecycle、內容安全、M3 / M4c / M7分工與追溯收斂於同一commit。M3不實作LCD、Progress或動畫；啟停以Blank為Baseline，M7才導入啟動動畫並以Blank作fallback。

## 規範性附件

PM須將下列兩份附件與本brief一併交付；附件內容是完整產品要求，並非參考資料：

- Display Spec Requirements
- Display Milestone Requirements

Core Team Designer須逐項落實附件內容。所有標示為Core / POC提案的欄位須在response中定位處置；如有異議，須逐項提出，不得自行簡化或未讀附件取代回覆。

## 必做事項

| ID | Priority | Required action | Acceptance |
| --- | --- | --- | --- |
| OUT-M3-DISPLAY-2026-001 | High | 維持chip-independent Display邊界：上層只依賴 `DisplayDevice`、`size()`、Renderer / Arbiter與selected profile；SSD1351-specific import、native artifact、config mapping、pixel-format / rotation mapping限於SSD1351 backend / factory / profile邊界。LCD維持未選定backup，不納入本輪實作、測試或硬體gate。 | Design Ready文件可定位共用層與SSD1351-specific邊界；共用Renderer / Arbiter / Resource Manager不直接import或判斷SSD1351；不新增ST7789 code / test / evidence前置條件。SSD1351產品化須引用未來 Accepted POC完整SHA、artifact checksum、license及特產品化項目，不得直接採用POC branch HEAD。 |
| OUT-M3-DSP-2026-001 | High | 建立 `docs/display_spec.md`，採六區塊：範圍 / 選定Profile、視覺基礎、UI組成、情境 / lifecycle、內容 / 設定 / 失敗 / 核准 / 追溯。保留Layout / Component / Scenario / Requirement IDs。 | 文件只以SSD1351 OLED logical 128×128為現行profile；LCD僅標未選定backup。SPI / GPIO / ABI / build細節不重複進UX Spec，並可定位Ch 2a / 8 / 10權威邊界。 |
| OUT-M3-DSP-2026-002 | High | 固定產品行為：Normal = StatusBar + Main、Fullscreen互斥；State、Main Text、Error、Blank及M7 Animation；Perception / Tool / Speak目前內容預設顯示且可設定關閉；privacy、換行、截斷、缺字、Null / runtime failure及Blank fallback完整。 | Scenario matrix逐項列trigger / authoritative data / layout / component / content mapping / replace / clear及profile。禁止完整歷史、credential、內部prompt、raw tool arguments與未處理模型輸出；目前沒有Progress產品需求。 |
| OUT-M3-DSP-2026-003 | High | 提交Design Ready資料：128×128 mock contact sheet、固定離線繁中字型、visual tokens、license / version / checksum、支援字元 / missing glyph，以及所有Core-owned TBD的處置。 | 同一commit可定位State、Perception短 / 長文、Tool、Speak、Error mock及font / asset inventory；不依賴OS字型。列出Accepted Display POC exact SHA，若尚未取得則明確標示只阻擋real-backend integration，不阻擋文件設計。 |
| OUT-M3-DSP-2026-004 | High | 同步M3 / M4c / M7 milestone與Ch 2a / 8 / 10定位：M3完成OLED Baseline、State與Blank；M4c接Perception / Tool / Speak / Error；M7完成啟動動畫、正式assets與OLED保護。Design Ready後才寫詳細test spec、拆Developer工作包及實作。 | 提供requirement traceability、完整design commit SHA與architecture-change聲明。Display scope若未改HAL / ownership / lifecycle，逐項說明No change；整份delivery仍須如實反映其他scope的architecture change，不得一概聲明No。 |

## 本輪排除

- 不要求M3程式實作、詳細test spec、work package或Pi硬體驗收。
- 不實作、測試或等待ST7789 / LCD，不建立LCD layout或mock。
- 不加入Progress UI、Display process / service / queue / IPC / overlay或preemption。
- 不直接合併POC branch；產品化只能引用未來Accepted POC exact SHA與artifact provenance。

## 回覆與交付

- PM交付包：本brief、`display_spec_requirements.md`、`display_milestone_requirements.md` 三份文件必須一併交付。
- Response須明確確認已閱讀兩份規範性附件，並分別定位 `OUT-M3-DISPLAY-2026-001` 與 `OUT-M3-DISPLAY-SPEC-2026-001` 的處置。
- Response：`docs/outsource/responses/OUT-M3-DISPLAY-SPEC-2026-001.md`
- Delivery：併入下一份 `docs/outsource/deliveries/<m3-design-delivery-id>.md`；008全部要求須在同一design commit收斂。
- Design artifacts：正式Spec、mock、font / asset inventory須commit於repo並由response定位；如另附design evidence，放在 `docs/outsource/evidence/<m3-design-delivery-id>/display-design/`。
- SHA：Response不得保留 `TBD`；須列完整40-character design commit SHA。若本輪純設計，implementation SHA標 `N/A - design-only`；若合併code / tests，另別被測implementation SHA與結果。
- PM拉回後另通知branch與repo HEAD完整SHA，Internal Designer再啟動exact-SHA intake。
