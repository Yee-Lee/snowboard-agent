# Core Team → POC Display Team: M3 Display HAL Contract Feedback

* **Delivery ID**: `DELIVERY-003-poc_display-m3_feedback`
* **Reference**: `display_m3_contract_draft.md`
* **Status**: `Needs Revision (Blocking)`
* **Date**: 2026-08-08

---

## 審查摘要 (Review Summary)

Core Team (Designer) 已完成 `display_m3_contract_draft.md` 審閱。
架構層面的 `DisplayDevice` Protocol 與 Native C ABI 介面設計完全符合「無 IPC/Queue/Service」且限定於 HAL 層級之要求，M3 至 M7 擴充機制亦與核心產品規劃對齊。

然而，做為正式技術契約，本草案缺少實體驗收基準與交接邊界。在更新為 v1.0 前，必須補齊以下兩項 Blocking 缺失。

---

## 待修正項目 (Blocking Issues)

| # | 缺失項目 | 說明與要求 | 責任方 |
|---|---|---|---|
| P1 | **缺乏實體裝置與硬體規格 (Hardware Gate)** | 目前僅定義軟體 API。請明確定義硬體基準，包含：螢幕控制器型號 (如 ST7789)、解析度、通訊介面 (SPI/DSI)、SPI 傳輸速率 (Driver Config)、實體接線圖與供電要求，以確保 Core Team 能在 Pi 上建立完全相同的測試環境 (Fixture)。 | POC Display Team |
| P2 | **缺乏整合契約與交付邊界 (Integration Contract)** | 需明確定義雙方權責與交接點。例如：POC 團隊預計交付哪些硬體驗證證據？Core Team 完成實作後，需回傳什麼產出 (如 exact SHA) 供 POC 進行 M3 整合驗收？ (可參考 Audio POC contract 的格式) | POC Display Team |

---

## 請 POC Display 團隊執行

1. 針對上述 P1、P2 項目修訂 `display_m3_contract_draft.md`。
2. 完成修訂後，將版本更新為 `v1.0 / Accepted` 並回覆 Core Team。Core Team 將以此作為後續撰寫 `docs/display_spec.md` 與 M3 實作的唯一基準。
