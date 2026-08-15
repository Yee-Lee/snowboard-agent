# ALPHA 規劃 ── Voice-only 產品化收斂 Gate

## 定位

`ALPHA` 是 M4 Accepted 後、M5 開始前的 **產品成熟度 Gate**，而非功能 milestone。它不新增功能，而是對 M4 已驗收的 Voice-only 能力進行產品化收斂，並固定後續開發的 exact-SHA baseline。

> **ALPHA ≠ M4**：M4 Accepted 代表功能通過，ALPHA Accepted 代表 Voice-only 產品化收斂通過。兩者分開記錄，M4 通過不推定 ALPHA 通過。

---

## 1. 範圍（ALPHA Scope）

ALPHA 固定為以下能力的產品化收斂，必須在同一候選 SHA 全數通過：

### 1.1 納入能力（Voice-only 主線）

* Button 觸發入口
* Listen / ASR 流程
* Reasoner / LLM（LiteRT-LM）推論
* Speak / TTS 播放
* M4c Session Display（狀態、Perception、Tool intent、Error）
* 離線操作（不依賴外部網路連線）

### 1.2 固定化要求

* 固定 hardware revision、config、model、runtime、dependency、license、checksum，全部記入 `ALPHA.md` Evidence 欄位。
* 定義可重現的 session lifecycle（重複 session、soak 測試、failure / recovery / shutdown、resource / thermal 觀察）。
* Privacy：log 不含 transcript、prompt、raw model output、credential 或完整 audio payload。
* Manifest：列出所有 artifact / model / config / dependency 的版本、來源、授權、checksum 與已知限制。

---

## 2. 排除項目

以下項目**明確排除**，不得在 ALPHA 候選 SHA 中引入：

* MQTT / external message / 實際 tool dispatch（屬 M5）
* Voice wake / Vision（屬 M6）
* M7 正式動畫、完整 icons、Progress UI 或生產級 assets
* systemd / supervisor / deployment / persistent config / update / rollback（外部獨立處理，不在本文件範圍）
* 任何 GA / production release 等同語義

---

## 3. Entry / Exit Gate

### 3.1 Entry（進入 ALPHA 的前提）

| 條件 | 說明 |
| :--- | :--- |
| M4 Accepted | M4a + M4b + M4c 在同一 exact SHA 通過；M4 conclusion 已記錄 |
| Test spec 就緒 | Tester 依本文件完成 `docs/test_spec/test_spec_ALPHA.md`，且 Designer 已審查並簽核（`TR_spec_ALPHA_I` Resolved） |
| Developer 工作包 | Developer 已提供 ALPHA 估點與工作包，引用 M4 Accepted exact SHA |
| Manifest 初稿 | hardware / config / model / artifact / dependency inventory 已列出待固定清單 |

### 3.2 Exit（ALPHA Accepted 條件）

| 條件 | 說明 |
| :--- | :--- |
| Tester 驗收通過 | Tester 依 `test_spec_ALPHA.md` 對候選 SHA 全數驗收（含 regression） |
| Designer Code Review | Designer 最終 Code Review 無 Blocking finding（`CR_ALPHA` 若有則需 Resolved） |
| Exact SHA | ALPHA Accepted 必須對應單一候選 SHA；不以不同 SHA 拼接通過結論 |
| Manifest 完整 | 所有 artifact / model / config / dependency 的版本、來源、授權、checksum 已全數固定並記入 Evidence |
| 分開記錄 | `M4 Accepted` 與 `ALPHA Accepted` 各自獨立記錄，不得以前者推定後者 |

---

## 4. Requirement Mapping（M4 → ALPHA trace）

| ALPHA Requirement | 來源 / 依據 | Future Test ID |
| :--- | :--- | :--- |
| Button → Listen → ASR → LLM → TTS → Speak 完整離線 session | M4c 驗收、`arch.md` 主線契約 | `ALPHA-T-001` |
| 重複 session / soak（連續多次不退化） | ALPHA 產品化要求 | `ALPHA-T-002` |
| failure / recovery / shutdown 符合 arch.md 收斂規則 | `arch.md` Level 1/2/3 契約 | `ALPHA-T-003` |
| resource / thermal 在 target-device budget 內 | M4a + M4b resource 要求 | `ALPHA-T-004` |
| log 不含 transcript / prompt / raw model output / credential | Privacy 要求（M4c、`arch.md`） | `ALPHA-T-005` |
| Manifest：artifact / model / config / dependency 全數固定 | ALPHA 固定化要求 | `ALPHA-T-006` |
| Session Display 只呈現已驗證內容，privacy mapping 正確 | `display_spec.md`、M4c | `ALPHA-T-007` |

> Test ID 為規劃佔位，Tester 建立 `test_spec_ALPHA.md` 時對應補全。

---

## 5. 可重複驗收

### 5.1 自動化

在 Raspberry Pi 5 執行：

```bash
python -m pytest -v
python -m pytest -v -m rpi tests/milestones/test_alpha_voice_only.py
```

### 5.2 人工 Checklist（於同一候選 SHA 執行）

* [ ] 重複 N 次完整 session，記錄每次耗時與 resource 使用
* [ ] Soak 測試：連續執行至穩定，記錄 thermal / memory
* [ ] 刻意觸發 failure（ASR 失敗、LLM timeout、TTS 失敗）各一次，確認 recovery 路徑
* [ ] 正常關機 / 異常關機，確認無 orphan child、無殘留 fullscreen owner
* [ ] 審核 log：確認不含 transcript / prompt / raw model output / credential / 完整 audio

### 5.3 Evidence Index（ALPHA Accepted 時填入）

| 項目 | SHA / 版本 / 路徑 |
| :--- | :--- |
| 候選產品 SHA | *(待填)* |
| ASR engine + model + checksum | *(待填)* |
| TTS engine + model + checksum | *(待填)* |
| LiteRT-LM artifact + checksum | *(待填)* |
| hardware revision | *(待填)* |
| config hash | *(待填)* |
| 自動化測試 log 路徑 | *(待填)* |
| 人工 checklist 記錄路徑 | *(待填)* |
| known limits | *(待填)* |

---

## 6. 後置效果

* **M5 entry**：必須引用 `ALPHA Accepted exact SHA`，不得引用 M4 Accepted SHA 或任何部分通過結論。
* **Architecture change**：本 Gate 不引入 systemd / supervisor / deployment；若未來需要，須另開 AR_impl 審查並修訂 `arch.md`。

---
