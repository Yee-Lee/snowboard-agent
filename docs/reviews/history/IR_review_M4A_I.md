---
requestor: "Reviewer"
owner: "Designer"
status: "Resolved"
---

# M4A Audio Production 設計審查 (IR_review)

## 審查對象與完整核准範圍 (Full Handoff Scope)
- `docs/implement/ch_m4a_audio_production.md` (M4A production design)
- `docs/model_spec.md` (Audio baseline / provenance / license / product commands)
- `docs/protocol.md` (Audio Protocol v1)
- `docs/implement/ch10_config.md` (M4a extension)
*(包含上述文件與 `arch.md`、`docs/milestones/M4.md` 及 `ch02b`、`ch05`、`ch06` 的跨章節一致性確認)*

## 審查結果 (Findings)

### 1. [Blocking] Factory 與 Adapter 建構子簽名不一致，缺乏依賴注入說明
- **權威依據**: `docs/implement/ch_m4a_generic_scaffold.md` §2.2 與 §3.2 規定 Factory 簽名為 `make_asr_adapter(cfg: ASRConfig) -> ASRAdapter`。
- **矛盾前後語意與影響**: `ch_m4a_audio_production.md` §5.1 與 §6.1 要求 adapter constructor 接收 `lock: AudioArtifactLock`。但 §7.2 未說明 `make_asr_adapter` 如何在不改變簽名的情況下提供此 lock。若不釐清，實作時將導致編譯或執行期錯誤，破壞依賴反轉與既有介面。
- **首選修訂方向與最低驗收條件**: 在 §7.2 補充說明：「`make_asr_adapter` 與 `make_tts_adapter` 內部在 `driver` 為 `whispercpp` 或 `sherpa_matcha` 時，應自行讀取 `cfg.artifact_lock_path` 並解析出 `AudioArtifactLock`，再傳入 Adapter 建構子，維持對外 factory 簽名不變」。

### 2. [Blocking] Evidence 目錄權責衝突
- **權威依據**: `docs/roles/workflow.md` §1 目錄與權責映射規定 `docs/outsource/evidence/` 屬於 `[Tester]` 負責。
- **矛盾前後語意與影響**: `ch_m4a_audio_production.md` §10 規定「Developer delivery 建立 `docs/outsource/evidence/<M4-delivery>/m4a/inheritance.json`」。這違反了目錄擁有權，有 Developer 逕行寫入驗收證據的假綠燈風險。
- **首選修訂方向與最低驗收條件**: 修改 §10，規定 Developer 僅負責提供 `inheritance.json` 的產生腳本 (generator) 或模板 (template)（落點於 `scripts/` 或 `tests/`）；最終的 `inheritance.json` 必須由 Tester 在執行 Gate 3 驗收後寫入 `docs/outsource/evidence/`。

### 3. [Advisory] `AdapterError` 捕捉機制確認
- **說明**: §5.2 提及「child明確可恢復錯誤轉AdapterError」。依 `arch.md` P5 降級原則，請 Designer 確認既有的 `Listen` 與 `Speak` worker 已經能正確捕捉 `AdapterError` 並轉為 `PerceptionResult(status="error")`，以避免 Exception 洩漏導致非預期的 `ErrorOccurred` 進入 ERROR 狀態。此項僅為提醒，不阻擋本次審查收斂。

## Designer 修訂回覆（2026-08-26）

### Finding 1 — Revised

- 已於`ch_m4a_audio_production.md` §7.2固定對外factory仍只接收`cfg`。
- real branch由factory讀取`cfg.artifact_lock_path`，以不import native engine的parser驗證並建立`AudioArtifactLock`，再lazy import adapter並以keyword-only `lock`注入。
- lock失敗在child、Audio HAL與work artifact建立前fail closed；`mock`／`null`不讀lock。
- 最低驗收：Developer以factory signature regression及missing/malformed/identity-mismatch lock negative cases證明上述順序，無需修改既有composition caller。

### Finding 2 — Revised

- 已於§10明定Developer只提供`scripts/` generator／template與`tests/`，fast loop僅寫temporary output。
- 正式`docs/outsource/evidence/<M4-delivery>/m4a/inheritance.json`改由Tester在同一candidate完成Gate 3後產生與核對，且Tester為唯一writer。
- 已同步修訂§11 `M4A-WP-13`，移除Developer建立正式inheritance evidence的殘留歧義。
- 最低驗收：Developer regression證明generator不推導branch HEAD、不自行宣告PASS、不寫正式evidence；Tester驗收時再核對same-SHA與locator完整性。

### Advisory 3 — Confirmed, no code change required

- 現行`src/sbd/perception/listen/listener.py`已捕捉`AdapterError`並產出`PerceptionResult("listen", "error", ...)`。
- 現行`src/sbd/action/speak/speaker.py`已捕捉`AdapterError`並產出`ActionCompleted("speak", "error", ...)`。
- 兩者只有非`AdapterError`的unexpected exception才發布`ErrorOccurred`並重新拋出，符合`arch.md` P5；production adapter必須維持以`AdapterError`表示可翻譯失敗。

兩個Blocking finding的主文件及直接影響面均已修訂，請Reviewer複審。Tester在本單`Resolved`且完整M4a handoff scope獲明確核准前仍維持queued；Developer仍等待`TR_spec_M4_I` coverage sign-off。

## Reviewer 最終確認（2026-08-26）

- **Finding 1**: 修訂符合預期，Factory 簽名維持一致且依賴注入流程明確。
- **Finding 2**: 修訂符合預期，確保目錄權責分明，證據產生流程符合安全規範。
- **Finding 3**: 確認已知行為符合架構設計，無需變更。

**結論**: 所有 Blocking 矛盾均已收斂，本設計審查單 (IR_review) 正式通過並結案。上述完整 M4a handoff scope (包含 `model_spec.md`、`protocol.md`、production design 與 `ch10_config.md`) 已確認無矛盾，跨章節一致性審查通過，特此明確核准。文件將移至歷史歸檔。
