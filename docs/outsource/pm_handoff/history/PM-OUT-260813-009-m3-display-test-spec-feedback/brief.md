# M3 Display / Test Spec 收斂回饋

- **Handoff ID** : `PM-OUT-260813-009-m3-display-test-spec-feedback`
- **Status** : `Ready for PM`
- **Feedback ID** : `OUT-M3-REVIEW-2026-001`
- **Related handoff** : `PM-OUT-260811-008-m3-display-spec-design` 、 `PM-OUT-260805-002-m3-m4-poc-planning`
- **Reviewed candidate** : branch `dev_agent_m3` , HEAD `61a17005de6076a3b79a4598cabd89be8b363e33`
- **Comparison baseline** : `9379d9167903313f1a860f3487fc1a5763b51333`

## 結論

Display POC已通過並可直接作為Core產品化輸入，POC team無補件。Core目前的Display設計方向可行，但產品strict config、Spec / mock一致性、M3 Test spec與正式delivery仍未收斂，因此候選維持 Revisions required / M3 Design Ready Blocked。請依下列四項一次修訂並以單一候選commit回覆；本brief已包含本輪所需的POC決策，不另附內部POC稽核文件。

## 已固定產品決策

- Display POC已由內部Accepted for productization：POC repo `display` @ `aecf75f45b7117cbc20010f4eb88e45e0cefa14e` ； tested source `5c2b6ba532a2661d5db79e27736e79890931515f` ； P3 evidence `055517a905bd2c8f8531c05acfa658854e25491f` ； P4 review `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40` 。Core不重驗或要求POC補件，應自行依產品架構抽取並產品化selected driver / ABI / HAL，不整合合併POC repo。
- Selected profile : SSD1351 、 128×128 、 RGB565 MSB first 、 rotation 0 ； co-I2S fixture為DC= `BCM24` 、 RST= `BCM25` 、 CE0= `BCM8` kernel-managed 。POC module revision不要求補寫。
- 架構可保留 `status_bar` / `main` / `fullscreen` 三個仲裁target ；產品UI只有Normal ( StatusBar + Main ) 與互斥FullScreen兩種layout，不是三區同時顯示。
- 目前沒有Progress產品需求。M3驗State、Main fixture、Boot / Shutdown Fullscreen Blank與底層能力；Perception / Tool / Speak、session-content setting及Error情境屬M4c；Animation屬M7。

## 必做修訂

### `OUT-M3-DISPLAY-2026-002` — Blocking — strict config未定義完整

- **問題**：Ch10 `DisplayConfig` 尚未定義SSD1351產品化所需的artifact / ABI / SPI / GPIO / rotation / byte order與buffer限制，但Test spec已假設real backend可以由strict config建構。
- **必做**：在Ch10及相關factory / milestone定義公開、可驗證的selected-backend config與cross-field validation；fixture值由local deployment config提供，不直接複製POC loader，也不寫入generic defaults。
- **驗收**：合法selected profile可strict parse；unknown、矛盾或超規值在硬體前拒絕；只有選real backend時才lazy載入native code；Test spec只使用已定義欄位與observable failure。

### `OUT-M3-TEST-2026-002` — Blocking — M3範圍與硬體覆蓋不正確

- **問題**：M3 Test spec納入M4c session content / Error / Progress預留及private `_rendering_enabled` ，同時缺少既定Pi驗收項目。
- **必做**：將Perception / Tool / Speak、session-content setting及Error情境移至M4c；移除Progress與private-field gate，改驗公開結果。M3補齊Display方向 / 顏色 / flicker / latency / reopen / invalid config / cleanup、喇叭可聽結果、Camera real RGB / YUV，以及recovery進行中短按忽略。
- **驗收**：Test ID只追M3 requirement；每個Pi test card具硬體 / 接線、完整implementation SHA、config hash、命令、操作、預期結果及artifact欄位；定義RPI / evidence code與portable deselection。尚未執行的產品硬體測試標Pending。

### `OUT-M3-DSP-2026-005` — High — Spec、trace與mock不一致

- **問題**：PM-008要求的M7 deferred stable IDs與milestone / approval trace缺漏；Error mock又同時把Status畫成error色並在Main重複「錯誤」，與Spec規則不一致。
- **必做**：補回 `CMP-ANIMATION` 、 `SCN-BOOT-ANIMATION` 、 `SCN-SHUTDOWN-ANIMATION` 並明確標M7 Deferred；補齊 `DSP-REQ-001` ~ `009` 的milestone與approval owner；修正Error mock，使Status state與Main Error只呈現Spec定義的顏色及文案。
- **驗收**：Spec、trace、mock三者一致，M7項目不進入M3 implementation或test gate。

### `OUT-M3-DELIVERY-2026-001` — Blocking — 缺正式exact-SHA交付

- **問題**：目前沒有涵蓋本輪Display design / M3 Test spec的正式delivery；既有Test response仍為 `Delivery commit SHA: TBD` ，文件間的完成狀態也不一致。
- **必做**：提交feedback response及正式M3 design / test-spec delivery，列branch、完整candidate / comparison SHA、architecture-change聲明、變更摘要、驗證結果、known limitations及逐finding disposition。Coverage sign-off前不得標Test spec Complete或M3 Design Ready。
- **驗收**：`response` 、 `delivery` 、 `Spec` 、 `Test spec` 、 `index`及progress commit將於同一候選HEAD，所有SHA皆為40 characters且狀態一致。

## 回覆與交付

- Response：`docs/outsource/responses/OUT-M3-REVIEW-2026-001.md`
- Delivery：`docs/outsource/deliveries/<m3-design-test-delivery-id>.md`
- Evidence：`docs/outsource/evidence/<m3-design-test-delivery-id>/`
- 若仍是design / test-spec only，Implementation SHA寫 `N/A - design/test-spec only` ；未執行的Pi項目寫 `Pending` ，不得宣稱implementation或milestone Accepted。
- 請以單一候選commit回覆。PM拉回後提供branch與完整HEAD SHA供下一輪intake。
