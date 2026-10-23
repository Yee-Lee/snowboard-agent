# Current handoff

- Updated: 2026-10-23
- Writer: Designer only
- Current milestone: M5.tool → M5 MQTT → M6 Look
- Current stage: **Developer — M5.tool 設計與 Test Spec 已就緒**
- Next owner: Developer
- Developer entry: **Open — TR_spec_M5_TOOL_I 已 Resolved**
- Working baseline: USER 已接受的原 ALPHA `8b4af53f433c4bcdb5b858973e10767318986554`；
  ALPHA.R1 未 Accepted，見 [M5 §2.2](../milestones/M5.md#22-entry)。

## Exact routing

| Owner | 下一步 | 最小讀取範圍 |
| :--- | :--- | :--- |
| Developer | 依核准設計與 Test Spec 實作 M5.tool，於 Pi 驗證相同待提交內容 | [設計 §7](../implement/ch_m5_tool.md#7-實作路徑與交-test-spec)、[Test Spec](../test_spec/test_spec_M5_tool.md)、[已結案 review](../reviews/history/TR_spec_M5_TOOL_I.md) |

## Scope boundary

M5.tool 使用真實 Gemma、mock.send、mock Camera／Vision 驗證能力選擇與下一輪回答。
新 Conversation 首次合法推論保留 `runtime_prefill_tokens <= 128`，並觀察首輪與後續
turn 的實際等待；若完整能力 prompt 無法符合此限制，回 Designer 修正設計，不能用
未定義的第二 turn 啟用方式直接宣稱通過。
M5 再接 MQTT 發送，以及外部 response／主動通知進 buffer／read；外部結果不是
handler return。M6 先用 Camera＋YOLO＋結果整理→原對話 LLM；VLM 描述是獨立 POC。
Wake 在 BETA 前重新評估，read／Look 交錯暫不納入。詳細決策分別見
[M5](../milestones/M5.md) 與 [M6](../milestones/M6.md)。

M4／ALPHA 已交付證據不重開。M5 broker／domain、M6 YOLO 型號與 VLM POC 均不阻擋
M5.tool Test Spec 已完成，`TR_spec_M5_TOOL_I` 已結案；目前沒有 M5.tool 程式碼
或 Pi PASS。本輪文件尚未 commit／push。
