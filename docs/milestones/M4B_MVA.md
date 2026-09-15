# M4B — clean rewrite gates

狀態：**Foundation verified / byte-for-byte POC constrained-JSON authority and Tester mapping resolved /
Developer correction open**。

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
| `M4B-DESIGN-COMPLETE` | Designer | Revised — 2026-09-14 | [`ch_m4b_llm_production`](../implement/ch_m4b_llm_production.md)撤回regex/GBNF及後續未經POC驗證的`oneOf/const/minLength`，改綁commit `4f34226...`的exact 352-byte schema artifact與Python semantic boundary |
| `M4B-ARCH-REVIEW` | Architect + Designer | Closed — 2026-09-12 | [`AR_impl_M4B_IV`](../reviews/history/AR_impl_M4B_IV.md)確認SM授權planned-recovery時序；Designer對齊§5.3；`arch.md`無修改 |
| `M4B-DESIGN-REVIEW` | Reviewer + Designer | Closed — 2026-09-12 | [`IR_review_M4B_III`](../reviews/history/IR_review_M4B_III.md) PASS／0 Blocking；Designer採納A1/A2並確認A3無需修改 |
| `M4B-TEST-COVERAGE` | Tester + Designer | Resolved — exact POC schema remapped | P03/P09/A05 profile-ready、native/Python boundary、raw/decoded/S2與real Pi regression改綁exact artifact；Developer-review command/catalog/state/finalizer mapping保留 |
| `M4B-DEVELOPMENT-REWRITE` | Developer | Closed — portable aligned 2026-09-13 | [`CR_M4B_II`](../reviews/history/CR_M4B_II.md)於 exact SHA `9ffd6e17ad5504d53c7c18799ca4718f69988f7e` Resolved；Linux aarch64 3.11/3.12/3.13各1005 PASS且零 forbidden outcome |
| `M4B-SINGLE-PV-DESIGN` | Designer | Revised — human review aligned | 七項均由script執行；USER判讀#2答案；Developer逐項檢查#1/#3–#7所有數值與輸出，script summary不得單獨接受；不新增身份簽核或authorization gate |
| `M4B-SINGLE-PV-COVERAGE` | Tester + Designer | Resolved — review portion only | 六項逐欄review可執行、綁定完整raw evidence、case aggregation無歧義，script-only Pass被禁止；不代表schema mapping closed |
| `M4B-PRODUCT-VERIFICATION` | Developer → Verify | Active — correction open | Developer實作、portable與fresh Pi development evidence仍待驗；舊tuple與簡化review無credit，final seven-ID `PV` Pending |
| `M4B-THRESHOLD-ADOPTION` | Design → Test Spec → Developer → Verify | Pending — after valid `PV` estimates | 另案採用threshold estimates並只驗直接受影響行為；不得稱為PR或預設重跑已接受的產品／人工 corpus |

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
  Resolved；Developer correction open）。
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
Tester coverage與Designer mapping已依[`TR_spec_M4B_VI`](../reviews/history/TR_spec_M4B_VI.md)關閉。
[`CR_M4B_II`](../reviews/history/CR_M4B_II.md)已在 exact SHA
`9ffd6e17ad5504d53c7c18799ca4718f69988f7e`完成獨立 portable PASS 與 Designer alignment。
USER已明確取消角色簽核與authorization JSON；舊§5.4 approval文字不具gate效力。`IR_dev_M4B_V`
帶入更新的USER決策後，Designer接受B1並修訂產品§§5.3/11.2：PM、PR、PH不再是三個stage，改由
一個`PV` aggregate disposition彙整彼此獨立的Test IDs，且不做第二次release run。Tester完成
`TR_spec_M4B_VIII` B1–B5修正，Designer複審Resolved；Developer現在實作exact mapping並在Pi驗證。
有效estimates的採用屬後續focused normal pipeline；目前不宣稱PV PASS或M4B Accepted。
所有先前PM/PR/PH run及其partial/complete outputs一律作廢，不得作為新`PV`的輸入或證據；新run
必須使用新run ID與空的private/public active evidence roots。

USER於2026-09-14確認Core換成regex後，real LLM無法正常回答，且POC並未交付J-via-regex、
canonical member order/whitespace或GBNF產品身份。Designer因此撤回`IR_dev_M4B_VI`後續的
`char+`修補方向，不再以regex的shortest-path問題改寫產品語意。現行設計回復POC constrained-JSON
`J`：`ResponseFormat.json(response_schema)`、真實JSON decoder與exact semantic validation；合法member order與
insignificant whitespace必須等價，`end=true`再次允許empty text。Tester已完成直接影響映射，
Designer當時誤認constrained-JSON本身無Blocking缺口；Tester隨後指出script-only evidence與最新USER要求
衝突。§11.2現已修成七項均由script執行，#2由USER判讀答案，#1/#3–#7由Developer逐一檢查所有
數值與輸出合理性，且不得只接受script summary。Tester現已補齊exact review command/schema、完整
catalog/evidence binding、強制`NeedsDeveloperReview`、one per-Test-ID WAKE/RES review及G07–G10；
Designer確認review-contract同步；但後續provenance audit證明Designer提供的`oneOf/const/minLength`
schema並非POC artifact，因此當時不得開放Developer。Tester現已改綁352-byte artifact
`796c311...`、locator與native/Python validation boundary；Designer確認映射無Blocking缺口並開放
Developer correction。現有簡化review實作仍不得取得credit。
