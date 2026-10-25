# Current design status

- Updated: 2026-10-25
- Owner: Designer
- Scope: M5 MQTT local-test peer、真實 publish、external result／notification read 與 M6 Look 階段邊界
- State: **M5 MQTT 設計與 [`test_spec_M5_mqtt.md`](../test_spec/test_spec_M5_mqtt.md) 已完成複驗（[`TR_spec_M5_MQTT_I`](../reviews/history/TR_spec_M5_MQTT_I.md) Resolved）；Developer entry 已開啟**

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

## M5 MQTT active design

- [M5 MQTT 設計](../implement/ch_m5_mqtt.md) 已固定 local send 與 application result 分離：本地 send
  `0` 只觸發既有固定「已送出。」；外部完成／失敗只能另經 result topic → buffer → `read` → THINK。
- local-test peer 是專案能力，development profile 預設 `empty`（接收但不發布完成）；另以明確模式
  產生 success／failure／duplicate／malformed 與 notification。正式目標只靠配置替換，不做 failure fallback。
- 工作站 disposable local-peer POC 已完成：驗證 success／failure result、`empty` 無 result 與獨立
  notification 的基本 MQTT round trip；它不是產品 implementation 或正式 evidence。
- USER 已選定 deterministic read-only scheduling：external message 不打斷 current operation；下一個
  eligible listen boundary 由 StateManager 以 opaque pending IDs 強制改成 read-only，不啟動 listen。
  Look 已選定／執行時不混入 read，pending 留到 Look flow 後第一個 listen boundary。此決策與原
  Reasoner-owned pending scheduling矛盾已由
  [AR_impl_M5_MQTT_I](../reviews/history/AR_impl_M5_MQTT_I.md) 修訂 architecture 並 Resolved。
- External read 維持同一 c2 base system prompt（`M5_SYSTEM_PROMPT`）不變，只在 perception kind=`read` 時套專屬
  `source=external_message`／`messages[]`／`instruction` wrapper（`application_result` 與 `notification` 均進 LLM 轉告）；
  模型不看 request/event ID，read source 只允許 `speak|end`。Read 不套 M5.tool fresh prefill 128，但仍做 1024
  context admission。已依 USER 決策與 Pi Gemma 4 E2B POC 定稿：`external_message.buffer_max=8`（可配置）、
  `overflow_policy="drop_newest"`；單次 read 固定 1 則（`READ_MAX_BATCH_MESSAGES = 1`）、單則 `READ_MAX_TEXT_CODEPOINTS = 160`、
  wrapper `READ_MAX_WRAPPER_CODEPOINTS = 320`；讀取層超限以 `ToolInputTooLarge` 拒絕且丟棄、不截斷、不呼叫 LLM。
- [`protocol.md` §8](../protocol.md#8-m5-mqtt-wire-v1) 與 [Ch 10 §8.1](../implement/ch10_config.md) 已定稿 Wire v1、
  `MQTTConfig` 欄位與 `MQTT_EXTERNAL_NO_FALLBACK` 等 stable code。
- Read 不增加「我收到一個訊息，請稍等」的 spoken preamble；read→THINK 後只播放一次含來源的完整
  回答。若 Pi latency 後續顯示明確 UX 風險，再依量測評估非語音 cue。

[`TR_spec_M5_MQTT_I`](../reviews/history/TR_spec_M5_MQTT_I.md) 已由 Tester 核對 B1–B4 並歸檔為 `Resolved`；
Designer 已完成開發前複驗，確認 [`test_spec_M5_mqtt.md`](../test_spec/test_spec_M5_mqtt.md) 完整覆蓋核准設計，
並於 [`current.md`](current.md) 開啟 **Developer entry**（Next owner = `Developer`）。ALPHA 與 M5.tool
已 Accepted 的證據不重開。

Tester 交付 readiness、驗收問題、測試拓撲與 evidence 邊界已規劃於
[M5 MQTT §7](../implement/ch_m5_mqtt.md#7-test-spec-交付準備)。這是後續 gate 的輸入清單，不代表
Test Spec 已開啟，也不取代 Tester 對 Test ID、fixture、步驟與 PASS/FAIL 的 ownership。External
message 到達後的行為已精簡為六個不同風險代表：IDLE、active listen、tool_feedback、Look boundary、
兩則 batch與一次 Interrupt；THINK/Speak、read-window close前後及 end/error/shutdown沿用代表案例或
Ch 7 regression，不另做產品情境，也不做內容×state笛卡兒積。
