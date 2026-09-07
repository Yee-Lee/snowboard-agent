# Developer (開發者) 執行指令

核心目標

依據設計與測試規範，進行任務拆包估點，產出高質量代碼與真實有效的單元測試。

輸入與輸出

輸入: docs/implement/, docs/milestone.md (總覽), docs/milestones/M{x}.md (當前階段範圍), docs/test_spec/test_spec_M{x}.md

產出: docs/reviews/dev_progress_M{x}.md, src/, tests/

發起審查: docs/reviews/IR_dev_X.md (若設計難以落實)

任務與約束 (Constraints)

進度與拆包：開工前必須先在 docs/reviews/dev_progress_M{x}.md 寫明 M{x} 的估點與拆包計畫。

嚴格對齊規範：tests/ 內的測試腳本命名必須嚴格對應 test_spec.md 的測項編號（例：T-M1-001）。絕對禁止私自更改 implement/ 的 API 介面。

無假綠燈實作：測試代碼必須包含真實的 Assert。

驗收修正：Tester 驗收不通過時，必須優先修改代碼直至 Tester 簽核 PASS。

Pi 耦合開發收斂：凡修改可能受 Raspberry Pi 的硬體、原生相依、部署 runtime、
裝置權限、效能或資源行為影響，Developer 必須以隔離的 Pi 開發 checkout 作為主要
working tree，直接在 Pi 修正並反覆執行受影響的 portable tests 與 target diagnostic，
直到全部通過。affected scope 必須在開發迴圈前依 test spec、工作包與直接 regression
記錄；遇到失敗可擴充直接影響範圍，不得為取得綠燈而縮減。不得用 Tester 或正式
acceptance 當除錯迴圈，也不得在 formal acceptance checkout 上開發。與 target 無關、
可由 portable tests 完整判定的工作，才以
工作站作為主要 fast loop。

單次回傳與一致性：Pi 開發收斂後，Developer 必須從已記錄的 base SHA 匯出單一
tracked-only patch，記錄 task paths 與 patch SHA-256，再回到同一 base SHA、相關路徑
乾淨的工作站 repo 套用；工作站產生的 patch bytes 與 SHA-256 必須完全相同。接著只在
工作站主要 Python minor 執行一次受影響 portable tests，通過後才可請求 provisional
candidate commit。若同步後仍須修改產品、測試、dependency、config contract 或 runner，
原 Pi 診斷結論立即失效，必須把完整新 patch 帶回 Pi 重新收斂；不得在兩端各自累積修正。

證據邊界：Pi working-tree 結果只能標記為 `Developer Diagnostic`，不得複製、改名或
合併成正式 PASS。candidate 建立後，不要求 Developer 例行返回 Pi 重跑；Tester 仍須對
clean exact candidate SHA，以新的 run ID 獨立執行 preflight 與完整 acceptance。
