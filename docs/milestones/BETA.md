# BETA 規劃 ── 已納入能力的產品收斂 Gate

## 定位

`BETA` 是 M7 Accepted 後的**已納入能力產品成熟度 Gate**，而非功能 milestone。
它對當時產品實際納入的能力做必要整合、穩定性與診斷收斂；Wake 是否納入須在
BETA 設計前決定，不因舊規劃文字自動成為必做功能。

> **BETA ≠ M7**：M7 Accepted 代表 Display UX 功能通過，BETA Accepted 代表已納入能力的產品化收斂通過。兩者分開記錄，M7 通過不推定 BETA 通過。
>
> **BETA ≠ GA / Production Release**：Beta 是收斂 gate，不等同正式發行；systemd image、OTA 與 release packaging 另案規劃。

---

## 1. 範圍（BETA Scope）

BETA 覆蓋當時已納入的能力；測試依具體產品失敗風險選擇，在相同待提交內容上完成：

### 1.1 納入能力

| 來源 | 驗收能力 |
| :--- | :--- |
| M4 (= ALPHA 基礎) | Button、Listen / ASR、Reasoner / LLM、Speak / TTS、M4c Session Display、離線 session |
| M5.tool + M5 | 真實模型能力選擇、固定派發回饋、MQTT 發送與外部訊息 read 流程 |
| M6 | Camera / YOLO / 結果整理與 look 接續回答；若 BETA 前決定加入 Wake，才納入 wake daemon 與第三入口 |
| M7 | 正式 Display UX、StatusBar、Main、Fullscreen、icons、動畫、OLED 保護 |

### 1.2 固定化要求

* 穩定性：依實際失敗風險設定連續多 session 情境，記錄相關 resource / thermal / failure 統計。
* 診斷：完整 log hygiene（不含 transcript / prompt / raw model output / credential / MQTT password / 完整 message / tool arguments）。
* Beta inventory：記錄已納入組件的版本、來源、授權與已知限制。必要內容核對由 operator
  在明確移轉或問題診斷邊界獨立執行，不作為 startup 或每個測項的 checksum 斷言。
* Startup readiness：M6 先保留 Resource Manager 循序啟動，YOLO26s 單次 warm-up 完成後才使
  Vision READY；這會增加整體 App READY 等待，是已知待收斂議題。BETA 以正式 App 在 Pi 的
  啟動時間線比較「維持循序」、「受控平行初始化」及「App READY 後背景完成 Vision READY」；
  同時觀察 process start→IDLE、各 required resource READY、首個一般 turn、首個 Look、memory、
  thermal 與 startup failure rollback。只在確實縮短使用者等待，且不把冷啟動偷移到第一個
  Look、不暫時宣告不可用能力為可用、也不破壞 deterministic cleanup 時採用變更。需要修改
  lifecycle 或 startup-static capability map 時，須先完成對應架構修訂；BETA 規劃本身不預選方案。

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
| M7 Accepted | M7 功能已完成驗收，結果可定位 |
| Test spec 就緒 | Tester 依當時已納入能力與實際風險完成 `docs/test_spec/test_spec_BETA.md` |
| Developer 工作包 | Developer 已提供 BETA 估點與工作包，說明沿用的 M7 基礎與直接變更 |
| ALPHA Accepted | ALPHA Gate 已通過，確認 Voice-only 基線可重現 |

### 3.2 Exit（BETA Accepted 條件）

| 條件 | 說明 |
| :--- | :--- |
| 適用驗證通過 | 對新增整合與直接影響的 regression、硬體及人工情境，在 Pi 以相同待提交內容完成驗證；不得以 skip / xfail 掩蓋適用失敗 |
| Tester 驗收通過 | Tester 依 `test_spec_BETA.md` 對候選內容完成驗收 |
| 相同內容 | BETA Accepted 對應單一已驗證產品內容，不拼接不同候選的結論 |
| Inventory 完整 | 已納入組件的版本、來源、授權與已知限制已記錄 |
| 分開記錄 | `M7 Accepted` 與 `BETA Accepted` 各自獨立記錄，不得以前者推定後者 |

---

## 4. Requirement Mapping（M7 → BETA trace）

| BETA Requirement | 來源 / 依據 | Future Test ID |
| :--- | :--- | :--- |
| 已納入能力的必要整合與直接影響 regression | 各 milestone 驗收契約與實際變更風險 | `BETA-T-001` |
| M5.tool / M5 能力、MQTT / read regression | M5 驗收契約、`arch.md` | `BETA-T-002` |
| M6 Look / Vision regression與 startup readiness 比較；Wake 只在 BETA 前決定納入時涵蓋 | M6 驗收契約、YOLO warm-up 已知議題與 Wake 決策 | `BETA-T-003` |
| M7 Display UX regression（human checklist 含 hardware） | M7 驗收契約、`display_spec.md` | `BETA-T-004` |
| 依實際風險選定的連續 session 與資源釋放 | BETA 穩定性 | `BETA-T-005` |
| log 不含任何敏感內容（全 M4 ~ M7 範圍） | Privacy 要求、`arch.md` | `BETA-T-006` |

> Test ID 為規劃佔位，Tester 建立 `test_spec_BETA.md` 時對應補全。

---

## 5. 可重複驗收

### 5.1 自動化

Tester 依當時新增整合與直接影響風險指定命令及人工情境；在 Raspberry Pi 5 對
相同待提交內容完成適用自動、整合、硬體及人工驗證。

### 5.2 人工 Checklist（於相同待提交內容執行）

* [ ] 執行當時 Test Spec 選定的已納入能力整合與直接影響回歸，無 skip / xfail 掩蓋
* [ ] 執行選定的連續 session 情境，記錄相關 thermal / memory / resource
* [ ] 針對新增整合中實際可能發生的 failure 驗證 recovery；Wake 僅在已決定納入時檢查
* [ ] 正常關機 / 異常關機，確認無 orphan child / daemon、無殘留 fullscreen owner
* [ ] 記錄正式 App startup 與首個一般 turn／Look 時間線；依 §1.2 比較適用 readiness 方案並保留現行循序基準
* [ ] 審核全 log：確認不含任何敏感內容
* [ ] Beta inventory 記錄已納入組件的版本、來源、授權與已知限制

### 5.3 Evidence Index（BETA Accepted 時填入）

| 項目 | 結果 / 版本 / 路徑 |
| :--- | :--- |
| Beta 已驗證內容定位 | *(待填)* |
| 適用自動與整合驗證 | *(待填)* |
| 適用硬體與人工判讀 | *(待填)* |
| 連續 session 記錄（若選用） | *(待填)* |
| Beta inventory 路徑 | *(待填)* |
| known limits | *(待填)* |

---

## 6. 後置效果

* BETA Accepted 代表當時已納入能力的產品收斂完成。
* 正式 GA / 發行、systemd image、OTA 等後續行動，另開規劃，不以 BETA 通過直接授權。

---
