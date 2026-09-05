# REQUEST-LLM-POC-M4B-MVA-MEASURE-001 — MVA product-parity measurement

- Date: 2026-09-05
- From: Core Designer
- Intended owner: LLM POC Team；需要Audio parity時由POC協調Accepted Audio package
- Status: FROZEN FOR DELIVERY / REVIEWER PASS / NOT DELIVERED
- Work / baseline / gate: M4B-MVA / M4B-MVA-001 / M4B-MVA-POC
- Basis: [M4B-MVA design](../../implement/ch_m4b_llm_production.md)、IR_dev_M4B_III
- USER direction: 工程量測優先POC；性能門檻可修訂，miss不代表放棄整個計畫。

## 1. Purpose and responsibility

量測M4 MVA短句對話：雪板身分、一般知識、當前能力、同session追問與明確結束。
Core固定產品語意与首選semantic text/end輸出；POC不得自行決定Reasoner政策或記憶架構。
Developer不承擔參數試錯，Tester不反覆執行探索；POC不取代Core exact-SHA acceptance。
本計畫與arch/design一同由Reviewer審查，Designer定版後才交付；交付使gate Open。
POC依定版範圍建立runner、凍結執行snapshot後量測，無額外常規plan再授權gate。
七步流程及release條件見[M4B-MVA gate](../../milestones/M4B_MVA.md)。
回交結果只有經Designer審核／採用並明確解除gate，Developer／Tester才能進場。
本文件未複製至外部repo，無執行/發布/跨repo寫入授權。

## 2. Required parity before measurements

| Surface | Required declaration / evidence |
| :--- | :--- |
| Hardware/runtime | Pi5 4GB、OS/CPython/backend/threads、exact Gemma/LiteRT artifacts與SHA |
| Product facts | 雪板／語音小助理、繁中短句、listen/speak目前可用、無look/tool；同Core SessionFacts |
| Model interface | exact text/end constrained schema；一次LLM call；Reasoner deterministic speak/listen or rest |
| Lifecycle | one active Conversation per product session；正常turn reuse、end/discard、dirty session end |
| Prompt/token | 完整system/user template bytes與hash、exact tokenizer、new-user/incremental/KV/output分項 |
| Controller cost | session create/close、IPC、parse/validation計入caller TTC；未模擬的Core成本標明 |
| Audio integration | 只有exact Accepted Audio/VAD/ASR/TTS/HAL/config＋可驗證onset方法才可聲稱M4 E2E |
| Trust/recovery | install generation、initial full verification、same-install replacement驗證策略與完整timing |

先提供runtime API proof：reuse下render/token_count/response constraints/close/cancel真實語意；
不得把先前0.14/0.15問題或非選定platform當exact-product缺陷。
若不能取得product Audio/physical onset量測，縮小claim為LLM subsystem；
交付缺口由Core另外發包，不能拿TTFT或host benchmark填M4卡。

## 3. Frozen comparison plan

執行前先commit development catalog、prompt/schema/profile/runner hashes、case order、repetitions、
raw sanitized result schema、scope exclusions，並回報該exact SHA。Case輸入與輸出上限固定；
每個session至少有opening＋follow-up，包含第一輪與後續輪耗時。
本次實驗envelope固定user-new admission 32 tokens、maximum output 128 tokens、Engine KV
1024 tokens、temperature 0、top-p 1、CPU backend 4 threads；32只限制每turn新user input，
不限制system prompt或累積context。exact tokenizer判定catalog任一輸入超界時，在inference前
標Blocked並回Core，不臨時放寬。這些是單一變因比較的受控實驗值，不是已核准產品limit；
多turn結果須回報實際rendered/incremental/KV/output token分項供Step 6採用。

Baseline = M4B-MVA same-session reuse、compact text/end、no disposable inference prewarm。
唯一主要變因 = disposable public inference prewarm none/once；
prewarm完成後Conversation必須丟棄，後續product session另開。
可用舊fresh/full-envelope一次sanitized diagnostic作reference，但不混入主要A/B樣本。

- Cold boot：每mode三個獨立reboot；固定cache/環境條件與mode順序，禁止同次boot冒充cold。
- Same-boot replacement：每mode五次fresh process/Engine；條件、等待時間、cache狀態記錄一致。
- 每次都量READY總耗時、下一個product request TTFT/TTC、同session第二輪TTC。
- Timing固定公開兩turn：`天空為什麼是藍色的？`→`再簡單一點。`；prewarm若啟用固定
  `請用一句話打招呼。`，其Conversation完成後丟棄。cold固定順序N1/O1/N2/O2/N3/O3，
  replacement固定N1/O1/.../N5/O5（N=none、O=once）；不得依前次答案更換prompt、
  mode或重排有效樣本。
- Repetitions是描述性sample，報每筆與median/range；不以小樣本推論可靠P95或顯著收益。
- Hard operational bounds：每啟動120秒、每generation30秒、每mode runner1800秒；
  watchdog觸發保存sanitized outcome並cleanup，不能以延長timeout把原結果改PASS。
  這些僅POC execution watchdog，不是Core product SLA或最終production值。
- 主要matrix完成前不增加其他prompt/schema/profile變因；需要改surface先回Core修訂plan。
  目標miss不自動觸發模型淘汰、无限tuning或全計畫no-go。

## 4. Memory and recovery observations

同一selected baseline完成三個fresh-child周期；每周期20個完整product sessions，
每session固定使用上述公開兩turn，第二turn terminal後由controller正常close；依session 1–20
順序執行，不因attempt8/16主動recycle。
逐turn及session clean-terminal記unique-owner PSS、MemAvailable/system-used、swap、
OOM/throttle/temperature、KV tokens與child generation，startup/first allocation亦保留。
每周期bounded7200秒；遇OOM、不可收斂、swap或thermal violation保留failure並停止該周期，
不得為取得plateau忽略資源保護。runner安全線固定為每筆`MemAvailable >= 512 MiB`
（等價`MemTotal - MemAvailable <= MemTotal - 512 MiB`）；低於安全線即停止新session、
完成bounded cleanup並把該周期標Fail。這是POC執行保護，不是Core產品capacity reserve。
任何swap使用量增加、OOM/kernel fault、`get_throttled != 0x0`、溫度>=80°C、identity drift、
sampler失效或cleanup無法證明，同樣停止該周期並保留既有樣本。

交付完整trajectory。每周期預先固定session 11–20的十筆clean session-terminal sample為
steady analysis window；不足十筆即該周期Incomplete，不改選其他窗口。
對owner PSS及`MemTotal-MemAvailable`各報十筆、ordinary least-squares slope（MiB/session）、
session 11–15與16–20的median及late-minus-early delta；三周期分開報告，不合併掩蓋差異。
分開startup allocation、session內KV growth、session結束後resident retention。
不得事後挑最好窗口或刪warm-up samples；分析窗口可分開但全資料保留。
提出MemAvailable headroom與需要時的owner上限，說明Audio composition與最壞turn所需reserve。
受控recovery另做三次：在selected baseline為READY_NO_SESSION且無active session時，
以test-only hook注入`reason=capacity_test`的同key replacement request，不製造實體記憶壓力；
量從controller接受request到新child完整READY並可接受新session。逐次驗舊owner退出、
single-flight ticket、identity及barrier；不要求自然soak硬湊三generation。
若低capacity由Audio/系統占用主導且LLM replacement不解決，明記，不用recycle loop掩蓋。

## 5. Manual semantic quality

Development例：
「請問你是誰？」→身份雪板/語音小助理；
「天空為什麼是藍色的？」→基本科學正確的短解釋；
「你現在可以看到東西嗎？」→不虛構當前視覺；
後續「再簡單一點」「那你怎麼知道？」等驗continuity，另測明確結束與否定結束。

評估者在prompt/schema freeze後建立並保管12個未供調參的sessions，順序固定為
H01–H03身分、H04–H06知識、H07–H09能力、H10–H12追問；H03/H06/H09/H12
依序覆蓋明確end、否定end、明確end、否定end。每session至少兩turn。
逐例一次generation，no best-of、retry、literal repair、keyword/LLM judge決定PASS。
Rubric：身份一致、知識基本正確、能力誠實、指代/追問連贯、簡短、
end意圖正確。適用rubric皆Pass才算case Pass；錯誤/無法判讀明列Fail/Unclear，
Unclear由獨立人工複核，不算PASS。先固定參考事實／來源，禁止事後迎合答案改rubric。
只保存case ID/rubric/operator/time/sanitized reason；public catalog可tracked，
private audio/prompt/response只瞬時呈現給operator，不提交Git或回填raw answer。
人工Pass是有限案例證據，不宣稱模型全領域正確。

## 6. Deliverable and acceptance by Core

交付一個committed packet，含full SHA、plan/surface hashes、parity matrix、
sanitized每筆timing/resource結果、manual case/rubric表、invalid/missing/failed runs、
cleanup證據、推薦profile与限制。

每筆machine sample至少包含：run/cycle/mode/case/session/turn ID、UTC與monotonic時間、
完整implementation SHA及plan/profile/schema/config/model/runtime/Audio digest、platform/Python、
command、start/end/exit/status、READY/open/TTFT/TTC/close與caller TTC、各token分項、owner PID set與PSS/RSS、
MemTotal/MemAvailable/system-used/swap、temperature/throttled/OOM、typed terminal、cleanup status
及raw sanitized log path。缺值用`null`加reason；Invalid/Blocked/Fail仍保留同一schema與artifact。
人工列另含operator、六項rubric逐項Pass/Fail/NA、overall及sanitized reason，不存raw內容。
M4 E2E須同timebase的speech-end annotation→first meaningful audible onset；
ASR開始、PCM write、提示音皆不能冒充端點。TTFT、TTC、audible latency分欄。
Accepted Audio package或可驗證onset方法不可用時，audible latency填`null`並記
`scope=llm_subsystem`與缺口原因；E2E項維持Open，不得填0、估算值或以TTFT代替。
每個threshold miss保留原目標/實測/瓶頸/建議調整，Core/USER再採用；不重標舊POC machine FAIL。

Core一次審查身份、產品等價性、完整性、品質、可繼承範圍；
不足之處提供精確修正面，不讓Developer/Tester代替POC探索。
M4B-MVA產品candidate仍依既有Architect/Reviewer/Tester/USER commit gates。
