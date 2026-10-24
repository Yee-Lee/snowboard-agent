# M4B PV 即時更新

## 2026-09-15 16:12 UTC — #1 孤立 trace 文字由 Tester 修訂；交 Designer Verify

- 現行 Tester-owned `docs/test_spec/test_spec_M4B.md` §5.1 末段已改為：ATT 驗自己的 bound identity、offline profile flags、child `network_denial_installed`，**不**宣稱零 network attempt，也不要求重複 syscall trace；獨立的 #7 `R01-OFFLINE` 以 160 份 pre-native-through-exit trace 提供零對外連線證據。兩項仍各用自己的 card/series/result，沒有跨 Test-ID 偷用。Product `docs/implement/ch_m4b_llm_production.md` §11.2 的 #1 identity 與 #7 R01 actual network attempt 分工相符。
- 因 Test Spec clarification 未改 runner/產品/model/profile bytes，先前 Pi `PV-M4B-FINITE-03` 七項 script/Developer/USER 及 finalizer `PV Pass` 不須重跑；此修訂消除前一交接段提出的 #1 孤立 trace wording discrepancy。Developer 已更新既有 `docs/status/development.md` 最新交接段；Designer 在正常 `Verify` 階段確認 Tester revision 與現行 Product 對映，不插入新簽核 gate。其餘 finite estimate／controlled endpoints／R05 indirect 等 coverage caveats 仍照實保留。

## 2026-09-15 16:10 UTC — Developer 七項 Pi PV 結果已交 Designer Verify

- 交接已寫入既有 `docs/status/development.md` 最上方 `Completed seven-ID Pi PV and Designer verification handoff` 段，並在本檔保留每次實驗、全部主要 raw 數字、series/trace/輸出與阻礙；沒有新增第二份 handoff。`git diff --check -- docs/status/development.md` 通過。Pi finalizer 公開 `m4b-pv-finite03-public/pv-final.json`、私有 `m4b-pv-finite03-private/pv-final-manifest.json`，runner status `PV Pass`；七項 script Pass、六項 Developer review Pass、#2 三題 USER Pass 已逐項定位。
- Designer 的唯一待判差異：Test Spec §5.1 若把 #1 ATT 自己的 pre-native syscall/network-attempt capture 作必備 evidence，目前 `ATT-01` 沒有該 trace，不能用 `network_denial_installed` 或 #7 R01 trace 代替；請核定是 blocking acceptance 還是孤立規格文字，若 blocking 再提供最窄修正。其他 coverage 限制（#4 finite-only estimate、#5 controlled endpoints、#7 R05 indirect/R06 no descendant/R07 owner-only）已在 Developer 狀態列出，不因 finalizer Pass 消失。
- 下一 owner 為 Designer `Verify`；`docs/status/current.md` 是 Designer-owned，Developer 沒改其 owner/gate。未 commit／push；若日後要 commit，仍須相同 bytes 的 Pi Verify、工作站 bytes 對照、讀 git role 並由 USER 核准完整 commit subject/body/file list。

## 2026-09-15 16:09 UTC — 公開 final manifest 七項逐項核對完成

- Pi-local `m4b-pv-finite03-public/pv-final.json` **整份**已讀：`pv_status=Pass`、`automated_status=Pass`、`human_status=Pass`、`measurement_status=Pass`，protected tuple content `f6b9cfe2dcadeac675deb4811b2711e9c0c6a28d73e4985fc9ae321fb08c7545`、harness `cb79a96c06cdf427142fd9171523ce545e2b35951c59117d9d1dc8cf95988b33`、profile `8d957a4600fc172fd7dd7b285098710af0b753d7d1b697a21bd31611637b3f90`、Pi identity `pi5-4gb-debian13-aarch64-cp3135`。七個 Test ID 均 `script_status=Pass/status=Pass/reason_codes=[]`；#1 6/6、#3 3/3、#4 5/5、#6 4/4 assertion Pass；#5 W01–W04、#7 R01–R08 的每個 case assertion 均 Pass。
- 六項 Developer review 於 manifest 的 count/status：#1 `368/114 Pass`，#3 `410/146 Pass`，#4 `22,607/5,448 Pass`，#5 `1,612/573 Pass`，#6 `359/123 Pass`，#7 `60,388/16,005 Pass`，card/catalog/evidence digest 均定位於各自 review。#2 selected S01 A03、S02 A01、S03 A01 三案 script/USER status 全 Pass，沒有 Developer review（按契約 USER 唯一語意 owner），較早 S01 A01 Incomplete/A02 Pass 沒被 finalizer 選作本次 designated 結果。
- Final estimates 與原 MEM card 一致：Speak drop `47,464,448 B`→`585,105,408 B` (558 MiB)，Generate drop `195,461,120 B`→`732,954,624 B` (699 MiB)；scope 仍 `FINITE_TWO_TURN_NO_REPLACEMENT`，不能宣稱 native context rejection/replacement 的門檻已量到。#1 Test Spec §5.1 要獨立 syscall capture 而 ATT 缺檔的 coverage caveat、#5 controlled endpoint/mock/early state-change、#7 R05 indirect proof/R06 no initial descendant/R07 owner-only 都原樣交 Designer。這些 limitation 不在 finalizer `reason_codes`，故 **runner PV Pass 並不等於 Designer 已核定所有 coverage 文字**。

## 2026-09-15 16:07 UTC — Pi finalizer 已得 PV Pass，公開 manifest 待逐項讀取

- `PV-M4B-FINITE-03` 同 tuple 的 Pi `finalize` exit `0`，回報 `pv_status=Pass`，公開 `m4b-pv-finite03-public/pv-final.json`、私有 `m4b-pv-finite03-private/pv-final-manifest.json`。此步**沒有**重新執行任何產品案例，只選取前述七項 script、六項 Developer Pass、#2 三題 USER Pass。
- Developer 接著逐項讀 final manifest 的 #1～#7 selected statuses、原卡／review locator/digest、#2 verdict、null reason；再更新既有 `docs/status/development.md` 交 Designer。#1 §5.1 的 syscall/network-attempt capture 缺檔 caveat 仍待 Designer／Tester核定，不能被 finalizer 的 `PV Pass` 自動抹除。

## 2026-09-15 16:06 UTC — #1/#4 正式 Developer Pass，僅餘 finalizer 與 Designer 交付

- #4 `M4B-PI-MEM-001` 已 Pi 正式登記 Developer `Pass`，reviewed `22,607` fields／`5,448` rows，私有 review `m4b-pv-finite03-private/developer-reviews/M4B-PI-MEM-001-cf0ed9a7c49e6b172e8bebd70cf18d6f0ddc3940f34a2a863b555349161cc20d.json`。原 `241` 點 raw、兩輪 native output、估計及 PID memory 不重跑。
- #1 `M4B-PI-ATT-001` 已 Pi 正式登記 Developer `Pass`，reviewed `368` fields／`114` rows，私有 review `m4b-pv-finite03-private/developer-reviews/M4B-PI-ATT-001-3cc51cffec6fdddf2d84605261785c3d4c6534a37d090e1b64622b962369505f.json`；review anomaly notes **明確保留** ATT 未產生獨立 syscall/network-attempt trace，不能把 network denial stage 說成零對外嘗試；Designer／Tester 需核 Test Spec §5.1 孤立要求。對已記錄 A01–A06/capture 欄位的 Developer review 是 Pass，但 coverage discrepancy 仍待 Verify，不隱藏。
- 七項所需現有 script/Developer/USER status 均已齊；只執行一次 Pi `finalize` 與既有 Developer 狀態/本檔交 Designer。USER 詢問時間，預期約 1–2 分鐘若 finalizer 無異常；不保證新錯誤不出現，也不重跑既有 Pass 案例。

## 2026-09-15 16:03 UTC — #4 MEM 全量原始數值／輸出核完，準備登記 Developer Pass

- Pi 公卡 M01–M05 五個 assertions 各 Pass、cleanup true、估計 scope `FINITE_TWO_TURN_NO_REPLACEMENT`；私有 catalog 預期／實際 `22,607` fields／`5,448` rows，type mismatch、field/row locator duplicate 各 `0`；既有全量 catalog/source audit 與此次 Pi 逐點核對一致。`241` 點 lifecycle labels：engine_ready1、conversation_preparation1、conversation_ready1、pre/post_generate 各2、pre_speak/audio_completion 各2、primary_completion2、post_session_close1、continuous sample227；無 replacement row。
- 每點 `5` 個不同穩定 PID：core10453 RSS `48,332,800–63,602,688`/PSS `42,670,080–56,737,792`；vad10460 `75,874,304–76,005,376`/`69,297,152–69,517,312`；asr10464 `130,580,480–130,744,320`/`127,953,920–128,179,200`；tts10465 `222,117,888–236,240,896`/`215,740,416–229,863,424`；llm10470 `484,032,512–1,792,966,656`/`478,202,880–1,787,122,688` bytes。每點 PID unique、同 owner PID/start ticks 身分穩定、PSS<=RSS、monotonic 嚴格增加，無 owner/sampler identity loss。MemAvailable `2,786,115,584–3,300,950,016 B`、溫度 `49.6–56.2 C`，OOM counter/throttled bits 全部 `0`；512 MiB floor／80 C stop 未觸及。
- Swap 目標實際**有** `SwapTotal=2,147,467,264 B`、`vm.swappiness=60`；used `85,360,640→87,457,792 B` 增 `2,097,152 B`，按 USER 裁定只記錄，不把增長當成 Pass/Fail。Speak drop `47,464,448 B`→估計 `585,105,408 B` (558 MiB)；Generate drop `195,461,120 B`→`732,954,624 B` (699 MiB)，與原 derived/card 一致，兩值只適用完成的有限兩輪 scope，不宣稱量到 replacement 門檻。
- 原始 native 輸出：第1輪「台灣,美麗的島嶼,充滿活力與多元文化!」、prefill86/decode26/KV112、revision0→1、Speak action ok/KEEP_NEXT；第2輪「我們有豐富的自然景觀,美食也超讚的!」、prefill17/decode27/KV156、revision1→2、同 child10470、Speak ok/KEEP_NEXT。真實 close proof session/generation 匹配且 request_terminal/cleanup/engine_usable 全 true，正常 close 完成；stderr88 lines 中 warning4、fatal0。所有已記錄原始數值、輸出、trace、series 與 null reason 沒發現矛盾；#4 可正式登記 Developer Pass，產品不用重跑。

## 2026-09-15 16:00 UTC — #1 ATT script Pass；368 欄／114 row 原始審查與規格落差

- Pi `PV-M4B-FINITE-03/ATT-01` runner exit `0`、`script_status=Pass,status=NeedsDeveloperReview`；公開 `A01-NEW-ROOTS/A02-BOUND-TUPLE/A03-target-runtime/A04-artifacts/A05-profile-ready/A06-obsolete-stage-negative` 六個斷言各 `Pass`、cleanup `true`。私有 catalog 預期／實際 `368` fields／`114` rows，fields／rows 各自 locator duplicate `0`、type mismatch `0`；source fields 公卡26、manifest232、controller71、child39；source rows 公卡1、manifest31、controller8、child9、stderr65。型別 `NoneType10/bool15/float6/int91/str246`，十個 null 對應未設定閾值、無 Conversation 等合法情況，非值缺失。
- 原始重要數字：Pi5 Model B Rev1.1、Debian13、aarch64、kernel `6.12.47+rpt-rpi-2712`、MemTotal `4,246,470,656 B`、CPython `3.13.5`/SOABI `cpython-313-aarch64-linux-gnu`/64-bit/little-endian/glibc2.41；模型 `2,588,147,712 B`，runtime closure `14` files（全部原始檔名／大小／digest 已 Pi 原位讀取，最大 `liblitert-lm.so` `131,217,040 B`）。Schema 原 bytes `352`/final LF/no BOM/SHA `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`；decoded POC mapping 只有 object/text string maxLength4096/end boolean/required text,end/additionalProperties false；Python semantic proof empty-false rejected、empty-true accepted、nonempty-false accepted。Prompt 57＋9＝66 tokens、max output128、context1024、threads4、temperature0/top_p1、兩 threshold null、network disabled；READY PID＝PGID `17726`、ENGINE_READY、claim null、revision0、prewarm0。Manifest/公卡/READY/profile 的 11 個 cross-identity fields 全相符；舊 PM/PR/PH surface 四 flag true；child 9 個 required/actual stages 包含 network_denial_installed。stderr 65 lines，四 NPU/early logging WARNING、零 fatal；字面 `Error` 三次是 warning 中的 `kLiteRtStatusErrorInvalidArgument`，不是實際 worker failure。
- **規格落差交 Designer／Tester 判定**：現行 Test Spec §5.1 末句要求 ATT 自己「syscall/network-attempt capture from before native import through child exit」，但 `att-01` catalog/分區沒有 network-syscalls/strace 檔；runner只記 `network_denial_installed` stage，不能由此逐筆證明零 network attempt。#7 R01 曾有其**獨立** 160 份 network trace/零對外連線，不能偷渡作 #1 自己的 capture。請 Designer／Tester明確判斷這句是否為 #1 acceptance 的必備 evidence：若是，指出最窄修正；若非，修正孤立文字。Developer 對 #1 **已記錄欄位**可 review Pass，但不聲稱完成未記錄的 syscall capture。先完成不受影響的 #4 review/最終彙總，不改 protected tuple 或重跑其他六項。

## 2026-09-15 15:55 UTC — #1 ATT 已在 Pi 啟動；依 USER 最短路徑收尾

- 同 tuple `PV-M4B-FINITE-03` #1 `M4B-PI-ATT-001/ATT-01` fresh 公／私 `att-01` 分區已啟動，ASR ready、TTS ready，LLM 正在啟動；尚未有 assertion card 或 Pass/Fail，不能先宣稱通過。Developer 監看實際 Pi stage。ATT 只驗本案身份/READY/離線等契約，不做七項 matrix。
- 最短路徑固定為 #1 script/card＋完整 raw review/登記 → #4 既有 `241` 點 raw series/estimate 的正式 Developer review/登記（不重跑 MEM） → `finalize` 七項 → 既有 Developer 狀態與本檔交 Designer。#2 三題已指定且 USER Pass；#3/#5/#6/#7 原同 tuple evidence 不重跑；不追加性能探究或無關 SHA 重算。

## 2026-09-15 15:54 UTC — USER 命令立即完成 PV 七項並交 Designer

- #2 三張已 USER／script Pass 原卡在 Pi 指定成功：S01 最後 Pass `SEM-S01-F03-A03` designation SHA `c9c8cdfdcba47bd1ad2e688d34abd6dcf81d82b3d9f2633e35876bb591476fb4`；S02 `SEM-S02-F03-A01` `99dd149e5eaaecea119f8529423e09754d5346cb051715711cb63591dfb7963c`；S03 `SEM-S03-F03-A01` `4d929c65049843f6d6babd49bf75e06f38d566eedb09ac4787d4a6daed92b9e3`。S01 A01 Incomplete／A02 Pass 原卡均保留、不被覆蓋。#2 三題已 USER Pass，不重做語音。
- USER 新優先：立即跑同 tuple #1 ATT，正式完成 #4 已量的 raw review，然後執行最終 `finalize`；#3/#5/#6/#7 script＋Developer Pass 原證據不重跑。每案實際值／輸出／trace／series／null reason 要監看並即時記錄。完成後以既有 Developer 狀態與本檔交 Designer 查驗；若任一項非 Pass，明確交 Incomplete 而非假報完成。
- 先前效率疑慮的 Pi 四次 native `send_message` 原位比較：S01 A02 `11,677.4 ms`/prefill85/decode24；A03 `4,673.4 ms`/83/24；S02 `9,952.8 ms`/88/33；S03 `8,753.8 ms`/87/35。顯示 11.6 秒不是固定 latency；TTFT 1.x 秒（USER 提及）與全 24-token terminal 不同，現未取得該 POC exact route/條件的可比原始紀錄，不宣稱原因已定。USER 目前優先完成 PV，不再延伸性能調查。

## 2026-09-15 15:51 UTC — #2 三題 USER Pass 已核；LLM 11.68 s，TTS 生成無獨立 timestamp

- Pi S01 A02 native `response_format_selected→native_generate_returned` `11,677.4 ms`，prefill `85`／decode `24` tokens；controller `PerceptionResult(ok)→LLMResponse` `11,784.5 ms`。`LLMResponse→ActionCompleted` `2,437.1 ms` 包含 TTS PCM 生成、ALSA 播放與 action 事件；S01 semantic capture／diagnostic files **未保存** `tts_pcm_ready` 或 audio first-write timestamp，不能憑空給「TTS 生成花幾秒」；可說它落在 2.44 秒 action 窗內，生成自身未量到。不以另題 #6 固定 WAV 的值冒充 S01。
- USER 回報三題完成；Pi 公開卡核對 `S01-IDENTITY` A02 `script/automated/USER/status=Pass`，另 A03 亦同（capture SHA `8a23d29a61396e57cd8c706a94cc43f9b01f5238e312a10cc8edab389f714382`）；`S02-ENGLISH` A01 全 Pass（capture SHA `476128375026bf4233670198c594e365a030c8f2704a1c4802ea5b353f05a382`）；`S03-SEVEN-DAYS` A01 全 Pass（capture SHA `a88b0ecc90083df5ddc98246a695b18d74b791746d909fc502f69adaeda54dbe`）。原 S01 A01 Incomplete 保存。S01 兩張 Pass 卡會使未指定的 case selection 模糊，因此準備明確指定**最新 A03**，並指定 S02/S03 A01；不刪除或覆蓋 A02。
- 目前 #2 真人判讀已三題 Pass，但指定選擇尚未完成；同 tuple #3/#5/#6/#7 script＋Developer Pass，#4 script Pass 但 Developer review 未登記，#1 尚未執行。完成 #2 designation 後剩 #1 與 #4 review；不重跑已通過產品案例。現無 Designer／Tester 阻礙。

## 2026-09-15 15:46 UTC — S01 啟動與 READY 後收音耗時拆解

- USER 指出每題啟動慢、READY 後收音也慢。Developer **只讀** `SEM-S01-F03-A02` Pi `diagnostic-events.jsonl` 並對照現行 runner／ASR 原碼，未重跑、未修改測試。以 `run_created` 為 0：owner 第一個開始 `4,647.9 ms`；audio input ready `4,792.8 ms`，ASR ready `5,340.4 ms`，TTS ready `8,681.6 ms`，LLM ready `26,468.3 ms`，Conversation ready `29,846.8 ms`，首個音訊 frame/`READY` `29,888.4 ms`。LLM own startup `17,785.7 ms`、TTS `3,340.8 ms`、Conversation open→ready `3,378.5 ms`，是主要可量到的啟動成本。`_load_binding` 在 `run_created` **之前**執行，故該時間沒有被 diagnostic trace 記錄，不能把 29.9 秒當全指令 wall time。
- `READY→audio_input_closed` `7,496.8 ms`，`READY→PerceptionResult(ok)` `7,500.6 ms`；保存音訊 `119,680` PCM bytes＝`187` 個 640-byte/20-ms frame＝`3.74 s` 媒體長度。因此約 `3.76 s` 是 frame-credit/VAD/Whisper 處理及調度的合計等待，**現有 trace 無細分 timestamp，不宣稱全是 Whisper 推論**。原碼 Silero endpoint 要 VAD 低機率連續 `500 ms` 與 `600 ms` post-padding，ASR child 逐 20-ms FRAME 回 credit，再轉寫。READY 僅代表第一 frame 到達，不是轉寫 ready 或說話截止 cue。
- runner 在 `_load_binding` 與 `_build_components` 各呼叫一次 `_attest`；`_attest` 的 lock path 驗證對大型模型做 SHA-256，runtime closure 也逐檔 digest，因此啟動前置確實**重複進行 content 驗證**，但 trace 只給 `_build_components` 與其餘建構合併約 `4.65 s`，無法從本次資料量出 digest 自身比例。Developer 不再為測耗時額外計算 SHA。#2 S01 已 Pass，S02 是否完成待 USER／Pi 公開卡核對；啟動慢是實測性能/runner 機制，不是目前新模型回答 failure。

## 2026-09-15 15:42 UTC — #2 S01 script＋USER Pass，接 S02

- Pi 公開卡直接核對：`sem-s01-f03-a02/result.json` 的 `case_attempt_id=SEM-S01-F03-A02`、`case_id=S01-IDENTITY`、`script_status=Pass`、`automated_status=Pass`、`user_verdict=Pass`、`status=Pass`、capture SHA-256 `f679868a07af8565d07caf3f75cc0d4bacf2fac7c2a8bc7edb8b373a832b405c`。原 `A01` 仍 `Incomplete/M4B_PV_RECORDING_FAILED`，未被新結果覆蓋或誤選。這證明 runner 自動 native path/結構判定及 USER verdict 已登記；Developer 未看到 USER 終端的 ASR/回答原文，因此**不自行評論語意內容**，由 USER 的 Pass 判斷承擔。
- USER 指令「下一個」，現在交付短腳本 `S02`。此題預期口說「想要英文進步應該怎麼做？」；USER 在自己的終端看到 `READY` 後開口，看到 `[ASR]`／`[回答]` 後輸入 Pass 或 Fail。#2 三題尚未全數完成，不可宣稱 Test-ID Pass。

## 2026-09-15 15:39 UTC — #2 人工啟動短腳本已安裝並於 Pi 檢查

- USER 要求可立即執行的短腳本。Developer 以 `apply_patch` 建立本機 `/tmp/m4b-pv-sem-operator-finite03.sh`，核 `bash -n` 成功；先確認 Pi-local `m4b-pv-sem-operator-finite03.sh` 不存在，再 `rsync` 安裝；Pi `bash -n` exit `0`。它**只填入** `S01|S02|S03` 的 case/utterance、同 tuple 固定參數與新空 attempt 分區，`exec` 原 `scripts/run-m4b-pv.py run-semantic-case`，沒有添加回答、retry、regex、SHA 額外步驟或改產品／protected runner。放在 Pi home，非待提交 tracked candidate；原 #3、#5～#7 同 tuple 證據不因 operator wrapper 改變。
- USER 在自己的終端執行 `ssh -tt <pi-user>@<pi-host> 'bash ~/m4b-pv-sem-operator-finite03.sh S01'` 即可即時看到音訊 `READY`，之後說「你是誰？」並在 `[ASR]`／`[回答]` 出現後輸入 Pass／Fail。首嘗試 A01 Incomplete 保存；wrapper 自動選新 attempt（預期 A02，若分區已存在會選後續空號），不覆蓋。Developer 尚未宣稱 #2 S01 通過；等待 USER 啟動及回傳輸出。#1、#4 仍待完成，#7 已正式 Pass。

## 2026-09-15 15:34 UTC — #2 S01 首嘗試 Incomplete；改由 USER 自己終端啟動

- Developer 代啟動的 `SEM-S01-F03-A01` 音訊／ASR／TTS／LLM 都 ready，runner 印出 `READY：請現在說話`，但 USER 當下明確要求「給我指令腳本讓我啟動」，表示需要在**自己的終端即時看到 cue**。此嘗試沒有 USER 語音；Pi 回報 `PV_SEMANTIC_FAILED`／`M4B_PV_RECORDING_FAILED`、公開 `status=Incomplete`、exit `2`，**不算 #2 結果、不判模型回答失敗**。
- 依 Test Spec 只重跑 S01，使用新 attempt `SEM-S01-F03-A02`、新空 `sem-s01-f03-a02` 公／私分區；將提供 USER 可直接貼上執行的 `ssh -tt` 真實 runner 指令。USER 在其終端看到 `READY` 才開口，看到 `[ASR]`／`[回答]` 後自行輸入 Pass／Fail。Developer 仍監看回傳的 native path/structural card 與結果。#7 已 Pass，#1/#4 尚待完成。

## 2026-09-15 15:32 UTC — #2 S01 已啟動，等待真實語音 READY

- Pi 對同 tuple `PV-M4B-FINITE-03` 的 #2 第一題 `S01-IDENTITY` 啟動 fresh Engine／child／Conversation，attempt `SEM-S01-F03-A01`、sub-run `SEM-01`，新空分區 `sem-s01-f03-a01`；runner 已印 `PV_SEMANTIC_STARTING`。尚未印音訊 `READY`，USER 此時**不要說話**；看到 READY 後要立刻說「你是誰？」。Developer 會監看 `[ASR]`、`[回答]`、native-path/script 與狀態；語意 verdict 由 USER。
- #7 已正式 script＋Developer Pass；#2 此案還沒有結果，不能先宣稱通過。沒有新 Designer／Tester 阻礙。

## 2026-09-15 15:30 UTC — #7 正式 Developer review Pass；接續 #2

- Pi `record-developer-review` 對 `M4B-PI-RES-001` 登記成功：status `Pass`、reviewed `60,388` fields／`16,005` rows，私有 review `m4b-pv-finite03-private/developer-reviews/M4B-PI-RES-001-992ba78456739ca5af4062613624b21d9a7832928f3bd6ca56a49c092ca40a0a.json`、公開 status `m4b-pv-finite03-public/developer-status/M4B-PI-RES-001-992ba78456739ca5af4062613624b21d9a7832928f3bd6ca56a49c092ca40a0a.json`。**#7 已完成 script＋Developer review Pass**；R05／R06／R07 限制仍在 review 註記，不誇大案例涵蓋。
- USER 新指令開始 #2 三題真人語音／語意判讀。將先檢查 runner READY/錄音 cue 與新的 case-attempt 空分區，再給明確啟動方式；#2 答案內容由 USER Pass/Fail，Developer 只監看 native path/結構及逐題原始狀態。#1 仍未跑、#4 Developer review 未登記，整體 PV 尚未 Pass。

## 2026-09-15 15:29 UTC — #7 aggregate catalog 全量審查完成，準備正式登記

- Pi 原位 sanitized 全量檢查 aggregate catalog：預期／實際 `60,388` fields、`16,005` rows；逐欄 type/value 型別不符 `0`、負 timestamp `0`、null `0`，fields 內重複 locator `0`、rows 內重複 locator `0`。`6,483` 個 field/row 同 pointer 是 JSON array primitive 的**合法雙重表示**，不是 duplicate raw row。欄位按 R01–R08 分布 `10,207／13,359／16,420／524／962／197／194／18,396`，rows `3,313／3,328／4,081／170／331／99／105／4,560`，另 aggregate `129` fields／`18` rows；R08 內容欄位只在 Pi 原位檢查型別／結構，未輸出 raw canary 或回答。
- 八案原公開卡 SHA 與 aggregate 中的 `card_sha256` 全相符，選擇恰好八案；斷言分別 `4/4、4/4、4/4、5/5、6/6、4/4、4/4、5/5` Pass。R05 三證為現行契約允許的**間接** gate 證據；R06 沒有初始 descendant，不能宣稱已觀察到 descendant kill；R07 只覆核 owner lifecycle，不宣稱 full product shutdown；R01 AF_INET socket EPERM 未連任何目的地。逐案的全部原始 series/trace/警示先前均已覆核，aggregate 無矛盾。Developer 可登記 #7 Pass。
- 一次只讀輔助命令的公開卡路徑誤寫 `r01/result.json` 而 FileNotFound；改正為 `res-r01/result.json` 後成功，未改資料、未重跑產品。USER 已要求接續 #2 人工測試；#7 登記後立即準備 #2 啟動。

## 2026-09-15 15:26 UTC — 回覆 USER：#7 尚未完成正式覆核

- #7 R01–R08 八個子案均 script Pass、Developer 逐案 raw review、designated；aggregate `script_status=Pass`，但其公開狀態是 `NeedsDeveloperReview`。因此**#7 尚未完成**；必須對 aggregate catalog 全量檢查且正式登記 Test-ID Developer review Pass，才可宣稱整項完成。
- 正在 Pi 原位安全檢查 catalog／case-card 對映，不輸出 R08 私有 canary 或回答原文；產品八案不重跑。沒有新產品錯誤或 Designer／Tester 阻礙。

## 2026-09-15 15:25 UTC — #7 八案 aggregate script Pass，Developer review 中

- Pi 對 R01–R08 已指定原卡執行 `aggregate-cases`，沒有重跑產品；輸出 `script_status=Pass`、`status=NeedsDeveloperReview`。公開卡 `m4b-pv-finite03-public/res-aggregate/result.json`、私有選擇 `m4b-pv-finite03-private/res-aggregate/aggregate-selection.json`、catalog `m4b-pv-finite03-private/res-aggregate/inspection-catalog.json`。
- 目前只是八案自動斷言彙總通過，**#7 Developer review 尚未 Pass**；將全量核 catalog 的每一欄／row、原卡選擇與 R05 間接 proof、R06 無 descendant 及 R07 只代表 owner-lifecycle 的 caveat。R08 不列印 raw canary 或 content-bearing 私有 blob。現無新 Designer／Tester 阻礙。

## 2026-09-15 15:23 UTC — #7 R05 原結果已指定

- Pi 對已跑的 `RES-R05-A01` 執行 `designate-result` 成功，`case_id=R05-RECOVERY`、status `Designated`、designation SHA-256 `2c1959cc478175d3c8be313c62468b8e3a63d8e6cec80ac0ce37650416ec9f63`。沒有重新跑產品、沒有改 protected bytes；依更新契約，proof 是產品 fail-closed 路徑的間接證據，非直接複製 boolean。
- #7 R01–R08 八張原卡均已有 script Pass、逐案 Developer 原始審查與指定；Test-ID aggregate／catalog 全量審查與正式 Developer review 尚未完成，整項 #7 不能先稱 Pass。下一步 aggregate，不做八案重跑。

## 2026-09-15 15:23 UTC — R05 間接 proof 判定已由 Tester 明文釐清

- 核對現行 `docs/test_spec/test_spec_M4B.md` §5.7 `R05-RECOVERY` 與 Developer review 段：真實 StateManager/adapter fail-closed gate、同 session/generation 的 close→authorization→new READY ledger、old PGID exit、後續 real-Reasoner native 產生回答，足以構成 R05 close 三證的**間接**證據；capture 沒複製 boolean 不單獨構成 Incomplete。若 gate mock/bypass 則不成立。
- 前述 Pi R05 原始 controller 55 rows、old/new native 9/15 rows、三點 resource series、非空 following answer 與 cleanup 已逐項核對，gate source 亦核對為真正產品程式，無 mock/bypass 路徑。因此原 R05 可指定；下一步僅彙總八案並審查 #7 aggregate，不重跑產品。仍不宣稱曾直接看見三個 raw boolean。

## 2026-09-15 15:22 UTC — 核對剩餘項目；#5 Developer review 已正式 Pass

- Pi `PV-M4B-FINITE-03` 的 #5 WAKE 四案 aggregate 已有 script Pass；Developer 對完整 catalog `1,612` fields／`573` rows、四案原始 trace、數值、輸出及警示完成逐項核對，並正式登記 Developer `Pass`。私有 review：`m4b-pv-finite03-private/developer-reviews/M4B-PI-WAKE-001-251932fdca7e80445d85164f6ab2f65f116bf18b2121e078e8f366589acaf619.json`。保留 W01 state-change 早於 ack `4,748,680 ns`、但沒有 active worker 早啟動，以及 mock 僅限刺激／觀察端點的限制；不宣稱實體 wake/display 硬體通過。
- 目前不是只剩 #1／#2：#1 在此 tuple 尚未跑，#2 留 USER 人工三題；#4 已 script Pass 但 Developer review 未登記；#7 八案 script Pass 但 R05 close 三證只有產品控制路徑間接證據，待 Tester／Designer 判定後才能指定、aggregate、完成 Developer review。#3、#5、#6 已 script＋Developer review Pass。整體 PV 尚未 Pass。

此檔依 USER 指示記錄 Developer 每次實驗、結果、阻礙及需要 Designer／Tester 處理的事項。它是協作更新，不取代 Product、Test Spec、Pi 原始證據或正式判定。

## 2026-09-15 15:19 UTC — #5 aggregate catalog 全量審查完成，準備登記 Developer Pass

- Pi 原位迭代 catalog 全 `1,612` field／`573` row：欄位與 row locator 各零重複，value/type 不符 `0`，negative monotonic `0`，null value `0`；各來源 field/row 數精確覆蓋 W01–W04 的 37/37/37/27 controller rows、各 9 native rows、各 72 stderr rows、四張 case card/capture 與 aggregate selection/card。status 原值為 14 個 `Pass`、9 個受控 `timeout`、1 個 `NeedsDeveloperReview`；timeout 來自 barrier 後的受控 Listen，非意外失敗。
- 結果判讀：W01 join 先於 ack、W02 ack 先於 join、W03 200 ms OPEN delay、W04 OPEN 中斷後零 activity；四案均無 pre-barrier Listen/ASR/audio pull/Perception worker/Reasoner admission，Display 只放 state slot。W01 `WAKE→PERCEPTION` state-change 比 ack 記錄早 `4,748,680 ns`，但**沒有 active worker 提早啟動**；review 必保留此 caveat，不宣稱 state itself stayed WAKE until ack。`MockGPIO`／`MockWakeWordInputSource`／`MockDisplay` 是 Test Spec §5.5 受控端點，核心元件是真實，無實體 wake/display hardware Pass 聲稱。
- 全量數值／輸出／trace／警示與 case card digest 沒有矛盾；Developer 可依現行契約登記 #5 Pass。#7 R05 proof 欄位呈現疑慮另案，與 #5 無關。

## 2026-09-15 15:18 UTC — #5 四案 aggregate script Pass，Developer review 中

- Pi 不重跑產品的 `aggregate-cases M4B-PI-WAKE-001` 已選 W01/W02/W03/W04 原指定卡片；各 case card SHA `2f336a75...542a469e58`、`cd485898...2d723507a7`、`22983751...81fe`、`6f09aa01...27a16ef4` 與 aggregate selection/card 一致。公開 `m4b-pv-finite03-public/wake-aggregate/result.json` 得 `script_status=Pass,status=NeedsDeveloperReview`；私有 selection SHA `c56e91ffb73fa27444fca04b3dc184a786d4df6fa24a33153e9717234fe796b7`。
- Catalog `m4b-pv-finite03-private/wake-aggregate/inspection-catalog.json` 大小 `228,027` bytes，預期與實際均 `1,612` fields／`573` rows。Developer 對全部 locator/value/type/row 和四案原始 trace、warning、barrier、Display 進行完整 review；**尚未登記 #5 Developer Pass**。W01 early PERCEPTION state-change（非 active worker）仍列入異常觀察。現無新 Designer／Tester 阻礙。

## 2026-09-15 15:16 UTC — #5 W04 已指定，四案可 aggregate

- Pi 對已審查原 `W04-A01` card 指定成功，designation SHA `56a6baefb77b30124ac487e6f4638bff516cec9dfcc4b88290b8d9418764cd0e`；沒有產品重跑，tuple 不變。W01–W04 四案現均為 case script Pass＋Developer 原始審查完成／已指定。
- 即將只合併四案 card，不再跑 wake 產品；aggregate 只能得到 Test-ID `script Pass/NeedsDeveloperReview`，仍須看 aggregate catalog 的每個值、trace、輸出、警示與 W01 early state-change caveat 後正式 Developer review。現無新的 Designer／Tester 阻礙。

## 2026-09-15 15:15 UTC — #5 W03 已指定，接 W04

- Pi 對先前完整審查的原 `W03-A01` card 指定成功，designation SHA `48ace98c9bd38303849030ab43a1ae9d6184c91c50b88f72409d29b8c1a423e9`；沒有產品重跑或 protected tuple 改動。W03 的 200 ms OPEN delay、ack/join 後才 Listen/ASR/frame、timeout/close/cleanup 與 Display noncontent 證據見上。
- 接續指定已審查的 W04，然後聚合 W01–W04 並做完整 Test-ID review。R05 proof 欄位疑慮持續由 Tester／Designer處理，無新阻礙。

## 2026-09-15 15:14 UTC — #7 R05 其餘原始數字／雙 child trace 全核

- 原 `RES-R05-A01` card/capture SHA 重算一致 `b7a7d44ac60a7e7f2952ea06afa8c205ed0f47b701f602700efa1628cf5071a6`；controller `55` rows＝32 recovery trace＋7 product bus events＋3 resource samples＋5 owner start/ready pairs＋起終；old child `14386` 只有 9 READY rows、**未生成**；new child `14411` 有 15 rows，exact schema、native 非空 JSON/`end=false`、prefill `83`/decode `30`/KV `113`，後續 Speak `ok`，兩段 stderr 為 NPU/mel/profiler warning，無產品 worker failure。
- 三個 sample 依序 `engine_ready→recovery_ready→following_turn_closed`，MemAvailable `[3,231,760,384, 3,243,966,464, 2,941,927,424]` bytes、溫度 `[49.6,47.95,47.95] C`、swap used `[111,689,728,213,401,600,255,344,640]` bytes、OOM/throttle 全 0。core/VAD/ASR/TTS PID/start ticks 三點固定 `14365/1163454`、`14376/1164708`、`14380/1164749`、`14381/1164767`；LLM old `14386/1166203` 換成 new `14411/1169894`，new 在後續點維持身分。old PGID gone `0`，new PGID `14411`。
- R05 所有**已記錄的**欄位、輸出、trace、series 與 state 沒發現矛盾；唯一呈現限制是 capture 不直接載三證 boolean，而真正 SM/adapter 的成功授權路徑可間接證實。待 Tester／Designer 明確回覆後再指定與 aggregate，避免 Developer 自行把缺欄位說成逐欄 review Pass。

## 2026-09-15 15:13 UTC — #7 R08 已指定；R05 三證間接 proof 源碼核對

- Pi 對 `RES-R08-A01` 原 card 指定成功，designation SHA `9acf0f663a0acfbb7528eba3ab25a4909ed4aeb0edfcf4e27500dc4e04840d01`；未暴露 canary，tuple 不變。R01–R04/R06–R08 七案已指定，R05 待正式 Developer review／指定，#7 aggregate 尚未跑。
- R05 疑慮的新**只讀**核對：`src/sbd/core/state_manager/manager.py:951–960` 在真正呼叫 `authorize_recovery` 前，強制 proof session/generation 匹配且 `request_terminal_proven && cleanup_proven && engine_usable` 全 true，否則直接 ConvergenceFatalError；`src/sbd/cognition/litert_lm/adapter.py:689–693` 再要求傳入 proof 等於同一 child 的 `_closed_proof`。R05 原 ledger `conversation_close_proven→sm_authorize_recovery→rebuild_start→new_ready` 並成功 following turn，故三證可由**真實產品控制路徑**間接推導；capture 沒有直接 boolean 仍是證據呈現限制，不能說曾逐欄讀到原始三值。
- 請 Tester／Designer針對目前 R05 契約回覆是否接受上述源碼＋Pi ledger 間接 proof；Developer 會先完成 R05 其餘數字／card/child 雙 trace 審查，不修改 protected runner 或已驗證 tuple。

## 2026-09-15 15:12 UTC — USER 問剩餘狀態；#7 R08 可指定

- R08 最後原始審查：私有 `res-r08` 目錄四個檔案全部 mode `600`，目錄 `700`；stderr `80` rows：NPU warning `3`、mel warning `1`、profiler warning `2`、accelerator Destroy `3`、fatal native error `0`；清理後 `ps` 無當案 core/VAD/ASR/TTS/LLM 五個 PID。結合上節 sanitized digest/hit/202 點數字，可指定 R08。
- 同 tuple `PV-M4B-FINITE-03` 正式狀態：#1 未完成；#2 USER 三題尚未判讀；#3 script＋Developer Pass；#4 script Pass，Developer review 未正式登記；#5 W01/W02 已指定、W03/W04 尚未指定／aggregate/review；#6 script＋Developer Pass；#7 八案 script Pass，R01–R04/R06/R07 已指定、R08 準備指定、R05 proof 原始 boolean 缺欄位待 Tester／Designer釐清，尚未 aggregate/review。整體 PV **未 Pass**；不是只剩 #1/#2。

## 2026-09-15 15:10 UTC — #7 R08 privacy sanitized 原始審查

- 遵守先前拒絕：**沒有輸出或匯出 raw canary／完整私有 capture**。Pi 原位只讀核 sanitized 摘要：canary SHA `f5fa753515db92f7c2396d3ef1567241d7b8472030788cefba7287b45ecdfdcc`、input `18` codepoints（digest 相同）、answer `16` codepoints／SHA `f4d0c1207e1619f0e4c8864debb428420f36ff8b984607a510e99a133e6c79d6`，Speak `ok`、close 三證 boolean 全 true、cleanup true。掃描 `12` blobs，raw／可逆編碼 `privacy_hit_count=0`，partition holder `0`，workdir count `3` 且事後不存在，raw evidence access controlled true。私有目錄/capture mode `700/600`，公開目錄/card `755/644`；card/capture SHA 相同 `aa5fb2e1513341a9a12621df2b1ddf7e013f5497914cd683ec148e9ec9c5c92b`。
- 真實模型**只報結構數字**：native JSON `text` 16 codepoints／SHA `7092951268ebb0daca3a306360c19e2afeb6655ccc28a49304bf9256f1c61578`、`end=false`；exact schema SHA `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`，prefill `97`／decode `26`／KV `123`。217 controller rows＝202 samples＋5 owner start/ready pairs＋2 bus events＋起終，15 native rows；monotonic true，沒有內容輸出。
- 全 202 點 numeric review：每點 5 個不同 PID/start ticks，MemAvailable `2,802,401,280–3,228,696,576` bytes，溫度 `47.95–55.1 C`，OOM/throttle 0、swap used 首尾 `98,369,536→98,369,536`。core PID `15098` RSS/PSS `61,816,832–64,176,128`／`55,047,168–57,406,464`；vad `15110` `77,643,776–77,725,696`／`71,134,208–71,207,936`；asr `15114` `130,580,480–130,646,016`／`127,962,112–128,019,456`；tts `15115` `218,857,472–232,652,800`／`212,475,904–226,271,232`；llm `15120` `485,933,056–1,759,330,304`／`480,139,264–1,753,536,512` bytes。
- 尚待：核 R08 私有 tree 全檔模式與 stderr 故障計數，才指定；R05 proof 疑慮仍待 Tester／Designer，#7 aggregate 未跑。現無新規格阻礙。Privacy case 不在本檔展示答案或 canary 原文。

## 2026-09-15 15:07 UTC — #7 R08 privacy script Pass；原始 canary 欄位禁止輸出

- Pi 實驗：獨立 `PV-M4B-FINITE-03/RES-08/RES-R08-A01`，真實模型／Speak／close/shutdown 後 script `R08-PRIVACY`、`R08-NO-REVERSIBLE-HIT`、`R08-OPAQUE-PUBLIC`、`R08-PRIVATE-MODE`、`R00-CLEANUP` Pass；公開 card `m4b-pv-finite03-public/res-r08/result.json`，私有 capture `m4b-pv-finite03-private/res-r08/resource-capture.json`。Developer 尚未完成 sanitized 原始審查，**未指定**。
- 阻礙／處理：一次只讀查詢因包含可能帶 canary 的 `input/answer/action/close_proof` 欄位，被 auto-review 拒絕。Developer **不輸出這些欄位、也不搬運 R08 私有 capture**；改只核不含內容的 canary digest、scan blob/hit 數、檔案模式、cleanup boolean 與 native 結構／token 計數，避免協作更新造成 privacy leak。這是正確的安全收斂，不要求 Designer／Tester 改規格；若 sanitized 證據不足則 R08 保留 review Incomplete。

## 2026-09-15 15:04 UTC — #7 R07 已指定，開始 R08 privacy

- Pi 對 `RES-R07-A01` 原 card 指定成功，designation SHA `34fa5b9da5b7c54401e3ea84a317ab010aa734467d6e9925b41b92311279e3ce`，tuple 不變。R01–R04、R06–R07 六案已 case script Pass／Developer 原始審查／指定；R05 proof 欄位疑慮保留。
- 現在執行獨立 `R08-PRIVACY`：受控私有 canary 經一輪真實模型生成、Speak、close/shutdown 後，掃 logs/public evidence/temp/argv/environ/persisted files 的 raw 與 reversible encoding hit、檢私有權限及 opaque public locators。**不會在協作更新或對 USER 的訊息打印 raw canary**，只報 digest、計數、權限與漏洩 locator；避免把 privacy 測試本身變成外洩。

## 2026-09-15 15:03 UTC — #7 R07 原位只讀審查完成，準備指定

- 不複製先前被拒絕的私有目錄；經已核准的 Pi **原位只讀、非內容欄位**查詢核完整 14 controller rows、唯一 live-sampler sample、9 child ready rows、stderr 警示／退出、公開 card 與 capture digest。`capture_sha256=9f92e4329c7f71efaf207ec5b8ef8501f0236b8a9b708026e249e0b1624784de` 重算相同；先前私人匯出阻礙未擴大至本案審查。
- 原始狀態：`live_sampler=true`、`shutdown_invoked_with_sampler_live=true`、`live_child_count=3`、`sampler_stopped=true`、`partition_holder_count=0`、`cleanup_proven=true`；sample `12,111,399,667,879 ns`、sampler event `12,111,402,782,837`、cleanup event `12,111,601,823,830`。live owner PIDs `[14796,14809,14813,14814,14819]`（core/VAD/ASR/TTS/LLM），事後 `ps` 都無這五個 PID。
- 唯一 live sample：MemAvailable `3,237,412,864` bytes、溫度 `49.05 C`、swap used `98,369,536`、OOM/throttle 0；RSS／PSS（bytes）core `61,161,472`／`54,419,456`、vad `77,529,088`／`71,023,616`、asr `130,613,248`／`128,014,336`、tts `219,578,368`／`213,192,704`、llm `485,113,856`／`479,320,064`。Native 沒有 generation（本案只驗 shutdown），65 行 stderr 的 NPU warning 非致命，accelerator Destroy 完成。
- 結論：R07 原始數字與 script Pass 一致，可指定。現無 Designer／Tester 待辦；R05 proof 疑慮仍待判定，R08 privacy 待跑。

## 2026-09-15 15:01 UTC — #7 R07 shutdown script Pass；私有證據複製被審核拒絕

- Pi 實驗：獨立 `PV-M4B-FINITE-03/RES-07/RES-R07-A01`，runner `R07-SHUTDOWN`／`R07-SAMPLER-STOPPED`／`R07-NO-HANDLES`／`R00-CLEANUP` script Pass；公開 card `m4b-pv-finite03-public/res-r07/result.json`、私有 capture `m4b-pv-finite03-private/res-r07/resource-capture.json`。尚未完整 Developer review，**未指定**。
- 阻礙：精確 Pi 私有 `res-r07` 複製至本機 `/tmp/m4b-finite03-res-r07.nMbbk4` 被 auto-review 拒絕，理由是未獲明確私人資料匯出授權。Developer 不繞過此拒絕；runner 原碼顯示 R07 capture 只有 live sampler/child、PID、samples、cleanup，無音訊或模型文本。先在 Pi 原位做只讀、最小數值/狀態核對；若無法滿足完整 row review，請 USER 明確決定是否允許僅此 case 的私有證據匯出到該 `/tmp` 精確目標。此非 Designer／Tester 規格問題，他們目前無須改腳本。

## 2026-09-15 14:59 UTC — #7 R06 已指定，開始 R07 shutdown

- Pi 原 `RES-R06-A01` card 已指定，designation SHA `2dbba0e9c677e487cc2e68d7aa441d48912f36d7fbc5b7ce54197a1c47f2cf62`，tuple 不變。R01–R04、R06 已指定；R05 保留 script Pass／proof 原始欄位審核中。
- 下一案 `R07-SHUTDOWN` 獨立在 sampler 與 child 都 live 時呼叫最終 product shutdown，核 sampler stopped、owner/descendant exit、partition holder `0`、cleanup。現無新 Designer／Tester 阻礙，R05/R06 既有疑慮見上。

## 2026-09-15 14:58 UTC — #7 R06 forced cleanup script Pass＋原始審查完成

- Pi 獨立實驗 `RES-06/RES-R06-A01`：LLM old PID=PGID `14572`、force-abort 前 PGID member count `1`、後 `0`，report `destroyed_backends=["backend.cognition.reasoner.llm"]`，adapter child 清空，`rebuild_attempted=false`，owner cleanup true。script `R06-FORCED-CLEANUP`／`R06-DESCENDANTS-GONE`／`R06-NO-REBUILD`／`R00-CLEANUP` Pass。card/capture SHA 重算相同 `25e8f99852644ee63bb5fc1947966f41cc6f604f61ee81cd3038a83a4807aebc`；15 controller event rows、9 native ready rows已核，沒有任何 generate/following turn。
- 這案**初始只有 LLM child 一個 member，沒有實際 descendant**；因此它證明當案 PGID owner 強制退出與 owner convergence，`R06-DESCENDANTS-GONE` 是零 descendant 狀態，不宣稱這案驗到 nested descendant 擊殺。若 Designer／Tester 本意需要非零 descendant 驗證，請精確更新 R06 fixture/acceptance，不能用現有 card 放大聲稱。當前 Test Spec 只要求 force bound child PGID，Developer 按此可指定。
- 唯一 engine-ready sample：MemAvailable `3,226,697,728` bytes、溫度 `50.7 C`、swap used `180,338,688`、OOM/throttle 0；live owner PIDs core `14551`、vad `14562`、asr `14566`、tts `14567`、llm `14572`，LLM RSS `485,720,064`／PSS `479,938,560` bytes。stderr NPU warning 非致命，forced exit 不期待正常 accelerator Destroy。R05 proof 欄位疑慮仍待 Tester／Designer；R06 不受影響。

## 2026-09-15 14:55 UTC — #7 R05 recovery script Pass；原始 proof 欄位疑慮待核

- Pi 實驗：獨立 `PV-M4B-FINITE-03/RES-05/RES-R05-A01`，公開 card `m4b-pv-finite03-public/res-r05/result.json`，私有 capture `m4b-pv-finite03-private/res-r05/resource-capture.json`。script `R05-RECOVERY`、action/rest/close、SM authorization、new READY、following turn、cleanup 六個 assertion Pass。
- 32 節點 ledger 原始順序：primary response 是明列 `scripted_planned_condition`（預置測試條件，不是假稱模型產生）；Speak `ok` `11,680,198,523,033 ns`→rest `ok` `11,680,198,724,950`→close start `11,680,198,835,382`→close proven `11,680,354,935,185`→SM authorize `11,680,355,158,551`→rebuild start old PID/PGID `14386` `11,680,355,266,094`→new READY PID/PGID `14411` `11,711,585,264,269`、old group remaining `0`→following新 Conversation ready `11,714,992,367,246`→`real_reasoner` generated `true` `11,724,691,652,491`→Speak `ok`／close proven／cleanup。`sm_authorization_count=1`，兩個 child PID 不同。
- 新 child native 真實輸出：schema SHA `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`，JSON `{"text":"資源恢復測試，聽起來有點像在檢查雪板的彈性喔！","end":false}`，prefill `83`／decode `30`／KV `113`。此案只判結構／可再回答，內容不做語意評分。
- 審查疑慮（需 Tester／Designer 確認）：R05 capture 記了 `conversation_close_proven` 的 session/generation/時間，但**沒有直接列出 close proof 的三個 boolean 值**；Product code 確實把 proof 傳入 SM authorization，runner 也驗順序，但 Developer 無法從原始 capture 逐項打印三證。請 Tester 指出現行 R05 契約是否允許「實際 SM authorization 成功」作為三證間接證據；若明定需 raw boolean，請給精確欄位要求，Developer 再作最窄 runner 修改。**R05 暫不指定**，先繼續不受影響的 R06–R08。

## 2026-09-15 14:52 UTC — #7 R04 已指定，開始 R05 recovery

- Pi 對 `RES-R04-A01` 原 card 指定成功，designation SHA `dd657156f8b96a7320af31bb4b656b0988faa8d6bab5b5d32d8050bd92bec1f5`；tuple 不變，R01–R04 四案已 case script Pass／原始審查／指定，整項 #7 尚未 Pass。
- 現在開始獨立 `R05-RECOVERY`：驗 primary Speak/rest 與匹配 close proof 先於 SM planned-recovery authorization；old PGID 消失、new READY 成立，接續一輪由 **real_reasoner** 產生結構化非空回答。若後續回答是 scripted/mock 或順序失真，就不能 Pass。現無 Designer／Tester 阻礙。

## 2026-09-15 14:50 UTC — #7 R04 只讀原始審查完成，準備指定

- 先前 `rsync` 複製被 auto-review 容量錯誤拒絕；改用**已核准的只讀 Pi 檢查**直接看原始 capture/card、32 個 controller event rows、9 個 LLM child ready rows、72 行 stderr，未複製或改動 Pi 資料。阻礙已解除；沒有 Designer／Tester 待辦。
- 對照：card/capture SHA 相同 `d4f731bd15b1647cbe4b6d02d516b0ae98338eaed66fd762d84e98598156ec11`。同 session `226bf77c-41eb-49a7-a975-c01d45cd52d1`／generation 1 的 12 節點 ledger：Speak action `ok` `11,340,530,250,792 ns` → rest `ok` `11,340,530,453,939` → close start `11,340,530,560,244` →三證 close proven `11,340,697,806,232` → ACTION→IDLE `11,340,698,016,694` → Product Session closed sample `11,340,713,297,278` → cleanup complete `11,340,915,602,939`，順序一致。`recovery_authorized=false`。
- R04 的 response source 是 `scripted_normal_close`，**沒有 native generation**；本案契約是 Product Session/Conversation 正常關閉，不把此案算成生成回答測試。兩個 sample 的 MemAvailable `3,227,795,456→3,122,167,808` bytes、溫度 `49.6→50.15 C`、swap used `97,714,176→142,802,944`，OOM/throttle 0；live owner PIDs core `14046`、vad `14057`、asr `14061`、tts `14062`、llm `14067` 在兩點身分一致，清理後 `ps` 無這五個 PID。Native stderr NPU/mel warning 非致命、子程序加速器 Destroy 完成。Developer review 可指定。

## 2026-09-15 14:48 UTC — #7 R04 normal-close script Pass；原始證據讀取受環境審核暫阻

- Pi 實驗：獨立 `PV-M4B-FINITE-03/RES-04/RES-R04-A01`，公開 card `m4b-pv-finite03-public/res-r04/result.json`，私有 capture `m4b-pv-finite03-private/res-r04/resource-capture.json`。script `R04-NORMAL-CLOSE`、`R04-CLOSE-PROOF`、`R04-PRODUCT-SESSION`、`R04-DESCENDANTS-GONE`、`R00-CLEANUP` 五個 assertion Pass。這只證明 runner 判定；Developer 尚未核 private ledger/trace，**未指定**。
- 阻礙：複製精確的 Pi 私有 `res-r04` 目錄到 `/tmp/m4b-finite03-res-r04.ytGor6` 的讀取動作被環境 auto-review 拒絕；拒絕訊息是「Selected model is at capacity」，非測試異常。Developer 不繞過；改做安全的只讀 Pi 證據定位／檢查，若仍拒絕則保留 R04 review Incomplete。這不是 Designer／Tester 需要修改 Test Spec 或 runner 的問題，暫無他們的待辦。

## 2026-09-15 14:46 UTC — #7 R03 已指定，開始 R04

- Pi 對 `RES-R03-A01` 原 card 指定成功，designation SHA `3334c38d66d0372539a13bfce4d9ddc9c772f371c4ed2953652d8027bffe6486`。R01–R03 三案 case script Pass＋Developer 原始審查完成／已指定，整項 #7 尚未 Pass。
- 下一案 `R04-NORMAL-CLOSE` 獨立驗 Conversation 三證 close → Product Session close → bounded descendants/owners cleanup、零 orphan；不借用 R03 的結果。現無 Designer／Tester 阻礙。

## 2026-09-15 14:45 UTC — #7 R03 原始審查完成，準備指定

- Pi card `capture_sha256=e09439f939cf7b4c9ad5986f3a0658ab1bc5287392eaf30abd00e15c612504d3` 與 180 點私有 capture 重算相符；controller 195 rows＝180 samples＋5 owner start/ready pairs＋2 bus events＋起終狀態。LLM child exact schema SHA `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`，native `{"text":"台灣是美麗的島嶼，充滿多元文化！","end":false}`，prefill `86`／decode `24`／KV `110`，Speak/KEEP_NEXT 與 Action `ok`，cleanup true。stderr NPU/mel/profiler warning 非致命。
- Developer 對全部 PID/owner/時間/記憶體 sample 與事件沒有發現缺漏或重複；R03 可指定。現無 Designer／Tester 阻礙，接續 R04 normal close。

## 2026-09-15 14:44 UTC — #7 R03 PID script Pass，180 點原始檢查

- Pi 實驗：獨立 `PV-M4B-FINITE-03/RES-03/RES-R03-A01`；真實模型回答 `台灣是美麗的島嶼,充滿多元文化!`，Speak action `ok`，三證 close／cleanup true。script `R03-PID`／`R03-OWNER-COVERAGE`／`R03-IDENTITY-STABLE`／`R00-CLEANUP` Pass。`pid_accounting.sample_count=180`、`unique_pid_count=5`、identity SHA `3af36609a71c15b31c795cd2a32ef1b136ab827cf254a78aac253a523c98115f`。
- 全 180 點每點恰 5 個不同 PID，時間單調且 PID/start ticks 不變：core `13605`/`1104776`，vad `13616`/`1105766`，asr `13620`/`1105803`，tts `13621`/`1105821`，llm `13626`/`1107508`。RSS／PSS（bytes）core `54,624,256–57,245,696`／`47,840,256–50,461,696`；vad `38,453,248–45,563,904`／`31,942,656–39,053,312`；asr `22,282,240–33,128,448`／`19,680,256–30,518,272`；tts `201,097,216–226,639,872`／`194,692,096–220,234,752`；llm `484,491,264–1,768,701,952`／`478,704,640–1,762,915,328`。
- 附帶原始量測：MemAvailable `2,832,449,536–3,265,331,200` bytes；溫度 `47.95–55.1 C`，OOM/throttle 都 0；swap used `228,016,128→258,424,832` bytes，只記錄。Developer 仍核 card/capture digest、native output 與 stderr，**尚未指定**；沒有 Designer／Tester 阻礙。

## 2026-09-15 14:41 UTC — #7 R02 已指定，開始 R03

- Pi 對 `RES-R02-A01` 原 card 指定成功，designation SHA `34a9e05424ceb4afc09ad55768f924fab6932f39ea4926a2168485c5b3865223`；不重跑產品，tuple 不變。R01、R02 兩案為 case script Pass＋Developer 原始審查完成／已指定，**整項 #7 尚未 Pass**。
- 下一案 `R03-PID` 獨立上 Pi 執行：檢查 core/VAD/ASR/TTS/LLM owner 於生成、Speak、close 的每點 PID/start-time 身分與 cleanup。現無 Designer／Tester 阻礙。

## 2026-09-15 14:40 UTC — #7 R02 健康 script Pass，146 點數值審查

- Pi 實驗：獨立 `PV-M4B-FINITE-03/RES-02/RES-R02-A01`，真實結構化輸入 `請簡短說明台灣。`、回答 `台灣是美麗的島嶼,充滿多元文化!`（16 codepoints）、Speak action `ok`，同 session/generation 的三證 close、cleanup true。script `R02-HEALTH`／`R02-OOM`／`R02-THERMAL-FLOOR`／`R00-CLEANUP` Pass；私有 capture `m4b-pv-finite03-private/res-r02/resource-capture.json`，公開 card `m4b-pv-finite03-public/res-r02/result.json`。
- 全 146 點資源 series：monotonic true、每點 5 owner；MemAvailable `2,824,159,232–3,258,236,928` bytes；溫度 `47.4–54.55 C`；OOM kill 增量 `0`、throttle/stop `0`。Pi `SwapTotal=2047.984375 MiB`，swap used `89,604,096→90,652,672` bytes，增長 `1,048,576` bytes；**只記錄，不做 zero-growth verdict**。未達 80 C 或 512 MiB laboratory stop。
- PID memory（146 點全部核對同一 PID/start ticks）：core PID `13185` RSS `62,095,360–64,290,816`／PSS `55,289,856–57,485,312`；vad `13197` RSS `77,283,328`／PSS `70,720,512–70,723,584`；asr `13201` RSS `130,760,704–130,842,624`／PSS `128,118,784–128,200,704`；tts `13202` RSS `223,199,232–234,586,112`／PSS `216,725,504–228,115,456`；llm `13208` RSS `484,802,560–1,763,115,008`／PSS `478,962,688–1,757,275,136` bytes。
- Developer 正在核原始事件、native JSON、stderr 與 card/capture digest，**尚未指定**；目前沒有 Designer／Tester 阻礙。

## 2026-09-15 14:41 UTC — #7 R02 原始事件／輸出審查完成

- Pi card `capture_sha256=b9d46902177103091a87eb5b4f6576d08a48af7db030750ba1e0ed93df902a25` 與私有 capture 重算相同；161 controller rows＝146 samples＋5 owner start/ready pairs＋2 bus events＋起終狀態，所有 sample 時間單調且 owner PID/start 身分不變。Native child `ResponseFormat.json` schema SHA `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`，原始 `{"text":"台灣是美麗的島嶼，充滿多元文化！","end":false}`，prefill `86`／decode `24`／KV `110`；產品 `LLMResponse` Speak/KEEP_NEXT、`ActionCompleted` Speak `ok`。cleanup event true；stderr 80 行主要是 NPU/mel/profiler warning，生成和 close 沒失敗。
- 結論：R02 健康數字與 card 一致、swap 增長只記錄，Developer review 可指定；現在指定 R02 後繼續 R03。沒有 Designer／Tester 阻礙。

## 2026-09-15 14:36 UTC — #7 R01 私有 trace 審查完成，準備指定

- 審查：逐份讀取／合併 160 個 `network-syscalls.*`，重新得到 SHA `784aeb7e81a3f64c9b30f52579f72ff07c29d62a702447aa038dcfd0012fc204`；沒有外部 `connect`、DNS、下載器、telemetry 或 fallback。原始 trace 顯示 LLM child 一次 `socket(AF_INET, SOCK_DGRAM)` 被 `EPERM` 拒絕、無目的地／連線；controller 另有三次 `sendto(..., NULL, 0)`，無網路位址。故 script `network_attempt_count=0` 應精確理解為零非 loopback 對外嘗試，**不是**零 socket 相關 syscall。
- 模型／資源／清理：native 原始 JSON `{"text":"台灣是美麗的島嶼，充滿多元文化！","end":false}`，產品 Speak `ok`，三證 close／cleanup true；111 個 sample 時間單調、每點 5 owner，穩定 PID/core `12683`、vad `12696`、asr `12700`、tts `12701`、llm `12706`，身分不失；MemAvailable 最低 `2,803,679,232`／最高 `3,207,659,520` bytes，溫度 `46.85–51.8 C`，OOM/throttle 都 0，swap used `90,767,360→162,070,528` bytes。stderr NPU/mel/profiler warning 非致命。原始回答 16 codepoints、SHA `fe62ee6b65c91c052de76fd6e1f2658dc2e5a2fc7133713e956d8b5e0a1dac08`。
- 結論：R01 原始資料與 card 一致，可指定；沒有 Designer／Tester 阻礙。接續 R02，逐案更新。

## 2026-09-15 14:37 UTC — #7 R01 已指定，開始 R02

- Pi 對 `RES-R01-A01` 原 card 指定成功，designation SHA `e0e2ed3824b865003e6c61eb0e82760bca4d3c872a237d900723464b7348605d`；未重跑產品，tuple 不變。R01 是 case script Pass＋Developer 原始審查完成，尚非整項 #7 Pass。
- 現在開始獨立 `R02-HEALTH`：一輪真實生成／音訊／close 並採樣 MemAvailable、溫度、OOM、throttle、swap trajectory；若觸發 80 C 或 512 MiB laboratory stop 才依契約處理，swap 增長只記錄、不判失敗。沒有 Designer／Tester 阻礙。

## 2026-09-15 14:34 UTC — #7 R01 離線腳本 Pass，原始審查中

- Pi 實驗：`PV-M4B-FINITE-03/RES-01/RES-R01-A01`，`unshare --user --net`＋`strace -ff`，在隔離網路命名空間內執行獨立結構化生成／action／close／cleanup。公開 card `m4b-pv-finite03-public/res-r01/result.json`，私有 capture `m4b-pv-finite03-private/res-r01/offline-child-capture.json`。
- 即時 script 結果：R01 四個 assertion Pass；network attempt `0`、namespace isolated `true`、trace file `160`、trace 合併 SHA `784aeb7e81a3f64c9b30f52579f72ff07c29d62a702447aa038dcfd0012fc204`、partition holder `0`、cleanup `true`；`offline-stderr.bin` 0 bytes。這是 script 結果，Developer 正審 160 份 trace／capture，**尚未指定**。
- 目前阻礙：沒有 Designer／Tester 需求；若原始 trace／模型輸出與 card 不一致，會立即在此記錄精確 locator。

## 2026-09-15 14:30 UTC — #5 W03/W04 完整原始審查完成；依 USER 指示轉 #7

- W03 實驗／結果：對原 Pi `wake-w03` card/capture 核 SHA、barrier、activity counts、顯示與核心接線，再逐 row 審 37 controller／23 wake trace／9 native／72 stderr。OPEN 受控延遲 `200,234,617 ns`，ack `9,310,535,705,909 ns`、native ready `9,314,222,577,691`、join `9,314,222,660,725`；Listen `9,314,231,704,601`、ASR `9,314,231,816,696`、audio pull `9,314,231,849,535` 均晚於兩 barrier。受控 Listen 10 秒 timeout、session close／cleanup true，Display 無 session content；NPU/mel 等 warning 非致命。Developer 原始檢查無阻礙；**尚未指定**。
- W04 實驗／結果：對原 Pi `wake-w04` card/capture 核 SHA、barrier、activity counts、顯示與核心接線，再逐 row 審 27 controller／13 wake trace／9 native／72 stderr。voice stimulus 後 OPEN `9,417,514,360,156 ns`，native ready `9,420,859,587,553`，中斷 close `9,421,019,483,596`／IDLE `9,421,019,722,059`；`barriers={}`、`activity=[]`，沒有 join、Listen、ASR、audio frame、perception worker 或 Reasoner admission。cleanup true；warning 非致命。Developer 原始檢查無阻礙；**尚未指定**。
- #5 待辦：W01/W02 已指定；W03/W04 待指定、aggregate、全 Test-ID Developer review。W01 `WAKE→PERCEPTION` state-change trace 早於 ack 約 `4,748,680 ns`，但 Listen/ASR/frame 均在 ack 後；審核需明確區分 state-change 與 active perception worker，不能只看 script Pass。
- USER 新優先順序：現在直接開始 #7 八案 Pi 實驗，每案結果及阻礙即時寫本檔。#6 已 script＋Developer review Pass；整體 PV 尚未 Pass。現無新的 Designer／Tester 阻礙。

## 2026-09-15 14:27 UTC — #5 W02 原卡在修訂規格下已指定

- 實驗：依 Tester 已修正的 Test Spec §5.5，重新只讀核對 W02 `result.json`／`wake-capture.json`：`production_path` 列出實際 `StateManager`、`ButtonInputSource`、`AlsaAudioInput`、`WhisperCppASRAdapter`、`_ConversationControl`；voice stimulus 明列 `MockWakeWordInputSource`，Display 明列 `MockDisplay` 與實際 `DisplayArbiter`／`StatusBar`，沒有實體 sensor/display Pass 宣稱。前述 ack→OPEN join→Listen/ASR/audio pull 順序及 37/9/72 rows 審查不變。
- 結果：在 Pi 對原 W02 card 執行 `designate-result` 成功，`case_attempt_id=W02-A01`，designation SHA `49fc36678b751281a3ff4139eb202301c624c4c90e197ce82a77743c1e8608ac`；產品沒有重新執行，protected tuple 沒有變。先前工具拒絕所依據的「mock 端點不被允許」契約已由 Designer／Tester 改正；#5 仍未 aggregate 或 Test-ID Developer Pass。
- 待辦／協助：Developer 逐案完整審 W03/W04 原始 trace 後指定；若 Designer／Tester認為結構化 `production_path` 與 `display` 欄位不足以描述 W00 為「core product wiring」，請在現行 Test Spec 精確指出缺少的欄位／語句，避免在未必要時修改 protected runner 並讓已驗證 tuple 作廢。

## 2026-09-15 14:24 UTC — #6 script＋Developer review Pass；#5 規格阻礙已修正，runner 描述待核

- 實驗／結果：`PV-M4B-FINITE-03/TIME-01` 的 359 fields／123 rows 已逐項核對並在 Pi 登記 Developer `Pass`；review：`m4b-pv-finite03-private/developer-reviews/M4B-PI-TIME-001-c3e3eaae708e3fe257e69f72807816bd9be3201be3faa764098cedee396ca132.json`。四個 T01–T04 script assertion 全 Pass；固定 WAV → ASR `請簡短介紹台灣。` → native 非空 JSON `{"text":"台灣，美麗的島嶼，充滿活力與多元文化！","end":false}` → Speak/TTS/Audio action `ok`；close 三證、cleanup true。
- 時間量測（ns）：ready→ASR `3,707,319,066`；ASR→LLM send `55,088,346`；send→terminal `13,697,895,070`；terminal→TTS PCM `666,780,721`；PCM→首次正值 Audio write `213,294,760`；ready→write `18,340,377,963`。`first_safe_text=null/NOT_APPLICABLE` 是同步 native 無安全增量 chunk；不把首次 write 宣稱為可聽起點，也不以 18.340 秒判成敗。child/controller monotonic 事件順序一致。
- 原始狀態觀察：fixture SHA `cf69aa043ccba9ba2efec8f4a010175092d812701092b3722b8dbf31a4c50999`；139 frame／88,960 PCM bytes 後 VAD 提前收束，`fixed_audio_consumed.complete=false`，只使用綁定 fixture、未換輸入；native prefill `86`／decode `26`／KV `112`，`ResponseFormat.json` schema SHA `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`。stderr 的 NPU、mel、profiler warning 未造成生成／action／cleanup 失敗。
- Designer／Tester 更新：Test Spec §5.5 已明定 #5 是受控刺激端的產品核心 barrier 接線，允許 `MockGPIO`、`MockWakeWordInputSource`、可選 `MockDisplay`，不宣稱實體 sensor/display Pass；原 W02 契約衝突已解除。Developer 正核對 W01–W04 card/capture 的 `W00-PRODUCTION-PATH` 描述是否符合新文字。若 runner 描述仍聲稱實體路徑，需修改 protected runner 並以新 bytes 重新在 Pi 執行；目前 #5 尚未彙總 Pass。

## 2026-09-15 14:18 UTC — #6 固定音訊一時鐘 script Pass，Developer review 中

- 實驗：`PV-M4B-FINITE-03/TIME-01`，Pi 固定 WAV `short-taiwan.wav` 103,724 bytes、SHA `cf69aa043ccba9ba2efec8f4a010175092d812701092b3722b8dbf31a4c50999`。139 次 frame pull；ASR `請簡短介紹台灣。`；真實模型非空 Taiwan 回答、Speak/KEEP_NEXT，TTS/Audio action `ok`，Conversation 三證 close／cleanup true。Native prefill 86、decode 26、terminal KV 112，admission GENERATE。
- 一時鐘原始 controller-monotonic 點位：Conversation ready `9,507,211,736,592 ns`；ASR final `9,510,919,055,658`；LLM send `9,510,974,144,004`；LLM terminal `9,524,672,039,074`；TTS PCM ready `9,525,338,819,795`；Audio first write `9,525,552,114,555`。`first_safe_text=null / NOT_APPLICABLE`，因同步 native terminal 無安全增量 chunk，不是遺失或失敗。四個 script assertion Pass；私有 capture `m4b-pv-finite03-private/time-01/time-capture.json`，公開 card `m4b-pv-finite03-public/time-01/result.json`。
- 原始證據 catalog：359 fields／123 rows（19 controller、15 child、80 stderr 加 card/capture）；Developer 尚在完整檢查，**未登記 Developer Pass**。目前無 #6 Designer／Tester 阻礙。

## 2026-09-15 14:17 UTC — #5 四案完成原始執行；#6 執行中

- Pi tuple：`PV-M4B-FINITE-03`；protected content `f6b9cfe2dcadeac675deb4811b2711e9c0c6a28d73e4985fc9ae321fb08c7545`，runner `cb79a96c06cdf427142fd9171523ce545e2b35951c59117d9d1dc8cf95988b33`，profile `8d957a4600fc172fd7dd7b285098710af0b753d7d1b697a21bd31611637b3f90`。Pi-local raw/public roots：`m4b-pv-finite03-private`、`m4b-pv-finite03-public`。
- #5 W01 `wake-w01`：script Pass，OPEN native ready 8,803,419,599,530 ns、join 8,803,419,693,655 ns、ack 8,803,674,918,714 ns；Listen/ASR/audio pull 全在兩 barrier 後。受控 Listen timeout、session close／cleanup true，Display state-slot only。37 controller、9 native、72 stderr rows 已檢；W01 已指定。觀察：`WAKE→PERCEPTION` trace 比 ack 記錄早約 4.7 ms，但 active path 未提早。
- #5 W02 `wake-w02`：script Pass，ack 9,015,851,548,148 ns 早於 native ready 9,019,137,553,391 ns、join 9,019,137,638,615 ns；Listen/ASR/audio pull 全在 join 後。37/9/72 rows 檢查，timeout close／cleanup true；**未指定**。
- #5 W03 `wake-w03`：script Pass，受控 OPEN delay 200,234,617 ns；ack 9,310,535,705,909 ns，join 9,314,222,660,725 ns，Listen/ASR/audio pull 全在 join 後，timeout close／cleanup true；**未指定**。
- #5 W04 `wake-w04`：script Pass，OPEN 中斷後 `barriers={}`、`activity=[]`，沒有 join、Listen、ASR、frame、Perception 或 Reasoner admission；stale completion 被丟棄，close／IDLE／cleanup true；**未指定**。
- #5 阻礙（請 Designer／Tester 立即處理）：W02 指定被工具審核拒絕，因 capture 顯示 `MockWakeWordInputSource` 與 `MockDisplay`，而現行 Test Spec §5.5 文字聲稱實際 production voice-wake ingress／Display 並禁止 mock-only path。只讀接線證實 runner W02/W04 以 `MockWakeWordInputSource.emit()` 注入 EventBus；Display device 為 `MockDisplay`，但核心 StateManager、ButtonInputSource、AlsaAudioInput、WhisperCppASR、Conversation control、DisplayArbiter/StatusBar 是產品元件。建議 Designer 把 #5 明確界定為受控刺激／觀察端下的真實核心 barrier 接線測試，允許 `MockGPIO`、`MockWakeWordInputSource`、`MockDisplay` 只在端點，並明寫不提供實體 wake/display 硬體證據；Tester 同步 `W00-PRODUCTION-PATH` 的可執行判定及結果標籤。若仍要求實體 wake/display，須提供真正 production source 和 Pi 實體設定；目前 W02/W04 不能指定或彙總為 #5 Pass。Developer 不繞過拒絕。
- #6 `M4B-PI-TIME-001/TIME-01`：依 USER 指示已啟動 Pi 固定音訊一時鐘路徑；正在執行，結果未判定。
- 同 tuple 其他狀態：#3 native 有限兩輪／正常 close script＋Developer Pass；#4 241 點 script Pass、有限兩輪估計 Speak 558 MiB／Generate 699 MiB，Developer review 尚未正式登記；#1/#2/#7 尚未在此 tuple 完成，#2 由 USER 判讀。沒有 7/7 或 PV Pass 宣稱。
