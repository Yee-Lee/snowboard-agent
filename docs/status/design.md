# Current design status

- Updated: 2026-10-25
- Owner: Designer
- Scope: M5.tool 結案（Accepted）；M5 MQTT 具體設計準備與 M6 Look 階段邊界
- State: **M5.tool 已完成 final Verify PASS（Accepted）；待展開 M5 MQTT 設計輸入**

## 已固定的設計

- [milestone](../milestone.md) 固定 M5.tool → M5 MQTT → M6 Look；Wake 延後至 BETA 前評估。
- [M5](../milestones/M5.md) 固定 c2 兩欄模型輸出、固定 `mock.send("啟用遠端連線")` 命令映射、
  物件觀察與顏色限制、真實 MQTT 發送與外部 read 的不同責任，並記錄唯一可用的原 ALPHA baseline
  與 M5 Whisper `initial_prompt="遠端連線"` 設定。
- [M5.tool 設計](../implement/ch_m5_tool.md) 固定模型端兩欄 JSON（`intent`, `text`）與內部四欄
  v4 語意框架分界、`tool`/`look` 模型文字抑制（不進 SAFE_TEXT／Display／TTS）、單次固定派發與回饋、
  Look-only 下一輪與經 Pi 驗證的 Look wrapper `instruction`、以及失去 Conversation 時的錯誤路徑；
  保留新 Conversation 首次合法推論 `runtime_prefill_tokens <= 128`（c2 否定句依 USER 決定僅保留為診斷歷史，
  不作為現行驗收測項）。
  [protocol §7](../protocol.md#7-m5tool-llm-protocol-v4) 固定 child wire 差異。
- [M6](../milestones/M6.md) 固定 Camera＋YOLO＋結果整理的產品路徑，另列兩段式 VLM POC。

## 開發交接

M5.tool 已依 [IR_dev_M5_TOOL_I](../reviews/IR_dev_M5_TOOL_I.md)、[`TR_dev_M5_TOOL_I`](../reviews/history/TR_dev_M5_TOOL_I.md)
與 [Test Spec §7](../test_spec/test_spec_M5_tool.md#7-final-verify-result--2026-10-25) 完成 Pi same-byte
驗證與 final Verify **PASS**（WIP `108264c420fb4ed020e517a8dc64c625da373e81`，Pi Run
`m5tool-repair-verify-20261025-cGrEVf`）。

架構修訂與規格／開發審查見 [AR_impl_M5_TOOL_I](../reviews/history/AR_impl_M5_TOOL_I.md)、
[TR_spec_M5_TOOL_I](../reviews/history/TR_spec_M5_TOOL_I.md) 與 [TR_dev_M5_TOOL_I](../reviews/history/TR_dev_M5_TOOL_I.md)。

下一步由 **Designer** 依 [M5 §3.2](../milestones/M5.md#32-此階段才需要固定的輸入) 固定 M5 MQTT
的 broker、認證配置、topic namespace、domain schema 與 publish/read 契約；M5 MQTT 完成
`Design → Test Spec` 前不開啟 Developer entry。ALPHA 與 M5.tool 已 Accepted 的證據不重開。
