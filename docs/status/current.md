# Current handoff

- Updated: 2026-10-25
- Writer: Designer only
- Current milestone: M5 MQTT → M6 Look
- Current stage: **M5 MQTT Design — architecture delta Resolved；external wrapper native POC 待執行**
- Next owner: Designer
- Developer entry: **Closed — M5.tool 已完成 final Verify PASS；M5 MQTT 設計與 Test Spec 尚未開啟**
- Working baseline: `e9cef60ea5d169bbae3b74caf1dbe707803fca28`（已 push；其中 source/test Verified snapshot 為 `108264c420fb4ed020e517a8dc64c625da373e81`，Pi Run `m5tool-repair-verify-20261025-cGrEVf`）。

## Exact routing

| Owner | 下一步 | 最小讀取範圍 |
| :--- | :--- | :--- |
| Designer | 執行真實 Gemma external wrapper native POC，固定 prompt disposition與batch/text上限；再完成 MQTT wire/config並交 Test Spec | [M5 MQTT 設計 §5](../implement/ch_m5_mqtt.md#5-external-message--read--think)、[M5 MQTT §7](../implement/ch_m5_mqtt.md#7-test-spec-交付準備)、[AR_impl_M5_MQTT_I](../reviews/history/AR_impl_M5_MQTT_I.md) |

## Scope boundary

M5.tool 已於 2026-10-25 完成 final Verify **PASS**（Accepted）：真實 Gemma c2 兩欄 JSON 輸出、
固定映射 `mock.send("啟用遠端連線")`、模型 `tool`/`look` 文字抑制、物件觀察有據回答
（使用經 Pi 驗證的 Look wrapper `instruction`；否定句依 USER 決定僅保留為診斷歷史）、新 Conversation
首輪 `runtime_prefill_tokens <= 128`，以及 `TR_dev_M5_TOOL_I` B1/B2 修正（WIP `108264c420fb4ed020e517a8dc64c625da373e81`，
Pi Run `m5tool-repair-verify-20261025-cGrEVf` targeted 32/32 Pass、affected regression 122/122 Pass）均已驗收通過。

目前 **M5 MQTT Design** 將已驗證的派發能力接到真實 MQTT 發送，並將外部 response／主動通知經
buffer／read 納入對話（外部結果不是 handler return）。local send 成功只觸發既有固定「已送出。」；
專案 local-test peer 預設 `empty`，另提供 success／failure／duplicate／malformed 與 notification 測試模式，
正式目標由明確配置取代且失敗時不 fallback。M6 先用 Camera＋YOLO＋結果整理→原對話 LLM；
VLM 描述是獨立 POC。Wake 在 BETA 前重新評估，read／Look 交錯暫不納入。詳細決策分別見
[M5](../milestones/M5.md) 與 [M6](../milestones/M6.md)。

M5 MQTT 已確認 active-session external message 不打斷 current operation；下一個 eligible listen boundary
強制 read-only，且不另播 spoken preamble。[AR_impl_M5_MQTT_I](../reviews/history/AR_impl_M5_MQTT_I.md)
已完成 architecture修訂並 Resolved。下一步為 Designer 的 native prompt POC；Developer entry維持關閉。
M4／ALPHA 與 M5.tool 已 Accepted 的證據不重開。
