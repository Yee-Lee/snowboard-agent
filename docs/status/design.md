# Current design status

- Updated: 2026-10-24
- Owner: Designer
- Scope: M5.tool 具體設計（對齊 c2 兩欄模型契約與固定遠端連線命令）；M5 MQTT／M6 Look 階段邊界
- State: **M5.tool 設計與 Test Spec 已依 IR_dev_M5_TOOL_I 完成對齊；Developer entry 已開啟**

## 已固定的設計

- [milestone](../milestone.md) 固定 M5.tool → M5 MQTT → M6 Look；Wake 延後至 BETA 前評估。
- [M5](../milestones/M5.md) 固定 c2 兩欄模型輸出、固定 `mock.send("啟用遠端連線")` 命令映射、
  物件觀察與顏色限制、真實 MQTT 發送與外部 read 的不同責任，並記錄唯一可用的原 ALPHA baseline
  與未來 M5 Whisper `initial_prompt="遠端連線"` 方向。
- [M5.tool 設計](../implement/ch_m5_tool.md) 固定模型端兩欄 JSON（`intent`, `text`）與內部四欄
  v4 語意框架分界、`tool`/`look` 模型文字抑制（不進 SAFE_TEXT／Display／TTS）、單次固定派發與回饋、
  Look-only 下一輪與經 Pi 驗證的 Look wrapper `instruction`、以及失去 Conversation 時的錯誤路徑；
  保留新 Conversation 首次合法推論 `runtime_prefill_tokens <= 128`（c2 否定句依 USER 決定僅保留為診斷歷史，
  不作為現行驗收測項）。
  [protocol §7](../protocol.md#7-m5tool-llm-protocol-v4) 固定 child wire 差異。
- [M6](../milestones/M6.md) 固定 Camera＋YOLO＋結果整理的產品路徑，另列兩段式 VLM POC。

## 開發交接

Designer 與 Tester 已完成 [IR_dev_M5_TOOL_I](../reviews/IR_dev_M5_TOOL_I.md)（含 Developer recheck）
要求的權威設計與 [Test Spec](../test_spec/test_spec_M5_tool.md) 對齊；由 **Developer** 確認並繼續
於 Pi 對相同待提交內容完成產品路徑驗證後交 Verify。

架構修訂與先前規格審查已結案，見 [AR_impl_M5_TOOL_I](../reviews/history/AR_impl_M5_TOOL_I.md) 與
[TR_spec_M5_TOOL_I](../reviews/history/TR_spec_M5_TOOL_I.md)。

M5 broker／domain、M6 YOLO 型號及 VLM POC 結果留在對應後續階段，不是 M5.tool
的 entry 條件。ALPHA 已 Accepted 的證據不重開，本輪沒有產品 PASS。
