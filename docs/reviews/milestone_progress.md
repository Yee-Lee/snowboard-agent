# Milestone Progress

本文件由 **Designer** 維護，記錄 milestone 定案 gate、跨角色阻擋、外部 POC 相依與下一動作。穩定範圍及驗收原則以 `docs/milestone.md`、`docs/milestones/M{x}.md` 為準；Developer 估點與工作包由 `docs/reviews/dev_progress_M{x}.md` 維護。

* **Current milestone**: M3
* **M3 gate status**: `Not Ready`
* **Last updated**: 2026-08-09
* **Owner**: Designer

---

## M3 Design / Development Gate

### 結論

M3 尚未放行 Developer 拆包或任何 M3 產品實作。外部 POC contract readiness 目前只被 Display 阻擋；Audio 已可作設計輸入，LLM 不屬 M3 gate。團隊不先開 Audio-only、Camera-only、GPIO-only 或其他部分工作包；Display contract 收斂後，仍須完成 Core `display_spec.md` Baseline、整體 M3 Design Ready、M3 test spec 與 Designer 覆蓋簽核，才交由 Developer 建立 `dev_progress_M3.md` 並正式開始 M3。

### Gate matrix

| Gate | 狀態 | 證據 / 依據 | Owner / 下一動作 |
| :--- | :--- | :--- | :--- |
| M2 acceptance | `PASS` | PM handoff `PM-OUT-260807-006-m2-tester-verification` 已 Resolved | Core Team；無動作 |
| Audio POC design input | `ACCEPTED WITH CONDITIONS` | `docs/outsource/references/poc_audio/audio_m3_contract_v1.0.md`；`DELIVERY-AUDIO-POC-M3-ACK-001` | 可供 Designer / Tester 準備整合設計；Developer 不得在 Display 與整體 M3 gate 放行前先行實作。POC Audio 在 M3 delivery SHA 前完成 P1/P2；P3 TTS winner format 延至 M4，不阻擋 M3 |
| Display POC design input | `BLOCKED` | v0.2；`DELIVERY-004-poc_display-m3-v0.2-review` 的 D1–D5 | POC Display 回交 v0.3 disposition、修訂 contract/header/fixture/evidence；Designer 複審 |
| LLM POC input | `N/A FOR M3` | `docs/milestones/M3.md` §5.3 排除真實 LLM | 不等待 LLM；轉列 M4 / M4b entry blocker |
| Core Display Baseline | `MISSING` | `docs/display_spec.md` 尚未產出 | Designer 待 Display contract 收斂後完成 Baseline profile，並同步檢查 Ch 2a / Ch 8 / Ch 10 |
| M3 Design Ready | `BLOCKED` | Display input與 Display Baseline 未完成 | Designer 在同一 gate 確認 arch / implement / milestone / profile 一致且無開發阻擋 TBD |
| M3 test spec / coverage sign-off | `PENDING` | Design Ready 後才可撰寫 `docs/test_spec/test_spec_M3.md` | Tester 撰寫；Designer 以 `TR_spec_M3` 確認 100% 覆蓋 |
| `dev_progress_M3.md` / 工作包 | `NOT CREATED` | Developer-owned；不得早於 test spec 簽核 | Developer 在 gate 放行後估點拆包，引用下列 POC baseline 欄位 |
| M3 target-device acceptance | `PENDING` | `docs/milestones/M3.md` §5.4；`OUT-M3-TEST-2026-001` | Tester 對 delivery exact SHA 獨立驗收；POC 自驗只作外部 evidence layer |

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

任何工作包若依賴尚未 Accepted 的 Display contract、未定位的 binary、未知 license、branch HEAD 或只有「畫面可見／不 crash」的 POC 自驗，狀態必須保持 `Blocked`；Developer 不得自行補寫 HAL/ABI/fixture 語意。

---

## M4 / LLM Forward Gate

LLM POC contract 不阻擋 M3。它是 M4 / M4b 開發進場條件：M3 Accepted 後，仍須完成 `docs/model_spec.md` 的 M4 baseline與已 review 的 `docs/protocol.md` LiteRT-LM child schema，才能拆 M4 工作包。目前 LLM POC input 尚未收到，狀態為 `BLOCKED FOR M4`。

---

## 下一動作順序

1. POC Display 依 `DELIVERY-004-poc_display-m3-v0.2-review` 回交 v0.3，處理 D1–D5。
2. Designer 複審 Display v0.3；通過後記錄 Accepted design input 與 adoption ACK。
3. Designer 完成 `display_spec.md` Baseline，並在單一 M3 Design Ready gate 核對 arch / implement / milestone / profile。
4. Tester 產出 `test_spec_M3.md`；Designer 以 `TR_spec_M3` 簽核覆蓋。
5. Developer 建立 `dev_progress_M3.md`，依已採用 Audio / Display baseline 估點拆包後才開始實作。
6. M3 delivery 前收齊 Audio P1/P2 與 Display artifact/fixture/performance evidence，再由 Tester 對 exact SHA 驗收。
