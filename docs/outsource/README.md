# External-work routing

外部往返文件依用途分流；Agent 只讀與當前任務直接相關的入口及文件。

| 路徑 | 用途 |
|---|---|
| [`pm_handoff/`](pm_handoff/) | PM 提供、仍需 Core 行動的 input；完成後進 `history/` |
| [`references/`](references/) | 外部技術 baseline 的 exact-SHA locator，不複製外部 repo |
| [`deliveries/`](deliveries/) | Core 對外 task、ACK、decision 與 receipt；日常從 active index 開始 |
| [`responses/`](responses/) | Core 對 PM request 的回覆 |
| [`evidence/`](evidence/) | Tester／operator 的正式驗收結果與原始證據 |

`history/` 與 `deliveries/archive/` 都是按需查詢的 provenance，不是角色背景必讀。
任何現行產品契約仍以 architecture、implementation、milestone 與 test spec 為準。
