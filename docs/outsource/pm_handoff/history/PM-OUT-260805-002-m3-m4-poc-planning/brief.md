# Audio / Display / LLM 設計與 POC 接合準備

* **Handoff ID** : `PM-OUT-260805-002-m3-m4-poc-planning`
* **Legacy ID** : `PM-OUT-2026-002-R1`
* **Status** : `Ready for PM`
* **Related Feedback** : `OUT-FB-2026-002-R1`
* **Reference candidate** : `af890249d8634df11b1a30a27aaee1720f5a8b67`

## 結論

請核心開發團隊先完成 Audio、Display、LLM 對現行產品設計與 milestone 的影響盤點，並把 M3、M4a Audio、M4b LLM、M4c Session Display 的範圍與 gate 寫入唯一產品 repo。M4 只有在 M4a / M4b / M4c 全部通過後才 Accepted，M5 必須依賴 Accepted M4 exact SHA。

現階段不得把 POC code 或候選直接視為產品 baseline；各 POC 只有在內部 Accepted 並由 PM 發出後續 OUT-TASK 後，才能進入產品化。本輪只交付完整設計、milestone / progress、requirement mapping、相依與風險，不撰寫 test spec、不拆 development packages，也不提前實作尚未 Accepted 的候選。Design Ready 後才依序進入 test spec、拆包與 code。

## 指定輸入文件

PM 交付本 brief 時，請一併提供下列文件；外包回覆須逐組標明已讀版本與影響範圍。

* **Audio** : `poc_audio/handoff/20260805-1018-audio-poc-guidance/`
* **Display** : `poc_display/handoff/20260805-1022-display-task-split/`
* **LLM** : `poc_llm/handoff/20260805-1032-llm-poc-guidance/`

## 外包必做事項

| ID | Priority | Required action | Acceptance |
| --- | --- | --- | --- |
| `OUT-POC-2026-001` | Blocking | 逐組閱讀指定 POC 文件，建立產品文件、程式模組、milestone、test 與硬體對照 | Response 逐組列出受影響路徑、執行順序、阻擋、風險與待確認決策 |
| `OUT-POC-2026-002` | Blocking | 修訂產品 milestone 與 progress：M3 包含 Audio / Display HAL；M4 拆成 M4a Audio、M4b LLM、M4c Session Display | `docs/milestone.md`、M4 / M5 / M7 planning 與 progress 使用一致相依；M4c 依賴 M4a / M4b，M4 三者全通過才 Accepted，M5 明確依賴 Accepted M4 exact SHA |
| `OUT-POC-2026-003` | High | 依 Audio 核心要求固定 M3 input / output、PCM / VAD / ASR 邊界與 HAL handoff；M4a winner 尚未 Accepted 前不選 model / voice | Ch 2a / 2b / 5 / 10、milestone、Requirement ID 與 test impact 一致；列出 M3 / M4a 設計相依，不提前拆工作包 |
| `OUT-POC-2026-004` | High | Display 規劃拆成 M3 Baseline、M4c Session、M7 Complete；只抽取未來 Accepted 的 native / HAL 元件，不採用 POC Service / queue / IPC / video 架構 | 固定 selected hardware gate；`display_spec.md` 明列三種 profile；Ch 2a / 5 / 8 / 10、NullDisplay、renderer / arbiter、session state/content/lifecycle 與各階段 Pi 驗收觀察一致；M7 只保留完整資產、動畫、全能力 UX 與 polish |
| `OUT-POC-2026-005` | High | 依 LLM 核心要求規劃 M4b：model baseline、persistent child、protocol、P5、history isolation 與 M4a 共同常駐，並提供 M4c 可觀察的 sanitized session output | `model_spec.md` `protocol.md` `Ch 2b / 4 / 5 / 9 / 10 / 11` Reasoner / RM 與 M4c display input 邊界一致；winner 欄位待 Accepted POC，不提前拆工作包 |
| `OUT-POC-2026-006` | Blocking | 維持 POC 與產品化邊界：不得直接複製 POC repo、不得把 branch HEAD 或團隊自驗當 Accepted | 每個未來 integration 工作包都引用 PM 交付的 POC handoff ID、Accepted POC SHA、artifact checksum / license 與尚待產品化項目 |
| `OUT-POC-2026-007` | Blocking | 防止設計、測試與開發拆包次序倒置或失去追溯 | 同一 milestone 的 arch / implement / milestone / profile 文件在單一 Design Ready gate 以 exact SHA 一次確認；通過後才寫 test spec、拆 development packages 與 code；Requirement ID / Test ID 支援最終反向追溯 |

## M4c Session Display 邊界

* M4c 完成 Button 啟動的本機語音 session 顯示：startup、IDLE、WAKE / listen、think、speak、rest、interrupt、error / recovery 與 graceful App shutdown。
* M4c 使用 M3 已驗收的 Display HAL、renderer / arbiter 與 `display_spec.md` Session profile；main text / progress / error 必須 sanitized，Display failure 不阻斷語音主線或改變 exit code。
* M4c 不提前實作 MQTT / Tool、voice wake、Vision 專屬畫面，也不包含 M7 的正式圖示、完整資產、複雜動畫、全能力呈現與 pixel-level polish。
* M4c 拆分本身預期不改變既有 Display module / owner / event / failure 邊界；外包仍須核對 `docs/arch.md` 與 Ch 8。若無需修改，delivery 明確聲明 `Architecture change: No` 及理由；若發現語意缺口，須在同一 Design Ready delivery 修訂並宣告。

## Design Gate 與追溯順序

每個進入開發的 milestone 只設一個整合 Design Ready gate；Architect / 必要 reviewer 的檢查彙整為同一 gate 結論，不按文件建立多個串行 gate。

```
accepted arch / implement / milestone / profile requirements
-> test spec
-> development packages
-> code + tests
-> milestone target-device acceptance
```

最終交付必須可反向追溯：

```
code / test
-> test_spec Test ID
-> implement/design Requirement ID / 章節
-> arch product contract
```

若 test spec 或拆包時發現不可測、矛盾或遺漏，退回同一 Design Ready finding 修訂，不得由 test 或 private implementation 自行發明產品行為。

## 範圍邊界

* 本輪可修改權威設計、milestone、progress、profile、requirement mapping 與 test impact。
* 本輪不撰寫 test spec、不拆 development packages、不修改產品 code / tests；Design Ready 後另依已核准 Requirement ID 執行。
* 本輪不得預選尚未 Accepted 的 runtime、model、voice、panel profile 或私有實作。
* `docs/arch.md` 只有在產品模組邊界改變時才修訂；每次 delivery 都必須聲明是否變更及原因。
* 歷史 `Snowboard/snowboard-agent/` 不是現行產品基線，不作同步或差異 gate。

## 回覆方式

* **Response** : `docs/outsource/responses/OUT-FB-2026-002-R1.md`
* **Delivery** : `docs/outsource/deliveries/<new-delivery-id>.md`
* **Evidence** : `docs/outsource/evidence/<new-delivery-id>/`
* 請提供承載完整設計的 repo commit SHA、comparison baseline、逐項修改定位、Requirement mapping、architecture change 聲明、文件檢查結果、未完成事項與待 PM / 內部團隊決策；PM 拉回後另通知 repo HEAD 完整 SHA。
