# Milestone Progress

本文件由 **Designer** 維護，記錄 milestone 定案 gate、跨角色阻擋、外部 POC 相依與下一動作。穩定範圍及驗收原則以 `docs/milestone.md`、`docs/milestones/M{x}.md` 為準；Developer 估點與工作包由 `docs/reviews/dev_progress_M{x}.md` 維護。

* **Current milestone**: M3
* **M3 gate status**: `Development Ready — target-device acceptance Pending`
* **Last updated**: 2026-08-13
* **Owner**: Designer

---

## M3 Design / Development Gate

### 結論

Core Display 設計、strict SSD1351 mapping 與 M3–M7 規劃已收斂；Display POC v0.3 是 Accepted design input。Tester 的 M3 test spec 經 PM-009 修訂後由 Designer 以 `TR_spec_M3_I` 確認 100% 覆蓋，內部 Development Ready gate 已批准。Developer 可建立 `dev_progress_M3.md` 後拆包實作；本結論不是 M3 acceptance，RPI-NATIVE cards 與外部 PM exact-SHA intake仍為 Pending。

### Gate matrix

| Gate | 狀態 | 證據 / 依據 | Owner / 下一動作 |
| :--- | :--- | :--- | :--- |
| M2 acceptance | `PASS` | PM handoff `PM-OUT-260807-006-m2-tester-verification` 已 Resolved | Core Team；無動作 |
| Audio POC design input | `ACCEPTED WITH CONDITIONS` | `docs/outsource/references/poc_audio/audio_m3_contract_v1.0.md`；`DELIVERY-AUDIO-POC-M3-ACK-001` | 可供整合設計；Audio P1/P2 在 M3 delivery SHA 前完成，P3 TTS winner 延至 M4a |
| Display POC design input | `ACCEPTED` | v0.3；`DELIVERY-005-poc_display-m3-v0.3-ack`；source candidate `5c2b6ba532a2661d5db79e27736e79890931515f`；stage-exit `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40` | D1–D5 全數 Resolved；Pi build+evidence PASS；無 blocking finding |
| LLM POC input | `N/A FOR M3` | `docs/milestones/M3.md` 排除真實 LLM | 不等待 LLM；轉列 M4b entry blocker |
| Core Display Spec | `REVIEWED` | `docs/display_spec.md`；`docs/display_mock_contact_sheet.svg`；`IR_review_III`；PM-009 `OUT-M3-DSP-2026-005` Resolved | M7 stable IDs / trace / Error mock 已收斂 |
| Font asset / provenance | `READY` | Noto Sans TC Regular + Medium 2.004、OFL 1.1；Spec 記錄 paths / SHA-256 | 納入 Design Ready delivery；不得改用 OS font |
| Ch 8 / Ch 10 alignment | `READY` | strict SSD1351 artifact / ABI / SPI / GPIO / rotation / byte-order / buffer mapping；PM-009 `OUT-M3-DISPLAY-2026-002` Resolved | Developer 依已簽核 config / factory boundary 實作 |
| M3 / M4 / M5 / M7 planning alignment | `REVIEWED` | M4a / M4b / M4c、M5 exact-SHA dependency、M7 spec-first 規則；`MR_review_II` Resolved | 建立本輪 design commit |
| M3 Design Ready | `READY` | Core design commit `08032cfa63e776b5e7771ff3817bcfb275e8bac1`；Display POC ACK `DELIVERY-005-poc_display-m3-v0.3-ack`（source `5c2b6ba...`）；Audio ACK `DELIVERY-AUDIO-POC-M3-ACK-001` | **Gate 解除**；Tester 即可開始 `test_spec_M3.md` |
| M3 test spec / coverage sign-off | `APPROVED` | `docs/test_spec/test_spec_M3.md`；`TR_spec_M3_I` Resolved；PM-009 test finding Resolved | 100% coverage sign-off 完成 |
| `dev_progress_M3.md` / 工作包 | `AUTHORIZED / NOT CREATED` | Developer-owned；test spec 已簽核 | Developer 現可估點拆包後開始實作 |
| M3 target-device acceptance | `PENDING` | `docs/milestones/M3.md`；`OUT-M3-TEST-2026-001` | Tester 對 delivery exact SHA 獨立驗收；POC 自驗只作外部 evidence layer |

### Reviewer handoff scope（pre-commit working tree）

本輪須由 Reviewer 分成兩張審查單，避免把設計一致性與 milestone gate 混為同一結論。Reviewer 依 workflow 自行建立審查單、提出 findings 與裁定；Designer 不預先代寫審查結論。

#### `IR_review_III` ── Display design alignment

審查輸入：`docs/display_spec.md`、`docs/display_mock_contact_sheet.svg`、`src/sbd/core/display/assets/fonts/`、Ch 2a、Ch 8、Ch 10，以及 PM-008 的 brief / Display Spec Requirements。至少確認：

1. `display_spec.md` 是唯一產品顯示設計權威，只描述使用者可觀察內容；沒有 milestone 狀態、test gate、SPI / ABI / build 細節或實作進度。
2. User 已確認的 OLED 128×128、Normal = StatusBar + Main、Fullscreen 互斥、`接收中` / `回應中`、mock-first 與 visual tokens，均與 mock、字型 inventory、license、checksum 一致；LCD 與 Progress 沒有被偷渡進目前產品行為。
3. `DSP-REQ-001` 至 `DSP-REQ-009` 可追溯至版面、component、scenario、privacy、Blank、animation principle 與 failure fallback；PM-008 的 Core-owned TBD 已處置，沒有用 POC pending facts 偽裝成已核准 backend baseline。
4. Ch 2a 仍只定義 chip-independent HAL；Ch 8 的 `main.error`、Progress technical reservation、initial IDLE seed、ownership / release / failure 行為與 `arch.md` 相容；Ch 10 的 `show_session_content` 只影響 Perception / Tool / Speak，且未提前形成 production implementation。
5. Reviewer 明確裁定本輪是否改變公開 HAL、ownership、lifecycle 或跨模組架構。若沒有，記錄 `No architecture change`；若有，依 workflow 另開架構審查，不得在 IR finding 中默認核准。

#### `MR_review_II` ── M3–M7 planning alignment

審查輸入：`docs/milestone.md`、M3–M7 milestone、`docs/test_spec.md` 的術語同步、PM-008 Display Milestone Requirements，以及本進度表。至少確認：

1. Core spec / mock / font / chip-independent design 可在 Display POC v0.3 前完成，但 M3 Design Ready、test spec、Developer 拆包與產品實作仍受 Accepted Display input 阻擋。
2. M3 沒有等待 LLM；M4a Audio、M4b LLM、M4c Session Display 的先後與同一 delivery exact-SHA 規則清楚；M5 不得拼接不同 SHA 的 M4 子 gate 結論。
3. M4c 只提前定義 Tool display intent / fixture，沒有把實際 ToolRegistry handler 從 M5 搬入；`SET-SHOW-SESSION-CONTENT` 不改變 session、audio、action、resource lifecycle 或 exit code。
4. M7 任何正式資產、動畫、轉場、OLED 保護或新增 Progress 需求，都必須先修訂 `display_spec.md`；M6 沒有另創 Display profile。
5. `docs/test_spec.md` 本輪只同步已廢除的 profile 名稱，沒有提前建立 M3 詳細驗收、降低既有 gate 或宣稱 M3 Ready。

#### 本輪排除與 Reviewer 必要輸出

- 不在本輪技術驗收 Display POC v0.3 D1–D5；Reviewer 只確認 Core 文件未把 v0.2 或 pending input 誤寫成 Accepted。POC 回交後由 Designer 依既有 delivery findings 複審。
- 不審 production code、M3 詳細 test spec 或 Developer 工作包，因三者尚未獲准建立。
- 不以個人視覺偏好重開 User 已確認的 mock；只有與核准需求、架構、可讀性或資料安全矛盾時才可形成 finding。
- `IR_review_III` 與 `MR_review_II` 必須依 workflow 將 findings 分成 `Blocking` / `Advisory`。兩張單的 Blocking 全數 Resolved，且明確記錄 architecture-change 與 milestone-gate 結論後，才可建立本輪設計候選 commit。

### Developer 建立 `dev_progress_M3.md` 時的必要欄位

Developer 拆包時必須加入 `POC Input Baseline` 表，至少包含：

| 欄位 | 要求 |
| :--- | :--- |
| POC domain | `audio` / `display` |
| Accepted contract | 文件版本與 repository 路徑 |
| Core adoption record | ACK / Delivery ID 與 decision |
| Source/artifact identity | full source SHA；header / `.so` / adapter SHA-256；target OS/arch |
| License / notice | 授權識別與必要 notice；不明即阻擋使用 artifact |
| Fixture/config | hardware revision、sanitized config 路徑與 config hash |
| Open conditions | owner、期限，以及 `blocks package start` / `blocks M3 acceptance` 分級 |
| Evidence index | automated logs、P50/P95、人工 checklist、照片/影片 metadata 的可定位索引 |

任何工作包若依賴尚未 Accepted 的 Display contract、未定位的 binary、未知 license、branch HEAD 或只有「畫面可見／不 crash」的 POC 自驗，狀態必須保持 `Blocked`；Developer 不得自行補寫 HAL / ABI / fixture 語意。

---

## M4 Forward Gates

M4 包含 M4a Audio、M4b LLM、M4c Session Display。M4a 與 M4b 可依各自 Accepted input 準備；M4c 必須等兩者通過。三個子 gate 必須對同一產品 delivery exact SHA 通過，M4 才是 Accepted，M5 才能開始。

| Gate | 狀態 | 阻擋 |
| :--- | :--- | :--- |
| M4a Audio | `PENDING` | M3 Accepted、Audio M4 winner與 `model_spec.md` baseline |
| M4b LLM | `BLOCKED` | 尚未收到 LLM POC contract；缺 `model_spec.md` LiteRT-LM baseline 與已 review 的 child protocol |
| M4c Session Display | `PENDING` | 依賴 M4a + M4b；Display content / privacy design 已在 `display_spec.md` |

---

## 下一動作順序

1. ~~Reviewer 複審 `IR_review_III` 與 `MR_review_II`~~ — **Done**（`IR_review_III`、`MR_review_II` 已 Resolved）
2. ~~POC Display 回交 v0.3，處理 D1–D5~~ — **Done**（stage-exit `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40`）
3. ~~Designer 複審 Display v0.3 → Accepted~~ — **Done**（`DELIVERY-005-poc_display-m3-v0.3-ack`）
4. ~~Designer 彙整 M3 Design Ready conclusion~~ — **Done**（本 commit；gate 解除）
5. ~~Tester 產出 `test_spec_M3.md`；Designer coverage sign-off~~ — **Done**（`TR_spec_M3_I` Resolved；Development Ready approved）
6. 取得 USER commit 同意後建立 PM-009 單一候選 commit，回傳完整 40-character HEAD 完成 external exact-SHA intake。
7. Developer 建立 `dev_progress_M3.md`，依已採用 Audio / Display baseline 估點拆包後開始實作。
8. M3 delivery 前收齊 Audio P1/P2 與 Display artifact / fixture / performance evidence，再由 Tester 對 exact implementation SHA 驗收。
