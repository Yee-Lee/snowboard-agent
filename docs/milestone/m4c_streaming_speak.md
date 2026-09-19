# M4C-SS：true streaming-speak feasibility

狀態：`IN_PROGRESS / PI PREFLIGHT PARTIAL / EXECUTION NOT AUTHORIZED`

External gate：`M4C-SS OPEN`

Core product baseline：`f87cfa50b9c9415430973076a59c6b1961228090`

POC starting baseline：`5080abd84dafcbc0f8307a086fa8009a0b6a818b`

## Goal and delivery contribution

以Accepted M4B的pre-terminal `SAFE_TEXT`、Gemma 4 E2B／LiteRT-LM 0.16.0及Accepted M4A
Matcha TTS／Audio path，完成bounded true streaming-speak prototype與實體acoustic A/B。唯一正式
return為`DELIVERY-LLM-POC-M4C-STREAMING-SPEAK-001`，其disposition限於
`B_RECOMMENDED`、`A_FALLBACK_CRITICAL_FAILURE`、`UNSUPPORTED`或`INCONCLUSIVE`。

POC結果不關閉`M4C-SS`。Core Designer依證據固定M4C唯一產品行為後才可關閉gate；本工作不修改
Core composition、Accepted M4A public contracts、M4B semantic validation或State Manager。

## Authority and entry review

- Income：`REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001`；source/destination SHA-256均為
  `234b5998589d3c956005f465862e137b471a2e26e75c3a19c6be5cb166c0b59c`。
- Core delivery commit：`56962d5c9802c1355d21187def74769c29f02620`，已位於`origin/core`；其中request
  原件與本repo Income byte-identical。
- Core M4B Accepted commit：`f87cfa50b9c9415430973076a59c6b1961228090`；Core記錄M4B於
  2026-09-16由User接受，舊M4B-MVA／efficiency工作不再是active blocker。
- User於2026-09-19先指示開始準備M4C-SS，之後明確授權本repo持續workstation開發與測試至
  pre-Pi gate；不包含Pi存取／execution、網路切換、reboot、artifact download／replacement、
  commit、push或結果發布。
- Starting tracked tree為上述POC SHA的481個tracked entries；`git ls-tree -r -z --full-tree
  <SHA>`位元組的SHA-256為
  `5f930e7e016ea1b2090ce86fb21e8e79fb198f8e6feb3b0150bd5352bbaff4c7`。這是intake
  baseline identity，不是未來execution-surface lock；implementation freeze會另建explicit、
  non-recursive、content-SHA-256 manifest。

Entry review結論：delivery contribution、Core owner、fixed behavior、result semantics、bounded candidate
budget及目前授權已辨識，故milestone進入`IN_PROGRESS / WORKSTATION IMPLEMENTATION VERIFIED`。Target實際artifact
inventory、acoustic設備可用性、private roots及exact executable commands尚未驗證，不能進入Pi或量測。

## 2026-09-19 workstation checkpoint

`SS-WP01～03`的artifact-independent implementation已完成：bounded `FragmentChannel`、B1/B2 mapping、
15個C01–C10 executable subcases、single-operation A/B pipeline、Accepted S2 normalization/terminal proof、
blocking LiteRT raw iterator到async queue的同步backpressure bridge、Accepted TTS/Audio private binding、
共同generation/TTS/playback cancel與force-abort、append-only sanitized evidence、82-case catalog及deterministic
USB-acoustic onset detector。Core public `generate()`目前只在terminal後回傳，但LiteRT raw stream path可由
POC-private wrapper在不修改Core public contract下供S2使用；target artifact上的實際pre-terminal interval仍須
Pi驗證，不能由workstation宣稱。

M4C-SS targeted tests為48/48 PASS，既有efficiency regression為46/46 PASS，82個case key唯一且
`git diff --check`通過。全repo macOS run為364 PASS／6 SKIP／14 FAIL／9 ERROR；非PASS項集中在既有
Linux `/proc`、process/Audio owner、`/tmp` canonical path及subprocess system-Python dependency assumptions，
未出現在M4C-SS或efficiency suites。這些是workstation engineering checks，不是prototype、Pi或benchmark
evidence。

## 2026-09-19 Pi preflight checkpoint

User授權且限定只做preflight。Pi 5／Debian 13／aarch64／CPython 3.13.5及frozen Gemma檔案
size/SHA-256符合；I2S VoiceHAT speaker與獨立`AB13X USB Audio` microphone可同時playback/capture。
實測明確使用I2S playback與USB capture，未使用I2S microphone、Listen或ASR。USB硬體實際協商為
48 kHz mono S16_LE，而非最初請求的16 kHz；後續必須freeze 48 kHz或另行review conversion path。

固定短pulse已被USB mic收到，暫存PCM已清除。不過system Python缺少`alsaaudio`，嚴格monotonic
calibration在播放前即fail-closed；依User指示沒有尋找其他runtime或安裝套件。因此duplex availability
為engineering `PASS`，但`<=50 ms` uncertainty仍未證明，acoustic latency維持`INCONCLUSIVE`。
本次沒有執行LLM/TTS、controller、mapping、live A/B、negative或benchmark case。完整sanitized紀錄見
[Pi preflight assessment](../response/ASSESSMENT-LLM-POC-M4C-SS-PI-PREFLIGHT-001.md)。

## Frozen behavior carried from Core

- 每turn最多一個綁定`(session_id, turn_id, correlation_id)`的logical streaming-speak operation；
  fragment不是Fact、action或turn。
- `SAFE_TEXT`須non-empty、ordered、non-revisable，累積值永遠是terminal normalized text的exact prefix。
- terminal `LLMResponse`仍是唯一cognition Fact；semantic validation與speech completion前不得發布正常
  `ActionCompleted(status=ok)`。
- queue硬上限為兩個pending fragments及256 UTF-8 bytes；滿載只能backpressure，不得drop、silent merge、
  reorder或建立unbounded task/list。
- normal release boundary為punctuation或24 normalized codepoints；已播語音不rollback，但cancel後不得開始
  新fragment、發布success或把late output帶入新turn/session。
- 無barge-in；短按是唯一active-Session interrupt。network在native import前關閉並維持offline。

## Bounded candidate mappings

兩個候選都只存在POC-private controller，不修改`TTSAdapter.synthesize(text)`、`AudioOutput.play()`或
Core `Speak` public contract：

1. `B1-IMMEDIATE-SEQUENTIAL`：每個eligible `SAFE_TEXT`立即依序呼叫既有`synthesize(fragment)`，
   完整消費該PCM/playback後才處理下一個fragment；以最小複雜度優先取得overlap。
2. `B2-ONE-LOOKAHEAD-COALESCE`：private `open/feed/finish/cancel` facade最多保留一個fragment；只有下一個
   fragment已在bounded queue時才以exact concatenation共同送入一次`synthesize`。不得插字、改寫或跨
   terminal等待；所有額外delay必須量測。

兩者都維持單一logical operation、同一bounded queue、terminal prefix/equality gate及共同cancel owner。
若B1已通過，B2仍依frozen screen執行，避免事後依結果決定candidate set。禁止第三候選或動態調segmentation。

## Fixed case accounting

| Partition | Fixed count | Accounting |
| --- | ---: | --- |
| Deterministic controller | 15 subcases | C01–C06各1；C07三個injection；C08兩個；C09三個；C10一個 |
| Real TTS mapping screen | 18 samples | 2 candidates × T01–T03 × 3 repetitions |
| Live A/B | 40 samples | L01–L04 × 5 paired repetitions × A/B |
| Live negatives | 9 subcases | N01、N02、N05、N06各1；N03三個；N04兩個 |
| Total | 82 | no retry；唯一允許的harness-defect retained rerun不取代原sample |

Candidate order、A/B order、五秒idle、watchdogs、resource stop rules及public strings完全沿用Income。
Implementation packet須把82個expected IDs逐一列出，missing case固定為`INCONCLUSIVE`而不是縮小分母。

## Acoustic and evidence preparation

- User於2026-09-19指定target preflight使用USB microphone，實體speaker固定朝向該mic；I²S維持產品
  playback-only路徑，USB mic只作獨立measurement capture，不啟動Listen/ASR或建立barge-in。
  Capture block以與event timeline同一monotonic clock標記。speaker volume、USB ALSA identity/gain、
  sample rate、distance、角度、ambient gate、onset detector及calibration
  pulse在Pi measurement前freeze。未實測證明mapping／detector uncertainty `<= 50 ms`前，latency disposition
  必須是`INCONCLUSIVE`。
- Raw logs、prompt/output及audio只寫入private logical root`M4C_SS_PRIVATE_RUNS`；repo只保存public input、
  normalized lengths、digests、timings、resource facts、rubric verdict、null reason及neutral locator。
- Private bundle digest使用相對路徑、byte length與per-file SHA-256的sorted canonical JSON manifest；manifest
  不hash自身，整個canonical manifest再取SHA-256。每個case使用獨立append-only partition。
- 預定sanitized paths為`poc_llm/evidence/m4c_ss/`，contracts／fixtures／harness／tests／tools分別置於同名
  `m4c_ss` surface；任何host path、credential、raw transcript或PCM不得進Git。

## Work packages

1. `SS-WP00 — intake`：完成byte comparison、M4B closure reconciliation、本milestone與intake ACK。**完成。**
2. `SS-WP01 — deterministic contract/controller`：queue、fragment ledger、terminal equality、one-operation、
   completion gate、cancel/late-output isolation及C01–C10 tests。**workstation完成。**
3. `SS-WP02 — evidence/acoustic`：schema、append-only writer、clock mapping、onset detector、resource sampler、
   owner cleanup及private bundle manifest。**除target calibration／resource probe外workstation完成。**
4. `SS-WP03 — mappings/runtime adapters`：B1/B2、Accepted TTS/Audio private binding、A control與live LLM S2 feed。
   **workstation binding與fake/raw-stream tests完成；實體artifact binding待Pi。**
5. `SS-WP04 — freeze`：exact commands、82-case catalog、explicit surface manifest、clean pushed SHA、artifact
   receipt及immutable packet；需另行User授權commit/push。
6. `SS-WP05 — target execution`：獲Pi／offline／hardware授權後才做identity preflight、controller、mapping、
   live A/B及negative cases；不得自動retry或修改frozen bytes。
7. `SS-WP06 — audit/review/return`：Technical Lead先核對identity、packet、cleanup、quality及timing；User審閱
   benchmark與candidate recommendation後，才可commit/publish正式delivery。

## Current next action and blockers

Workstation implementation及partial Pi preflight已完成；model identity與I2S speaker＋USB microphone
duplex已確認。下一步仍須完成`<=50 ms` monotonic calibration，並在formal execution前補齊runtime/TTS/
voice/Audio、clean checkout、private root及offline identity。User已授權本checkpoint commit/push；formal
execution及正式result publication仍分別需要exact-scope authorization與User review。
