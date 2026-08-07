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
