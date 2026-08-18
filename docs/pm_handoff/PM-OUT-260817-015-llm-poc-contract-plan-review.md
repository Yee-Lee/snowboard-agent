# M4b LLM POC contract 與執行規劃補強

- **Handoff ID** : `PM-OUT-260817-015-llm-poc-contract-plan-review`
- **Status** : `Ready for PM`
- **Related contract** : `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Reviewed Core candidate** : branch `dev_agent_m3`, HEAD `c559e5cf65d20676696293f06f1e5bc2afd02ae6`
- **Reviewed POC planning** : branch `llm`, HEAD `4ac7ba3941077babf34c7c575003a65f5c541009`

## 結論

LLM POC 的候選選型、Ubuntu 初篩、Pi 5 驗證、persistent child、offline、resource 與 evidence 方向合理，不需重作整份計畫。但現行M4b contract的P1～P12仍有cancellation level、M4a dependency、產品輸出契約與acceptance matrix等衝突或未定事項；這些屬Core產品裁決，不應交由POC團隊自行解釋。

Core須先把contract裁決commit在response與適用的權威產品文件，再由PM交付該committed outcome，讓POC團隊自行補強milestone、harness、tests與evidence schema。在裁決完成前，POC可整理Gate 0文件與不依賴裁決的scaffold，但不得凍結Gate 1 acceptance packet、啟動Pi Gate 2或自行宣告爭議項目PASS。

## 必做裁決

### `OUT-M4B-2026-002` — Blocking — Cancel escalation與產品架構不一致

- P6要求cooperative cancel於500ms內恢復READY；P7把SIGTERM稱為Level 2、SIGKILL稱為Level 3，但權威 `docs/arch.md` 將terminate / 必要時kill / waitpid都定義為Level 2 `force_abort()`，Level 3是force-abort或rebuild失敗後讓產品process退出並由systemd重啟。
- 修訂contract，使Level 1 cooperative cancel、Level 2 terminate->kill->waitpid->rebuild/READY barrier、Level 3 process exit/systemd restart與產品架構一致。
- 裁決native cooperative cancel不可用但成功升級Level 2時，候選是否仍可成為winner；覆蓋cancel success、cancel timeout、force-abort success及rebuild failure。

驗收：contract、`docs/arch.md`、M4 milestone、POC Test ID與no-go table使用同一套Level語意。

### `OUT-M4B-2026-003` — Blocking — P9依賴M4a但缺少可執行Gate

- P9要求M4a ASR/TTS與M4b同時常駐，但未指定Accepted M4a baseline、owner與取得方式；P9標題稱模擬，內容要求實際M4a。P10的20 sessions也未說明是LLM-only或M4a+M4b combined soak。
- 固定P9 prerequisite、4GB / 8GB target、正式M4a baseline、RSS/PSS/system memory口徑、swap、threads、thermal、throttling與latency evidence。
- 未取得Accepted M4a時P9必須為 `Blocked`；surrogate只能作規劃，不能取代正式PASS。固定P10 workload與combined session範圍。

驗收：POC可依contract直接判斷何時能執行P9/P10，以及何種證據足以PASS。

### `OUT-M4B-2026-004` — High — P2/P3不足以證明產品輸出與fallback

- P2只有非空response / structured JSON，P3只有20組常用prompt，未完整涵蓋 `LLMResponse`、capability、P5 fallback與log hygiene。
- 固定 `speak/tool/rest`、payload、`next_perceptions`、capability allowlist、tool-intent-only，以及拒答、空輸出、壞JSON、unknown action的P5 fallback。
- Core擁有或核准fixture catalog、重複次數、validator、格式 / 品質門檻及prompt/raw output/payload不得入log的界線。

驗收：P2/P3具事前固定、可失敗的測試與明確pass threshold，且與M4產品語意一致。

### `OUT-M4B-2026-005` — High — P1～P12 acceptance matrix不完整

- 現行no-go table只將P1/P6/P7/P8/P9/P12列為winner必要項，未清楚處理P2、P5、P10、P11；P4雖為可協商目標，但量測方法尚未固定。Pi 5 4GB / 8GB是雙平台必過或分級target也不清楚。
- 將P1～P12分類為 `Mandatory`、`Conditional escalation`、`Negotiable performance` 或 `Informational`，並固定cold/hot、warm-up、prompt/output長度、P50/P95、power/cooling與有效soak定義。

驗收：每項結果都能依事前決定表得到PASS、FAIL、INCONCLUSIVE、Blocked或需Core threshold decision，不得看完候選結果才修改gate。

### `OUT-M4B-2026-006` — High — External Gate與POC內部規劃缺少唯一crosswalk

- POC規劃把External Gate 0與Internal M0合併，並同時使用D1–D6 / D1–D8；Gate 1 Ubuntu pre-screen尚未形成獨立可執行packet。
- Core committed contract revision須固定：Gate 0只作receipt / Initial Manifest收件與Core記錄；Gate 1包含frozen harness、candidate proposal與Ubuntu pre-screen，最多兩個finalist並經Core書面確認；Gate 2執行Pi P1～P12並取得final winner ACK；之後才進Core主線Gate 3。
- 提供External Gate->Internal Milestone->Delivery Area->P1～P12->Evidence唯一crosswalk。
- POC團隊全部修訂完成後只commit/push一次並通知PM；不要求其文件預填或指向自身SHA，由PM拉回後記錄branch HEAD。

驗收：POC能依Core已commit裁決自行更新權威milestone index、真實Initial Manifest、Gate 1/2 packet與evidence schema，且各文件狀態、owner、approver與dependency一致。

## Core回交要求

Core在產品repo提交：

- **Findings response** : `docs/outsource/responses/PM-OUT-260817-015-llm-poc-contract-plan-review.md`
- **必要的 `docs/arch.md`、M4 milestone及適用contract / test specification修訂**；若不需變更，明確聲明 `Architecture change: No` 並說明contract如何與現行架構一致。

Response須逐項定位 `OUT-M4B-2026-002` ～ `006` 的裁決、修改路徑、POC執行影響、M4a dependency owner與仍未決事項，內容或其引用的權威文件須足以讓POC直接執行，不要求POC自行解釋Core未決產品契約。

Core可自行決定是否另於 `docs/outsource/deliveries/` 發布POC-facing contract文件。若另發，response只引用其路徑、版本與適用範圍，不重複契約內容；若不另發，response與其引用的權威文件仍須完整承載上述裁決。是否另發delivery不是本handoff的acceptance條件。

## PM動作

PM只交付本 `brief.md` 給Core Team，不交付同目錄 `review_notes.md`。Core回覆並push後，PM拉回約定branch、記錄實際HEAD並通知Designer intake；Core裁決完成前，暫不交付POC-facing修訂要求。Core若選擇另發delivery，由Core在response聲明；PM不把delivery文件是否存在當成收件gate。
