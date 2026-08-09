# LLM M4：M4a Combined Validation and Delivery

狀態：`NOT_STARTED`

## 目標與交付貢獻

在活動產品 repo 明確 Accepted 的 M4a Audio HAL SHA 上完成 LLM combined
validation、offline/failure injection、至少 20 個固定 sessions 與正式 POC delivery
package。推進並關閉 D1–D8。

## Entry Conditions

- M3 `COMPLETE`，唯一 winner 或核准 no-go 已固定。
- Accepted M4a full SHA、owner、acceptance reference、Test ID 與已知限制已登錄。
- Combined session fixtures、success criteria、fault schedule、resource/thermal gates 已 frozen。
- Delivery exact SHA 可被 Pi fetch，workstation/Pi checkout clean，M0 pre-test rerun 通過。

## Work Packet

- Audio models 與 LLM 同時常駐，執行至少 20 個預先固定的 combined sessions。
- 記錄 end-to-end latency、LLM latency/tokens/s、RSS、CPU、threads/processes、temperature、
  throttling 與跨 session 累積。
- 注入 LLM timeout、cancel、malformed output、child crash 與 force-abort；驗證 Audio
  結果語意、Reasoner fallback、rebuild、cleanup 與後續 session recovery。
- 停用外部網路後重跑 frozen offline subset；不允許 runtime/model download 或 cloud fallback。
- 組裝 delivery manifest、winner/no-go、source/tests、schemas、fixtures、sanitized evidence
  index、risks、licenses、checksums 與 productization handoff。

## Exit Gate

- 至少 20 個 combined sessions 依預先定義 criteria 完成，無資源或 history 累積。
- Offline 與所有 mandatory fault cases 均有有效結果及 cleanup/exit proof。
- M4a SHA 與 LLM exact SHA、artifact/config/protocol IDs 可完整追溯。
- Delivery draft 的 D1–D8 均有證據，或每個未關閉項目都有 blocking finding/change request。
- 完整 SHA 交付狀態只標記 `Ready for internal review`。
- Tester/Reviewer 關閉 blocking findings且 Designer 核准後，才標記 `POC Accepted`。

## Necessary Evidence

- Accepted M4a dependency record 與 exact combined test request。
- 20-session manifest、per-session results、aggregate metrics 與 raw evidence checksums。
- Offline/fault/recovery/cleanup proof與 post-run environment inventory。
- Final delivery manifest、winner/no-go、risk/finding/change-request indexes。

## Prohibited in M4

- 不以 demo、摘要數字或非 Pi 結果取代 evidence packet。
- 不在 combined test 中改動 Pi worktree、M4a baseline、fixture 或 acceptance gate。
- 不因提交完整 SHA 而提前宣告 `POC Accepted`。
