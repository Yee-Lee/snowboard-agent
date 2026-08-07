# M2 Designer 最終審核

* **Handoff** : `PM-OUT-260807-006-m2-tester-verification`
* **Status** : `Ready for PM`
* **Candidate** : `dev_agent_m2` @ `b4a6c11a0178b6157b9ae32db3a0af1295f72844`

## 結論

M2 功能與測試範圍 Accepted，無 Blocking finding，可進行 M3 Design Gate。內部 Tester 已確認 Windows portable `199 passed`、M2 signed nodes `35 passed`，21 個 Test ID / 36 個 unique nodes 完整，高風險 race / cleanup 測項連跑 5 輪通過。

以下三項為非阻擋修訂，納入下一個產品 commit；不要求外包另建 response、delivery 或 evidence 文件。

| ID | Priority | 問題 | 必做修訂 | 驗收方式 |
| :--- | :--- | :--- | :--- | :--- |
| `OUT-M2-2026-003` | High | Clean checkout 依正式命令無法 import `sbd`。M2 分支由無共同祖先的 snapshot history 重建；初始 snapshot 漏掉 accepted M1 的 `pyproject.toml`，不是 `.gitignore`。 | 恢復可安裝的 package / test metadata，同步 runbook 與 test spec；在已提交的開發紀錄交代為何重建 history 時漏檔、確認方式及防止再發措施。Designer 比對 accepted M1 與 M2 初始 snapshot，未發現其他必要產品檔遺漏。 | Clean Python 3.11 不使用未記載的 `PYTHONPATH`，M1 entrypoint、M2 entrypoint、full suite 依平台矩陣均為 0 Fail。 |
| `OUT-M2-2026-004` | Medium | Ch7 要求 `channel` 必須由 composition root 註冊，但 `ExternalMessageSource` 目前接受任意非空名稱，config / composition 無註冊清單，測試也未覆蓋未知 channel。 | 由 composition 明確注入允許的 channel 集合；未知 channel 必須在配置 / 存入 / 分配 ID / 發布 Signal 前拒絕，並補上 M2-MSG-001 測項。 | 已註冊 channel 正常 ingest；未知 channel 無 item、ID 或 Signal，正式 M2 suite 通過。 |
| `OUT-M2-2026-005` | Medium | 處理 `IR_dev_M2_I` 的 commit `79f7c95...` 誤刪 Ch5 §3.4 的 `required_kinds` 推導內容，現文件仍引用已不存在的定義；runtime 實作與測試目前正確。 | 恢復 §3.4 必要 kind 推導，內容須與 `ResourceManager._required_catalog_kinds()`、startup coherence gate 及 tests 一致。 | Ch5 不再有斷裂引用；文件、實作與既有 RM/M2 tests 一致。 |

## PM 動作

1. 交付本文件即可；不要求外包書面回覆。
2. 外包直接於下一個產品 commit 完成三項修訂，並在既有開發紀錄留下 `OUT-M2-2026-003` 根因說明。
3. PM 拉回後提供 branch 與完整 HEAD SHA；Designer 於下一次 intake 順帶確認，不另開 M2 驗收輪。
