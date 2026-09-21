# M4C — complete offline voice-device integration

狀態：**Design complete；M4-ERR Accepted；M4C-SS Closed（採用 B2）；Test Spec complete／Developer open**。

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

`M4C-SS`已由Designer裁定 **Closed／採用true streaming B**，唯一產品mapping為
`B2-ONE-LOOKAHEAD-COALESCE`。依據是
[`DELIVERY-LLM-POC-M4C-STREAMING-SPEAK-001`](../outsource/pm_handoff/history/DELIVERY-LLM-POC-M4C-STREAMING-SPEAK-001.md)：
POC implementation／reviewed-report source為`a6de0e66d7effe03549037eb8f50b99e42399620`，delivery binding
commit為`a492a1416721c73c989dd46067b3e9dd1c24508d`，Core保存檔SHA-256為
`c097d550d263070ef216bfa391e87c69b6b27aa68baf26f09ea7428be8bf069f`。

此裁決只採用可行性與mapping選型，不把POC自評當產品PASS。POC明列原定82項formal case執行數為0、
Pi使用dirty development checkout、live A值為projection，且沒有完整negative／resource／human-quality
matrix；這些限制不支持任何M4C Test ID的PASS credit。它仍足以關閉設計選型，因為同一retained
generation的實體A／B replay直接觀察到B提前2.019秒audible onset，真實
`LiteRT-LM → S2(12) → B2 → Matcha → I2S speaker → USB microphone`鏈路也在terminal前269.958毫秒
開始發聲，21.677030毫秒acoustic uncertainty內沒有改動既有public TTS／Audio／Fact contract。
未完成的qualification全部回到正常`Test Spec → Developer → Verify`，不得再保留A／B雙重產品路徑。

### Adopted streaming-speak contract

1. SM在每個需要real-model generation的THINK entry建立一個private `StreamingSpeakControl`，另配唯一
   speak correlation，並與本turn的`(session_id, turn_id)`綁定。Reasoner只可把同turn、同generation、
   已由`snowboard.llm/3` ledger驗證的`SAFE_TEXT`送入該control；fragment不是Fact、action、turn或
   state transition。
2. M4C前瞻性把Accepted M4B §4.2在此產品composition的release boundary固定為「punctuation或
   **12個normalized codepoints**，取最早者」。Unicode／JSON仍先經完整incremental decode與穩定
   normalization segment；escape、partial UTF-8、未穩定combining sequence、JSON syntax及`end`不得
   提前外洩。這是M4C implement delta，不改寫M4B Accepted歷史。
3. 每個fragment必須non-empty、sequence連續、不可revision；已admit文字串接後永遠是terminal
   normalized text的exact prefix。queue只計尚未consume的fragment，最多2個且合計最多256 UTF-8
   bytes；滿載時producer backpressure，不drop、重排、偷偷merge或建立unbounded task/list。
4. B2每次dequeue取queue head，且只可合併當下已在queue中的下一個fragment；不得等待未來lookahead。
   合併只做exact concatenation，不改字。每個batch依序呼叫既有`TTSAdapter.synthesize(text)`並由同一
   `AudioOutput`完整play／drain後才ack；同turn永遠只有一個logical Speak operation與一個最終
   `ActionCompleted`。
5. 第一個fragment可在THINK啟動既有Speak owner；SM從啟動起把它列為同turn in-flight。Speak即使先
   播完也只能留下private completion，不得在terminal semantic validation及ACTION admission前publish
   或return normal success。Reasoner驗證terminal speak intent、完整text與fragment equality後關閉
   admission並發布唯一`LLMResponse`；SM進ACTION時adopt既有Speak record，才允許它在全部batch
   drain後發布唯一`ActionCompleted(ok)`。
6. 產品沒有runtime A/B knob或第二條full-response acceptance path。若某turn在terminal前沒有合法
   `SAFE_TEXT`，同一B2 control於terminal validation後把完整terminal text當唯一final fragment；這是B2
   的terminal-only退化，不是可選A mode。只要已有fragment admit，就禁止以完整terminal重播或以A
   重試。
7. Empty／duplicate／out-of-order／oversize／post-terminal／stale-operation fragment一律fail closed。
   Invalid terminal、prefix mismatch，或已admit fragment後的replaceable generation failure，必須取消
   generation、queue、TTS iterator與Audio playback且不得發布正常`LLMResponse`或`ActionCompleted`。
   request terminal、stream cleanup、Conversation cleanup與`engine_usable=True`全部有typed proof時，使用
   M4-ERR既有taxonomy的`STREAMING_TERMINAL_FAILED + REUSABLE`（無recovery key）；任一proof缺失則使用
   `LLM_CLEANUP_UNPROVEN + UNPROVEN + LLM key`。identity／intent／wire不一致仍使用既有
   `LLM_PROTOCOL_FAILED + UNPROVEN + LLM key`。若尚未admit任何fragment，原M4B具完整proof的R2仍可走
   code-declared固定提示。
8. Interrupt、shutdown或任一LLM／TTS／Audio system fault立即關閉admission並沿用M4-ERR Level 1／2／3
   與原backend disposition。已可聽見內容不回滾；正確性要求停止未來generation、fragment、synthesis
   與playback，拒絕late callback，清空queue/in-flight iterator與device owner，且不污染下一turn/session。
9. ACTION Display只顯示terminal-validated回答，不顯示provisional fragment。公開log／evidence只保存
   sequence、長度、digest、queue high-water、timing與stable code，不保存fragment／terminal文字、PCM、
   session ID或private path。

### Test Spec handoff for M4C-SS

POC的non-formal結果不可替代Core qualification。Tester須把下列內容納入M4C Test Spec，與其他M4C
scenario在同一正常pipeline收斂，不新增POC review gate：

- portable controller coverage須逐項固定single／multi fragment、2件／256-byte backpressure、invalid
  terminal、prefix mismatch、post-terminal、queued／synthesizing／playing interrupt、shutdown、TTS
  error／timeout／force-abort、late old-operation callback及zero-owner cleanup；每項都驗證恰一個logical
  operation與0或1個合法terminal Fact。
- outcome coverage須區分zero-fragment R2、partial-fragment且完整proof的
  `STREAMING_TERMINAL_FAILED + REUSABLE`、cleanup proof缺失的`LLM_CLEANUP_UNPROVEN + UNPROVEN`，以及
  identity／intent／wire mismatch的`LLM_PROTOCOL_FAILED + UNPROVEN`；未使用的control也必須close且零owner。
- extraction／mapping coverage須驗證punctuation-or-12、Unicode normalization stability、terminal flush、
  B2只合併一個already-available lookahead、exact concatenation，以及沒有lookahead時不等待。
- Pi exact-product qualification須在same-bytes M4C candidate上使用真實LiteRT-LM、Matcha、25% product
  volume、I2S speaker及獨立microphone。至少一個eligible正常turn須證明first `SAFE_TEXT`、first PCM、
  Audio first write、physical audible onset、terminal、final audible sample的同clock ordering，並證明
  terminal前已開始實體發聲；這是功能／完整性判定，不建立latency ceiling或A/B performance gate。
- selected B2須用固定公開speech sample做understandable、無duplicate／missing／reorder、無破壞理解的
  artificial boundary之真人判讀；只有這項產品本身需要的聲音品質保留人工結果。negative cancellation
  tail與cleanup使用自動target facts，不要求人工逐項判讀。
- `M4C-S09-STREAMING-SPEAK`同時覆蓋正常turn與queued／synthesizing／playing三個短按variant；每個
  variant fresh setup，停止後無later fragment／success／cross-session leakage。所有結果綁定tracked-only
  content digest、product config、artifact digests、target facts與private evidence digest。

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

上述四項已由M4B Accepted disposition滿足。USER後續新增的兩個Test Spec前置依賴也已完成：
M4-ERR以commit `f572915d0b0d5c52067e9100c5b022e57aefe506`完成same-bytes Pi Verify並Accepted；
M4C-SS由本章依回傳evidence裁定Closed／B2。Tester已在
[`test_spec_M4C.md`](../test_spec/test_spec_M4C.md)完成所有scenario、streaming contract與直接
regression映射；`TR_spec_M4C_I`已Resolved／0 Blocking，Developer entry因此開啟。

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
| `M4C-S09-STREAMING-SPEAK` | 使用唯一B2路徑完成一個eligible正常turn；另以fresh setup在queued／synthesizing／playing三點實體短按 | 正常turn在terminal前開始實體發聲，spoken text與terminal validated text一致；各中止variant無duplicate／missing／reorder／late output、正常success或owner leak；audible onset、tail與completion節點可定位 | 正常turn續Listen／REST；各中止variant清理後`IDLE` |

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
