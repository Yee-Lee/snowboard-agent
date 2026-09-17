# M4C — complete offline voice-device integration

狀態：**Scenarios recorded／M4C-SS open；M4-ERR Accepted且M4C-SS Closed前不進Test Spec／Developer**。

M4C完成Button→Listen/ASR→Reasoner/LLM→Speak/TTS、Rest與基本Session Display的exact-product
composition。Camera/look與voice wake留M6，tool/MQTT留M5，完整圖形與動畫留M7。

M4C另納入startup-static software output volume：產品composition以config固定輸出音量，並保留
未來`adjustments/volume`可注入的獨立control seam；本階段不交付runtime按鍵調整、Display音量
聯動、OSD、獨立mute state或音量持久化。

M4C假設[`M4-ERR`](M4.md#m4-err-boundary)已完成底層error taxonomy、propagation、diagnostic、
recovery與fatal-exit契約。M4C只以whole-product場景驗證composition是否正確使用該契約，不在
整機測試期間才臨時設計或修補底層error framework。

## Product interaction boundary

- M4C不支援barge-in。TTS播放期間不啟動Listen，也不以語音打斷播放；實體短按是本階段唯一的
  active-Session中止方式。正常turn順序固定為`Listen → THINK → TTS播放完成 → next Listen／REST`。
- 使用者說完的收音終點沿用Accepted M4A VAD／endpoint baseline，不是barge-in議題。M4C在整機
  品質項目觀察是否截斷尾音、漏字或產生明顯多餘等待；沒有可重現問題即不調參。若有問題，必須以
  固定語料及before／after evidence做focused delta並重跑受影響M4A regression，不在驗收時臨時調值。
- 正常語音結束保持簡單：Pi真實情境使用一個明確結束語句（例如「請結束對話」），要求既有LLM
  contract回傳`end=true`；有非空回答就播放完成後REST，空回答則直接REST。情境以Conversation
  close、Session cleanup及回到`IDLE`為PASS，不新增application關鍵字parser。

## M4C-SS gate

`M4C-SS`是M4C streaming-speak設計gate，必須在M4C交Tester建立Test Spec前Closed。其證據工作由
[`REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001`](../outsource/deliveries/active/REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001.md)
提供；POC結果本身不關閉gate。Designer必須依證據明確採用true streaming方案B，或有證據地放棄B並
固定full-response方案A。Closed後Test Spec只允許一種產品行為，不保留A／B雙重驗收路徑。

## Accepted entry baseline

- M4A Audio與M4B LLM／Reasoner均為Accepted input；M4B的same-bytes Pi `PV`已Pass，完成commit
  `f87cfa50b9c9415430973076a59c6b1961228090`並push。
- M4C不得沿用舊M4B encoding、streaming chunk、queue、response target、context-full或session-count
  行為。這些surface由replacement M4B與後續M4C review重新定義。
- M4B已交付Audio+LLM combined memory evidence、各階段同時駐留模型／資源，以及同一monotonic
  clock的節點時間紀錄。M4C用這些資料做whole-product composition，不回頭重做subsystem breakdown。
- M4C仍負責整機State Manager／Display wiring、實體audible onset與final product SHA驗證；M4B的
  Audio first write只是一個節點，不等於聲音已可聽見。

## Entry conditions

M4C design entry所需條件已完成：

1. `M4B-DESIGN-GATE-REASONER-BEHAVIOR` Closed；
2. M4B replacement design、protocol/profile及新test coverage完成並通過必要review；
3. M4B Audio+LLM vertical slice產出可重用的memory與timing facts；
4. M4B product candidate完成，且與Accepted M4A的inheritance/delta可對齊。

上述四項已由M4B Accepted disposition滿足，因此Designer可開始M4C產品場景design。USER後續新增
M4-ERR與M4C-SS作為M4C Test Spec／Developer entry的前置依賴；前者未Accepted或後者未Closed時可
繼續收斂場景，但不得把M4C交Tester或開始實作。

M4C不得直接把M4B觀測值固定為response-time target、resource reserve/hysteresis、streaming策略、
session soak數或其他驗收數值；只有M4C產品需求與設計可以建立這些新契約。先前M4C planning內容
只留Git history，不可取代新的Design → Test Spec流程。

## Static output volume boundary

- `AudioOutput`既有`start/stop/play` Protocol維持不變；M4C不重開Accepted M4A public contract。
- M4C composition在raw `AudioOutput`與`Speak`之間建立唯一
  `VolumeControlledAudioOutput` decorator。raw factory、ALSA negotiation與direct `hw:` device不變。
- `AudioOutputConfig.volume_percent`合法值為integer `0..100`；schema default為`100`以保持舊設定
  bytes的行為，M4C real product config明確固定`25`。此欄位只在startup載入，不支援runtime reload。
- decorator在canonical 16 kHz mono S16_LE stream進入ALSA native-format adaptation前縮放；每個sample
  以sign-preserving truncation toward zero計算，`0`為靜音、`100` bit-exact passthrough，chunk長度不變。
- decorator另實作獨立`VolumeControl` port，讓未來`adjustments/volume`取得同一instance；M4C目前
  沒有runtime caller，也不發布Event、Signal或Fact，不改State Manager狀態。
- scaling不得改變upstream iterator、cancel/error propagation、AudioOutput drain或
  `audio_first_write`觀測點；任一product path只允許一次gain，M4B runner保持Accepted read-only。

Test Spec至少覆蓋config default／range、`0/25/100`與正負edge samples、invalid/partial S16_LE、
chunk-by-chunk streaming、單次composition、cancel/drain透明性，以及Pi direct-ALSA在M4C product
config下的audible playback。這些是M4C既有pipeline內的Test IDs，不新增獨立gate。

## Session no-input completion

M4C把現行逐turn的no-input retry補成完整產品Session行為。每個Product Session持有一個連續
no-input streak：listen timeout、listen完成但沒有usable text或ASR stable code `NO_SPEECH`時計入；
第一次使用既有固定語音「我沒聽清楚，請再說一次。」並保持同一Session／Conversation再次listen，
第二次連續no-input不再播放重試語音，改走application-owned `rest + END_SESSION`，完成全部cleanup
後回到內部`IDLE`與Display「待命」。

任一有效非空listen結果在後續input/admission判定前把streak歸零；Session cleanup也必須清除，
不得帶入下一個Session。Listen必須把ASR的sanitized stable request-error code保存在
`PerceptionResult.extra["asr_error_code"]`，不得傳exception string、transcript、PCM或native diagnostic。
`MULTIPLE_UTTERANCES`使用固定語音「請一次只說一句。」後再次listen且不改streak；
現行`INFERENCE_REJECTED`混合native內部錯誤與未知exception，不是可要求使用者重說的R1；由
M4-ERR移除或重新定義此lossy mapping，M4C一律把其system-fault結果交既定ERROR／recovery流程。
`INVALID_FRAME`同樣是內部contract failure，進E1／ERROR而非提示使用者重說。

M4C Test Spec必須完整覆蓋此產品行為，而不只單元測試counter：至少包含first retry保持相同
Session／Conversation、第二次直接正常結束且沒有第二段重試語音、有效非空listen後歸零、跨Session
不繼承、適用request code的產品分類／redaction，以及final Pi exact-product composition中從Button啟動、真實
Listen/ASR路徑、Speak/Rest、Conversation close、worker/resource cleanup、Display清除與回到`IDLE`
的整條路徑。System fault不計入no-input streak，也不得提示使用者重說；其whole-product代表情境
統一由`M4C-S06-RECOVERABLE-FAULT`覆蓋。Rebuild resource可用性由M4-ERR證明，M4C不要求再啟動
第二個Session，也不逐一重跑所有native diagnostic cause。受影響的M4B outcome與M4A/M4B regression在相同final bytes上保留；Accepted M4B歷史
evidence不因本delta改寫，也不直接提供M4C PASS credit。

## M4C／ALPHA quality boundary

M4C每個產品情境到`IDLE`、`exit 0`或定義的nonzero fatal exit即完成；不要求第二個正常Session、
repeated-session corpus或soak，也不從M4B observation建立正式latency、memory、thermal或長時間穩定性
門檻。M4C仍須完成單次整機功能、真實audible／Display結果及VAD品質觀察。連續Session、soak、正式
response／recovery ceiling、resource與thermal收斂由[`ALPHA`](ALPHA.md)負責。

## Whole-product scenario authority

M4C驗收的是使用者可觀察的exact-product composition，而不是重跑M4-ERR的cause-code matrix。下列
scenario各自fresh setup、獨立結果；除同一正常Session內明列的turn外，不跨scenario沿用Session、
Conversation、Display Main、no-input streak或in-flight owner。成功終點只能是清理完成後的`IDLE`、
graceful `exit 0`，或明列的Level 3 nonzero exit。

| Scenario | Trigger與主要步驟 | 必須觀察 | 終點 |
| :--- | :--- | :--- | :--- |
| `M4C-S01-START-IDLE` | 手動啟動正式application；等待required resources READY | 尚未建立Conversation；Status=`待命`；Main為空；Display保持開啟 | `IDLE` |
| `M4C-S02-NORMAL-END` | IDLE短按；說「你是誰？」並完成回答；下一turn說「請結束對話。」 | WAKE後才建立Conversation；THINK保留final ASR文字；ACTION顯示並播放同一validated回答；同一Session／Conversation；`end=true`有文字則播完再REST、無文字直接REST | close／cleanup後`IDLE`、Status=`待命`、Main清空 |
| `M4C-S03-NO-INPUT` | IDLE短按；連續兩次timeout、空白或`NO_SPEECH` | 第一次只說固定重試句並保持同一Session／Conversation；第二次不再說重試句且不呼叫LLM | REST／cleanup後`IDLE` |
| `M4C-S04-INTERRUPT` | 三個獨立variant分別在PERCEPTION、THINK、ACTION實體短按 | 接受後Main=`已中止`；停止未來收音／生成／播放；不發布舊operation正常成功；完成Conversation與owner cleanup | `IDLE`且Main清空 |
| `M4C-S05-APP-EXIT` | application READY／IDLE時實體長按 | 停止接受新Session；reverse cleanup；Display final blank；所有child／HAL owner bounded exit；不要求Pi關機或application自啟 | application `exit 0` |
| `M4C-S06-RECOVERABLE-FAULT` | 三個獨立variant在PERCEPTION、THINK、ACTION各注入一個M4-ERR已驗證的backend system fault | 不fabricate正常Fact、不要求USER重說；ERROR安全摘要；Session convergence及對應rebuild完成；不重跑底層diagnostic cause matrix | recovery barrier clear後`IDLE`；不要求第二Session |
| `M4C-S07-DISPLAY-DEGRADE` | 正常Session中注入Display runtime failure | Display依既有contract latch disabled；語音主流程不進ERROR且仍完成；process exit code不因Display改變 | Session cleanup後`IDLE` |
| `M4C-S08-RECOVERY-FATAL` | 一個代表性backend system fault後注入rebuild timeout／READY mismatch | 不回假`IDLE`、不接受新Session；bounded cleanup；保存sanitized stable failure evidence | Level 3 nonzero exit |
| `M4C-S09-STREAMING-SPEAK` | 使用M4C-SS Closed後唯一採用的A或B路徑完成正常與短按中止turn | spoken text與terminal validated text一致；無duplicate／missing／reorder／late output；audible onset與completion節點可定位 | 正常turn續Listen／REST，或中止後`IDLE` |

所有適用scenario在network disabled的產品設定執行；不得fallback至網路服務。公開log／evidence不得含
transcript、prompt、raw model output、PCM、credential、session ID或完整私人path。Display沿用
selected profile：`IDLE=待命`、`WAKE=準備中`、`PERCEPTION=接收中`、`THINK=思考中`、
`ACTION=回應中`、`ERROR=錯誤`；IDLE清Main、shutdown維持Blank。THINK Main顯示final ASR文字，
ACTION Main只顯示terminal-validated實際回答，不顯示streaming provisional fragment。

### Product-quality observations

`M4C-S02`及`M4C-S09`另保存單一product timeline：button acceptance／Conversation ready、ASR final、
LLM send、first safe text、LLM terminal、TTS first PCM、Audio first write、physical audible onset及final
audible sample。這些值在M4C是完整性與順序證據，不建立正式response ceiling。VAD使用固定短句、
一般句及尾音較弱句觀察是否截斷、漏字或有明顯多餘等待；只有可重現問題才依前述focused-delta
規則調整。startup-static volume須為product config的`25`，聲音可懂且無clipping；長期品質、
repeated sessions、soak與正式performance/resource門檻仍由ALPHA承接。

Accepted M4B disposition見[`M4B_MVA.md`](M4B_MVA.md)，current owner見
[`status/current.md`](../status/current.md)。
