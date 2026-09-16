# M4B — clean rewrite gates

狀態：**Accepted — same-bytes Raspberry Pi `PV` Pass；commit `f87cfa5` pushed**。

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
| `M4B-DESIGN-COMPLETE` | Designer | Closed — 2026-09-14 | [`ch_m4b_llm_production`](../implement/ch_m4b_llm_production.md)撤回regex/GBNF及後續未經POC驗證的`oneOf/const/minLength`，改綁commit `4f34226...`的exact 352-byte schema artifact與Python semantic boundary |
| `M4B-ARCH-REVIEW` | Architect + Designer | Closed — 2026-09-12 | [`AR_impl_M4B_IV`](../reviews/history/AR_impl_M4B_IV.md)確認SM授權planned-recovery時序；Designer對齊§5.3；`arch.md`無修改 |
| `M4B-DESIGN-REVIEW` | Reviewer + Designer | Closed — 2026-09-12 | [`IR_review_M4B_III`](../reviews/history/IR_review_M4B_III.md) PASS／0 Blocking；Designer採納A1/A2並確認A3無需修改 |
| `M4B-TEST-COVERAGE` | Tester + Designer | Resolved — exact POC schema remapped | P03/P09/A05 profile-ready、native/Python boundary、raw/decoded/S2與real Pi regression改綁exact artifact；Developer-review command/catalog/state/finalizer mapping保留 |
| `M4B-DEVELOPMENT-REWRITE` | Developer | Closed — portable aligned 2026-09-13 | [`CR_M4B_II`](../reviews/history/CR_M4B_II.md)於 exact SHA `9ffd6e17ad5504d53c7c18799ca4718f69988f7e` Resolved；Linux aarch64 3.11/3.12/3.13各1005 PASS且零 forbidden outcome |
| `M4B-SINGLE-PV-DESIGN` | Designer | Closed — human review aligned | 七項均由script執行；USER判讀#2答案；Developer逐項檢查#1/#3–#7所有數值與輸出，script summary不得單獨接受；不新增身份簽核或authorization gate |
| `M4B-SINGLE-PV-COVERAGE` | Tester + Designer | Closed | 六項逐欄review可執行、綁定完整raw evidence、case aggregation無歧義，script-only Pass被禁止；exact POC schema mapping已同步 |
| `M4B-PRODUCT-VERIFICATION` | Developer → Verify | Closed — Accepted 2026-09-16 | `PV-M4B-FINITE-03`七項Pass；相同bytes commit `f87cfa5`已push；USER完成milestone disposition |
| `M4B-THRESHOLD-ADOPTION` | Design → Test Spec → Developer → Verify | Deferred — separate post-acceptance delta | 558/699 MiB仍為finite-session estimates；若日後採用，另走正常pipeline，不阻擋M4B Accepted或M4C entry |

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
  （Designer byte-for-byte POC constrained-JSON與human-review authority complete；Tester schema mapping
  Resolved；same-bytes Pi `PV` Accepted）。
- Foundation implementation design:
  [`m4b_foundation_revision.md`](../implement/m4b_foundation_revision.md)（Designer complete；Tester
  coverage approved）。
- Current progress: [`status/design.md`](../status/design.md)。
- POC inputs:
  [`EFFICIENCY-003`](../outsource/pm_handoff/DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003.md) and
  [`PROMPT-V2D2-004`](../outsource/pm_handoff/DELIVERY-LLM-POC-M4B-PROMPT-V2D2-004.md)。
- Temporary legacy Designer archive: `docs/implement/archive/m4b_legacy/` and
  `docs/status/archive/M4/M4B_MVA_legacy.md`。不得由current role自動載入。

## Completion

`PV-M4B-FINITE-03`在Raspberry Pi 5對最終protected-content／harness／profile tuple完成七項
驗證；七項script、六項適用Developer review及#2三題USER verdict全部Pass。Designer確認
#1 ATT與#7 R01 evidence分工、R08 normalized answer digest及155/155直接受影響Pi測試，沒有新的
design deviation或高風險regression。相同待提交bytes已成為commit
`f87cfa50b9c9415430973076a59c6b1961228090`並push至`origin/core`；USER於2026-09-16接受M4B完成。

此Accepted範圍不宣稱physical wake/display hardware、native context exhaustion/replacement、R06
nested-descendant killing或R07 full-product shutdown。558/699 MiB是finite-session estimates，尚未成為
release thresholds。這些界線不阻擋M4C Design entry；後續threshold adoption若發生，另走正常
`Design → Test Spec → Developer → Verify`流程。
