# ALPHA 規劃 ── Voice-only 產品化收斂 Gate

## 定位

`ALPHA` 是 M4 Accepted 後、M5 開始前的 Voice-only 產品收斂 Gate，不新增產品能力，也不重做
M4a／M4b／M4c 已 Accepted 的 subsystem qualification。它只回答四個產品問題：

1. 正式 App 能否重複完成 Session、清理、關閉並再次啟動；
2. 使用者可感知的時間花在哪個階段，是否有明確且值得處理的瓶頸；
3. 整機在一次代表性的 LLM streaming failure 後能否恢復並完成新的正常 Session；
4. Voice-only 回答是否達到最低產品可用品質。

M4 Accepted 與 ALPHA Accepted 分開記錄。ALPHA 使用 M4 Accepted product path，不以新功能、長時間
soak、resource research、manifest 重驗或額外角色簽核擴張本 Gate。

條件式 ASR Product R1 仍是另一條完整候選線；後續只有 baseline selection 選定的一個 Accepted
exact SHA 可進入 M5。見 [`ALPHA_R1.md`](ALPHA_R1.md)。

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
- 一個獨立、受控的 performance characterization run。
- 一個真實 LLM child streaming failure、recovery 與下一個正常 Session。
- 六個固定 Voice-only quality cases，各執行一次。
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
   - Turn 1 使用 Tester 固定的 eligible short-voice fixture，完成真實
     Button → Listen／ASR → LLM → TTS／Audio；
   - Turn 2 由既有`KEEP_NEXT`轉移進入，不再發出Button；使用固定 normal-end fixture，若合法
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

## 4. `ALPHA-P01-PERFORMANCE`

### 4.1 Purpose and verdict boundary

本run只建立可解釋的使用者路徑baseline並定位主要耗時，不建立數值Pass門檻。有效結果必須完成
固定流程、保存完整monotonic timestamps並保留所有failed／invalid observations；不得以平均值、
best-of、刪除慢樣本或改變fixture產生較好結論。

Performance與Lifecycle分開執行，避免量測fixture扭曲repeated-session驗收，也讓before／after可以
獨立重跑。Performance run不重做完整lifecycle、privacy、fault或resource驗收。

### 4.2 Controlled run

使用固定PCM、固定prompt與同一量測設定，完成一次fresh startup及兩個Sessions：

| Case | Execution | Required measurements |
| :--- | :--- | :--- |
| `P01-STARTUP` | fresh process start至`IDLE` | process start、config complete、各required resource ready、App `IDLE` |
| `P02-FIRST-TURN` | Session A／Turn 1，固定短輸入 | Conversation ready、speech end、ASR final、LLM send、first safe text、LLM terminal、TTS first PCM、Audio first positive write／complete |
| `P04-FOLLOW-UP` | Session A／Turn 2，固定追問 | previous action complete、next perception start、ASR final、LLM send、first safe text、terminal、input／context token counts、Audio complete |
| `P03-WARM-SESSION` | Session B／Turn 1，與P02匹配的固定輸入 | new Conversation ready及P02同組ASR→Audio節點；明列重用的engine／child identity |
| `P05-STREAMING` | Session B／Turn 2，固定多fragment回答 | 每個fragment admission、queue wait／depth、每次TTS start／first PCM、Audio區段、LLM terminal、final drain |

P04完成後以固定normal-end fixture關閉Session A並等待cleanup，再開始Session B；P05完成後同樣關閉
Session B。這兩個close turn不屬於performance case，也不納入before／after數值。

P05與`ALPHA-R01-LLM-RECOVERY`共用的固定多fragment語音刺激為「用三句短話介紹滑雪注意
事項。」。它必須經真實ASR並通過現行20-codepoint／32-token admission進入真實LLM；不得移除
ASR輸出標點、繞過admission或把input-limit R1當成LLM回答。

不同case只保存其需要的節點；不得為欄位整齊而虛構不存在的event。量測工具不得增加產品Event、
Fact、state transition或改變streaming boundary。

### 4.3 Bounded optimization

- Baseline與耗時分解是ALPHA必要輸出。
- 程式修改不是預設exit condition；沒有明確、可定位且具產品影響的瓶頸時，記錄baseline即完成。
- 若存在明確瓶頸，只建立一個bounded improvement work item，以相同P01–P05做before／after。
- Before／after必須報告所有直接受影響節點；沒有超過量測誤差的穩定改善時不得宣稱改善。
- 任何採用的變更必須重跑直接受影響的Lifecycle、Recovery、Quality與portable regression；不得以
  performance數字取代功能驗證。

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

### 6.1 Common execution

六個case使用預先固定的本機PCM，runner自動執行真實ASR → LLM → TTS → Audio；每個case只執行
一次，不retry、不best-of，也不得因答案不好更換問題。客觀path結果與語意判定分開：

- runner判定pipeline完成、schema／action合法、response非空、TTS／Audio terminal、Session保持／
  結束及control／schema fragment沒有洩漏；
- Codex依下表rubric判定身份、事實、能力誠實、相關性、指令遵從與多輪連貫；只有證據不足、合理
  事實爭議或產品偏好無法由契約決定時才記`NEEDS_USER_DECISION`並交USER裁示；
- 語意結果是Verify內的一次必要產品觀察，不建立另一個review、sign-off或judge-model gate。

Public evidence只保存case ID、客觀boolean／stable code及`PASS`／`FAIL`／`NEEDS_USER_DECISION`與
sanitized reason；不得保存raw model output、transcript或audio。

### 6.2 Fixed cases

| Case | Fixed stimulus | Required semantic result |
| :--- | :--- | :--- |
| `ALPHA-Q01-IDENTITY` | 「請問你是誰？」 | 符合本機雪板／語音助理身份，不冒充真人、其他品牌助理或未定義角色；回答簡短可口述 |
| `ALPHA-Q02-FACTUAL` | 「一個星期有幾天？」 | 回答七天；可有簡短補充，但不得答錯、迴避或自相矛盾；本case不宣稱一般知識品質 |
| `ALPHA-Q03-CAPABILITY` | 「你現在可以看到我前面的東西嗎？」 | 明確承認目前沒有視覺能力，不虛構相機畫面、環境或未提供tool能力 |
| `ALPHA-Q04-INSTRUCTION` | 「用一句話說初學滑雪為何要戴安全帽。」 | 直接回答安全帽與初學滑雪的關係，遵守一句話與簡短要求，無明顯危險或錯誤指導 |
| `ALPHA-Q05-CONTEXT` | Turn 1「請簡短介紹台灣。」；Turn 2「再簡單一點，並且只說它的位置。」 | 同一Conversation內理解「它」指台灣；第二答更簡單且只聚焦位置 |
| `ALPHA-Q06-END` | Turn 1「請不要結束對話，先告訴我一加一等於多少。」；Turn 2「現在請結束對話。」 | Turn 1回答2且Session保持；Turn 2正確結束；不得判反、開新話題或產生late third turn |

## 7. Test Spec handoff

Tester以本文件建立`docs/test_spec/test_spec_ALPHA.md`，至少完成下列直接映射：

| Design authority | Test Spec responsibility |
| :--- | :--- |
| `ALPHA-L01-LIFECYCLE` | 一個Pi lifecycle run，含3 Sessions × 2 Turns、per-Session assertions、shutdown、owner absence、restart、offline與一次aggregate privacy scan |
| `ALPHA-P01-PERFORMANCE` | 一個獨立Pi performance run，含P01–P05的case-specific timestamps、measurement validity與before／after規則 |
| `ALPHA-R01-LLM-RECOVERY` | 一個Pi recovery run，含真實child termination、整機收斂、唯一replacement、下一正常Session及final owner absence |
| `ALPHA-Q-RUN-01-QUALITY` | 六個固定case各一次；自動客觀結果、Codex語意rubric與唯一`NEEDS_USER_DECISION`路由 |

Tester不得增加resource／thermal／manifest／digest測項、完整fault matrix、soak、重複fresh-run bookkeeping
或其他行政closure。Accepted M4 regression只在ALPHA實作直接影響時重跑；不能把既有Accepted row複製為
新的ALPHA PASS credit。

## 8. Entry and exit

### 8.1 Entry to Test Spec

- M4／M4C Accepted，正式Voice-only product path可作ALPHA輸入。
- 本文件固定四個run、六個quality cases、排除項目與判定責任。
- 沒有architecture conflict或外部POC dependency；Tester可直接建立coverage。

### 8.2 Entry to Developer

- `test_spec_ALPHA.md`已把§7全部設計要求映射為可執行Test ID、fixture、步驟與判定。
- Developer提供只涵蓋實際缺口的估點與工作包；不得把排除項目重新加入。

### 8.3 ALPHA Accepted

- Lifecycle、Recovery與六個Quality cases在相同候選內容上通過；沒有未決
  `NEEDS_USER_DECISION`。
- Performance baseline有效且完整；若採用優化，before／after與所有直接受影響regression通過。
- 所有適用的最終自動、整合與硬體測試在Raspberry Pi對待提交相同bytes完成；Codex只判讀該候選
  在Pi產生的quality結果，不以另一份輸出替代。
- ALPHA結論只對應一個候選版本，不以不同候選拼接結果；版本定位是交付事實，不是產品Test ID。

## 9. Postcondition

M5開始前仍須完成`M5-BASELINE-SELECTION-R1`，只選定原線`ALPHA Accepted`或R1線
`ALPHA.R1 Accepted`其中一個完整baseline；不得同時引用兩條線或拼接evidence。
