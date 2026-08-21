# Core Team → PM → Audio POC Team: M4a Audio POC Contract

- **Delivery ID**: `DELIVERY-AUDIO-POC-M4A-CONTRACT-001`
- **Finding ID**: `OUT-M4A-2026-001`、`OUT-M4A-2026-002` ～ `OUT-M4A-2026-005`
- **References**: `PM-OUT-260814-010-m4a-audio-poc-contract-gate`、`DELIVERY-AUDIO-POC-M3-P4-ACK-004`、`DELIVERY-AUDIO-POC-M3-VALIDATION-001`、`docs/milestones/M4.md §6.1–6.2`
- **Revision**: `2026-08-21 / DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003`
- **Status**: `GATE 1B REVISED — M2A BASELINE SURVEY / M2B OPTIMIZATION AUTHORIZED`
- **Contract owner**: Core Team Designer
- **Delivery owner**: Core Team Designer（直接交付 Audio POC Team）
- **Tracking owner**: PM / User（只記錄雙方 committed path / branch / full SHA，不代傳技術裁決）
- **Date**: 2026-08-14
- **Architecture change**: `No`

---

## 1. 背景與授權邊界

M3 Audio以`DELIVERY-AUDIO-POC-M3-P4-ACK-004`完成Option A final selection（HAL內顯式48→16 kHz conversion）；P1維持`FAIL`、P2為`PASS`。Accepted POC delivery為`882e2b6ff571eb9d54ec96bae7d3b63338c5965c`，implementation / test SHA為`de3b0bab4daaf47f62956d4b27f6697b3d4fa823`。這只解除M3 real-backend implementation gate，不代表Core M3產品驗收或M4a candidate selection已完成。

M4a Audio 是以 M3 Accepted Audio HAL contract 為基礎，在 Core production code 中實作真實 ASR 與 TTS adapter。Audio POC Team 的責任是技術探索、candidate 驗證與 evidence 提交；Core 保留 dependency selection、design acceptance 與 final ACK 決定權。

**在本 contract 各 gate 取得 Core書面授權前：**

- Audio POC repository只可在本contract及最新ACK明列範圍內執行；M2A/M2B
  observation不得標成Gate 2A selection、winner或`POC Accepted`。
- 不得以 POC 自排 roadmap、口頭結果或 branch HEAD 取代 Core 核准的 contract 或 gate evidence。
- Developer 不得引用候選名稱或 POC branch HEAD 解除 Blocked，不得加入 production dependency lock 或開始 real ASR / TTS backend。

既有 M3 條件澄清：
- P1 維持 `FAIL`（target hardware 不得改寫為 native 支援 16 kHz / mono / S16_LE）
- P2 為 `PASS`（device / config / wiring evidence 已通過）
- P4已由`DELIVERY-AUDIO-POC-M3-P4-ACK-004`完成final selection；不在M4a重跑
- P3（ASR / TTS winner）為 M4a 候選選型輸出，不得以 POC 自排 roadmap 預先視為已授權或已完成

---

## 2. 目標

在 Raspberry Pi 5 + `googlevoicehat-soundcard` 環境，以 M3 Accepted Audio HAL 為輸入，確認並固定：

1. **ASR**：接受 `AudioInput.frames()` 標準 20 ms / 320-sample / 640-byte S16_LE 串流，產生非空 text result；固定 engine、model、版本、授權、checksum 與 Pi 安裝方式。
2. **TTS**：接受固定文字，產生格式正確（`audio.output.stream_format`）的 TTS PCM，完成播放；固定 engine、voice、版本、授權、checksum 與 Pi 安裝方式。
3. **Resource budget**：M4a（ASR + TTS）與 M4b（LiteRT-LM）同時常駐時，符合 target-device Pi 5 資源與 thermal budget；CPU、RSS、throttling 均須有 evidence。

Audio POC可依G1A ACK評估VAD及frozen endpoint state machine，供其M2～M4組合驗證；VAD仍屬`perception/listen`或`voice_wake`且位於HAL外。本contract不藉此選定Core M4a production VAD dependency。

---

## 3. 候選比較基準（Comparison Baseline）

| 域 | 起始候選 | 說明 |
| :--- | :--- | :--- |
| VAD（POC evaluation only） | Silero VAD ONNX、WebRTC VAD | Gate 1B須列exact variant；維持HAL外，不構成Core M4a production selection |
| ASR engine | Whisper.cpp (ggml)、sherpa-onnx Zipformer / Paraformer、Vosk；Qwen3-ASR 0.6B int8限feasibility | M2A依ACK-003作低成本比較；PocketSphinx、HAT、cloud與未固定community conversion不在scope |
| TTS engine | Piper、espeak-ng、Coqui TTS | 同上 |
| 語言 / voice | `zh-TW` | User於2026-08-17接受；沿用Audio POC已凍結fixture / metric。切換語言須走change request |
| Pi 安裝模式 | pip wheel / source build / system package | 不得提交 binary、wheel 或 `.so` 進 Core Git |

每個候選都須與 M3 Audio HAL stream contract 對齊（16 kHz / mono / S16_LE / 320-sample frames）；不得在 ASR / TTS / Speak 層隱式 resample 或格式轉換。

---

## 4. Gate 架構與逐 gate 責任

### Gate 0 ── M3 P4 Final Selection（前置相依）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Audio POC依`DELIVERY-AUDIO-POC-M3-VALIDATION-001`回交完整source SHA與P4-A01～A10 evidence（已完成） |
| Exit | `DELIVERY-AUDIO-POC-M3-P4-ACK-004`已核准binding / resampler / valid-bit / buffering / async I/O；POC delivery `882e2b6ff571eb9d54ec96bae7d3b63338c5965c`（已完成） |
| Owner | POC 執行；Core Designer 決定 |
| Blocking scope | `Resolved`；不得把M3 P4 ACK誤作M4a candidate / model ACK或Core product Pass |
| 下一動作 | Gate 1A planning已接受；進入Gate 1B exact candidate proposal準備 |

### Gate 1 ── M4a Planning / Candidate Scope（分1A / 1B）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 0已完成。**Gate 1A**：POC提交committed executable plan；**Gate 1B**：依G1A允許的provenance-only acquisition回交VAD / ASR / TTS exact candidate proposal、checksum、license / notice、dependency、native format與Pi build recipe |
| Exit | G1A由`DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001`接受plan與D01～D05，只放行provenance acquisition / fake scaffold；G1B原逐列裁決由ACK-001 / ACK-002留下歷史，最新ASR scope由ACK-003預授權明列families在同一committed packet固定identity後執行M2A/M2B |
| Owner | POC 提交；Core Designer 核准範圍 |
| Blocking scope | G1A ACK不核准任何candidate。G1B前不得build / install / import / execute真實candidate，不得inference / benchmark / Pi run。任何階段都不得在Core production引用未核准candidate |
| 下一動作 | POC依ACK-003建立共同低成本packet、完成M2A scorecard與M2B optimization return；VAD / TTS及未列ASR family仍遵循既有逐列裁決 |

### Gate 2 ── M4a POC comparative selection / qualification（POC 執行）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 1已取得候選授權。**M2A**依ACK-003執行低成本baseline survey；**M2B**只對shortlist作DSP / endpoint、decoder/runtime、number/domain與post-processing單變因優化；**Audio M3**再對M2B recipe作target/HAL qualification；**Gate 2B**以qualified組合完成Audio POC internal M4的20-session、offline、failure injection與final handoff review |
| Exit | M2A回交無Pass/Fail的comparative scorecard與2～3列shortlist；M2B回交primary / fallback、exact pipeline recipe與delta table後，Core可發provisional selection ACK放行candidate-specific adapter / provisional dependency integration；Audio M3完成target/HAL qualification後才可準備Core product exact-SHA acceptance；只有Gate 2B取得`POC Accepted`並回交final handoff ID、Accepted POC SHA與conformance kit後，Core才固定final reference package / model baseline |
| Owner | POC 執行；Core Designer 審核；PM 轉達 ACK 通知 |
| Blocking scope | Generic protocol / fake scaffold可依G1A繼續；M2B reviewed selection前不得做candidate-specific Core integration。M2B後只允許provisional integration，不得固定production dependency / model / DSP / decoder profile。Audio M3前不得把recipe稱為target-qualified；Gate 2B前不得freeze final baseline；任何POC evidence都不等於Core product Pass |
| 下一動作 | POC先完成M2A/M2B committed packet，Core作provisional selection；再以同一recipe完成Audio M3 target/HAL qualification與internal M4。Gate 2B發現resource、offline、lifecycle、license或composition blocker時，停止final lock / product acceptance，只重開直接受影響的recipe比較或target evidence |

### Gate 3 ── M4a Core Production Implementation（Developer 實作，Core 內部 gate）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | M2B provisional selection ACK已發出，可開始candidate-specific adapter與provisional dependency/config integration；Audio M3 target/HAL qualification後才可準備產品exact-SHA acceptance；正式candidate freeze另要求Gate 2B final reference package已intake，baseline specification固定engine / model / DSP / decoder / voice / license / checksum與kit revision |
| Exit | Core delivery逐項完成§7.1 inheritance / product-delta mapping；Core Tester對產品exact SHA重跑adapter / HAL wiring、production config / lock / packaging、RM / SM lifecycle、composition、resource、offline與regression；Designer最終review無Blocking |
| Owner | Developer 實作；Tester 驗收；Designer 最終審查 |
| Blocking scope | M4a 未 Accepted 前，M4c 不得啟動；M4a + M4b 未同時 Accepted 前，M4 不得宣告 Accepted |
| 下一動作 | Developer不等待M2A即可建立generic scaffold；M2B provisional selection後建立candidate-specific integration工作包；Audio M3 qualification後準備產品acceptance；Gate 2B intake後才建立production lock |

---

## 5. M4a 驗證清單（POC 在 Gate 2 執行）

| ID | 驗證項目 | Required evidence / result |
| :--- | :--- | :--- |
| **M4A-P1** | ASR stream 輸入格式對齊 | 以 M3 HAL 標準 320-sample / 640-byte / 20 ms S16_LE frame 作為 ASR 輸入；不得在 ASR 層 resample；記錄 engine 收到的 actual format |
| **M4A-P2** | ASR comparative score | 固定 WAV與Common Voice sanity subset產生文字result；依候選記錄normalized CER、exact-sentence diagnostic、分類語意／關鍵實體結果與raw transcript identity。M2A/M2B不設品質threshold或Pass/Fail |
| **M4A-P3** | ASR 效能／可優化性評分 | 記錄load time、latency、RTF、RSS、disk與DSP / endpoint、decoder、number/domain、post-processing單變因delta；M2A/M2B不以threshold淘汰。Timeout、OOM或cleanup不完整只作fail-closed execution evidence |
| **M4A-P4** | TTS 輸出格式對齊 | 固定文字輸入，產生 PCM 符合 `audio.output.stream_format`（與 M3 AudioOutput HAL native format 一致，不得隱式轉換）；記錄 actual format |
| **M4A-P5** | TTS 播放完成 | TTS PCM 送入 M3 AudioOutput / Speak path 後播放完整不截斷；記錄 playback duration vs. text length 關係 |
| **M4A-P6** | TTS 品質門檻 | 固定文字可產生清晰可理解語音；人工評分（mean opinion）≥ 3.5 / 5；記錄 voice / model 版本與 evidence path |
| **M4A-P7** | Pi 資源（ASR only） | 10 warm-up 後保存 ASR inference CPU、RSS、P50 / P95 latency raw samples；temperature 與 throttling；Core 依數據核准，不可只寫「可接受」 |
| **M4A-P8** | Pi 資源（TTS only） | 同上，針對 TTS synthesis phase |
| **M4A-P9** | M4b Resource Reservation | Gate 2A使用Core核准、versioned deterministic M4b residency surrogate作Audio-only planning input；Audio POC不執行Core combined memory preflight，也不宣告跨POC capacity Pass。POC只依既有contract交付artifact、固定設定與reproduction command；Accepted Audio與LLM packages完成Core intake且Developer建立composition smoke後，Core Tester才依`M4-REG-001`作即時診斷。真實combined validation仍由LLM Gate 2B與Core Gate 3執行 |
| **M4A-P10** | Lifecycle | ASR / TTS engine init、warm-up、inference、shutdown 各至少 5 次；無 process / thread / fd 殘留；不得在 worker 內保留隱藏 session history |
| **M4A-P11** | Build / license | 從 clean Pi target 依文件可 build / install / rerun；列 OS、kernel、Python、ALSA、package 與 native library 版本；binary / wheel / `.so` 不得提交 Core Git；license / notice 逐項列出 |
| **M4A-P12** | Offline 驗證 | 所有 ASR / TTS inference 在 Pi 無網路環境可完整執行；log 不含 network call、external API endpoint 或 credential |

---

## 6. 必要回交結構

POC repository 回交至少包含下列可定位內容；manifest 中的 relative path 必須完整：

```text
poc_audio/
├── deliveries/
│   └── DELIVERY-AUDIO-POC-M4A-VALIDATION-001.md
├── tools/
│   └── <reproducible M4a runner: ASR + TTS>
├── harness/
│   └── <WAV fixture + text fixture generator>
└── evidence/m4a/
    ├── manifest.json
    ├── environment.txt
    ├── config.sanitized.*
    ├── results.*
    └── raw/
```

`manifest.json` 至少列：POC full SHA、hardware / wiring、sanitized config SHA-256、runner 與 fixture SHA-256、candidate source hashes、license、每個 M4A Test ID 狀態、raw artifact path、開始 / 結束時間與完整 reproduction command。未執行為 `Pending`，硬體或環境不足為 `Blocked`；不得標成 `Pass`。

---

## 7. Comparative selection / final reference decision table

| Decision item | Required answer |
| :--- | :--- |
| ASR engine | M2A全景scorecard、M2B primary / fallback、version、source SHA-256、license、比較理由與未入選alternatives；不得把metric threshold當唯一理由 |
| ASR model | model file name、SHA-256、source URL / archive、license、Pi install command |
| TTS engine | selected candidate、version、source SHA-256、license、理由與 rejected alternatives |
| TTS voice / model | voice name、SHA-256、source URL / archive、license |
| 語言設定 | `zh-TW`；其他語言須有正式change request、重凍fixture / metric與Core書面ACK |
| Stream format alignment | ASR 與 TTS 各自實際輸入 / 輸出 format（sample rate / channels / dtype / frame size） |
| Pi resource summary | P50 / P95 ASR latency、P50 / P95 TTS synthesis latency、peak CPU、peak RSS、thermal peak |
| Offline confirmation | 是否可在無網路 Pi 5 完整執行；log 是否無 credential / API endpoint |
| Residual risk | 已知限制、調整潛力、target/composition待驗事項與產品取捨；只有artifact / license / offline / bounded execution / cleanup使結果無效或所有路徑不可執行時才提出technical no-go |

M2A/M2B的ASR quality / performance score不形成hard gate；Core/User依比較結果、調整潛力與產品成本選primary / fallback。TTS quality、artifact / license、offline、bounded execution、cleanup及後續target / composition evidence仍依各自契約處理。M2B provisional ACK不是final reference package；Audio M3尚未完成時不得稱target-qualified，Audio POC internal M4的20-session、failure injection、offline或review出現Blocking時不得標`POC Accepted`，Core也不得freeze model baseline。

### 7.1 Evidence inheritance / product-delta matrix

| POC area | Classification | Core Gate 3 treatment |
| :--- | :--- | :--- |
| Candidate version、artifact checksum、license、rejected reasons | Inherited from accepted POC SHA | 引用immutable final handoff；identity不變時不重做candidate comparison |
| P1 ASR stream vectors / validator | Reused test asset / rerun on product SHA | 對Core adapter與M3 HAL wiring重跑format / frame assertions |
| P2 / P3 ASR quality comparison | Inherited + product smoke delta | 繼承frozen quality結果；Core以相同fixture subset驗adapter不改文字語意 |
| P4 TTS PCM vectors / validator | Reused test asset / rerun on product SHA | 對Core TTS adapter與AudioOutput wiring重跑exact format |
| P5 playback path | Product-only validation | POC可提供reference sequence；Core真實composition / Speak / HAL必須重驗 |
| P6 TTS quality / User review | Inherited + product smoke delta | 引用POC受控review；Core只確認產品adapter未換voice / model / text |
| P7 / P8 isolated resource metrics | Inherited benchmark | Core引用比較結果，但對產品process tree重跑resource / latency |
| P9 resource reservation | Reused method / product-only combined result | 沿用surrogate envelope與量測方法；真實M4a+M4b在LLM Gate 2B / Core SHA重驗 |
| P10 lifecycle / cleanup scenarios | Reused test asset / rerun on product SHA | 相同success / timeout / error / cancel / force-abort vectors重跑RM / SM integration |
| P11 provenance / build | Inherited identity + product packaging delta | 引用source / license；Core驗production lock、install與受控artifact取得 |
| P12 offline | Inherited reference + rerun on product SHA | POC offline證明候選可行；Core完整產品離線session仍須Pass |
| Audio POC internal M4 20 sessions / failure / offline | Inherited reference package | Core引用fixture、method與known risks；產品composition與exact-SHA regression另跑 |

Core Gate 3 mapping每列至少記：POC handoff ID、Accepted POC SHA、manifest / evidence path、fixture / metric revision + checksum、product implementation SHA、inheritance理由、delta Test ID / result。只寫「沿用POC」或把POC自驗標為Core Tester Pass均不合法。

### 7.2 Portable conformance kit

Audio POC final handoff至少提供可由POC wrapper與Core adapter共同使用的：

- candidate lock / provenance / license index；adapter protocol與expected result schema；
- fixture / prompt ID、revision、checksum、validator及事前固定threshold；
- success / timeout / error / cancel / force-abort / reopen / cleanup scenarios與assertions；
- offline check、resource量測方法 / budget、20-session sanitized result與known risks；
- manifest與evidence index，所有path相對於Accepted POC SHA可定位。

可重用資產：protocol、JSON schema、small non-sensitive test vectors / metadata、validators、tests與sanitized expected result。不得直接進Core Git：benchmark orchestration、raw audio、model / voice weights、wheel、`.so`、大型raw result或受控artifact。Core delivery引用kit version / SHA並提供POC→product conformance mapping；未沿用可重用資產時須列差異與替代驗證，不要求POC撰寫Core private implementation。

---

## 8. External Gate / Audio milestone crosswalk

| External gate | Audio POC milestone | P IDs / delivery | Exit / Core impact |
| :--- | :--- | :--- | :--- |
| Gate 1A planning ACK | M1 frozen method + M2 WP0～WP2 | P1～P12 executable plan、D01～D05、fake protocol / kit scaffold | `RESP-AUDIO-M4A-GATE-PLAN-001`已獲G1A ACK；只放行provenance-only acquisition與fake scaffold |
| Gate 1B candidate scope | M2 proposal + ACK-003 revision | ASR M2A families、M2B optimization tracks、VAD / TTS existing rows、checksum、license / notice、dependency、native format、aarch64 build proposal | ACK-003預授權明列ASR families依fail-closed identity record執行，不需逐列往返；其他domain / family仍須書面ACK |
| M2A baseline survey | M2A quick comparative packet | P2 / P3 score observations、internal 8-item subset、Common Voice `zh-TW` sanity subset | 無Pass/Fail；回交scorecard與2～3列shortlist；Core僅可做generic scaffold |
| M2B provisional selection | M2B one-variable optimization | DSP / endpoint、decoder/runtime、number/domain、recovery delta；primary / fallback exact recipe | Core provisional selection ACK；可做candidate-specific adapter與provisional dependency/config integration，不可lock final artifact |
| Gate 2A target qualification | Audio M3 Pi/HAL | P1～P8、P9 resource reservation、P10～P12，綁定M2B recipe | Core target qualification ACK；可準備產品exact-SHA acceptance，不可freeze final baseline |
| Gate 2B final reference | M4 combined validation / internal review | 20 sessions、failure injection、offline、final handoff、conformance kit | `POC Accepted` + final handoff ID / SHA；Core可固定model baseline並進Gate 3 acceptance |
| Gate 3 Core product | Core M4a | inheritance / delta matrix + Core `M4A-*` | Core Tester對產品exact SHA PASS；POC evidence不取代產品驗收 |

Audio POC須以M2A / M2B作Audio M2內部substage，不建立`m2a` / `m2b` milestone tag；必須提供唯一External Gate→M1/M2A/M2B/M3/M4→P1～P12→evidence crosswalk，逐項包含owner、producer、prerequisite、platform、fixture / input、command / runner、output path、comparison rule、cleanup及exact-SHA binding。

## 9. 溝通順序（Direct Core ↔ Audio POC flow）

```
Core Designer (contract owner)
  → [本 committed delivery] 直接交付 Audio POC Team
    → POC Gate 1A回交committed executable plan
      → Core G1A planning ACK（已接受D01～D05）
        → POC執行provenance-only acquisition，回交G1B exact candidate proposal SHA
          → Core G1B ACK-001 / ACK-002；ACK-003改採M2A/M2B comparative funnel
            → POC M2A快速baseline → scorecard + shortlist
              → POC M2B單變因優化 → primary / fallback + exact recipe
                → Core provisional selection → candidate-specific integration可並行
                  → Audio POC M3 target/HAL qualification
                    → Audio POC internal M4完成20 sessions / failure / offline / review
                      → POC Accepted final handoff + conformance kit直接交Core intake
                        → Core固定final reference / model baseline → Gate 3 product acceptance
```

每個步驟的ACK均由Core Designer直接書面發出，存放於`docs/outsource/deliveries/`並以committed path / branch / full SHA通知Audio POC Team；Audio POC Team直接以自己repo的committed path / branch / full SHA與manifest回交Core。PM / User只追蹤雙方immutable outcome，不代傳技術內容、不簽發ACK，也不代替任一團隊宣告gate通過。

---

## 10. Audio POC Gate 1A intake與Gate 1B return packet

Gate 1A plan已由`poc_audio/deliveries/RESP-AUDIO-M4A-GATE-PLAN-001.md`、branch `dev_audio_m2`、commit `5d4086d2ae9011c559b10012b55414a87a3a8522`回交，並由`DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001`接受。該plan已包含：

1. authoritative plan path與External Gate→M1/M2/M3/M4→P1～P12→evidence crosswalk；
2. work packages的owner、dependency、順序、estimate / throughput assumption、entry / exit與re-estimation trigger；
3. candidate eligibility / provenance / license / artifact取得與offline aarch64 build政策；
4. shared protocol / wrapper / harness / schema / vector / validator / cleanup設計；VAD / ASR / TTS與User TTS review安排；
5. M2 isolated、M3 Pi / HAL、M4 combined的evidence分界，包含Pi session、M4b surrogate / accepted baseline prerequisite、raw / sanitized / controlled artifact規則；
6. 每個P ID的producer、platform、fixture、command、output path、decision / no-go、cleanup及SHA cut point；
7. failure / no-go / change-request與fallback；
8. reply document path、branch、完整40-character committed HEAD。

Gate 1B proposal與focused / recovery ACK均已留下歷史。最新執行scope以
`DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003`為準：明列ASR family可在同一committed
packet先固定identity / provenance，再直接執行M2A與shortlist M2B，不需每列另等Core ACK。
POC回交通知仍須提供path、branch與full SHA；文件不得預填自己的未來SHA，聊天或branch
name不構成收件。VAD與TTS未被ACK-003改寫的row disposition維持原裁決。

## 11. 本 contract 阻擋範圍摘要

| 阻擋項目 | 解除條件 |
| :--- | :--- |
| Audio POC provenance-only acquisition / fake scaffold | Gate 1A planning ACK後，限ACK明列行為 |
| Audio POC ASR build / install / import / candidate execution | ACK-003明列family可先在committed packet固定identity / provenance後直接執行M2A/M2B；未列family仍須書面scope decision |
| Developer 準備fake / protocol scaffold | Gate 1A planning ACK後 |
| Developer 準備candidate-specific adapter / provisional dependency integration | M2B provisional selection ACK後；generic fake / protocol scaffold不等待M2B；不得lock final artifact |
| Developer 準備產品exact-SHA acceptance | Audio M3 target/HAL qualification ACK後 |
| Developer 加入ASR / TTS production dependency / model / voice lock | Gate 2B `POC Accepted` final handoff intake後 |
| M4a 視為 Accepted | Gate 3：Core Tester 對 delivery exact SHA 驗收 PASS |
| M4c 啟動 | M4a + M4b 均取得 Tester 驗收 PASS（同一 delivery SHA） |
| M4 宣告 Accepted | M4a + M4b + M4c 同一 delivery SHA 全數 Tester PASS |
