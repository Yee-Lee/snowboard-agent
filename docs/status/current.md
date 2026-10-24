# Current handoff

- Updated: 2026-10-24
- Writer: Designer only
- Current milestone: M5.tool → M5 MQTT → M6 Look
- Current stage: **Developer — M5.tool c2 兩欄模型契約設計與 Test Spec 已對齊**
- Next owner: Developer
- Developer entry: **Open — IR_dev_M5_TOOL_I 已完成 Designer 與 Tester 修訂**
- Working baseline: USER 已接受的原 ALPHA `8b4af53f433c4bcdb5b858973e10767318986554`；
  ALPHA.R1 未 Accepted，見 [M5 §2.2](../milestones/M5.md#22-entry)。

## Exact routing

| Owner | 下一步 | 最小讀取範圍 |
| :--- | :--- | :--- |
| Developer | 依已對齊的 c2 兩欄設計與 Test Spec 完成 M5.tool 收斂並於 Pi 驗證相同待提交內容 | [IR_dev_M5_TOOL_I](../reviews/IR_dev_M5_TOOL_I.md)、[M5 §2](../milestones/M5.md#2-m5tool--工具能力開發與驗證)、[設計 §§2–7](../implement/ch_m5_tool.md#2-固定能力與語意輸出)、[protocol §7](../protocol.md#7-m5tool-llm-protocol-v4)、[Test Spec](../test_spec/test_spec_M5_tool.md) |

## Scope boundary

M5.tool 使用真實 Gemma（c2 兩欄 JSON 輸出）、固定映射 `mock.send("啟用遠端連線")`、
mock Camera／Vision 驗證能力選擇、模型 `tool`/`look` 文字抑制與下一輪物件有據回答
（使用已更新的 Look wrapper `instruction`；否定句依 USER 決定僅保留為診斷歷史，移出本輪測試範圍）。
新 Conversation 首次合法推論保留 `runtime_prefill_tokens <= 128`，並觀察首輪與後續
turn 的實際等待。
M5 再接 MQTT 發送，以及外部 response／主動通知進 buffer／read；外部結果不是
handler return。M6 先用 Camera＋YOLO＋結果整理→原對話 LLM；VLM 描述是獨立 POC。
Wake 在 BETA 前重新評估，read／Look 交錯暫不納入。詳細決策分別見
[M5](../milestones/M5.md) 與 [M6](../milestones/M6.md)。

M4／ALPHA 已交付證據不重開。M5 broker／domain、M6 YOLO 型號與 VLM POC 均不阻擋
M5.tool。`IR_dev_M5_TOOL_I` 已完成設計與 Test Spec 對齊（`TR_spec_M5_TOOL_I` 已結案）；
Developer 已整合兩欄 parser／schema／c2 prompt，正式產品路徑 Pi `FLOW` Verify 尚未完成。
