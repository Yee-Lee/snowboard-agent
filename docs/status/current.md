# Current handoff

- Updated: 2026-10-27
- Writer: Designer only
- Current milestone: M5 MQTT → M6 Look
- Current stage: **M5 MQTT Verify PASS（Accepted）— 32 字 wire/read 契約、Pi 自動／Gemma 與 USER 已驗產品場景均通過；證據見 [`test_spec_M5_mqtt.md` §9](../test_spec/test_spec_M5_mqtt.md)**
- Next owner: Designer（M6 Look 階段路由）
- Developer entry: **Complete — 開發交付見 [`development.md`](development.md)；M5 MQTT Verify 已完成**
- Verified baseline: `8a64165b142942219679960277e03989cc99657b` 加上 Pi checkout `m5mqtt-formal-verify-20261027-01` 驗收的 M5 MQTT 變更。

## Exact routing

| Owner | 下一步 | 最小讀取範圍 |
| :--- | :--- | :--- |
| Designer | 依已核准 M6 Look 階段輸入安排下一個 Design 工作包；M5 MQTT 驗收證據保持可定位，commit／push 另依 Git 規則處理 | [M6](../milestones/M6.md)、[`test_spec_M5_mqtt.md` §9](../test_spec/test_spec_M5_mqtt.md) |

## Scope boundary

M5.tool 已於 2026-10-25 完成 final Verify **PASS**（Accepted）：真實 Gemma c2 兩欄 JSON 輸出、
固定映射 `mock.send("啟用遠端連線")`、模型 `tool`/`look` 文字抑制、物件觀察有據回答
（使用經 Pi 驗證的 Look wrapper `instruction`；否定句依 USER 決定僅保留為診斷歷史）、新 Conversation
首輪 `runtime_prefill_tokens <= 128`，以及 `TR_dev_M5_TOOL_I` B1/B2 修正（WIP `108264c420fb4ed020e517a8dc64c625da373e81`，
Pi Run `m5tool-repair-verify-20261025-cGrEVf` targeted 32/32 Pass、affected regression 122/122 Pass）均已驗收通過。

已驗收的 **M5 MQTT** 將派發能力接到真實 MQTT 發送，並將外部 response／主動通知經
buffer／read 納入對話（外部結果不是 handler return）。local send 成功只觸發既有固定「已送出。」；
專案 local-test peer 預設 `empty`，另提供 success／failure／duplicate／malformed 與 notification 測試模式，
正式目標由明確配置取代且失敗時不 fallback。M6 先用 Camera＋YOLO＋結果整理→原對話 LLM；
VLM 描述是獨立 POC。Wake 在 BETA 前重新評估，read／Look 交錯暫不納入。詳細決策分別見
[M5](../milestones/M5.md) 與 [M6](../milestones/M6.md)。

M5 MQTT 已確認 active-session external message 不打斷 current operation；下一個 eligible listen boundary
強制 read-only，且不另播 spoken preamble。[AR_impl_M5_MQTT_I](../reviews/history/AR_impl_M5_MQTT_I.md)
與 [`TR_spec_M5_MQTT_I`](../reviews/history/TR_spec_M5_MQTT_I.md) 均已 Resolved；[`test_spec_M5_mqtt.md`](../test_spec/test_spec_M5_mqtt.md)
已完成 32 字修訂，[`IR_dev_M5_MQTT_I`](../reviews/history/IR_dev_M5_MQTT_I.md) 已 Resolved。
Developer 交付後已完成 Verify PASS；M4／ALPHA 與 M5.tool 已 Accepted 的證據不重開。
