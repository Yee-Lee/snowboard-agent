# M4B-MVA — 跨團隊名稱與 POC 進場 Gate

日期：2026-09-05。USER已明確指定本文件的七步順序。
本文件是M4B的設計／量測工作基線，不新增milestone、永久Git branch或milestone tag。

## 1. Canonical naming

| Item | Canonical value / meaning |
| :--- | :--- |
| 中文名稱 | M4B 最小可行語音架構 |
| 跨團隊工作名稱 | M4B-MVA |
| 本次基線 ID | M4B-MVA-001 |
| POC 進場 gate ID | M4B-MVA-POC |
| Core profile ID | core-m4b-mva-001；實際內容/digest仍待POC結果採用後固定 |
| POC 工作單 | REQUEST-LLM-POC-M4B-MVA-MEASURE-001 |
| POC owner | 既有LLM POC團隊與repository；必要時協調既有Audio package |

先前草稿中的「R2」只表示Designer第二版草稿，沒有跨團隊正式身分，現統一改稱M4B-MVA。
M4B-MVA-001是本次package baseline ID，不表示已定版或已驗收。
不是ASR Product R1／ALPHA.R1，不是舊LLM POC pairing r1/r2/r5，也不是新模型選型。
公開wire的snowboard.llm/2只表示protocol breaking version，與工作名稱／基線版次分開。
既有IR_dev_M4B_III、AR_impl_M4B_I、TR_spec_M4B_IV與POC工作單ID保留，不為改名重編號。
跨團隊計畫、交付、result、review／ACK應同時引用work_name=M4B-MVA、
baseline_id=M4B-MVA-001、gate_id=M4B-MVA-POC、artifact full SHA與適用schema/config digest。
往後修改已交付package用下一個baseline ID並保留supersedes關係，不覆寫已發出的版本。

## 2. USER-defined seven-step sequence

| Step | Owner / work | Exit / gate effect |
| :--- | :--- | :--- |
| 1 | Architect修訂arch.md | AR_impl_M4B_I有主文件修訂與回覆，架構變更可交Reviewer |
| 2 | Reviewer同一輪審查arch.md、design/implement、POC計畫 | 三個面向都有明確結論，Blocking全數處置；不只審design，不把POC計畫留到外發後才看 |
| 3 | Designer定版 | 對齊Reviewer結論，固定設計／POC比較流程、案例與rubric、變因、量測端點、次數、執行上限、parity與交付要求 |
| 4 | Designer交付既有LLM POC團隊 | 記錄exact package SHA、baseline ID、交付位置／receipt；M4B-MVA-POC正式Open，Developer／Tester尚不得進場 |
| 5 | POC依定版計畫執行並交付結果 | exact implementation/plan/config identity、完整有效量測、人工quality、限制與建議；gate仍Open |
| 6 | Designer審核並採用结果 | 符合§3後記錄Accepted結果、最終產品profile與採用理由，明確解除M4B-MVA-POC gate |
| 7 | Developer／Tester進場 | Tester開始TR_spec_M4B_IV修訂，Developer估點拆包；對應test spec coverage簽核後才實作，後續candidate／驗收依原workflow |

步驟3固定的是「要測什麼、如何測、如何判讀」，不要求先知道步驟5才會產生的量測值。
未定token/capacity/prewarm等項目必須明列為量測輸出與Designer採用決策，不以猜值冒充定版。
步驟4以前不是gate已解除，而是設計準備階段；Developer／Tester均不因部分設計穩定提前進場。
先前允許提前寫spec draft、拆部分產品實作的建議由本USER決策取代。
Designer本輪已建立的TR_spec是待啟動handoff，不代表Tester已進場。
Developer原IR的requestor複審不另成為步驟1–6的進場工作；必要意見由既有紀錄供Reviewer判讀。

步驟4交付後，POC可依已定版範圍建立runner／凍結執行snapshot並進行bounded量測；
不額外增加一個常規「POC先回計畫、Core再准許執行」gate。
若POC發現計畫不可執行或需改產品語意／比較面，回Designer處置且gate保持Open。
改架構/design/POC計畫的實質delta交Reviewer聚焦補審，Designer發新版再交付，
不重開未受影響面。純粹依定版方法實作runner不要求重審整套設計。

## 3. Designer result acceptance / release

Designer一次核對：

1. 身份與完整性：result指向交付baseline與exact runner/config/model/runtime/target；
   缺sample、invalid run、cleanup failure不可當PASS。
2. 產品等價性：Conversation、semantic output、Reasoner政策與量測端點符合定版計畫；
   LLM-only只能支持子系統claim。若不能完成所需Audio/E2E範圍，該項仍Open，
   除非USER明確同意範圍修訂；不得以TTFT代替整體audible latency。
3. 品質：人工rubric與自動contract分開，錯誤/fallback不計正常性能PASS；
   有限case證據不宣稱模型全領域語意正確。
4. 採用：token/output/KV/capacity、prewarm、watchdog與產品目標皆有明確disposition，
   更新最終Core profile／設計／Tester handoff，不留需Developer猜測的blocking TBD。
5. 目標：2–3秒／10秒可修訂；miss先分析、改善或提USER採用新目標，
   不自動判整個計畫no-go，也不因可調整而自動通過。原結果與歷次目標全部保留。
6. 記錄：Designer acceptance response/ACK列baseline/gate ID、result full SHA、
   accepted scope、remaining advisory、profile digest及明確「gate released」；
   只收到POC檔案或POC自稱PASS不能解除gate。

需要改產品共識或目標的採用由USER裁決；Designer完成具體分析後再提出，
一般工程值在已核准範圍內由Designer依證據定案。
Gate解除不等於M4B Accepted；Core產品仍需Developer實作、Tester exact-SHA驗收與Designer確認。

## 4. Current state

- Work/baseline：M4B-MVA / M4B-MVA-001（draft，尚未定版）。
- Current step：1；等待Architect修訂arch.md。
- Reviewer：尚未審核本次三面package；Designer不可代標PASS。
- POC：工作包已在Core準備，未交付，未執行；gate未到Open交付階段，進場仍鎖定。
- Developer／Tester：尚未進場；TR_spec_M4B_IV為deferred request。
- Next：Architect處理[AR_impl_M4B_I](../reviews/AR_impl_M4B_I.md)。
- 本文件不授權commit/push或目前跨repo交付；執行到步驟3/4時依既有USER／repo規範交付。
