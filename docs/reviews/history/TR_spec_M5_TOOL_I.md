---
requestor: Designer
owner: Tester
status: Resolved
---

# TR_spec_M5_TOOL_I — M5.tool 中斷判準與模型能力措辭

## 範圍與價值／風險

審查 [M5.tool Test Spec](../../test_spec/test_spec_M5_tool.md) 對已定 M5 §2.3、
[M5.tool 設計](../../implement/ch_m5_tool.md) 與 [arch §6.4](../../arch.md#64-cancel-分級三級收斂)
的直接映射。真實 Gemma 選擇、首輪 prefill `<=128`、mock 派發與 Look 接續的主線已覆蓋。
本單只處理會錯判合規取消路徑的 blocking 項，以及一處驗收用語歧義；不重開產品範圍
或要求新的測試矩陣。

## Findings

| ID／等級 | 依據與可重現差異 | 產品／驗收影響 | 首選修正與最低驗收 |
| :--- | :--- | :--- | :--- |
| B1／Blocking | Test Spec `M5T-CAN-001` 步驟 3 包含 Look 輪 LLM `GENERATING`，但判定條件要求階段 1–3 的 active worker／phase 均「合作式取消並完成 join」。arch §6.4–§6.5 與 protocol §4.6 允許 native request 在 Level 1 無法及時停止時經 Level 2 `force_abort`／PGID waitpid 收斂；Level 2 失敗才 Level 3。 | 合規的 Level 2 收斂會被本 Test ID 判 FAIL，或迫使 Developer 對 native 操作聲稱不存在的合作式終止證明；若把 Level 3 當成正常中斷 PASS，又會錯放新 Session。 | 以本單下方的「B1 可直接採用的判定文字」修訂 `M5T-CAN-001`；保留原有場景與正常 `stop()` 判準，不增加新測試矩陣。 |
| A1／Advisory | `M5T-FLOW-001` PASS 寫「能穩定產出」四種合法語意，未說明「穩定」的有限判準；`FLOW-002/003` 已有具體真實模型情境。 | 可能讓一次成功與反覆失敗都被任意判 PASS／FAIL，或導致無價值的重複試次。 | 將「穩定產出」改為「在 `FLOW-002/003` 指定情境中產出符合 schema 的合法語意，並通過各場景判準」；不額外設定重複次數或統計門檻。 |

### B1 可直接採用的判定文字

> 步驟 1–3 中斷後，當前 active phase 依 arch §6.4 完成 Level 1 合作式停止，或於 Level 1 逾時後完成 Level 2 `force_abort` 的終止／資源釋放證明；外層 task 完成、handle 移除後才轉移狀態。`FX-M5T-SEND wait(event)` 與 `FX-M5T-VISION OBS_TIMEOUT` 等受控可取消等待，在未注入故障時應走 Level 1。Look 輪 LLM `GENERATING` 可先收到 `CANCEL_DEFERRED`；若 Level 1 逾時，須由 Parent 終止／回收 child PGID，不得偽造 `CANCELLED`、`RESULT` 或 `CLOSED`。若 Level 2 成功但破壞 backend，須進 `ERROR` 並完成 recovery barrier 後才可開啟新 Session；若 Level 2 失敗，依架構進 Level 3 fatal process exit，不能以同一 process 的「中斷後新 Session 正常」判 PASS。所有已取消路徑均不得產生遲到播音、被取消操作的正常 Fact，或讓舊 `last_dispatch_status`／Look generation 污染後續 Session。

上述是對原步驟 1–3 的分支判定，不要求另造 Level 2／Level 3 故障 fixture。步驟 4 的正常 `stop()` 判準維持獨立。

## Owner 回覆

- **B1（Adopted）**：已於 [`docs/test_spec/test_spec_M5_tool.md` `M5T-CAN-001`](../../test_spec/test_spec_M5_tool.md#m5t-can-001dispatchingobserving-中斷取消與正常-stop-收斂) 完整採用上述 B1 判定文字，並補列 `arch.md §6.4–§6.5` 與 `protocol.md §4.6` 來源契約；保留原有步驟 1–4 場景與正常 `stop()` 判準，不新增故障測試矩陣。
- **A1（Adopted）**：已於 [`docs/test_spec/test_spec_M5_tool.md` `M5T-FLOW-001`](../../test_spec/test_spec_M5_tool.md#m5t-flow-001pi-真實-gemma-schema-相容性與首輪-runtime_prefill_tokens--128-閘門) 及 `§6` 交付清單移除「穩定」一詞，明確對應為「在 `M5T-FLOW-002`／`M5T-FLOW-003` 指定情境中產出符合 schema 的 `speak`、`end`、`tool`（`tool_name="mock.send"`）與 `look` 四種合法語意，並通過各場景判準（不額外設定重複次數或統計門檻）」。

## Designer 複核結論

`M5T-CAN-001` 已允許可證明的 Level 1／2 收斂，且區分 Level 2 後的 recovery 與 Level 3 fatal exit；原有正常 `stop()` 判準與無遲到播音、跨 Session 污染要求均保留。`M5T-FLOW-001` 已以 `FLOW-002/003` 具體情境取代含糊的「穩定」用語。B1 收斂、A1 採納，無直接回歸；本 review 結案，Developer entry 可開啟。
