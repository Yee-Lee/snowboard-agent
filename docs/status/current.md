# Current handoff

- Updated: 2026-10-25
- Writer: Designer only
- Current milestone: M5.tool（Accepted）→ M5 MQTT → M6 Look
- Current stage: **M5.tool Accepted（final Verify PASS）— 待完成 M5.tool 交付 commit 並進入 M5 MQTT Design**
- Next owner: Designer
- Developer entry: **Closed — M5.tool 已完成 final Verify PASS；M5 MQTT 設計與 Test Spec 尚未開啟**
- Working baseline: M5.tool Verified WIP `108264c420fb4ed020e517a8dc64c625da373e81`（Pi Run `m5tool-repair-verify-20261025-cGrEVf`，基於原 ALPHA `8b4af53f433c4bcdb5b858973e10767318986554`；ALPHA.R1 未 Accepted，見 [M5 §2.2](../milestones/M5.md#22-entry)）。

## Exact routing

| Owner | 下一步 | 最小讀取範圍 |
| :--- | :--- | :--- |
| Designer | 依 `git.md` 準備 M5.tool 結案交付 commit（待 USER 同意後執行），並依 [M5 §3.2](../milestones/M5.md#32-此階段才需要固定的輸入) 展開 M5 MQTT 設計輸入（broker、認證、topic namespace、domain schema、publish/read 契約） | [test_spec_M5_tool.md §7](../test_spec/test_spec_M5_tool.md#7-final-verify-result--2026-10-25)、[development.md](development.md)、[M5 §3](../milestones/M5.md#3-m5-mqtt--發送與外部訊息接收)、[ch07_external_message.md](../implement/ch07_external_message.md) |

## Scope boundary

M5.tool 已於 2026-10-25 完成 final Verify **PASS**（Accepted）：真實 Gemma c2 兩欄 JSON 輸出、
固定映射 `mock.send("啟用遠端連線")`、模型 `tool`/`look` 文字抑制、物件觀察有據回答
（使用經 Pi 驗證的 Look wrapper `instruction`；否定句依 USER 決定僅保留為診斷歷史）、新 Conversation
首輪 `runtime_prefill_tokens <= 128`，以及 `TR_dev_M5_TOOL_I` B1/B2 修正（WIP `108264c420fb4ed020e517a8dc64c625da373e81`，
Pi Run `m5tool-repair-verify-20261025-cGrEVf` targeted 32/32 Pass、affected regression 122/122 Pass）均已驗收通過。

下一階段 **M5 MQTT** 將已驗證的派發能力接到真實 MQTT 發送，並將外部 response／主動通知經
buffer／read 納入對話（外部結果不是 handler return）。M6 先用 Camera＋YOLO＋結果整理→原對話 LLM；
VLM 描述是獨立 POC。Wake 在 BETA 前重新評估，read／Look 交錯暫不納入。詳細決策分別見
[M5](../milestones/M5.md) 與 [M6](../milestones/M6.md)。

M4／ALPHA 與 M5.tool 已 Accepted 的證據不重開。M5 MQTT 在固定 [M5 §3.2](../milestones/M5.md#32-此階段才需要固定的輸入)
的設計輸入並完成 `Design → Test Spec` 前，Developer entry 維持關閉。
