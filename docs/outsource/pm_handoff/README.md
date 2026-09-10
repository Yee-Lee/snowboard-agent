# PM handoff queue

此目錄只保留仍需 Core 行動的 PM input。已回覆、已裁決、已取代或已由 downstream gate
追蹤的項目都保存在 [`history/`](history/)。

## Active

| Input | Core action |
| --- | --- |
| [`DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003`](DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003.md) | Retained as a clean-redesign input; it is not an active product profile or formal gate blocker |
| [`DELIVERY-LLM-POC-M4B-PROMPT-V2D2-004`](DELIVERY-LLM-POC-M4B-PROMPT-V2D2-004.md) | Retained as the current POC prompt reference; replacement product prompt/customization remains to be designed |

## 使用方式

- 只有任務明確涉及 PM handoff 時才檢查此目錄；一般角色啟動不讀取它。
- 新 handoff 放在本目錄並清楚標記 ID、owner、status、requested action 與 authoritative input。
- 完成時先更新 response／ACK 與狀態，再將原項目原樣移入 `history/`。
- `history/` 不作背景載入；只有追查指定 ID、SHA 或 provenance 時才搜尋，例如：
  `rg -n '<ID-or-SHA>' docs/outsource/pm_handoff/history`。
- 交付、回覆與 evidence 的分流見 [`../README.md`](../README.md)。
