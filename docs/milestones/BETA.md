# BETA 規劃 ── 全能力產品收斂 Gate

## 定位

`BETA` 是 M7 Accepted 後的 **全能力產品成熟度 Gate**，而非功能 milestone。它在同一 Beta 候選 SHA 重跑 M4 ~ M7 完整 regression，涵蓋所有已實作能力，並完成產品級 manifest、診斷與穩定性收斂。

> **BETA ≠ M7**：M7 Accepted 代表 Display UX 功能通過，BETA Accepted 代表全能力產品化收斂通過。兩者分開記錄，M7 通過不推定 BETA 通過。
>
> **BETA ≠ GA / Production Release**：Beta 是收斂 gate，不等同正式發行；systemd image、OTA 與 release packaging 另案規劃。

---

## 1. 範圍（BETA Scope）

BETA 固定為以下全能力的產品化收斂，必須在同一候選 SHA 全數通過：

### 1.1 納入能力（全能力 regression）

在同一 Beta 候選 SHA 重跑以下所有 milestone 的 regression：

| 來源 | 驗收能力 |
| :--- | :--- |
| M4 (= ALPHA 基礎) | Button、Listen / ASR、Reasoner / LLM、Speak / TTS、M4c Session Display、離線 session |
| M5 | MQTT external message、read 流程、實際 tool dispatch |
| M6 | Voice wake daemon、Vision / look、三種入口完整 session、長時間穩定 |
| M7 | 正式 Display UX、StatusBar、Main、Fullscreen、icons、動畫、OLED 保護 |

### 1.2 固定化要求

* 長時間穩定性：連續多 session / soak，記錄 resource / thermal / failure 統計。
* 診斷：完整 log hygiene（不含 transcript / prompt / raw model output / credential / MQTT password / 完整 message / tool arguments）。
* Artifact / config / model / asset inventory：所有組件版本、來源、授權、checksum 與已知限制，記入 Beta manifest。
* Beta manifest：列出 M4 ~ M7 所有 artifact / model / config / dependency / asset 的最終固定清單。

---

## 2. 排除項目

以下項目**明確排除**：

* 任何 GA / production release 等同語義；BETA 不是正式發行
* systemd image 製作、OTA、release packaging（另案規劃）
* M4 ~ M7 範圍外的新功能或新能力
* 任何需要修改 `arch.md` 但尚未完成 AR_impl 的架構變更

---

## 3. Entry / Exit Gate

### 3.1 Entry（進入 BETA 的前提）

| 條件 | 說明 |
| :--- | :--- |
| M7 Accepted | M7 功能在同一 exact SHA 通過 |
| Test spec 就緒 | Tester 依本文件完成 `docs/test_spec/test_spec_BETA.md`，且 Designer 已審查並簽核（`TR_spec_BETA_I` Resolved） |
| Developer 工作包 | Developer 已提供 BETA 估點與工作包，引用 M7 Accepted exact SHA |
| ALPHA Accepted | ALPHA Gate 已通過，確認 Voice-only 基線可重現 |

### 3.2 Exit（BETA Accepted 條件）

| 條件 | 說明 |
| :--- | :--- |
| M4 ~ M7 regression 全數通過 | 在同一 Beta 候選 SHA 重跑所有 regression，不得有 skip / xfail 掩蓋 |
| Tester 驗收通過 | Tester 依 `test_spec_BETA.md` 對候選 SHA 全數驗收 |
| Designer Code Review | Designer 最終 Code Review 無 Blocking finding（`CR_BETA` 若有則需 Resolved） |
| Exact SHA | BETA Accepted 必須對應單一候選 SHA；不以不同 SHA 拼接通過結論 |
| Beta manifest 完整 | 所有 artifact / model / config / dependency / asset 全數固定並記入 Evidence |
| 分開記錄 | `M7 Accepted` 與 `BETA Accepted` 各自獨立記錄，不得以前者推定後者 |

---

## 4. Requirement Mapping（M7 → BETA trace）

| BETA Requirement | 來源 / 依據 | Future Test ID |
| :--- | :--- | :--- |
| M4 ~ M7 regression 全數通過（同一 SHA） | 各 milestone 驗收契約 | `BETA-T-001` |
| M5 MQTT / tool regression（replay fixture） | M5 驗收契約、`arch.md` Ch 7 | `BETA-T-002` |
| M6 wake / Vision regression（fixture） | M6 驗收契約、`arch.md` Ch 2a/6/8 | `BETA-T-003` |
| M7 Display UX regression（human checklist 含 hardware） | M7 驗收契約、`display_spec.md` | `BETA-T-004` |
| 長時間 soak：連續 session 無 orphan child / 資源洩漏 | M6 §8.4 要求延伸、BETA 穩定性 | `BETA-T-005` |
| log 不含任何敏感內容（全 M4 ~ M7 範圍） | Privacy 要求、`arch.md` | `BETA-T-006` |
| Beta manifest：全組件版本 / 授權 / checksum 固定 | BETA 固定化要求 | `BETA-T-007` |

> Test ID 為規劃佔位，Tester 建立 `test_spec_BETA.md` 時對應補全。

---

## 5. 可重複驗收

### 5.1 自動化

在 Raspberry Pi 5 執行：

```bash
python -m pytest -v
python -m pytest -v -m rpi tests/milestones/test_beta_full_regression.py
```

### 5.2 人工 Checklist（於同一候選 SHA 執行）

* [ ] 重跑 M4 ~ M7 所有 rpi-marked 測試，無 skip / xfail
* [ ] 連續 session soak，記錄 thermal / memory / resource
* [ ] 刻意觸發各層 failure（ASR、LLM、TTS、MQTT、wake、Vision、Display），確認各自 recovery 路徑
* [ ] 正常關機 / 異常關機，確認無 orphan child / daemon、無殘留 fullscreen owner
* [ ] 審核全 log：確認不含任何敏感內容
* [ ] Beta manifest 逐項對照 artifact / model / asset 版本與 checksum

### 5.3 Evidence Index（BETA Accepted 時填入）

| 項目 | SHA / 版本 / 路徑 |
| :--- | :--- |
| Beta 候選產品 SHA | *(待填)* |
| M4 regression log | *(待填)* |
| M5 regression log | *(待填)* |
| M6 regression log | *(待填)* |
| M7 regression log + human checklist | *(待填)* |
| soak 測試記錄 | *(待填)* |
| Beta manifest 路徑 | *(待填)* |
| known limits | *(待填)* |

---

## 6. 後置效果

* BETA Accepted 代表本專案全能力產品收斂完成。
* 正式 GA / 發行、systemd image、OTA 等後續行動，另開規劃，不以 BETA 通過直接授權。

---
