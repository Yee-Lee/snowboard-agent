# M3 單一 GPIO Button 開發前設計 Gate

* **Handoff ID** : `PM-OUT-260806-005-gpio-button-semantics`
* **Status** : `Ready for PM`
* **Finding ID** : `OUT-M3-DESIGN-2026-001`
* **Related handoff** : `PM-OUT-260806-004-m3-target-device-test-ack`
* **Reference candidate** : `af890249d8634df11b1a30a27aaee1720f5a8b67`
* **Architecture authority** : `docs/arch.md`

## 結論

產品確認使用單一 conversation button：短按依 App 對話狀態開始或中止 session，長按在 App 執行中觸發 graceful shutdown。App 未執行時由外部 launcher 處理長按啟動，不屬 Snowboard App 本輪開發或驗收；本產品不控制 Raspberry Pi OS shutdown 或實體電源。

現行 `docs/arch.md` 將非 IDLE 的 `ButtonPressed` 視為過期 wake，並以長按產生 `InterruptRequested`，與新決策不一致。本輪是單一 `M3 Design Ready` gate：同一個 exact-SHA delivery 必須同步完成 `docs/arch.md`、相關 `docs/implement/`、`milestone` / M3 planning 與適用 progress 的一致修訂。Gate 通過後才撰寫 M3 test spec、拆 development packages 與開始 code；不另設獨立的 arch gate 或 implement-design gate。

## 必做修訂

| ID | Priority | Problem | Required action | Acceptance |
| --- | --- | --- | --- | --- |
| `OUT-M3-DESIGN-2026-001` | Blocking | 現行短按 / 長按語意及跨文件設計與新產品決策衝突 | 在同一 delivery 修訂 `docs/arch.md`、相關 `docs/implement/`、`docs/milestone.md` `docs/milestones/M3.md` 與適用 progress，建立 requirement traceability | 所有設計文件在同一 exact SHA 一致且無阻擋開發的 TBD；單一 `M3 Design Ready` gate 確認後才可寫 test spec / 拆開發包 |

## 必須固定的架構語意

1. 裝置隻有一個 conversation button；按法分類由 `input_events/button` 負責，GPIO HAL 只提供 pin / edge / duration 所需的低階能力。
2. App 已 READY 且位於 IDLE 時短按，產生開始對話的 Signal，流程進入 `WAKE`，首 turn perception 為 `[listen]`。
3. App 在 `WAKE` / `listen` / `think` / `speak` / `rest` 時短按，一律產生 `InterruptRequested`，終止當前 session 並乾淨返回 `IDLE`（同原本長按中斷語意）。
4. App 在任何狀態長按，產生 graceful App shutdown 要求，通知系統退出 App，exit code 代表正常關機；不發送內部 session 中斷事件，也不觸發系統級 reboot / poweroff。
5. App 位於 `recovery` / `error` 時短按，代表使用者重試，清空當前錯誤狀態並重新進入 `WAKE`。
6. 按鍵硬體短按門檻（如 `>= 50 ms`）、長按門檻（如 `>= 1500 ms`）在 `docs/arch.md` 固定；軟體 `input_events/button` 只對上層輸出分類結果。

## 單一 Design Gate 必備文件

* `docs/arch.md`：固定產品語意、狀態 / 生命週期、責任與 App / external launcher 邊界。
* `docs/implement/`：至少核對並修訂 events、InputSource contract、State Manager 與 config；外包須自行盤點其他受影響章節，不以本清單作排除依據。
* `docs/milestone.md` `docs/milestones/M3.md` 與適用 progress：固定 M3 scope、相依、排除、開發前順序與最終驗收觀察點。
* Requirement traceability：為各項 button 行為配置 stable Requirement ID，逐項映射 arch、implement/design 與 milestone；不得只列「文件已更新」。

本 gate 是單一整體決策。Designer 彙整必要的 Architect / Engineering Reviewer 檢查後，只產生一個 `M3 Design Ready` 結論；專業檢查不是額外的串行 gate。任一文件矛盾、責任未定或影響實作的 TBD 都使整個 gate 不通過。

## Gate 後開發與追溯順序

Gate 通過後依下列正向順序工作：

```
accepted arch / implement / milestone requirements
-> M3 test_spec
-> development packages
-> code + tests
-> M3 target-device acceptance
```

交付與驗收必須能反向追溯：

```
code / test
-> test_spec Test ID
-> implement/design Requirement ID / 章節
-> arch product contract
```

* Test spec 只能把已 Accepted requirement 轉成測項，不得自行發明產品行為。
* Development package 必須引用 Requirement ID 與 Test ID；production code 不要求逐行嵌入文件連結。
* 若 test spec 或拆包時發現不可測、矛盾或遺漏，沿用 `OUT-M3-DESIGN-2026-001` 退回設計修訂，不建立平行設計 gate。
* M3 最終驗收時，任一 scope code / test 無法追溯至 Test ID 與 design requirement，均不得 Accepted。

## 本輪範圍與驗收

* 本輪要求完成所有受影響設計文件與 requirement mapping，不要求撰寫 test spec、拆 development packages 或修改產品 code / tests。
* `docs/arch.md` 的 input events、Signal、wake mapping、state handling、GPIO routing、shutdown / convergence 必須互相一致，且相關 implement、config、milestone 不得保留舊語意。
* Delivery 必須聲明 `Architecture change: Yes`，並列 comparison baseline、完整 repo commit SHA、各設計文件 SHA / 逐節定位、Requirement ID mapping 與未完成決策。
* Gate 要求零影響開發的未決行為；短按 / 長按門檻、state matrix、Signal ownership、external launcher handover 假設必須在本輪固定。
* Designer 完成 manifest / diff intake 並彙整必要專業檢查後，對 delivery exact SHA 作單一 `M3 Design Ready` 決定；確認前 finding 維持 `Open`。

## 回覆方式

* **Response** : `docs/outsource/responses/OUT-M3-DESIGN-2026-001.md`
* **Delivery** : `docs/outsource/deliveries/<new-delivery-id>.md`
* **Evidence** : 如有文件檢查輸出，放 `docs/outsource/evidence/<new-delivery-id>/`；本輪不要求硬體 evidence。
* Response / delivery 須列 Handoff / Finding ID、comparison baseline、全設計文件逐節修改定位、Requirement mapping、未完成事項及承載修改的完整 commit SHA；PM 拉回後另通知 branch / 完整 HEAD SHA。
