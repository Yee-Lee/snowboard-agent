# Current design status

- Updated: 2026-10-23
- Owner: Designer
- Scope: M5.tool 具體設計；M5 MQTT／M6 Look 階段邊界
- State: **M5.tool 設計與 Test Spec 已就緒；TR_spec_M5_TOOL_I 已 Resolved；Developer entry 已開啟**

## 已固定的設計

- [milestone](../milestone.md) 固定 M5.tool → M5 MQTT → M6 Look；Wake 延後至 BETA 前評估。
- [M5](../milestones/M5.md) 固定 mock 能力驗證、真實 MQTT 發送與外部 read 的不同責任，
  並記錄唯一可用的原 ALPHA baseline。
- [M5.tool 設計](../implement/ch_m5_tool.md) 固定有限模型語意、一次派發、固定回饋、
  Look-only 下一輪與失去 Conversation 時的錯誤路徑；answering／dispatching／observing
  為三條產品路徑，新 Conversation 首次合法推論保留 `runtime_prefill_tokens <= 128`。
  [protocol §7](../protocol.md#7-m5tool-llm-protocol-v4) 固定 child wire 差異。
- [M6](../milestones/M6.md) 固定 Camera＋YOLO＋結果整理的產品路徑，另列兩段式 VLM POC。

## 開發交接

Tester 已依 [TR_spec_M5_TOOL_I](../reviews/history/TR_spec_M5_TOOL_I.md) 修訂中斷取消與真實模型
能力選擇的判準；Designer 複核 B1 收斂且無直接回歸。Developer 依設計與
[Test Spec](../test_spec/test_spec_M5_tool.md) 實作；Verify 在 Pi 驗相同待提交內容。

架構修訂與 Designer 核對已結案，見 [AR_impl_M5_TOOL_I](../reviews/history/AR_impl_M5_TOOL_I.md)。

M5 broker／domain、M6 YOLO 型號及 VLM POC 結果留在對應後續階段，不是 M5.tool
的 entry 條件。ALPHA 已 Accepted 的證據不重開，本輪沒有產品 PASS。
