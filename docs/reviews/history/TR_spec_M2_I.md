---
requestor: "Designer"
owner: "Tester"
status: "Resolved"
---

# TR_spec_M2 ── Designer 對 test_spec_M2.md 的涵蓋率審查

> **審查對象**：`docs/test_spec/test_spec_M2.md`
> **審查依據**：`implement/ch02a_core_hal.md`、`implement/ch02b_workers.md`、`implement/ch07_external_message.md`、`implement/ch09_action_payload.md`、`arch.md`、`milestones/M2.md` §4
> **目的**：確認 Tester 撰寫的 M2 test spec **100% 涵蓋設計範圍**，簽核後進入 [D] 開發階段

---

## 1. 審查方法

作為設計文件的 Owner，Designer 從設計端出發驗證：

1. **milestones/M2.md §4.4「自動化驗收至少證明」** 的每一條是否都有對應 Test ID。
2. **Ch 7 §11 / Ch 9 §11 的全部編號測試項** 是否逐條映射至 test_spec_M2 的 Test ID。
3. **Ch 2a / Ch 2b 的行為契約**（無 §11 編號測試，但有明確 acceptance criteria）是否被 HAL / WRK 測項覆蓋。
4. 測試範圍是否嚴格限於 `milestone.md` §4.1 範圍與 §4.3 排除項目內。

---

## 2. milestones/M2.md §4.4 驗收條件對照

| # | milestones/M2.md §4.4 驗收項 | 對應 Test ID | 涵蓋 |
| :--- | :--- | :--- | :--- |
| 1 | 兩種 session 依序 IDLE→WAKE→PERCEPTION→THINK→ACTION，rest 後回 IDLE | M2-FLOW-001, M2-FLOW-002 | ✅ |
| 2 | 每 operation 恰走 normal/P5/exception/cancel 一條路徑，無重複 terminal Fact | M2-WRK-001 | ✅ |
| 3 | speak/tool duplicate next_perceptions 去重只啟動一個 worker；rest 忽略 | M2-FLOW-003 | ✅ |
| 4 | Interrupt 在 _TaskCompleted 未消費時不提早回 IDLE | M2-FLOW-006 | ✅ |
| 5 | read window begin/consume/close race 不遺失訊息；rest flush-to-wake、error/interrupt/shutdown discard | M2-MSG-002, M2-FLOW-006 | ✅ |
| 6 | mock force_abort() 純 asyncio completion proof 且不留 task | M2-WRK-001 | ✅ |
| 7 | default mock 不需 Pi 套件/網路/模型/credential | M2-FLOW-008 | ✅ |

**結論**：milestones/M2.md §4.4 全 7 條驗收項均已對應。

---

## 3. Ch 7 §11 驗收測試逐項對照

| §11 # | 設計測試項 | 對應 Test ID | 涵蓋 |
| :--- | :--- | :--- | :--- |
| 1 | ingest 先存再 publish，ID UUIDv4 | M2-MSG-001 | ✅ |
| 2 | 空 text / 非 JSON metadata 存前拒絕 | M2-MSG-001 | ✅ |
| 3 | 多訊息 arrival order 跨狀態保持 | M2-MSG-001 | ✅ |
| 4 | begin_read 原子移動指定 session items | M2-MSG-002 | ✅ |
| 5 | pending_ids 只回 metadata 不暴露 payload | M2-MSG-001 | ✅ |
| 6 | consume_for_read 原子刪除 + close，最多一次 | M2-MSG-002 | ✅ |
| 7 | timeout 關 window 還原 pending | M2-MSG-002 | ✅ |
| 8 | drop-oldest 不淘汰 turn-owned，退化 drop-newest | M2-MSG-004 | ✅ |
| 9 | drop-newest / reject 不分 ID 不 publish | M2-MSG-004 | ✅ |
| 10 | stale ID 與跨 session 重新指派可區分 | M2-MSG-001 | ✅ |
| 11 | flush 重設 ownership 按 arrival 重發原 ID | M2-MSG-005 | ✅ |

**結論**：Ch 7 §11 全 11 項均已對應。

---

## 4. Ch 9 §11 驗收測試逐項對照

| §11 # | 設計測試項 | 對應 Test ID | 涵蓋 |
| :--- | :--- | :--- | :--- |
| 1 | speak 只接受唯一非空 text | M2-PAY-001 | ✅ |
| 2 | speak 未知欄位 / 非 str / 空白拒絕且不 mutation | M2-PAY-001 | ✅ |
| 3 | tool envelope exact keys、dotted name、arguments object | M2-PAY-001 | ✅ |
| 4 | unknown tool 在 handler 前拒絕 | M2-PAY-002 | ✅ |
| 5 | validator 同步且不 dispatch | M2-PAY-002 | ✅ |
| 6 | rest 只接受 empty dict | M2-PAY-001 | ✅ |
| 7 | JSON validator 拒絕 bytes / tuple / NaN / 深層 | M2-PAY-001 | ✅ |
| 8 | duplicate / seal 後 register 失敗 | M2-PAY-002 | ✅ |
| 9 | schemas 排序且不暴露 handler / control | M2-PAY-002 | ✅ |
| 10 | schemas defensive copy 不污染 | M2-PAY-002 | ✅ |
| 11 | Reasoner 與 SM 同 payload 同結果 | M2-PAY-001 | ✅ |
| 12 | error 不含 payload / secret | M2-PAY-001 | ✅ |
| 13 | SM invalid kind/payload → ReasonerContractViolation → ERROR，不 ErrorOccurred | M2-FLOW-005 | ✅ |
| 14 | next_perceptions unknown kind 剔除 + WARNING | M2-FLOW-003 | ✅ |
| 15 | duplicate 去重保留首次順序，只啟一個 worker | M2-FLOW-003 | ✅ |

**結論**：Ch 9 §11 全 15 項均已對應。

---

## 5. Ch 2a / Ch 2b 行為契約涵蓋

Ch 2a 與 Ch 2b 無 §11 編號測試，但各節定義了明確的 acceptance criteria。以下確認關鍵設計意圖是否被覆蓋：

### 5.1 Ch 2a ── HAL 契約

| 設計意圖 | 對應 Test ID | 涵蓋 |
| :--- | :--- | :--- |
| Factory lazy import 不觸發 Pi-only 載入 | M2-HAL-001 | ✅ |
| Null lifecycle no-op、stop 冪等 | M2-HAL-002 | ✅ |
| AudioInput 同 process 第二 iterator 拒絕、aclose 後可重開 | M2-HAL-002 | ✅ |
| NullAudioOutput 完整消費 iterator | M2-HAL-002 | ✅ |
| NullDisplay size (0,0)、write_pixels buffer 長度驗證 | M2-HAL-002, M2-HAL-004 | ✅ |
| NullCamera 各格式長度合法、JPEG 可 decode | M2-HAL-002, M2-HAL-004 | ✅ |
| MockGPIO 一 pin 一 subscriber、debounce、unregister 冪等、output 需 configure | M2-HAL-004 | ✅ |
| GPIO 無 NullGPIO（capability 降級由 RM 處理） | M2-HAL-002 隱含排除 | ✅ |

### 5.2 Ch 2b ── Worker 契約

| 設計意圖 | 對應 Test ID | 涵蓋 |
| :--- | :--- | :--- |
| 單次呼叫不可重入 | M2-WRK-001 | ✅ |
| Normal/P5/exception/cancel 恰一 terminal Fact | M2-WRK-001 | ✅ |
| force_abort 純 asyncio completion proof | M2-WRK-001 | ✅ |
| Listen/Read/Look 成功回正確 kind/text/extra | M2-WRK-002 | ✅ |
| PromptBuilder 固定排序、pending 不含 payload | M2-WRK-003 | ✅ |
| 每次 reason 無隱藏 history | M2-WRK-003 | ✅ |
| P5 fallback 產 speak apology 或 rest | M2-WRK-003 | ✅ |
| Speak/Tool/Rest 行為符合 §4 契約 | M2-WRK-004 | ✅ |

---

## 6. 排除項目合規

| milestones/M2.md §4.3 排除項目 | test_spec 是否越界 | 判定 |
| :--- | :--- | :--- |
| 不安裝或呼叫真實 Pi HAL / ASR / TTS / Vision / LiteRT-LM | 否 | ✅ |
| 不驗證真實音訊品質 / OLED / CSI / GPIO 電氣 | 否 | ✅ |
| 不連接 MQTT broker | 否（MSG 測項用 direct ingest） | ✅ |
| Tool 只用 deterministic fake handler | 是（M2-WRK-004, M2-PAY-002 皆 fake） | ✅ |
| 不建立 wake daemon | 否（mock InputSource 產生 Signal） | ✅ |

---

## 7. 審查結論

### 判定：✅ Resolved — 100% 涵蓋設計範圍，簽核通過

| 驗證維度 | 結果 |
| :--- | :--- |
| milestones/M2.md §4.4 全 7 條驗收項 | ✅ 全數對應 |
| Ch 7 §11 全 11 項設計測試 | ✅ 逐項對應 |
| Ch 9 §11 全 15 項設計測試 | ✅ 逐項對應 |
| Ch 2a HAL 行為契約 | ✅ 關鍵意圖全覆蓋 |
| Ch 2b Worker 行為契約 | ✅ 關鍵意圖全覆蓋 |
| 排除項目合規 | ✅ 未越界 |
| 格式與慣例一致 | ✅ 與 M1 test_spec 一致 |

**Designer 簽核**：`test_spec_M2.md` 已通過 Designer 涵蓋率審查，確認 100% 覆蓋 M2 設計範圍。M2 正式進入 [D] 開發階段，Developer 可於 `docs/reviews/dev_progress_M2.md` 進行 M2 估點拆包並開始撰寫 `src/` 與 `tests/`。

---

## 8. Findings

**Blocking**：無

**Advisory**（不阻擋簽核）：

1. **Test ID 編號不連續**：M2-HAL-003、M2-MSG-003、M2-FLOW-007 缺號。功能涵蓋不受影響，但建議 Tester 於後續維護時補齊或加註說明。此觀察已由 Tester 在其自身審查中同步記錄。
