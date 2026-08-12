# Independent Review Exchange

本目錄是 implementation process 與獨立 reviewer process 的檔案式交接通道；專案進度的唯一權威仍是 `docs/poc/milestone_plan.md`。

## 檔案責任

- `P1_REVIEW_REQUEST.md`：由 implementation process 維護，記錄待審範圍、baseline、驗證結果與仍 pending 的 gate。
- `P1_REVIEW_FEEDBACK.md`：由獨立 reviewer process 填寫 findings、測試與 gate 結論。
- `P1_OPERATOR_ATTESTATION_REVIEW_REQUEST.md`：照片 gate 改為人工 attestation 後原先準備的審核範圍；本次由 Owner 直接核准並關閉。
- `P1_OPERATOR_ATTESTATION_REVIEW_FEEDBACK.md`：保留 Owner approval／review waiver 決策；不得誤稱為獨立 reviewer 結論。
- `P1_LINKER_FIX_REVIEW_REQUEST.md`：P3 發現 native link-order bug 後的修正審核範圍。
- `P1_LINKER_FIX_REVIEW_FEEDBACK.md`：由獨立 reviewer process 填寫 linker/runtime-symbol gate findings 與結論。

## Reviewer 工作邊界

1. 先讀根目錄 `AGENTS.md`，再讀目前狀態為 `READY_FOR_EXTERNAL_REVIEW` 的 request 所指定最小範圍。
2. 可以執行唯讀檢查與測試。
3. 不修改產品程式、測試、milestone、manifest 或 evidence。
4. 只將審核輸出寫入該 request 指定的 feedback 檔案。
5. 不建立 commit、不凍結 candidate、不宣告 Core ACK。

## Feedback 結論

Reviewer 必須選擇其中之一：

- `APPROVE`：沒有 blocking/high finding，可進入 candidate commit。
- `BLOCK`：存在必須在 candidate commit 前解決的 finding。
- `PENDING`：審核尚未完成。

Review request 只在 milestone stage 達到 exit gate 時提出一次；stage 內發現與修正的 findings 累積到該次 review，不得因每個小修正反覆停下。

若 stage-exit review 回報 finding，implementation process 依 feedback 修正，並在同一 stage exit 完成必要複審；不得自行覆寫 reviewer 判斷。

Owner 可直接核准或免除 review；必須記錄 authority、scope 與 waiver，且不得冒充 reviewer approval。

Pi P2/P3 evidence 與 Core Team P4 ACK 不屬於此 host-side P1 review 的可替代項目；缺少它們時必須維持 pending。
