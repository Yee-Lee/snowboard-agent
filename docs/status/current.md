# Current handoff

- Updated: 2026-10-23
- Writer: Designer only
- Current milestone: M5.tool → M5 MQTT → M6 Look
- Current stage: **Design — M5.tool review 已結案，architecture delta 待處理**
- Next owner: Architect
- Developer entry: **Closed — architecture delta 與 M5.tool Test Spec 尚未完成**
- Working baseline: USER 已接受的原 ALPHA `8b4af53f433c4bcdb5b858973e10767318986554`；
  ALPHA.R1 未 Accepted，見 [M5 §2.2](../milestones/M5.md#22-entry)。

## Exact routing

| Owner | 下一步 | 最小讀取範圍 |
| :--- | :--- | :--- |
| Architect | 處理有限模型意圖與 tool 後固定回饋的 ACTION phase；回覆實際修正 | [AR_impl_M5_TOOL_I](../reviews/AR_impl_M5_TOOL_I.md)、[arch](../arch.md) §2.7／§2.8／§4.5／§4.6／§4.8 |
| Tester（架構完成後） | 依真實模型選能力、mock 派發與 Look 接續的產品失敗風險建立 M5.tool Test Spec，更新自己擁有的索引 | [M5 §2.3](../milestones/M5.md#23-驗收問題)、[設計](../implement/ch_m5_tool.md)、[protocol §7](../protocol.md#7-m5tool-llm-protocol-v4) |
| Developer（Test Spec 完成後） | 實作 M5.tool profile，於 Pi 驗證相同待提交內容 | [設計 §7](../implement/ch_m5_tool.md#7-實作路徑與交-test-spec) 及 Tester Test Spec |

## Scope boundary

M5.tool 使用真實 Gemma、mock.send、mock Camera／Vision 驗證能力選擇與下一輪回答。
M5 再接 MQTT 發送，以及外部 response／主動通知進 buffer／read；外部結果不是
handler return。M6 先用 Camera＋YOLO＋結果整理→原對話 LLM；VLM 描述是獨立 POC。
Wake 在 BETA 前重新評估，read／Look 交錯暫不納入。詳細決策分別見
[M5](../milestones/M5.md) 與 [M6](../milestones/M6.md)。

M4／ALPHA 已交付證據不重開。M5 broker／domain、M6 YOLO 型號與 VLM POC 均不阻擋
M5.tool 的 Test Spec；沒有 M5.tool 程式碼或 Pi PASS。本輪文件尚未 commit／push。
