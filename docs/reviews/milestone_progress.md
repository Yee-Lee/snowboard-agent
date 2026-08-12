# Milestone Progress

本文件由 **Designer** 維護，記錄 milestone 定案 gate、跨角色阻擋、外部 POC 相依與下一動作。穩定範圍及驗收原則以 `docs/milestone.md`、`docs/milestones/M{x}.md` 為準；Developer 估點與工作包由 `docs/reviews/dev_progress_M{x}.md` 維護。

* **Current milestone**: M3
* **M3 gate status**: `Not Ready`
* **Last updated**: 2026-08-12
* **Owner**: Designer

---

## M3 Design / Development Gate

### 結論

Core Display 設計與 M3–M7 規劃已通過 `IR_review_III`、`MR_review_II`，且 visual proposal 已由 User 確認。這些設計輸出可建立單一 design commit，但不等於 M3 開發放行：Display v0.3 的 D1–D5 尚未回交，real-backend contract 仍不可作 baseline；Display input Accepted、M3 test spec 與 Designer coverage sign-off 完成前，Developer 不得拆包或開始任何 M3 產品實作。

### Gate matrix

| Gate | 狀態 | 證據 / 依據 | Owner / 下一動作 |
| :--- | :--- | :--- | :--- |
| M2 acceptance | `PASS` | PM handoff `PM-OUT-260807-006-m2-tester-verification` 已 Resolved | Core Team；無動作 |
| Audio POC design input | `ACCEPTED WITH CONDITIONS` | `docs/outsource/references/poc_audio/audio_m3_contract_v1.0.md`；`DELIVERY-AUDIO-POC-M3-ACK-001` | 可供整合設計；Audio P1/P2 在 M3 delivery SHA 前完成，P3 TTS winner 延至 M4a |
| Display POC design input | `BLOCKED` | v0.2；`DELIVERY-004-poc_display-m3-v0.2-review` D1–D5 | POC Display 回交 v0.3 disposition、contract/header/fixture/evidence；Designer 僅複審原 findings、直接影響與 regression |
| LLM POC input | `N/A FOR M3` | `docs/milestones/M3.md` 排除真實 LLM | 不等待 LLM；轉列 M4b entry blocker |
| Core Display Spec | `REVIEWED` | `docs/display_spec.md`；`docs/display_mock_contact_sheet.svg`；User 於 2026-08-12 確認 mock；`IR_review_III` Resolved | 建立本輪 design commit；POC input 未 Accepted 前不得實作 real backend |
| Font asset / provenance | `READY` | Noto Sans TC Regular + Medium 2.004、OFL 1.1；Spec 記錄 paths / SHA-256 | 納入 Design Ready delivery；不得改用 OS font |
| Ch 8 / Ch 10 alignment | `REVIEWED` | `main.error`、Progress 排除、initial IDLE seed、`show_session_content`；`IR_review_III` Resolved | implementation 留待 Developer gate 後 |
| M3 / M4 / M5 / M7 planning alignment | `REVIEWED` | M4a / M4b / M4c、M5 exact-SHA dependency、M7 spec-first 規則；`MR_review_II` Resolved | 建立本輪 design commit |
| M3 Design Ready | `BLOCKED BY DISPLAY POC` | Core design / review 已完成；Display POC D1–D5 與 Accepted design input 尚缺 | POC Accepted 後，Designer 將本 design commit SHA 與 Accepted POC SHA 彙整為單一 M3 Design Ready conclusion |
| M3 test spec / coverage sign-off | `PENDING` | Design Ready 後才可撰寫 `docs/test_spec/test_spec_M3.md` | Tester 撰寫；Designer 以 `TR_spec_M3` 確認 100% 覆蓋 |
| `dev_progress_M3.md` / 工作包 | `NOT CREATED` | Developer-owned；不得早於 test spec 簽核 | Developer 在 gate 放行後估點拆包 |
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

1. Reviewer 複審 `IR_review_III` 與 `MR_review_II`；Designer 已回覆全部 Blocking 與 Advisory，仍由 Reviewer 裁定是否 Resolved。
2. POC Display 依 `DELIVERY-004-poc_display-m3-v0.2-review` 回交 v0.3，處理 D1–D5；此工作可與第 1 項並行。
3. Designer 複審 Display v0.3；通過後記錄 Accepted design input 與 adoption ACK。
4. Designer 以單一 design SHA 彙整 M3 Design Ready conclusion，完成 PM-008 response / delivery 定位。
5. Tester 產出 `test_spec_M3.md`；Designer 以 `TR_spec_M3` 簽核覆蓋。
6. Developer 建立 `dev_progress_M3.md`，依已採用 Audio / Display baseline 估點拆包後才開始實作。
7. M3 delivery 前收齊 Audio P1/P2 與 Display artifact / fixture / performance evidence，再由 Tester 對 exact SHA 驗收。
