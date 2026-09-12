# M4B — clean rewrite gates

狀態：**Foundation verified / replacement design Reviewer PASS / Tester coverage approved /
Developer rewrite open**。

本輪依USER決策重寫M4B design、production implementation與tests。舊設計及decision overlay已
退役；POC交付只作新設計輸入，不自動成為產品契約。Accepted M4A與通用Core生命週期／錯誤
基礎維持有效。

## Gate matrix

| Gate | Owner | State | Exit |
| :--- | :--- | :--- | :--- |
| `M4B-LEGACY-DESIGN-CLEANUP` | Designer | Closed | 舊M4B Designer authority移出active design；replacement authoring從空白穩定入口開始 |
| `M4B-DESIGN-GATE-REASONER-BEHAVIOR` | Designer + USER | Closed | 完整normal/error語意固定action後路由、speech ownership、Conversation replacement與R2/R3/E1邊界 |
| `M4B-FOUNDATION-ARCH-REVIEW` | Architect | Closed | `AR_impl_M4B_III`修訂sequential replacement、post-action route與pre-perception readiness架構契約；Reviewer PASS及Designer確認 |
| `M4B-FOUNDATION-REVISION` | Designer + Tester + Developer | Closed — verified 2026-09-11 | Foundation candidate focused 68；immutable baseline 99 retained / 0 missing；strict baseline 99 passed / 0 skipped；full repository 770 passed / 2 pre-existing optional audio skips / 29 deselected |
| `M4B-DESIGN-COMPLETE` | Designer | Closed — 2026-09-12 | [`ch_m4b_llm_production`](../implement/ch_m4b_llm_production.md)完成session、prompt/token、capacity、memory、timing、`snowboard.llm/3`與驗證設計 |
| `M4B-ARCH-REVIEW` | Architect + Designer | Closed — 2026-09-12 | [`AR_impl_M4B_IV`](../reviews/history/AR_impl_M4B_IV.md)確認SM授權planned-recovery時序；Designer對齊§5.3；`arch.md`無修改 |
| `M4B-DESIGN-REVIEW` | Reviewer + Designer | Closed — 2026-09-12 | [`IR_review_M4B_III`](../reviews/history/IR_review_M4B_III.md) PASS／0 Blocking；Designer採納A1/A2並確認A3無需修改 |
| `M4B-TEST-COVERAGE` | Tester + Designer | Closed — 2026-09-12 | [`test_spec_M4B`](../test_spec/test_spec_M4B.md)完成11/11 portable與7/7 Pi-human mapping；[`TR_spec_M4B_VI`](../reviews/history/TR_spec_M4B_VI.md)由Designer確認Resolved |
| `M4B-DEVELOPMENT-REWRITE` | Developer | Open | 依[`CR_M4B_II`](../reviews/CR_M4B_II.md)重寫M4B implementation/portable tests；不得宣稱candidate/Pi acceptance |
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
- Designer在replacement profile中明示採用V2D2 exact bytes作`core-m4b-cognition-001`初始產品prompt；
  此次採用不建立任意personality設定，未來prompt/capability變更須換profile ID並重走quality/review gate。
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

- Current product design: [`ch_m4b_llm_production.md`](../implement/ch_m4b_llm_production.md)
  （Designer complete；Reviewer PASS；Tester coverage approved；Developer rewrite open）。
- Foundation implementation design:
  [`m4b_foundation_revision.md`](../implement/m4b_foundation_revision.md)（Designer complete；Tester
  coverage approved）。
- Current progress: [`status/design.md`](../status/design.md)。
- POC inputs:
  [`EFFICIENCY-003`](../outsource/pm_handoff/DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003.md) and
  [`PROMPT-V2D2-004`](../outsource/pm_handoff/DELIVERY-LLM-POC-M4B-PROMPT-V2D2-004.md)。
- Temporary legacy Designer archive: `docs/implement/archive/m4b_legacy/` and
  `docs/status/archive/M4/M4B_MVA_legacy.md`。不得由current role自動載入。

## Next action

`AR_impl_M4B_IV`已Resolved且`arch.md`無修改；[`IR_review_M4B_III`](../reviews/history/IR_review_M4B_III.md)
對replacement product authority與direct mappings判定PASS／0 Blocking，Designer已處理三項Advisory。
Tester coverage與Designer mapping已依[`TR_spec_M4B_VI`](../reviews/history/TR_spec_M4B_VI.md)關閉。Developer
現在依[`CR_M4B_II`](../reviews/CR_M4B_II.md)實作replacement與portable tests；完成獨立驗證前不得建立
產品candidate、執行Pi/human acceptance或宣稱M4B PASS。
