# M4a Audio POC 與 Core evidence inheritance / 產品化交接補強

- **Handoff ID** : `PM-OUT-260817-016-m4a-poc-core-evidence-handoff`
- **Status** : `Ready for PM`
- **Related contract** : `DELIVERY-AUDIO-POC-M4A-CONTRACT-001`
- **Related handoff** : `PM-OUT-260814-010-m4a-audio-poc-contract-gate`、`PM-OUT-260817-015-llm-poc-contract-plan-review`
- **Reviewed Core candidate** : branch `dev_agent_m3`, HEAD `c559e5cf65d20676696293f06f1e5bc2afd02ae6`
- **Reviewed Audio POC** : branch `dev_audio_m2`, HEAD `aad41ce13333bdf94bf6d6ab0996f83982f9f0b1`
- **Cross-team coordination owner** : Core Team（直接與Audio POC Team對齊）
- **Internal tracking owner** : PM / Designer（只收件並追蹤committed outcomes）

## 結論

現行Core M4a contract在Gate 2 winner ACK後直接開放Gate 3；Audio POC流程則在其M4才完成20-session組合、offline、failure injection、final handoff與 `POC Accepted`。兩邊皆要求Pi、lifecycle、resource與offline驗證，卻沒有規定POC M4如何成為Core可繼承的reference package，也沒有區分POC evidence與產品exact-SHA必須重驗的delta，會造成POC M4成果孤立或Core重做候選驗證。另P1～P12目前只有驗收清單，尚無已commit的Gate 2執行計畫；候選取得、wrapper / 共同harness、VAD / ASR / TTS工作流、Pi session、User review、M4b前置條件、evidence與exact-SHA切點均尚未排入可執行work package。

Core須主動與Audio POC Team協調，直接修訂既有權威產品文件並提交單一findings response，保留Gate 2後可開始產品開發的並行性，但固定POC M4 Accepted handoff的引用位置、evidence inheritance matrix與portable conformance kit。POC evidence不得取代Core Tester對產品SHA的獨立驗收；Core也不得無理由重跑候選比較或重新定義已凍結fixture / metric。內部不代傳遞純技術問題，只追蹤兩邊repo已commit的決定、交付、branch / 完整SHA與gate結果。

## 必做修訂

### `OUT-M4A-2026-002` — Blocking — Gate 2、POC M4與Gate 3缺少交接關係

- 明確區分Gate 2 final winner ACK可放行的「產品開發 / adapter scaffold」，以及POC M4 Accepted後才能固定的final reference package、dependency/model baseline與Gate 3 exit prerequisite。
- 固定流程：Gate 2 ACK -> Core可並行開發；Audio POC完成M4並取得POC Accepted -> Audio POC將final handoff ID / accepted POC SHA直接交由Core intake並納入Gate 3 delivery；Core Tester再對產品exact SHA完成驗收。PM / Designer只依兩邊committed outcome更新追蹤狀態。
- 若Core選擇不同分段名稱，仍須提供唯一External Gate <-> Audio M2/M3/M4 <-> Core Gate 3 crosswalk，明列entry、exit、owner、阻擋範圍與change-request回流。

驗收：POC M4新發現winner、resource、offline或lifecycle blocking問題時，contract能直接判斷Core Gate 3哪些動作可繼續、哪些baseline / acceptance必須停止或重開。

### `OUT-M4A-2026-003` — High — 缺evidence inheritance與product-delta驗證矩陣

- 對M4A-P1～P12及Audio POC M4 delivery areas逐項分類：`Inherited from accepted POC SHA`、`Reused test asset / rerun on product SHA`、`Product-only validation` 或 `Not reusable`。
- Candidate版本 / artifact checksum / license、frozen fixture / metric、品質比較與rejected reasons原則上由Accepted POC handoff引用；產品adapter/HAL wiring、production config / lock / packaging、RM / SM lifecycle、實際composition、產品資源與產品exact-SHA regression必須重驗。
- 定義引用欄位與狀態語意：POC handoff ID、Accepted POC SHA、manifest / evidence path、fixture / metric revision與checksum、被測產品implementation SHA、繼承理由、delta test與結果。不得只寫「沿用POC」或把POC自驗當Core Tester PASS。

驗收：Core Gate 3 delivery可逐項回答「引用哪個immutable POC evidence」及「在產品SHA額外驗了什麼」，沒有重複candidate comparison，也沒有省略產品整合風險。

### `OUT-M4A-2026-004` — High — 缺portable conformance kit與可重用邊界

- Core權威產品文件須規定Audio POC final handoff至少包含：candidate lock/provenance/license、adapter protocol、fixture / prompt ID與checksum、expected result schema、lifecycle / failure scenarios、cleanup assertions、offline check、resource量測方法 / budget、20-session結果、known risks與evidence index。
- 明確區分可重用的protocol / schemas / test vectors / validators / tests，與不得直接進產品主線的benchmark orchestration、raw audio、model、wheel、`.so` 及受控artifact。
- Core產品delivery須引用該kit的版本 / SHA並回交POC->product conformance mapping；若未沿用某項可重用資產，說明產品差異與替代驗證，不要求POC團隊代寫Core private implementation。

驗收：同一組事前固定的test vectors、metrics與assertions可套用於POC wrapper及Core product adapter；產品團隊只替換backend / composition並補product-delta evidence。

### `OUT-M4A-2026-005` — Blocking — Gate 2 P1～P12缺少可執行交付計畫

- Core須直接與Audio POC Team完成External Gate 1 / 2 <-> Audio M2 / M3 / M4 <-> P1 ~ P12 crosswalk；Audio POC在自己的repo提交權威Gate 2執行計畫，Core直接把相符的dependency / review規則寫入既有權威產品文件。不得由內部代寫POC private implementation。
- 計畫至少涵蓋：work package、owner、dependency、順序、估算 / 吞吐假設、entry / exit與re-estimation trigger；candidate eligibility / provenance / license / artifact取得及offline aarch64 build；共同protocol / wrapper / harness / schema / test vector / cleanup；VAD、ASR、TTS與User TTS review；M2隔離評測、M3 Pi / HAL P1～P12、M4組合交付的證據分界；Pi session、M4b stub / accepted baseline前置條件；raw / sanitized evidence、受控artifact / checksum、delivery ID與exact-SHA cut point；failure / no-go / change-request與fallback。
- Gate 1 proposal可先準備；在本計畫獲Core書面接受前，不得將Gate 1視為已核准，也不得開始真實候選下載、build或benchmark。

驗收：P1～P12每項均可定位owner、producer、prerequisite、platform、fixture / input、command / runner、output / evidence path、decision rule、cleanup及exact-SHA binding；Core response列出Audio POC committed plan path / branch / 完整SHA及Core權威文件修改路徑 / 完整SHA，沒有任何項目只標示「之後規劃」。

## Core回交要求

Core與Audio POC Team直接完成技術對齊後，由Core直接修訂 `docs/milestones/M4.md`、`docs/reviews/milestone_progress.md` 及適用的M4a test / model specification；若影響架構owner、public contract或lifecycle，修訂唯一 `docs/arch.md`，否則聲明 `Architecture change: No` 並說明理由。

本輪只新增一份正式提交文件：

- **Findings response** : `docs/outsource/responses/PM-OUT-260817-016-m4a-poc-core-evidence-handoff.md`

不另建內容重複的delivery addendum。權威契約內容留在既有產品文件；response只負責逐項finding對照、列出修改路徑、Audio POC committed plan path / branch / 完整SHA，以及本輪Core完整SHA。

Response須逐項定位 `OUT-M4A-2026-002` ～ `005` 的裁決、修改路徑、POC與Core各自影響、inheritance/delta分類、Gate 2執行計畫、未決事項及comparison baseline，並列出Audio POC repo中對應的committed outcome path、branch與完整SHA。討論、會議或聊天不構成收件；只有兩邊repo已commit的contract / response / handoff才納入內部追蹤與後續acceptance。

請提交單一reviewable commit，於response列出文件變更、驗證方式與完整被測implementation SHA；若Core自行另發delivery則只需引用。PM拉回後另通知repo HEAD完整SHA。

## PM動作

PM只交付本 `brief.md` 給Core Team，不交付同目錄 `review_notes.md`。後續跨團隊問題與契約對齊由Core Team直接和Audio POC Team處理；PM不代傳達純技術內容。Core與Audio POC各自push committed outcome後，PM拉回兩邊約定branch、記錄完整HEAD SHA並通知Designer；內部只做exact-SHA intake、finding / gate狀態與dashboard追蹤。
