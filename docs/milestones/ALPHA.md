# ALPHA 規劃 ── Voice-only 產品化收斂 Gate

## 定位

`ALPHA` 是 M4 Accepted 後、M5 開始前的 **產品成熟度 Gate**，而非功能 milestone。它不新增功能，而是對 M4 已驗收的 Voice-only 能力進行產品化收斂，並固定後續開發的 exact-SHA baseline。

> **ALPHA ≠ M4**：M4 Accepted 代表功能通過，ALPHA Accepted 代表 Voice-only 產品化收斂通過。兩者分開記錄，M4 通過不推定 ALPHA 通過。

---

> **與 ALPHA.R1 的關係**：條件式 ASR Product R1 可在本 Gate Accepted 前開立獨立候選線。`ALPHA` 與 `ALPHA.R1` 是兩個完整候選；只有後續 baseline selection 選定的一個 Accepted exact SHA 可進入 M5。見 `docs/milestones/ALPHA_R1.md`。

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
* 使用 M4 Accepted 的完整 Voice-only 路徑執行一次 LLM 品質把關與 POC triggering review；review 不預設調參，也不以主觀偏好改寫已通過的 M4 baseline。
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
| LLM quality disposition | POC triggering review 已完成並記錄 `NO_TRIGGER`、`BACKLOG` 或 `TRIGGER_CHANGE_REQUEST`；不得留有未處置的 Blocking 品質 finding |
| 分開記錄 | `M4 Accepted` 與 `ALPHA Accepted` 各自獨立記錄，不得以前者推定後者 |

### 3.3 LLM 品質把關與 POC triggering review

本 review 在 M4 Accepted 後、ALPHA candidate freeze 前執行。目的不是預先尋找可調參項目，
而是用完整 ASR → LLM → TTS 產品路徑確認是否存在值得啟動獨立 POC 的明確品質問題。

只有同時具備下列輸入，才可提出 POC trigger：

1. 可在受控 case 或 session 重現的具體症狀；
2. 可量化的現況基線與產品影響；
3. 初步 root-cause hypothesis，能區分 ASR、Core integration、prompt / template、context 與 model capability；
4. 預期改善指標、允許變更的 surface，以及獨立的 development / held-out 評估方式。

Review 必須選擇並記錄一個 disposition：

| Disposition | 判讀與後續 |
| :--- | :--- |
| `NO_TRIGGER` | 未發現明確、可重現且值得處理的品質問題；不建立 POC，繼續 ALPHA。 |
| `BACKLOG` | 問題存在但不阻擋 Voice-only ALPHA；記錄限制與後續觸發條件，不在 ALPHA candidate 內調參。 |
| `TRIGGER_CHANGE_REQUEST` | 問題具明確產品影響且需要實驗；先建立 change request，再以既有 repository 的短期 worktree 執行 POC。 |

POC 不得直接在 ALPHA candidate 上進行參數搜尋。若勝出方案改動 model、runtime、prompt、chat
template、PromptBuilder、response schema、token / sampling profile或其他 M4b frozen baseline，必須依
`model_spec.md` 建立新 lock，回到受影響的 M4b / M4 exact-SHA 驗證；通過後才能重新進入 ALPHA。
受控評估不得把 private transcript、prompt或raw model output提交至 Git；evidence 只保存核准的
catalog identity、sanitized metric與disposition。

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
| LLM 品質把關完成，且 POC trigger 有明確、可稽核 disposition | ALPHA §3.3；M4b frozen baseline change policy | `ALPHA-T-008` |

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
* [ ] 完成 LLM quality / POC triggering review，保存 `NO_TRIGGER`、`BACKLOG` 或 `TRIGGER_CHANGE_REQUEST` disposition

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
| LLM quality review disposition / evidence locator | *(待填)* |
| known limits | *(待填)* |

---

## 6. 後置效果

* **M5 entry**：必須先完成 `M5-BASELINE-SELECTION-R1`；若未建立 / 未採用 R1，引用 `ALPHA Accepted exact SHA`；若 User 選定 R1，引用 `ALPHA.R1 Accepted exact SHA`。不得引用 M4 部分結論、同時引用兩個 baseline 或拼接 evidence。
* **Architecture change**：本 Gate 不引入 systemd / supervisor / deployment；若未來需要，須另開 AR_impl 審查並修訂 `arch.md`。

---
