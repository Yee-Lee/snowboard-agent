M1 外包實作缺陷

審查範圍：外包提交 19b4445；判定依據為外包收到的設計基線 584aa89。以下只列程式明確違反其自身設計文件的項目。

嚴重度

缺陷

違反的設計契約

阻擋

core/logger.py 會原樣輸出 payload 等 extra 欄位，可能洩漏 transcript、prompt、tool arguments

Ch 11 §9、§14：敏感內容不得進 log

阻擋

State Manager 收到無效 LLMResponse 時先進 ACTION，驗證失敗後才進 ERROR

Ch 4 §6.4：必須在 THINK Exit 驗證，失敗直接進 ERROR

阻擋

一般 Interrupt 固定先進 ERROR，即使沒有 destroyed backend

Ch 4 §7.2、Ch 6 §7：正常 Interrupt 應在 in-flight empty 後直接回 IDLE

阻擋

RM 計算 worker capability 時忽略 capability_dependencies

Ch 5 §5：capability 必須同時考慮依賴能力與自身啟動結果

阻擋

WorkerCatalog.seal() 未驗證 reasoner、rest、first-turn 與 default workers

Ch 5 §3.4、§4.5：seal 前必須完成必要 kind coherence gate

阻擋

Recovery 直接替換 sealed catalog 中的 worker identity，且部分 replacement 失敗時清理不完整

Ch 5 §3.4、§6：只能替換 worker 持有的 backend，失敗須清理局部資源

高

Main 使用私有 sm._loop_task 監督生命週期，未依公開 wait_stopped() 傳遞 fatal；runtime fatal 仍嘗試完整 RM cleanup

Ch 11 §10：監督 wait_stopped() / wait_fatal()；Level 3 只保證有上限的 logger flush

高

Config 的相對 Path 依 process cwd 解析；malformed .env error 可能輸出原始行內容

Ch 10 §11–§12：相對 Path 以 config 目錄解析，錯誤不得暴露 secret value

高

同名 exception 在 core/exceptions.py 與各 owner 模組重複定義，實際不是同一型別

Ch 11 §13：exception taxonomy 與 owner 必須形成一致的 fatal handoff

中

EventBus 實作成單一 core/event_bus.py，未依規格建立 package 與公開 re-export

Ch 3 §2：core/event_bus/__init__.py + bus.py

補充：現有外包測試沒有攔住上述缺陷，部分測試甚至把「Interrupt 進 ERROR」寫成預期行為，需連同測試一起修正。
