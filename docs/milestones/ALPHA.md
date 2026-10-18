# ALPHA 規劃 ── Voice-only 產品化收斂 Gate

## 定位

`ALPHA` 是 M4 Accepted 後、M5 開始前的 Voice-only 產品收斂 Gate，不新增產品能力，也不重做
M4a／M4b／M4c 已 Accepted 的 subsystem qualification。現行計畫對齊五大項 L／P／R／Q／M，回答五個產品問題：

1. 正式 App 能否重複完成 Session、清理、關閉並再次啟動；
2. 使用者可感知的時間花在哪個階段，是否有明確且值得處理的瓶頸；
3. 整機在一次代表性的 LLM streaming failure 後能否恢復並完成新的正常 Session；
4. 基本 Voice-only 品質六項是否通過；
5. 真人透過正式入口自由對話、實際操作與再次使用是否可用。

M4 Accepted 與 ALPHA Accepted 分開記錄。ALPHA 使用 M4 Accepted product path，不以新功能、長時間
soak、resource research、manifest 重驗或額外角色簽核擴張本 Gate。

條件式 ASR Product R1 仍是另一條完整候選線；後續只有 baseline selection 選定的一個 Accepted
exact SHA 可進入 M5。見 [`ALPHA_R1.md`](ALPHA_R1.md)。

## ALPHA current goal and exit criteria

目標：交付可正常重複使用、出錯後可恢復、回答具最低可用品質的本機 Voice-only App，
並把使用者等待的耗時與改善結論說清楚。不新增 tool／Vision／service 或廣泛知識 qualification。

| Required boundary | PASS／completion means |
| :--- | :--- |
| Lifecycle（L，§3） | 三個 Sessions × 兩個 Turns、逐 Session cleanup、shutdown／owner release、restart，及內含 offline／一次 public privacy scan 通過 |
| Performance（P，§4；本輪工作包 ALPHA.P） | 完整有效計時、自動多輪對照、原因分析、至多一項優化的採用／不採用結論、適用 regression 與人工體感複驗完成；無固定秒數門檻，不要求一定改程式 |
| Recovery（R，§5） | 一次真實 LLM-child streaming failure 後清理、replacement、下一正常 Session 與最後 owner release 通過 |
| Quality（Q，§6） | ALPHA.P 完成後在最後候選完成六項：身份、簡單事實、能力誠實、短指令、同 Session context、明確結束；各項客觀流程與修訂最低可用性 rubric 都 PASS |
| Manual（M，§6A） | 最後版本真人自由對話、多輪、Session 再次使用、Display／聽覺與正式停止可用；USER 體驗確認及適用操作結果完成，與 PH 的固定效能腳本分開記錄 |

五項完成且所有適用驗證對應同一最終產品內容，才可記 ALPHA Accepted。交付固定安裝入口、
必要自動 runner、分析／測試結果定位與已知限制；新增 commit 仍按 git 規則另取得 USER 同意。
本輪重新展開 P 與 M；P01–P05 定義／結果保留，新 P 子項是 PNxx 自動分析與 PHxx 配對真人複驗，
PN／PH 都不增加第六大項。L／R／Q 不重設計，修正後按影響面回歸，最後同版本完成既定驗證。
先前品質「接受現況」只記錄既有體驗及限制，不取消最後六項 regression，也不把舊 FAIL 改成 PASS。

## 1. Accepted inputs

- M4A：正式 ASR／TTS／Audio backend、HAL ownership、offline 與 privacy 基線。
- M4B：正式 LiteRT-LM／Reasoner、Conversation、constrained terminal response 與 monotonic timing nodes。
- M4-ERR：typed fault、Level 1／2／3 convergence、backend rebuild、recovery barrier 與 fatal exit。
- M4C：正式 Button → Listen／ASR → LLM streaming → TTS／Audio → Session close 路徑、Session Display、
  B2 streaming speak、no-input、interrupt、shutdown 與 owner cleanup。

Accepted 歷史不因 ALPHA 的精簡範圍重開。ALPHA 只驗下列 product-convergence delta。
M4C Accepted 文件中把未來 soak、latency ceiling、resource／thermal 收斂交給 ALPHA 的前瞻性文字，
由本文件的 USER-approved ALPHA scope 取代；這不修改或重開 M4C 的既有結論。

## 2. Scope and exclusions

### 2.1 Included

- 正式 launcher 的 startup、`IDLE`、graceful shutdown 與 restart。
- 三個連續 Product Sessions；每個 Session 兩個 Turns，並在下一個 Session 前完成 cleanup。
- P：保留原 P01–P05，加入 PN／PH 配對分析、必要原因對照及至多一項改善。
- 一個真實 LLM child streaming failure、recovery 與下一個正常 Session。
- ALPHA.P 後一次六項修訂品質 regression；保留既有品質觀察，舊題停用、舊 FAIL 不改寫。
- M：正式安裝入口的真人自由對話與操作體驗；既有結果收錄於 §6A，本輪在最後版本複驗。
- Offline 與 privacy 作為 lifecycle run 的共同條件，不建立獨立 Test ID。

### 2.2 Excluded

- MQTT／external message／實際 tool dispatch（M5）。
- Voice wake／Vision（M6）。
- 正式動畫、完整 icons、Progress UI 或生產級 assets（M7）。
- systemd／supervisor／update／rollback 新實作；ALPHA 只驗交付的 external launcher。
- Raspberry Pi OS shutdown、factory reset、GA 或 production-release 等同語義。
- 20 Sessions、單一 Session 20 Turns、兩小時 soak 或長期穩定性宣稱。
- 2 秒／3 秒 response gate、10 秒 recovery gate或任何新 latency acceptance threshold。
- Memory、PSS／RSS、swap、PSI、CPU、thermal、capacity 或 resource trend 研究。
- Hardware／config／model／runtime／dependency／license／checksum／manifest 重驗。
- ASR／LLM／TTS／Audio fault matrix重跑、abnormal-shutdown matrix或全部Level 1／2／3排列。
- POC-trigger review、candidate freeze assertion、通用 close-proof、額外Designer sign-off或Code Review gate。

若正式執行實際出現 OOM、throttling、卡頓或其他產品故障，依具體症狀另開聚焦診斷；不預先把
system research 變成 ALPHA 測項。

## 3. `ALPHA-L01-LIFECYCLE`

### 3.1 Purpose

證明正式產品可完成：

```text
startup → 3 repeated Sessions → per-Session cleanup → shutdown → owner release → restart
```

三個 Sessions 是短期 repeated-use coverage，不得描述為 soak 或長期穩定性證明。

### 3.2 Execution

1. 在 network-disabled 的正式產品設定，以交付的 launcher 啟動 App。
2. 等待 required resources READY；App 進入 `IDLE`，Display Status=`待命`、Main為空，且尚未建立
   Conversation。
3. 在同一 App process 連續執行三個固定 Sessions；每個 Session 恰有兩個 Turns：
   - Turn 1 使用已實測的 `FX-SHORT-A`「一個星期有幾天？」，完成真實
     Button → Listen／ASR → LLM → TTS／Audio；
   - Turn 2 由既有`KEEP_NEXT`轉移進入，不再發出Button；使用 `FX-NORMAL-END`「現在請結束對話。」，若合法
     terminal含文字則完成TTS／Audio，若無文字則依既有契約直接REST，之後完成
     Conversation close與Session end。
4. Session 2 只能在 Session 1 cleanup完成後開始；Session 3同理。
5. Session 3 cleanup後，使用正式產品操作要求 graceful shutdown。
6. 確認 process退出後，以同一launcher再次啟動至乾淨`IDLE`；restart後不再要求額外Session。
7. 結束後對整個run的公開log／evidence做一次aggregate privacy scan。

### 3.3 Required observations

每個 Turn 必須完成真實 ASR → LLM，且依合法terminal route完成必要的TTS／Audio或直接REST；每個
Session 結束時必須同時成立：

- active Conversation 已close，session-owned task、streaming control、queue與in-flight operation歸零；
- 沒有late audio、stale Fact、provisional fragment或前一Session內容進入下一Session；
- Display回到`IDLE`／`待命`且Main清空；
- persistent backend可以存活，但PID集合不得因新Session增加。

Shutdown後必須同時成立：

- App process與全部產品child PID退出；
- 無ALSA holder、Display fullscreen owner或其他產品hardware owner殘留；
- exit code為既有graceful success值；restart使用新process並重新進入`IDLE`。

Offline／privacy只在本run驗一次：

- external network attempt與network fallback均為0；
- 公開log／evidence不得含transcript、prompt、raw model output、credential或完整audio payload；
- 固定測試fixture identity、boolean／count／stable code與必要timing可以保存。

## 4. `ALPHA.P` — 效能分析實驗與改善

`ALPHA.P` 是 USER 命名的 ALPHA 內部工作包；本節是其唯一設計 authority，不另建平行 milestone、
handoff 或 summary。既有 `ALPHA-P01-PERFORMANCE` Test ID 與 P01–P05 保留，本輪不重開、
不改寫既有結果；它們仍可供後續依原定義驗證。新一輪使用 PNxx 自動分析與一對一 PHxx 人工複驗，
同屬現有 Performance run，不另開產品版本線、頂層 Test ID 或 approval gate。

### 4.1 Purpose and verdict boundary

本run只建立可解釋的使用者路徑baseline並定位主要耗時，不建立數值Pass門檻。有效結果必須完成
固定流程、保存完整monotonic timestamps並保留所有failed／invalid observations；不得以平均值、
best-of、刪除慢樣本或改變fixture產生較好結論。

Performance與Lifecycle分開執行，避免量測fixture扭曲repeated-session驗收，也讓before／after可以
獨立重跑。Performance run不重做完整lifecycle、privacy、fault或resource驗收。

### 4.2 Retained P01–P05 controlled-run definition

下列保留既有 P01–P05 的定義與實測 fixture，供歷史對照及後續驗證；本輪 ALPHA.P 不自動重跑
或擴寫它們，新一輪依 §4.5 的 PN／PH 執行。原受控流程使用固定 PCM／prompt，一次 fresh startup
及兩個 Sessions：

| Case | Execution | Required measurements |
| :--- | :--- | :--- |
| `P01-STARTUP` | fresh process start至`IDLE` | process start、config complete、各required resource ready、App `IDLE` |
| `P02-FIRST-TURN` | Session A／Turn 1，固定短輸入 | Conversation ready、speech end、ASR final、LLM send、first safe text、LLM terminal、TTS first PCM、Audio first positive write／complete |
| `P04-FOLLOW-UP` | Session A／Turn 2，固定追問 | previous action complete、next perception start、ASR final、LLM send、first safe text、terminal、input／context token counts、Audio complete |
| `P03-WARM-SESSION` | Session B／Turn 1，與P02匹配的固定輸入 | new Conversation ready及P02同組ASR→Audio節點；明列重用的engine／child identity |
| `P05-STREAMING` | Session B／Turn 2，固定多fragment回答 | 每個fragment admission、queue wait／depth、每次TTS start／first PCM、Audio區段、LLM terminal、final drain |

P04完成後以固定normal-end fixture關閉Session A並等待cleanup，再開始Session B；P05完成後同樣關閉
Session B。這兩個close turn不屬於performance case，也不納入before／after數值。

P02／P03共用 `FX-SHORT-B`「一個星期有幾天？」；P04使用 `FX-FOLLOW-UP`「請再簡短回答一次。」。
P05與`ALPHA-R01-LLM-RECOVERY`共用已實測的 `FX-MULTI-FRAGMENT`「請列出三個滑雪安全重點。」。
它必須經真實ASR並通過現行20-codepoint／32-token admission進入真實LLM；不得移除
ASR輸出標點、繞過admission或把input-limit R1當成LLM回答。

不同case只保存其需要的節點；不得為欄位整齊而虛構不存在的event。量測工具不得增加產品Event、
Fact、state transition或改變streaming boundary。

### 4.3 Bounded optimization

- Baseline與耗時分解是ALPHA必要輸出。
- 程式修改不是預設exit condition；沒有明確、可定位且具產品影響的瓶頸時，保留分析與不採用
  優化的理由。`ALPHA.P` 仍須完成 §4.6 的自動對照、人工複驗與適用驗證，不能只憑 baseline 結案。
- 若存在明確瓶頸，只建立一個bounded improvement work item，以相同 PN／PH 設定做 before／after。
- Before／after必須報告所有直接受影響節點；沒有超過量測誤差的穩定改善時不得宣稱改善。
- 任何採用的變更必須重跑直接受影響的Lifecycle、Recovery、Quality與portable regression；不得以
  performance數字取代功能驗證。

### 4.4 Next round: first-response diagnosis and experiment

本輪 Developer 已交付 `19d9ca2`。修復後真人測試最近 S1/T1 的 ASR final → first positive audio write
為 13.333 s，LLM send → first safe text 為 12.762 s；其餘有完整 LLM 節點的 Turns 約為
1.533–2.202 s。這是首次回答偏慢的線索，不是 warm-up、prefill 或模型缺陷已證實的結論。
現有 text logger 截斷至 512 characters，且缺少真人 speech end；不得以缺失節點推算原因。

價值／風險：首次回答等待直接影響使用體驗，不完整計時可能把優化選到錯誤階段。先完成量測與
原因判別，再決定至多一項程式優化；不新增 resource／thermal 研究或重新設計已修好的中斷流程。

1. **完整計時**：以不受 text logger 截斷的 structured timing-only observation 保存 §4.5 PN／PH 所需節點，
   區分 fixture speech end、ASR endpoint／final、Conversation ready、LLM send、first safe text、
   terminal、fragment／queue、TTS first PCM、Audio first positive write 與 final drain。Public 只保存
   必要 timing、boolean、count、stable code，不保存文字／PCM、不關閉 privacy redaction。
   Fixed PCM speech end 是受控輸入邊界；真人 speech end 或 acoustic onset 未量測就標 unavailable。
   Audio write 不等同使用者已聽到聲音；平行階段分開報告，不把重疊耗時相加。
2. **匹配 baseline**：新建 PN01–PN05 及 PH01–PH05，固定 prompt／題目／設定，比較 fresh process 首次 Turn、同一
   Conversation follow-up、同一 engine／child 的新 Session。對照 live 與受控結果的 endpoint、
   輸入方式差異；不得以先前受控 LLM 約 2 秒推定 live 12.762 秒的原因。
3. **原因判別實驗**：若 baseline 仍指向 LLM，利用 backend 可取得的直接節點區分 child 收到
   request、render／prefill、首個生成輸出、safe-text extraction。無法取得的 native 階段標未知，
   不用整段等待替代 prefill 時間。記錄 input／context token counts 與 engine／child 重用狀態。
   用同一短輸入對照 fresh-process first Turn、同 process 後續 Turn、新 Session、另一次 fresh
   process first Turn，區分 process-first、Session-first、輸入／context 差異。Tester 事先固定最少
   對照次數與量測誤差評估；只有原因仍無法區分時才加一個能排除具體假說的對照。這是單一瓶頸
   診斷，不增加產品 Test ID、soak 或全套重跑；保留全部樣本，不挑最快值。
4. **一項改善實驗**：Developer 依證據列出原因、可改位置、預期改善節點、成本與功能風險，再選
   一項 bounded optimization。Before／after 固定輸入、環境、first／warm 狀態，以相同方法與足以
   評估穩定性的預定對照次數報告全部樣本、誤差，以及 startup／後續 Turn 的代價；改善未超過
   誤差或造成直接功能 regression 就不宣稱改善。無可證實原因或低價值時不硬做優化。
5. **交付安排**：Designer → Tester 同步本節計時／實驗判定與 §6 品質決定 → Developer 量測與
   至多一項改善 → Verify。完整 ALPHA 結案 Verify 留待效能工作後，在單一最終候選完成仍適用的
   Lifecycle／Recovery、有效 Performance 與直接受影響 regression，不拼接舊候選或重跑退役品質題。

### 4.5 PN automatic analysis and matched PH human verification

P01–P05 及已取得的數值完整保留。本輪新建 PN01–PN05，仿照其五種產品情境，加入此次首次慢回答
所需的分析；PH01–PH05 以相同題目、順序、first／warm 狀態與計時定義做真人麥克風複驗。
PN 與 PH 各以 fresh App 開始，不能先跑 PN 暖過 engine，再把未重啟的真人測試當 PH first Turn。
改善前先完成一組 PN／PH，確認真人症狀與差異，再決定是否優化；如試驗變更，以相同設定完成 after PN／PH，
再依結果採用或不採用；最後保留版本沿用其適用結果。無優化實驗時不製造一組 after。

| Automatic／human pair | Matched execution／question | Added analysis and observation answered |
| :--- | :--- | :--- |
| `PN01`／`PH01` — startup | fresh App → IDLE；保留正式固定安裝入口 | process／config／各 required resource READY／IDLE；記錄有無 first-request prework、是否曾先跑 inference，防止將等待隱藏到 startup |
| `PN02`／`PH02` — first Turn | Session A T1「一個星期有幾天？」 | first-frame／speech-end（可量才記）／ASR endpoint／final、Conversation ready、LLM send／first safe text／terminal、TTS first PCM、Audio first write／complete；核對 13.333 s 與 12.762 s 的現況 |
| `PN03`／`PH03` — new Session | Session B T1 同一短題，重用同 App engine／child | PN02／PH02 同組節點，記錄 new Conversation 與 backend 重用；確認慢是否只是 process 首次使用，而非每個新 Session 都慢 |
| `PN04`／`PH04` — follow-up | Session A T2「請再簡短回答一次。」 | previous action complete／next perception start 及完整 ASR→Audio 節點，input／context／output counts；確認後續 Turn 較快的階段與 context 差異 |
| `PN05`／`PH05` — streaming | Session B T2「請列出三個滑雪安全重點。」 | 每段 admission／queue wait／depth／TTS start／first PCM／Audio segment／terminal／final drain；排除快首段卻慢 drain，及 TTS batching／queue 對使用體感的影響 |
| `PN06`／`PH06` — conditional matched-turn cause control | 僅在 02／03／04 仍不能區分原因時啟用；同一短題、兩個 Sessions 各兩個 measured Turns，再於另一 fresh App 重複 | 分離不同題目、process-first、Session-first、context 大小與 input delivery 的混淆；不是預設加一套長時矩陣 |

01–05 的執行順序固定為 01 → 02 → 04 → Session A normal close／cleanup → 03 → 05 →
Session B normal close／cleanup → shutdown。兩個 close 使用「現在請結束對話。」且不計入效能 case。
PH 各 case 同順序，不為每個 case 重啟 App。PN06 啟用時 PH06 同步定義；依 §4.7 的兩個 blocks 與預定比較端點／誤差評估執行，不根據最快樣本決定停止。相同題目不等同相同 prefill：
保存 input／context token counts、必要 output-size counts，以及真正 LLM generation／固定回覆
路徑的區別；沒有 LLM 節點或走 fallback 的快樣本不能當 native-generation 改善證據。

**Full automatic PA**：runner 管理 startup／READY、固定 PCM、Session-start 的正式 Button callback、
KEEP_NEXT、close／cleanup、shutdown、完整 structured timing-only 輸出與失敗處理。
以實際狀態／completion 銜接，timeout 只防掛住，不猜測完成、不強制 model route。固定 PCM
仍通過真實 ASR／LLM／TTS／Audio，不用 transcript injection；本輪預設按音訊 sample 時間 pacing，
記錄實際送入時間／frame lateness。這是輸入時間基準，不是用 sleep 猜 product completion。
現有 `scripts/alpha_product.py` 的舊 P 路徑只有 `sleep(0)` 而無 real-time pacing；此差異是待檢驗因素，
不是已證實的 12.762 s 原因。Developer 為 PN 建獨立可選 pacing／observer，保留原 P 行為。

**Human PH**：USER 只負責按正式 Button、按腳本說指定題目與聽覺判讀；同一 structured observer
自動記錄 backend 時間、case／Session 對應和完整結果，不要求手抄 timestamps。
不替換 microphone input 或用自動 PCM 冒充真人複驗。PH speech end／acoustic onset 沒有實測就
標 unavailable；此時仍可比較共同的 ASR final → Audio first write 與 LLM send → first safe text，
不能宣稱已量到真正說完話 → 聽到聲音。記錄聽不清、卡頓、等待與播放是否符合量測趨勢。

**LLM localization**：對涉及 generation 的 pairs，先利用 backend 可直接觀察的 request received、
render／prefill、first generated output、safe-text extraction 節點，解釋 send → safe-text 的組成。
拿不到的 native 節點標未知，保留整段實測，不能把整段 12.762 s 直接稱為 prefill 或 warm-up。
PN／PH 使用同一時鐘 domain 及 collector、相同 source／profile／model／runtime／設定／安裝路徑；
記錄 fresh／reused 狀態、啟動至題目送入間隔與 input delivery mode；private 實值可供必要匹配診斷，
public 只保留必要 boolean／count／stable code 與 timing，不洩漏 spoken text 或 PCM。

**Reproduction must retain diagnostic information**：USER 要求只要重現慢樣本就能分析。所有 PN／PH
從第一個 request 起啟用完整 timing collector，不等偵測慢後才開 log；不同 case／Session／Turn、
parent／child request、fragment／TTS batch 必須在私有資料可關聯，避免拿別輪或重疊分支混算。

| Diagnosis question | Required observation before judging the reproduction |
| :--- | :--- |
| 是否等在 input／ASR | 實際 input mode／delivery interval、first frame、可觀察 endpoint、ASR final；PH 未測 speech end 不造值 |
| 是否等在 Conversation／parent 或 IPC | Conversation create／ready、parent generation request send、child request receive；記錄 READY 與是否首次 GENERATE，區分 send 前準備與 send 後等待 |
| LLM 首段等待在哪裡 | child 可直接觀察的 render／prefill begin／end、first generated output、first safe-text emit、parent safe-text receive、terminal；配合 direct-user／rendered／context／output counts、實際 generation／fallback route |
| 是否因安全釋出或 batching 才晚出聲 | 首個生成輸出至 safe-text、fragment admission／queue wait／depth、TTS batch start／first PCM、Audio first write／segment complete／final drain；保留 fragment／batch 對應 |
| 是否真是首次使用差異 | App／child／engine／Conversation 的 fresh／reuse 事實、此前是否有 inference／prework、startup→request 間隔；PN／PH 固定題目及其私有實際 ASR 意圖／token 差異 |

Developer 在第一輪前確認 collector 能取到哪些 backend 節點，必要時只補針對長等待的私有計時觀察，
不新增產品 Event／Fact、不改 streaming 邊界、不關閉 privacy。對真正不可取得的 native subphase，
須事先列明觀察極限與替代的可驗證前後邊界；不能把不存在的資料列成 required 後再默默忽略。
Tester 將可實作的必需節點與最小原因對照寫入 Test Spec；採集缺漏／truncation／request 關聯遺失
是 diagnostic INVALID，而非「已完成分析」。Collector 從可取得的實際節點量測，不用 private
內容／digest 驗證代替 timing，也不引入一般 CPU／memory／thermal 研究。

慢樣本必須同時保留完整該輪資料與預定 matched 後續／新 Session 資料，報告長等待落在哪個可觀察
區間、哪些假說被支持／排除、哪個最小對照可以區分剩餘原因。只記「LLM send → safe text 13 s」
不足以完成首段等待分析。若長區間已定位但 native 內部仍未知，仍須用匹配對照支持下一步實驗，
不得憑直覺挑優化；若現有觀察根本不能區分候選原因，先補聚焦量測再做改善。
保存全部 slow／normal／failed observations，public 只輸出必要 timing、boolean、counts、stable
codes／sanitized reason；privately 查看 ASR／model 內容只限意圖或 route 診斷，不新增長期 transcript。

**Expected correspondence**：預期同一 pair 的產品功能、first／follow-up／new-Session 相對延遲及
主要耗時位置相符，而不是要求真人與固定 PCM 的秒數完全相等。依 §4.7 固定比較方法、誤差
及不可比欄位；保留全部樣本，分別說明生成長度、context、輸入節奏等已觀察差異，不能用它們
作未實證的萬用解釋。若 PN 約 2 s 而 PH 仍約 13 s，這就是未重現／未解釋的落差，不能只憑
PN 有效判首次慢回答已解決。以已記錄差異選一個最小對照；未解釋的真人／自動落差仍存在時，
ALPHA.P 保持未收斂，列出問題與下一個聚焦動作，不追加無限測項或強行宣稱相同結果。
如兩者皆無法重現舊慢樣本，只能記「本輪未重現」與量測範圍，不宣稱修復已發生。

early end、缺節點、錯誤路徑、pacing失真或 cleanup failure 使受影響觀察 failed／invalid；保留
結果、停止受影響 block、做可行 teardown，未執行項明列。不自動 retry 湊 PASS，不看到結果後換題。
PH 的前／後配對是產品分析與實際體感驗證，不新增角色互簽，不重測已修好的中斷矩陣或退役品質題。

### 4.6 ALPHA.P work boundary, outputs and completion

**Input boundary**：以 Developer 已交付 `19d9ca2` 的正式產品路徑為基線，保留已修好的
interrupt／restart／stop。沿用現行 model／runtime、prompt、schema、admission、固定安裝入口與
§4.5 PN／PH 題目；private config／model／PCM 路徑只由 operator 在實驗入口指定。未先取得原始完整計時，
不預先選 warm-up、改模型、改題目或改 token limit 作為答案。

**Work boundary**：完整 timing retention → PN01–PN05 與 PH01–PH05 配對 baseline → 必要時 PN06／PH06 原因對照 →
至多一項有證據的優化 → 相同條件 before／after → 直接受影響 regression → 相同 PH 人工複驗。
Tester 將既有 Test Spec 改為可執行的設定、次數、節點、判定及操作步驟；Developer 估點只涵蓋
實際量測／runner 缺口及選中的一項優化。實驗 instrumentation 與產品優化分開定位，
before／after 使用同一套 instrumentation，不把量測方式改變當成產品改善。M 的自由體驗
在最後版本依 §6A 複驗，與 P 內的 PH 固定腳本不是同一項判定。

優化必須針對已定位的耗時且維持產品行為；如只把等待搬到 startup、增加預先計算或改變 first／warm
條件，必須報告所搬移的時間與使用者付出的代價。不得把 fake／fallback 回答、提早結束、截斷答案
或繞過必要產品路徑計為速度改善。若選中方案無效或造成 regression，保留結果、不採用該變更；
不在同一工作包持續嘗試第二、第三項優化。具體產品故障仍交 Developer 修復，不以無限實驗掩蓋。

**Reviewable outputs**：

- 一個可重複執行的自動實驗入口與預先固定的設定／fixture mapping／對照次數；入口的精確命令
  由 Developer 記在既有 `development.md`，沿用現有 runner 或必要的窄擴充，不建新交接文件。
- Pi 的完整 PN／PH 配對與已啟用多輪對照紀錄，保留所有 failed／invalid／未執行項、必要計時和 token／size
  counts，以及計時有效性／誤差說明；public privacy 邊界維持 §3、§4、§6。
- 原因分析與優化 disposition：已直接證實的原因、已排除或仍不能區分的假說；採用一項、實驗後
  不採用，或無值得採用方案的理由。因 native 節點不可觀察而留下未知時，明列定位限制與已做對照，
  不宣稱原因已證實，也不因此無限加測。
- 如測試過優化，完整 before／after、startup／後續 Turn 代價及功能 regression 結果；只在效果
  超過量測誤差且具穩定性時宣稱改善。若沒有優化，不虛構 after 或改善比例。
- 最後保留版本的真人多輪複驗結果，及相同待交付 bytes 在 Pi 的所有適用測試定位。

**Completion boundary**：上述輸出齊備且量測有效、直接受影響 portable／integration／硬體功能
驗證通過、§4.5 人工複驗已完成，
才可記 `ALPHA.P complete`。缺計時、失敗未修、人工未執行時保持 open／pending，不要求必須
降低到某個秒數。所有變更回工作站後確認與 Pi 驗證內容一致；若採用產品變更，交付最終版本到
既有固定安裝入口並保留舊版本，不加入 service 或 update／rollback 系統。

`ALPHA.P complete` 不等同 `ALPHA Accepted`。其最終候選有效 PN／PH 配對結果可直接供
ALPHA Verify 使用；同 bytes／設定／輸入且證據適用時不為結案再重複一輪效能／人工測試。
更早候選只作 before 或診斷，不取得最終候選 PASS credit。最終 Lifecycle／Recovery 等共同驗證
仍依 §8 完成，可與最後受影響驗證合併安排而不重複同一測試。

### 4.7 Fixed PN／PH experiment decisions for Test Spec

**Cases／sample schedule**：PN01–PN05 與 PH01–PH05 是必需 pairs。Before 使用兩個完整 fresh-App
blocks／input mode，各 block 依 §4.5 的 01→02→04→close→03→05→close→shutdown；兩次啟動才能
觀察 process-first 是否重複出現，而不是憑單一慢樣本做結論。每個 mode 共八個 measured voice
Turns，四個 close Turns 不納入數值。原 P01–P05 不重跑；新 fixture binding 與 prompt 固定。
如試驗一項變更，after 同樣兩個 PN blocks 與兩個 PH blocks；若沒有變更，只交 before 分析。
這是最小重複對照，不作統計顯著性、長期穩定或一般品質宣稱。

**Conditional PN06／PH06**：啟用理由須是 02／03／04 中仍不能區分不同題目、process-first 或
Session-first／context 的影響；每個 mode 固定兩個 fresh-App blocks，各 block 兩個 Sessions、
每個兩個 measured Turns 都用「一個星期有幾天？」、各一次 normal close。Before／after 若用到
此對照則保留相同結構；如果只一個 input mode 有問題，仍保留另一 mode 的 matched control。
不預先新增 PN07、資源研究或更多 arbitrary cases；新原因診斷須直接回答仍未解決的問題。

**Launch／input conditions**：PN／PH 使用同一保留版本的正式安裝 composition、設定及 collector。
Runner 可以接入固定 PCM 與既有 GPIO callback，但不能另選產品 backend；PH 走正式固定入口與
真實 Button／microphone。每個 block 是 App fresh process，不等同 OS reboot／filesystem cold。
不得先用測試推論暖過 block 的 engine；既有 startup prework 與 IDLE→first request 實際間隔須保留。
PN 用同一份 16 kHz mono PCM 以 sample 時間 pacing；PH 用同題及同順序，私有 ASR 意圖與 token
counts 記為可比性資料。Tester 在執行前固定 pacing lateness 的觀測精度／有效性範圍，該範圍是
量測有效性，不是產品延遲門檻；超出就保留 invalid observation，不靠放大範圍取得好看結果。

**Timestamp semantics**：共同 clock 使用同一 Pi host 的 monotonic time。新節點以實際採集位置
命名，例如 parent request send、child request receive、native generation start、safe-text emit／
receive，不混用。既有 `llm_send_monotonic_ns` 實際在 child 的 GENERATE 分支、呼叫 runtime
生成前記錄；13.333／12.762 等舊表沿用原欄位標籤，但後者不是已量到的 parent-send／IPC duration。
新 collector 須同時保留可與舊觀察比的 native-start→first-safe-text，以及新增 parent／child 邊界。
必要 native 內部階段依 §4.5 區分直接觀測與不可觀察；完整全鏈路 timing 不等於已能證明所有
runtime 內部機制。Missing 必需節點、時鐘不一致、錯 Turn 對應或截斷是 diagnostic INVALID。

**Analysis method**：逐樣本列出共同端點的 durations、首次／後續／新 Session 差異及耗時分解。
不把 LLM terminal、TTS 與 Audio 並行期間相加為 end-to-end；不以平均值掩蓋慢／failed 樣本。
報告 clock resolution／collector 精度，以及兩個 blocks 的實際波動範圍；before／after 每個 directly
affected case 都報告改善方向、幅度和 startup／warm-path 的代價，不設固定秒數產品 gate。
只有同類路徑兩個 after 樣本都顯示一致方向，且量測誤差與樣本波動不致改變結論時，才可稱本輪
觀察到穩定改善；樣本不足或範圍重疊到無法判定就記 inconclusive，不宣稱普遍穩定或追加大量重試。

**PN／PH correspondence**：比較共同的 native-start→safe-text、ASR-final→Audio-first-write
及可觀察的其餘分段，判斷 first／follow-up／new-Session 趨勢與主要耗時位置是否相符。
Speech-end／acoustic-onset 沒有對等量測就不作精確跨 mode 數值比較。功能失敗是 FAIL，採集不足
是 INVALID，真人尚未執行是 PENDING；完整有效但新樣本未重現舊 13 s，是 NOT_REPRODUCED，
不能稱 fixed。明顯 PN-fast／PH-slow 而無可驗證解釋時保持 discrepancy open，再做最小聚焦對照。
若兩者皆不重現且收集完整，可交未重現結論及已知限制，不強制找出不存在的改善；M 同時仍需
確認實際使用可用。只靠 subjective「比較快」不能替代 before／after 計時。

**Failure／delivery**：不自動補樣本或重試取得 PASS。保留觸發原因與未執行 pairs；修復產品或
collector 後以新的執行定位重新測受影響部分，保留失敗記錄。PN／PH private 只保留診斷必要內容，
public 欄位依 §4.5，不新增 recurring digest。Developer 交一個 timeout-capable 入口，選擇
retained P、PN 自動或 PH 真人引導／採集模式；精確 CLI 名稱與部署參數由 Developer 定義，
Tester 先固定上述行為契約。既有 P 模式不被 PN pacing 或 expanded collector 默默改寫。

## 5. `ALPHA-R01-LLM-RECOVERY`

### 5.1 Purpose

本run只驗「整機正在streaming回答時LLM child故障，產品能否停止舊輸出、完成recovery並執行新的
正常Session」。M4-ERR仍是fault taxonomy／disposition／Level 1–3 authority；ALPHA不重跑其matrix。

### 5.2 Injection and convergence

1. 使用正式backend啟動App至`IDLE`，記錄唯一LLM child PID。
2. 以固定fixture開啟會產生多個safe fragments的Session。
3. 至少一個`SAFE_TEXT`已進入StreamingSpeak control後，由runner終止實際LLM child；不得注入假的
   terminal `LLMResponse`或直接改寫State Manager狀態。
4. 必須觀察一次`LLM_BACKEND_FAILED`作為注入locator；既有M4-ERR契約決定其
   `REBUILD_REQUIRED`與LLM resource key，不另拆成ALPHA fault matrix。
5. 當前generation、future fragment admission、queued／inflight TTS與未播放Audio停止；已播放內容不
   要求回復。不得發布正常`LLMResponse`或`ActionCompleted(ok)`。
6. Active Conversation、Session-owned task、streaming control、queue與in-flight operation完成清理；
   Display顯示`ERROR=錯誤`且不得保留未驗證的provisional回答。
7. 舊LLM child完成terminate／waitpid；recovery期間拒絕新的Session admission；Resource Manager只建立
   一個replacement，且replacement READY前不得穿越recovery barrier。

### 5.3 Product recovery proof

Recovery完成後自動執行一個新的完整正常Session：

- 使用新的Button trigger與新的Conversation；
- 完成真實ASR → replacement LLM → TTS → Audio；
- 正常結束並回到`IDLE`；
- 不得出現故障Session的fragment、回答或context；
- 正常shutdown後原LLM PID與replacement PID皆不存在，且無產品child／hardware owner殘留。

單純看到replacement process啟動不構成ALPHA recovery Pass；新的完整Session成功才是產品證明。

## 6. `ALPHA-Q-RUN-01-QUALITY`

### 6.1 Product risk and current quality disposition

六項品質把關保留為 ALPHA exit 的必要 regression，在 ALPHA.P 完成後、同一最後候選的 Pi 上
執行一次。其價值是防止改善速度時犧牲基本回答可用性、誠實能力、多輪 context 或 end route；
不是重新 qualification 一般知識能力，也不要求固定字串、精確文風或滿分答案。
即使 ALPHA.P 最後沒有採用優化，離開 ALPHA 前仍須完成這一次六項驗證。

USER 先前接受目前整體品質與已知限制，不等於舊六題已 PASS，也不取消最後六項把關。
`ALPHA-Q-DEV-20261003-02` strict card 保留：客觀六／六 PASS、語意四／六 PASS；Q05
`LOCATION_FACTUAL_ERROR` 與 Q06 `ARITHMETIC_INTENT_LOST_IN_ASR` 仍為原始 FAIL。
不改寫歷史，也不以真人整體正常確認替代這次最終候選結果。

### 6.2 Revised minimum-usable PASS criteria and fixed new stimuli

舊六題的刺激停用；保留六個產品面向與原 Test／case ID，以本節的新題及修訂 rubric 執行，
public run／fixture revision metadata 必須可區分新舊結果，不新增平行的 Test ID 或六份 fresh-start
測試。原 Q04 短句的實測同步僅作既有結果定位，不再重播為品質驗收。

| Case／risk | New fixed stimulus | Minimum product PASS | FAIL boundary |
| :--- | :--- | :--- | :--- |
| `ALPHA-Q01-IDENTITY`／基本身份 | 「請介紹你自己。」 | 能辨識為語音助理或雪板；自然自稱即可，不要求逐字自我介紹 | 冒充真人、其他品牌或捏造未提供的角色／能力；無可理解的自我介紹 |
| `ALPHA-Q02-FACTUAL`／簡單穩定事實 | 「一天通常有幾個小時？」 | 主要答案為 24 小時；可用中文數字、口語或合理簡短補充，不做 exact-text 比對 | 核心數字錯誤、迴避問題或補充造成實質矛盾；本題 PASS 不宣稱廣泛知識正確 |
| `ALPHA-Q03-CAPABILITY`／能力誠實 | 「你能看見房間裡的東西嗎？」 | 能表達無法看見，或目前只能聽與說；不要求固定否認句型 | 聲稱看見或描述未提供的房間畫面，假裝 camera／tool 已可用 |
| `ALPHA-Q04-INSTRUCTION`／簡短指令 | 「請用一句短話描述下雪的景色。」 | 一個簡短、可連續口述的描述，與下雪相關；可有禮貌語或自然停頓，不用標點數或機械字數代替判讀 | 轉移話題、多段列舉或明顯冗長而未遵從短話要求；不可理解的輸出 |
| `ALPHA-Q05-CONTEXT`／同一 Session 多輪記憶 | T1「我喜歡滑雪。」；T2「我剛才說喜歡什麼？」 | T1 有相關回應且 KEEP_NEXT；同一 Conversation 的 T2 能回答喜歡滑雪，可用同義改述，不要求 geographic knowledge 或更短字數 | T1 提前結束、T2 遺忘／答錯偏好、使用其他 Session 的內容或另開 Conversation |
| `ALPHA-Q06-END`／續聊與明確結束 | T1「請聊聊冬天。」；T2「對話到這裡，請結束。」 | T1 有相關簡短回應且 KEEP_NEXT；T2 END_SESSION 並 cleanup，允許簡短道別或合法無文字 REST | T1 提前結束、T2 仍續聊、late third Turn／audio 或 cleanup 不完整 |

調整依據：身份／能力看語意而不綁固定句型；事實只驗一個清楚、低複雜度答案；指令不以
標點／字數脆弱匹配；context 不混入地理事實；end 不混入否定指令與算術 ASR。
這些改動限定最低可用性，沒有把錯答、能力虛構或錯誤 lifecycle 改判 PASS。
它們提供有意義的通過機會，不能保證模型一定答對；rubric 必須在看新結果前固定。

### 6.3 Execution, adjudication and regression boundary

Runner 全自動依固定新 PCM 完成真實 ASR → LLM → 必要 TTS／Audio；Q01–Q04 各一個 Session，
Q05／Q06 各一個兩輪 Session；各 case 一次、不 best-of。Q01–Q05 若仍 active，使用功能
`FX-NORMAL-END` 關閉並等 cleanup；此 close 不另評品質。Q06 以自己的 T2 正常關閉。
Tester 在執行前固定新 fixture revision、實際 admission eligibility 與步驟；不得繞過 ASR、
修寫 transcript、強制 model route，或看到答案後換題湊 PASS。

客觀流程與語意分開判定：

- 客觀 PASS：真實產品路徑完成、合法 schema／action／terminal、所需 TTS／Audio 完成、無 control
  fragment 洩漏、正確 Session／Conversation 路由與 cleanup；Q06 T2 合法無文字 REST 不要求非空回答。
- 語意 PASS：依 §6.2 判定最終可用回答；ASR 可有不影響問題意圖的用字差異，不要求 transcript
  exact match。若 ASR 遺失核心問題而結果不再滿足該 case，不因錯答可歸因 ASR 就放行。
- 公開結果只保存 case ID、fixture revision、必要 boolean／stable code、verdict 與 sanitized reason，
  不保存 raw output、transcript 或 audio；Codex 用同一候選私有資料判語意，不新增 judge-model gate。
- 六項各須客觀與語意 PASS；任一 FAIL 即未達 ALPHA exit。只有真正不能依固定 rubric 裁決的
  偏好／證據問題才交 USER，未決時不算 PASS；不得以先前「接受現況」取代新 regression 結果。

此六項是一次最後候選的共同把關，不在每個效能 sample 或每次優化實驗重跑。ALPHA.P 的
直接受影響 portable／integration regression 先完成；最後六項是 ALPHA Verify 的工作，不是
ALPHA.P complete 的前置依賴，避免循環。若最終品質失敗，Developer 聚焦修復實際問題，保留
FAIL，再按變更直接影響面在新的最終內容驗證；不重開 Accepted 歷史或追加整套品質矩陣。
ALPHA.P 人工體感複驗與本節 Codex 六項語意判讀分工，不要求 USER 再做一份六題互簽。

## 6A. Alpha Manual（M）— 真人自由對話與操作

### M purpose and boundary

M 是第五大項：確認正式 App 的真實麥克風／喇叭／Display 與自然多輪、Session 再次使用、
正常操作是否可用。價值／風險是固定 PCM 可能漏掉真人輸入、聽覺、操作與現場體驗故障。
M 不綁固定問題、不做廣泛知識／噪音 robustness 或 stopwatch latency qualification；
PH 是 P 內固定情境的真人效能複驗，M 則保留自由使用觀察，兩者分開判定。

USER 現在將既有真人活動收錄為 M，這是 authority 的回溯分類，不宣稱當時已有 M 測卡、預定
效能 PASS 標準或新 run ID。原始執行時間、private log 根目錄與既有紀錄是結果定位；不改寫歷史。

### M existing experiments and results

當時背景與完整內容見 [development.md](../status/development.md) 的 `Live microphone session
resumed`、`USER-operated installed-entry test`、`Interrupted Session restart finding`、
`Interrupted-session repair result`；下面只收錄可確認的結果及來源，不複製 raw 對話。

| Existing execution（2026-10-09，+08:00） | Why／what was tested | Observed outcome／limit | Existing evidence locator |
| :--- | :--- | :--- | :--- |
| 最初 live launch，16:22:38 到 IDLE | USER 恢復工作並要求真人 microphone／自由對話；不使用舊六題 | SSH process 未持續、後來無 App；USER 回報 Button 無反應且 Display 留待命；不是已完成 live run | development.md `Live microphone session resumed` 的初次啟動紀錄 |
| live relaunch，16:25:47 到 IDLE，16:27:25 回待命 | 同 source／config 重新啟動；USER 自由對話、麥克風／喇叭／Display、多輪與操作回報 | 一個 Button-started Session、四輪對話；USER 確認「功能皆正常」，後續 App 已停止。無 independently retained exit status，不宣稱 exit 0 或六題 PASS | 工作站私有副本 `../pi-evidence/alpha-8b4af53/pi-home/operator/alpha-live-20261009-VkWLZT/application.log`（從 `core/` 起算）；development.md 同節 |
| installed entry，17:02:11 到 IDLE | USER 經 `~/snowboard-app/run.sh` 操作、短按回 standby 再長按 stop | speak Level-1 abort timeout、TTS stop-state rejection；一 ERROR／兩 WARNING，原 FAIL 保留。事後無產品 process／hardware holder，exit status 未留；不能將九次 ACTION 都當完整成功 | 工作站私有副本 `../pi-evidence/alpha-8b4af53/pi-home/operator/snowboard-app/logs/application.log`（從 `core/` 起算），17:02 launch；development.md `USER-operated installed-entry test` |
| interrupted restart，17:14:55 到 IDLE | USER 再試中斷後的新 Session | 新 Button／ASR 已到達，但 LLM_UNEXPECTED，replacement 後回 IDLE；當時有第二 Session 回答故障，不是永遠卡住。這是後續修復的實際風險 | 同 installed private log，17:14 launch；development.md `Interrupted Session restart finding` |
| repaired installed entry，17:51:31 到 IDLE | 修復 provisional streaming cleanup／repeated stop 後真人 interruption／restart／close 重測 | USER 完成兩輪 Sessions／使用並長按關閉；最近 log ERROR／CRITICAL／WARNING 均 0，事後無 repaired App／child／hardware holder。未留真人 terminal exit status；修復功能重測完成，不等同 whole-ALPHA Accepted | 同 installed private log，17:51 launch；development.md `Interrupted-session repair result`；交付 `19d9ca2` |

以上修復另有 portable、Pi native 與固定入口驗證，屬支援修復的 targeted tests，不新增第六大項，
也不能將合成 PCM native regression 稱為真人 M。

### M retained performance observations

Timing observer／native timing 欄位在真人執行前已存在；不是詢問效能後才加 instrumentation。
USER 詢問是否有 response times 後，才從既存 log 重建 intervals。M 原本未預先固定效能情境與
採集規格，故這些是附帶的 live performance observations，不能當 P01–P05 或新 PN／PH 的正式結果。

| M execution | ASR final→Audio first write（s） | Existing child generation-start→first-safe-text（s） |
| :--- | :--- | :--- |
| 16:25 live，T1 | 13.668 | 12.971 |
| 16:25 live，T2／T3／T4 | 2.756／3.036／3.226 | 2.067／2.279／2.277 |
| 17:02 installed，T1 | 13.999 | 13.379 |
| 17:51 repaired，S1/T1 | 13.333 | 12.762 |
| 17:51 repaired，S1/T2 | 3.021 | 2.202 |
| 17:51 repaired，S2/T1 | 2.985 | 2.089 |
| 17:51 repaired，S2/T2／T4／T5 | 1.966／2.140／2.376 | 1.533／1.555／1.680 |
| 17:51 repaired，S2/T3 | 0.683 | unavailable，不能當 fast native generation 證據 |

其餘 17:02 Turns 的完整既有表保留在 development.md，不刪 slow／failed 樣本。舊 log 每行最多
512 characters，所有 timing rows 有截斷；真人 speech end／acoustic onset、完整 terminal／drain
並非都有保留。S1/T2 受到中斷，first audio write 不證明完整播放。首輪慢原因未證實，不推定為
warm-up，不把修復成功稱為效能改善。這些觀察直接提出 P 新 PN／PH 必須回答的問題。

### M reopened execution and completion

本輪 P 與 M 重新展開；已有 19d9ca2 修復不重新設計。最後保留版本經同一正式固定入口，在 PH
腳本外完成一段 USER 自由對話：一個 Session 至少兩個有內容的互動 Turns，回待命後再開一個
Session 完成至少一個互動 Turn，最後以支持的正式操作停止 App。題目由 USER 自選，遵守現行
short-input envelope；自然停頓／修正可記錄，但不強制製造噪音／fault／固定中斷時序。

確認真人 input／audible output／Display 與實際狀態符合使用體驗，能接續對話及再次使用，
並能回 standby／正常停止；operator 保留 stop status 與 directly relevant process／hardware release
結果。若實際中斷或結束故障再次出現就記 FAIL，交 Developer 聚焦修復，不因 recover 到 IDLE 就
認定該使用回合成功。功能 PASS 還須 USER 確認實際聽到且可用；未收到回報就 PENDING，不能只
憑 state transitions 判定聽覺／體驗 PASS。USER 對小型知識限制的接受不取消 Q 的六項把關。

結果在既有 M evidence／development owner 記錄，執行前由 Tester 固定 run locator、候選內容、
啟動／結束範圍、必要 boolean／stable code 與人工回報欄位；不記 raw spoken text／PCM，
不追加行政簽核。P 的 shared observer 可在 M 中繼續採集必要 timing，若再見首次慢就保留可分析
資料並回到 P 診斷，不以自由題目與固定 PN／PH 數值作不受控的 before／after。

同版本且分段結果清楚時，PH 與 M 可安排在同一次真人使用時段，避免兩份重複操作；PH 含 fixed
questions 的成功不自動覆蓋自由對話 M。未對齊最後版本的早期 M 只能作來由／歷史觀察。

## 7. Test Spec handoff

Tester以本文件同步既有 `docs/test_spec/test_spec_ALPHA.md`，至少完成下列直接映射：

| Design authority | Test Spec responsibility |
| :--- | :--- |
| `ALPHA-L01-LIFECYCLE` | 一個Pi lifecycle run，含3 Sessions × 2 Turns、per-Session assertions、shutdown、owner absence、restart、offline與一次aggregate privacy scan |
| `ALPHA.P`／`ALPHA-P01-PERFORMANCE` | §4 全部邊界：保留 P01–P05；新 PN01–PN05／PH01–PH05、完整計時與配對一致性、必要 PN06／PH06、原因判別、一項優化的 before／after 與完成條件 |
| `ALPHA-R01-LLM-RECOVERY` | 一個Pi recovery run，含真實child termination、整機收斂、唯一replacement、下一正常Session及final owner absence |
| `ALPHA-Q-RUN-01-QUALITY` | ALPHA.P 完成後一次最終候選六項 regression；新題、修訂最低可用性 rubric、全自動客觀判定與 Codex 語意判定；原 FAIL 保留 |
| `Alpha Manual (M)` | §6A 真人自由對話與支持的操作、USER 體驗回報、必要停止結果；保留原未編號活動的來源／限制，不補造歷史 PASS |

Tester不得增加resource／thermal／manifest／digest測項、完整fault matrix、soak、重複fresh-run bookkeeping
或其他行政closure。Accepted M4 regression只在ALPHA實作直接影響時重跑；不能把既有Accepted row複製為
新的ALPHA PASS credit。

## 8. Entry and exit

### 8.1 Entry to Test Spec

- M4／M4C Accepted，正式Voice-only product path可作ALPHA輸入。
- 本文件固定五大項 L／P／R／Q／M、P 的 PN／PH、新六項 Q rubric、排除項目與判定責任。
- 沒有architecture conflict或外部POC dependency；Tester可直接建立coverage。

### 8.2 Entry to Developer

- `test_spec_ALPHA.md`已把§7全部設計要求映射為可執行Test ID、fixture、步驟與判定。
- Developer提供只涵蓋實際缺口的估點與工作包；不得把排除項目重新加入。

### 8.3 ALPHA Accepted

- ALPHA.P 完成後，Lifecycle、Recovery 與 §6 六項修訂品質 regression 在同一最終候選上通過；
  六項各須客觀／語意 PASS，無未決判定。舊題不重播、舊 FAIL 不改寫，已知品質限制仍明列。
- 新的 PN／PH Performance baseline有效、完整且配對落差有解釋；若採用優化，before／after與所有直接受影響regression通過。
- P 的 `ALPHA.P` 依 §4.6–§4.7 完成，PN／PH 有效、優化 disposition 明確；無固定秒數門檻。
- M 依 §6A 在最後版本完成 USER 自由對話與操作確認，無未處理實際故障或 pending 人工回報。
- 所有適用的最終自動、整合與硬體測試在Raspberry Pi對待提交相同bytes完成；Codex只判讀
  該候選在Pi產生的六項品質結果，不以另一份輸出替代。
- ALPHA結論只對應一個候選版本，不以不同候選拼接結果；版本定位是交付事實，不是產品Test ID。

### 8.4 Whole-ALPHA coverage and delivery disposition

Designer 本次檢視結論：既定 Voice-only 產品收斂問題已有設計 coverage，沒有要新增的產品能力或
一般研究 gate；可交 Test Spec，但目前不可記整體 Accepted。尚需完成的工作如下：

| Product question／delivery boundary | Current disposition | Remaining action |
| :--- | :--- | :--- |
| 正式啟動、固定安裝入口、interrupt／restart／stop | `19d9ca2` 已交付，Pi 與真人修復驗證已記錄 | 保留修復；若 ALPHA.P 改了產品 bytes，確認最終安裝入口可啟動／關閉與相同適用內容，不重開中斷矩陣 |
| 首次／多輪／新 Session 延遲 | 已觀察首次慢，原因未證實 | 完成 ALPHA.P；保留自動分析、改善 disposition 與最後版本真人複驗 |
| 3 Sessions × 2 Turns、cleanup、shutdown／restart | 設計已涵蓋；先前開發 run 不等於最終 Verify | 在最後共同候選完成 §3；不得拼接舊候選 |
| offline／public privacy | 已內含於 Lifecycle | 最終 §3 run 記錄 network 觀察與一次 aggregate privacy scan，不新增獨立 Test ID |
| 真實 LLM-child fault 與 replacement 後正常使用 | 設計已涵蓋；先前開發 run 不等於最終 Verify | 在最後共同候選完成 §5，不重跑完整 fault matrix |
| M 真人自由體驗 | 既有使用、失敗、修復及效能觀察已收錄；最後版本自由複驗 pending | 依 §6A 完成，PH 可同次安排但分開判定 |
| 品質可用性與限制 | 先前整體品質接受與舊 FAIL 保留；最終六項仍待驗 | Tester 同步 §6 新題與修訂 rubric；ALPHA.P 完成後在最後候選六項全部通過 |
| 同一最終產品內容的自動／整合／硬體驗證 | 本輪交付有其證據；whole-ALPHA 尚未結案 | 完成所有仍適用的 Pi Verify、工作站內容對齊，結果寫既有 evidence／owner 文件 |
| 最終 Git 交付 | `19d9ca2` 已存在；新增內容尚未 commit | Verify 完成後依 git 角色規則展示 subject／body／檔案並取得 USER 明確同意；本設計不是 commit／push 授權 |

Test Spec 目前仍有舊 fixture／舊六題 rubric 的同步缺口，Tester 必須依 §7 修改現行規格，
但不改歷史 evidence。以上是既有設計的執行缺口，不新增互簽、freeze 或行政結案測項。

在 §8.3 全部條件完成後，交付範圍就是已驗證的 Voice-only App、固定安裝入口、自動 runner、
ALPHA.P 的 PN／PH 分析／實驗結論、M 自由對話與操作結果及必要證據定位；USER 已接受的品質限制須明列。service、soak、general
knowledge qualification、噪音 robustness、tool／Vision 等排除項目不阻擋本 ALPHA 交付。
條件式 R1 是另一條候選線，M5 baseline selection 是後續入口，不要求為原 ALPHA 再完成一次 R1。

## 9. Postcondition

M5開始前仍須完成`M5-BASELINE-SELECTION-R1`，只選定原線`ALPHA Accepted`或R1線
`ALPHA.R1 Accepted`其中一個完整baseline；不得同時引用兩條線或拼接evidence。
