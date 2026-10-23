# Current design status

- Updated: 2026-10-23
- Owner: Designer
- Scope: M5.tool 具體設計；M5 MQTT／M6 Look 階段邊界
- State: **IR_review_M5_TOOL_I 已 Resolved；architecture delta 待 Architect 處理，Developer entry 尚未開啟**

## 已固定的設計

- [milestone](../milestone.md) 固定 M5.tool → M5 MQTT → M6 Look；Wake 延後至 BETA 前評估。
- [M5](../milestones/M5.md) 固定 mock 能力驗證、真實 MQTT 發送與外部 read 的不同責任，
  並記錄唯一可用的原 ALPHA baseline。
- [M5.tool 設計](../implement/ch_m5_tool.md) 固定有限模型語意、一次派發、固定回饋、
  Look-only 下一輪與失去 Conversation 時的錯誤路徑；[protocol §7](../protocol.md#7-m5tool-llm-protocol-v4)
  固定 child wire 差異。
- [M6](../milestones/M6.md) 固定 Camera＋YOLO＋結果整理的產品路徑，另列兩段式 VLM POC。

## 交付開發前的必要工作

1. Architect 處理 [AR_impl_M5_TOOL_I](../reviews/AR_impl_M5_TOOL_I.md) 中真正的
   architecture 衝突，將採用或等價方案寫入 `arch.md`；Designer 只同步直接受影響的設計。
2. Tester 依 M5 §2.3、實作設計與 protocol §7 建立 M5.tool Test Spec。
3. Developer 依完成的設計與 Test Spec 實作；Verify 在 Pi 驗相同待提交內容。

M5 broker／domain、M6 YOLO 型號及 VLM POC 結果留在對應後續階段，不是 M5.tool
的 entry 條件。ALPHA 已 Accepted 的證據不重開，本輪沒有產品 PASS。
