# M4B — clean rewrite gates

狀態：**Redesign / Developer and Tester entry closed**。

本輪依USER決策重寫M4B design、production implementation與tests。舊設計及decision overlay已
退役；POC交付只作新設計輸入，不自動成為產品契約。Accepted M4A與通用Core生命週期／錯誤
基礎維持有效。

## Gate matrix

| Gate | Owner | State | Exit |
| :--- | :--- | :--- | :--- |
| `M4B-LEGACY-DESIGN-CLEANUP` | Designer | Closed | 舊M4B Designer authority移出active design；穩定路徑宣告無現行設計 |
| `M4B-DESIGN-GATE-REASONER-BEHAVIOR` | Designer + USER | Closed | 完整normal/error語意固定action後路由、speech ownership、Conversation replacement與R2/R3/E1邊界 |
| `M4B-FOUNDATION-ARCH-REVIEW` | Architect | Open | `AR_impl_M4B_III`修訂sequential replacement、post-action route與pre-perception readiness架構契約 |
| `M4B-FOUNDATION-REVISION` | Designer + Tester + Developer | Blocked | foundation design/coverage核准後遷移event、SM、rest、Conversation lifecycle與affected M1/M2 regression |
| `M4B-DESIGN-COMPLETE` | Designer | Blocked | 從空白結構完成session、prompt/token、capacity、memory、timing、protocol與驗證設計 |
| `M4B-ARCH-REVIEW` | Architect/Reviewer | Blocked | 只審 replacement design 的必要cross-boundary delta；舊review不得釋放本gate |
| `M4B-TEST-COVERAGE` | Tester + Designer | Blocked | 新test spec覆蓋核准設計；不沿用舊M4B測試語意 |
| `M4B-DEVELOPMENT-REWRITE` | Developer | Blocked | 重寫M4B implementation/tests，移除暫存legacy code/test inventory |
| `M4B-PRODUCT-VERIFICATION` | Tester + Designer | Blocked | portable與Pi exact-SHA結果完成，Designer確認對齊 |

Gate必須依表列順序解除。Foundation architecture、design與coverage未Closed前，只能準備
review，不開Developer entry；foundation revision驗證完成後才進M4B cognition/product設計與開發。

## Confirmed redesign inputs

- Product Session開始時先完成Conversation readiness與application preparation UX，再開始
  listen/ASR；兩者不競爭。同一session同時只保留一個真實Conversation，但允許cleanup proof後
  sequential replacement並繼續下一turn。
- Inference前以exact tokenizer、rendered incremental tokens、current KV與output reserve做
  admission；通過前不得呼叫`send_message`。
- MVA context limit採明示replacement，未來保留compact-context擴充點。
- V2D2是POC參考而非永久prompt freeze；prompt composition與runtime/context allocation使用
  分離dashboard。
- `prefill <= 128`只適用於單一listen、最多20 Unicode codepoints且最多32 model tokens的
  voice-only profile；其他perception不受此tier限制，但須有exact projector budget並符合Engine
  context admission。
- Memory驗證不重跑舊20-session drift；改驗單一Product Session持續多輪至context limit、
  replacement後再成功一輪，以及Conversation open與selected application preparation UX的
  重疊峰值；production不重疊active ASR/listen。
- 反應時間暫不設target/ceiling；同一integrated vertical slice只記錄必要節點時間供後續檢討。
- M4B先取得Audio+LLM資源與節點分解；M4C使用這些結果完成whole-product composition，不能再
  回頭重做subsystem breakdown。

## Current authority and reference boundary

- Current entry: [`ch_m4b_llm_production.md`](../implement/ch_m4b_llm_production.md)（redesign
  tombstone；尚無產品設計）。
- Current progress: [`status/design.md`](../status/design.md)。
- POC inputs:
  [`EFFICIENCY-003`](../outsource/pm_handoff/DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003.md) and
  [`PROMPT-V2D2-004`](../outsource/pm_handoff/DELIVERY-LLM-POC-M4B-PROMPT-V2D2-004.md)。
- Temporary legacy Designer archive: `docs/implement/archive/m4b_legacy/` and
  `docs/status/archive/M4/M4B_MVA_legacy.md`。不得由current role自動載入。

## Next action

由Architect處理`AR_impl_M4B_III`。Designer確認architecture authority後，先準備獨立的
foundation revision design與Tester coverage，再進M4B cognition/product design。現在沒有
Developer／Tester work package，也不得建立candidate或產品驗收結果。
