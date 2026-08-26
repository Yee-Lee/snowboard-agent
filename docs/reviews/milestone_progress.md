# Milestone Progress

本文件由 **Designer** 維護，記錄 milestone 定案 gate、跨角色阻擋、外部 POC 相依與下一動作。穩定範圍及驗收原則以 `docs/milestone.md`、`docs/milestones/M{x}.md` 為準；Developer 估點與工作包由 `docs/reviews/dev_progress_M{x}.md` 維護。

* **Current milestone**: M4
* **Permanent development branch**: `core`
* **M3 gate status**: `Accepted — Designer transition direct review complete`
* **M3 implementation SHA**: `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`
* **Last updated**: 2026-08-25
* **Owner**: Designer

---

## Git milestone identity migration (2026-08-20)

Core 後續只在 `core` 分支 append 開發。舊 `dev_agent_m*` 分支保留為歷史參考，
不刪除也不繼續開發。已完成 milestone 的不可移動 annotated tag 對應為：

| Tag | Completion commit | Basis |
| :--- | :--- | :--- |
| `core_m1` | `a82b766484734a5299314560037fdcd11ed2be83` | M1 carry-over Tester PASS 後完成 `DELIVERY-M1-II-001` evidence / SHA alignment；是現行 Core history 的 M1 closure |
| `core_m2` | `0f915158100aea889c5929eb0b4b8a9c5b022a7c` | M2 Accepted、`OUT-M2-2026-003`～`005` 修正已納入，並歸檔 `PM-OUT-260807-006` |
| `core_m3` | `2fb2e18f934c3d06392074adba3c4518402101e9` | Designer 完成 final review、標記 M3 Accepted 並記錄 implementation SHA `5c9e5aac47e7f4f0dd168d8c75541438ee74f858` |

M4 仍在進行，不預先建立 `core_m4`。Tag 只標識 milestone completion commit；
acceptance / delivery 仍以文件中的完整 implementation / candidate SHA 為準。

---

## M3 Design / Development Gate

### 結論

Core Display設計、strict SSD1351 mapping與M3–M7規劃已收斂；Display POC v0.3是Accepted design input。Audio P1 native failure / P2 PASS維持原判定；POC完整P4回交已由`DELIVERY-AUDIO-POC-M3-P4-ACK-004`選定direct ALSA binding、valid-bit mapping、resampler、buffer與async I/O。Developer可開始Audio real package與production dependency lock。本結論不是M3 acceptance；Core exact implementation SHA與RPI-NATIVE cards仍為Pending。

### Gate matrix

| Gate | 狀態 | 證據 / 依據 | Owner / 下一動作 |
| :--- | :--- | :--- | :--- |
| M2 acceptance | `PASS` | PM handoff `PM-OUT-260807-006-m2-tester-verification` 已 Resolved | Core Team；無動作 |
| Audio POC design input | `FINAL SELECTION ACKED` | `DELIVERY-AUDIO-POC-M3-P4-ACK-004`；POC delivery `882e2b6ff571eb9d54ec96bae7d3b63338c5965c`；implementation/test SHA `de3b0bab4daaf47f62956d4b27f6697b3d4fa823` | P1 native matrix`FAIL`、P2`PASS`；WP-M3-07可開始。P3延至M4a；Core Tester仍須驗收Core exact SHA |
| Display POC design input | `ACCEPTED` | v0.3；`DELIVERY-005-poc_display-m3-v0.3-ack`；source candidate `5c2b6ba532a2661d5db79e27736e79890931515f`；stage-exit `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40` | D1–D5 全數 Resolved；Pi build+evidence PASS；無 blocking finding |
| LLM POC input | `N/A FOR M3` | `docs/milestones/M3.md` 排除真實 LLM | 不等待 LLM；轉列 M4b entry blocker |
| Core Display Spec | `REVIEWED` | `docs/display_spec.md`；`docs/display_mock_contact_sheet.svg`；`IR_review_III`；PM-009 `OUT-M3-DSP-2026-005` Resolved | M7 stable IDs / trace / Error mock 已收斂 |
| Font asset / provenance | `READY` | Noto Sans TC Regular + Medium 2.004、OFL 1.1；Spec 記錄 paths / SHA-256 | 納入 Design Ready delivery；不得改用 OS font |
| Ch 2a / Ch 8 / Ch 10 alignment | `PARTIAL READY` | Audio native / stream語意已固定但implementation selection待P4；strict SSD1351 artifact / ABI / SPI / GPIO / rotation / byte-order / buffer mapping已固定 | Developer依package split實作；不得自行選Audio binding / resampler / buffering |
| M3 / M4 / M5 / M7 planning alignment | `REVIEWED` | M4a / M4b / M4c、M5 exact-SHA dependency、M7 spec-first 規則；`MR_review_II` Resolved | 建立本輪 design commit |
| M3 Design Ready | `READY` | Core design commit `08032cfa63e776b5e7771ff3817bcfb275e8bac1`；Display ACK；Audio final ACK-004 | M3整體可開工；Audio real package依ACK-004 selected baseline實作 |
| M3 test spec / coverage sign-off | `APPROVED + COMPLETED` | `docs/test_spec/test_spec_M3.md`；`TR_spec_M3_I` Resolved；ACK-002 amendment；`CR_M3_I` final disposition | test spec §3的Pending文字是簽核當時的execution snapshot，不是current milestone tracker；Accepted狀態以本表與CR為準 |
| `dev_progress_M3.md` / 工作包 | `COMPLETED SNAPSHOT / DEVELOPER-OWNED` | Developer最後修訂記錄停在exact-SHA retest前；後續fixed-SHA evidence與Designer closeout見`CR_M3_I` | 不回寫Developer-owned歷史敘述；current acceptance authority為本表與CR |
| M3 target-device acceptance | `ACCEPTED` | `CR_M3_I`；`designer-review-5c9e5aa-20260817/README.md`；implementation `5c9e5aa...` | USER核准transition direct review與免再次freeze；20/20 target cards、3項人工觀察及240項portable regression通過 |

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

任何工作包若依賴尚未Accepted的contract、未定位binary、未知license、branch HEAD或只有「可執行／不crash」的POC自驗，狀態必須保持`Blocked`；Developer不得自行補寫HAL / ABI / fixture語意。Audio real backend另須有POC P4完整source SHA與Core final selection ACK，不能以本ACK-002或候選套件資訊解除。

---

## M4 Forward Gates

M4 包含 M4a Audio、M4b LLM、M4c Session Display。M4a 與 M4b 可依各自 Accepted input 準備；M4c 必須等兩者通過。三個子 gate 必須對同一產品 delivery exact SHA 通過，M4 才是 Accepted，M5 才能開始。

| Gate | 狀態 | 阻擋 |
| :--- | :--- | :--- |
| M4 Candidate process gate | `MINIMAL RUNNER IMPLEMENTED — FIRST CANDIDATE MATRIX PENDING` | `PM-OUT-260818-018`已由`f87c5e6`收斂：日常fast loop只跑主要版本與affected tests；建立首個M4 frozen candidate時才跑3.11 / 3.12 / 3.13 portable matrix。通用manual handshake、debug授權鏈與六項dry-run不再是Blocking；M3不重跑 |
| M4a Generic Scaffold | `IMPLEMENTED` | `9f1f32e`完成NullASRAdapter、NullTTSAdapter、factory、config placeholders、RM ResourceKey與portable regression；此scaffold不宣稱real engine Gate 3 |
| M4a Audio | `DESIGN APPROVED — TESTER ACTIVE / TEST SPEC REVISION` | Audio `audio_m4`固定於`5694ead4ba6be928fdb4df6da7155b214d72bd`；corrected delivery `ca51bce...`，execution `8be3bc0...` / `26f33a3...`，Core intake `be19b70...`。`IR_review_M4A_I` 已 Resolved 並明確核准完整 M4a scope。交接順序：目前由 Tester 修訂 `test_spec_M4.md` 並將 `TR_spec_M4_I` 改為 `Revised`，等待 Designer 最終簽核 → Developer WP-09～13。real M4a+M4b resource row仍等待Accepted LLM input |
| M4b LLM | `GATE 1 R5 PLATFORM-CONFIG REVISION AUTHORIZED — REAL EXECUTION BLOCKED` | 已複驗`llm` / `341ccc012d87847fed1d3a68e5ef7cc68eb872ba`的`M2-G1-PLATFORM-CONFIG-001`：R4 candidate只有單一config，無法同時驗證x86與Pi strict identity。`DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001`接受finding並授權Gate 1-owned R5 platform-keyed config/schema/lock/runner regression；frozen M1 protected paths不得修改。R5 exact-SHA intake前不得發行candidate manifest或跑真實x86/Pi；Gate 2A/2B及017整合診斷邊界不變 |
| M4c Session Display | `PENDING` | 依賴 M4a + M4b；Display content / privacy design 已在 `display_spec.md` |

### M4a Audio Contract Relay Flow（2026-08-17 修訂）

```
Core Designer (contract owner) [DELIVERY-AUDIO-POC-M4A-CONTRACT-001]
  → committed delivery直接交付Audio POC Team
    Gate 1A: POC committed plan 5d4086d... → Core planning ACK（D01～D05 accepted）
    Gate 1B revision: ACK-003授權M2A/M2B comparative funnel
    M2A: low-cost baseline + Common Voice sanity → scorecard / shortlist（無Pass/Fail）
    M2B: shortlist單變因優化 → primary / fallback exact recipe
      → Core provisional selection（放行candidate-specific provisional integration）
    Gate 2A: Audio M3 target/HAL P1~P12 qualification
    Gate 2B: POC internal M4 → POC Accepted final handoff + conformance kit
    Gate 3: Core product inheritance / delta mapping → Core Tester exact-SHA 驗收
```

Revision response：`docs/outsource/responses/PM-OUT-260817-016-m4a-poc-core-evidence-handoff.md`；final intake：`docs/outsource/responses/RESP-AUDIO-M4-GATE2B-001.md`。016與019維持Resolved / archived；Audio POC downstream已由`audio_m4`完成，Core後續只由Gate 3 product design / test / delivery追蹤，不重開原handoff。

### M4b LLM Contract Relay Flow（2026-08-17 修訂）

```
Core Designer (contract owner) [DELIVERY-LLM-POC-M4B-CONTRACT-001]
  → User / PM relay revised contract → LLM POC Team
    Gate 0: POC 回交 revision receipt + initial manifest + committed planning packet
    Gate 1 R4: x86 full pre-screen + Pi compatibility packet（歷史接受；config identity finding後不得真實執行）
      → Gate 1 R5: platform-keyed config/acquisition identity + frozen runner/lock regression
        → Core R5 exact-SHA intake後，才可依環境／operator授權進行candidate manifest與真實Gate 1 run
          → authenticated x86 pre-screen + 最多兩名Pi compatibility → Core Gate 1 finalist ACK
    Gate 2A: LLM-only P1~P8 / P10A / P11 / P12 → provisional finalist ACK
    Gate 2B: Accepted Audio reference + P9 / P10B combined → final winner ACK
    Gate 3: Core product implementation → Core Tester exact-SHA 驗收
```

Revision response：`docs/outsource/responses/PM-OUT-260817-015-llm-poc-contract-plan-review.md`；Gate 0 R2維持接受。最新Gate 1 scope ACK為`docs/outsource/deliveries/DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001.md`；R5 repository revision待POC回交，真實Gate 1尚未開始。017仍只作Core test-stage preflight，不作Pi Gate 2A的獨立授權Gate。

---

## ALPHA / BETA Gate Forward Planning

依 `PM-OUT-260814-012` (`OUT-ROADMAP-2026-001`) 新增。ALPHA 與 BETA 為產品成熟度 Gate，不是功能 milestone，分別分開記錄。

| Gate | 狀態 | 阻擋 / 備註 |
| :--- | :--- | :--- |
| ALPHA Design Ready | `PENDING` | 阻擋：M4 Accepted；需 Tester 完成 `test_spec_ALPHA.md` 並由 Designer 簽核（`TR_spec_ALPHA_I`） |
| ALPHA Accepted | `PENDING` | 阻擋：ALPHA Design Ready；Tester 驗收 + Designer CR；ALPHA Accepted 是 M5 entry 唯一 baseline SHA |
| BETA Design Ready | `PENDING` | 阻擋：M7 Accepted 且 ALPHA Accepted；需 Tester 完成 `test_spec_BETA.md` 並由 Designer 簽核（`TR_spec_BETA_I`） |
| BETA Accepted | `PENDING` | 阻擋：BETA Design Ready；Tester 對同一 Beta 候選 SHA 重跑 M4 ~ M7 regression + Designer CR |

### Architecture Change Declaration

依 `PM-OUT-260814-012` 要求，針對 ALPHA / BETA gate 新增：

| 項目 | 結論 | 理由 |
| :--- | :--- | :--- |
| systemd / supervisor | **不引入** | 操作部署外部獨立處理；不在 Core 文件範圍 |
| deployment / persistent config | **不引入** | ALPHA 固定化只記錄文件與 manifest，不實作新 deployment 機制 |
| process ownership | **無變更** | 沿用 `arch.md` 現有定義，ALPHA/BETA 不新增 process 角色 |
| update / rollback | **不引入** | 外部獨立處理 |

**Architecture change: No**（`PM-OUT-260814-012` `OUT-ROADMAP-2026-001` 聲明）

## 下一動作順序

1. ~~Reviewer 複審 `IR_review_III` 與 `MR_review_II`~~ — **Done**（`IR_review_III`、`MR_review_II` 已 Resolved）
2. ~~POC Display 回交 v0.3，處理 D1–D5~~ — **Done**（stage-exit `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40`）
3. ~~Designer 複審 Display v0.3 → Accepted~~ — **Done**（`DELIVERY-005-poc_display-m3-v0.3-ack`）
4. ~~Designer 彙整 M3 Design Ready conclusion~~ — **Done**（本 commit；gate 解除）
5. ~~Tester 產出 `test_spec_M3.md`；Designer coverage sign-off~~ — **Done**（`TR_spec_M3_I` Resolved；Development Ready approved）
6. ~~取得 USER commit 同意後建立 PM-009 單一候選 commit，回傳完整 40-character HEAD 完成 external exact-SHA intake。~~ — **Done**
7. ~~Developer建立／更新`dev_progress_M3.md`：Display、Camera、GPIO、Audio Protocol / mock/null / schema / fake seam列Ready；Audio real backend與dependency lock列`Blocked by Audio P4`。~~ — **Done**
8. ~~Audio POC依`DELIVERY-AUDIO-POC-M3-VALIDATION-001`回交完整source SHA與evidence；Core Designer審核並另發final selection ACK後，Developer才開始Audio real package。~~ — **Done**（`DELIVERY-AUDIO-POC-M3-P4-ACK-004`）
9. ~~M3 delivery前由Core完成Audio Option A implementation / Pi evidence與Display artifact / fixture / performance evidence。~~ — **Done**（47/47 Test IDs；Accepted implementation SHA `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`）
10. ~~USER核准transition direct review；Designer核對固定SHA的20張target cards、人工觀察與portable regression。~~ — **Done**（不再次freeze；兩批debug run限制已揭露並接受）
11. ~~Designer完成最終Code/Test Review（CR_M3_I）。~~ — **Done**（CR-M3-001～006全部Pass；M3 Accepted）
