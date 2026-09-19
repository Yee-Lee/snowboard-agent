# ACK-LLM-POC-M4C-STREAMING-SPEAK-001 — intake and preparation boundary

- Income：`REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001`
- Work / baseline / gate：`M4C-SS` / Accepted M4B / `M4C-SS`
- Income source/destination SHA-256：
  `234b5998589d3c956005f465862e137b471a2e26e75c3a19c6be5cb166c0b59c`
- Core delivery commit：`56962d5c9802c1355d21187def74769c29f02620` (`origin/core`)
- Core accepted product baseline：`f87cfa50b9c9415430973076a59c6b1961228090`
- POC starting source SHA：`5080abd84dafcbc0f8307a086fa8009a0b6a818b`
- Starting tracked-tree SHA-256：
  `5f930e7e016ea1b2090ce86fb21e8e79fb198f8e6feb3b0150bd5352bbaff4c7`
- Status：`RECEIVED / WORKSTATION VERIFIED / PI PREFLIGHT PARTIAL / EXECUTION NOT AUTHORIZED`

## Intake conclusion

Core於2026-09-16接受M4B same-bytes Pi product verification；M4B與其MVA／efficiency inputs已完成並成為
M4C entry baseline，不再等待舊的Core revision。2026-09-19 User授權M4C-SS workstation開發與測試至
pre-Pi gate。
本工作推進的final checklist item是交付一份identity完整、可重現且經User發布前審閱的
`DELIVERY-LLM-POC-M4C-STREAMING-SPEAK-001`，讓Core Designer有證據地關閉`M4C-SS`。

POC接受`B`為主要目標、`A`只作control/emergency fallback，以及四種唯一disposition。POC self-test、
self-PASS或prototype成功都不關閉gate、不修改Core architecture，也不建立M4C Test Spec credit。

## Source and surface identity

Starting baseline是完整40-character commit，不是branch名稱。該commit的tracked tree有481 entries；
intake digest定義為：

```text
git ls-tree -r -z --full-tree 5080abd84dafcbc0f8307a086fa8009a0b6a818b | sha256
```

結果為上列`5f930e…4c7`。此digest只固定prototype開始前的完整tracked tree且不hash本ACK；它不是未來
execution surface。`SS-WP04`會以explicit path inventory與每檔content SHA-256另建non-recursive manifest，
並拒絕missing、symlink、checkout外路徑、uninventoried local import及manifest self-inclusion。

## Frozen target identities

下表分開記錄Core-required identity、repo內Accepted provenance與Pi actual proof。沒有target read-only
inventory前，不把歷史receipt推定為目前實際存在。

| Surface | Required / accepted identity | Pi actual status |
| --- | --- | --- |
| Target | Raspberry Pi 5 4 GB；Debian 13 aarch64；CPU/4；CPython 3.13.5 | pending read-only inventory |
| LLM runtime | LiteRT-LM 0.16.0；source `924e79c…2e4cbb`；wheel `5eb8c9fa…f2b00`；native `9b3a319b…75e4` | pending |
| Model | `gemma-4-E2B-it.litertlm`；2,588,147,712 bytes；`18193810…9a63c` | pending |
| Product profile | `core-m4b-cognition-001`；1024 context；128 output；temperature 0；top-p 1；CPU/4 | pending |
| Prompt/schema | prompt `872ae6b6…eb643`；schema artifact commit `4f342267…3d`；schema `796c3114…15de9` | pending |
| Audio acceptance | `audio_m4` tag object `24b2571a…924c`；completion `5694ead4…72bd`；manifest `74e2737f…fad` | pending |
| TTS | `tts-sherpa-matcha-zh-en-1.13.5`；archive `271b804a…86ef`；vocoder `b599142a…cf9e` | pending |
| TTS runtime | wrapper wheel `f5a6cc5a…00f`；core wheel `4cd75106…e2aa`；voice `matcha-zh-en-default-sid-0` | pending |
| Audio path | canonical 16 kHz mono S16_LE；Core HAL execution `6c7fc8ce…dcf`；controller-r2 manifest `6bb24f9a…76f4` | pending |

任一actual mismatch、alternate voice/model、untracked binary或network fallback都在measurement前停止。

## Proposed bounded mappings and case count

- `B1-IMMEDIATE-SEQUENTIAL`：每個eligible fragment立即做一次既有`synthesize(fragment)`並依序播放。
- `B2-ONE-LOOKAHEAD-COALESCE`：private session facade最多hold一個fragment；只有下一個已排入bounded
  queue時才exact-concatenate後合成，並量測額外delay。

兩者都只用POC-private wrapper，共用單一logical operation、兩個fragment／256-byte queue、terminal
prefix/equality gate與cancel owner，不修改Accepted M4A/Core public API。兩候選皆固定screen，禁止第三
候選。Expected accounting為15個controller subcases、18個mapping samples、40個live A/B samples及
9個live-negative subcases，共82；retained harness-defect rerun不取代原case。

## Commands and execution status

目前可執行的artifact-independent workstation checks為：

```text
.venv/bin/python -W error::ResourceWarning -m unittest discover -v -s poc_llm/tests/m4c_ss -p 'test_*.py'
.venv/bin/python -m poc_llm.tools.run_m4c_ss plan
.venv/bin/python -m poc_llm.tools.run_m4c_ss controller C01-ONE
```

2026-09-19結果為M4C-SS 48/48 PASS；既有efficiency regression為46/46 PASS；82個case key唯一，
`git diff --check`通過。全repo macOS check為364 PASS／6 SKIP／14 FAIL／9 ERROR，非PASS項為既有
Linux/platform/subprocess-environment assumptions，M4C-SS及efficiency targeted suites沒有failure。這不是
prototype、target或hardware result。Core public adapter目前不轉送pre-terminal frame；POC已以獲准的
private wrapper連接既有LiteRT raw stream與Accepted S2 parser語意，實際target interval待Pi驗證。
後續target CLI在產生clean pushed SHA前不可執行：

```text
.venv/bin/python -m poc_llm.tools.run_m4c_ss snapshot --output <LOCK_PATH>
python3 -m poc_llm.tools.run_m4c_ss preflight <frozen identity arguments>
python3 -m poc_llm.tools.run_m4c_ss controller <frozen case ID>
python3 -m poc_llm.tools.run_m4c_ss mapping <candidate/trace/repetition>
python3 -m poc_llm.tools.run_m4c_ss live <case/pair/order>
python3 -m poc_llm.tools.run_m4c_ss negative <case/injection>
```

Exact flags、82 IDs、order、timeouts、private config、surface digest及expected output會由immutable packet
逐字固定；目前不得用placeholder command進Pi或產生evidence。

## Acoustic and evidence method

User於2026-09-19指定使用USB microphone錄製固定朝向它的實體speaker。I²S只承接產品playback；USB
capture是獨立measurement instrumentation，不進Listen/ASR、不提供barge-in。Capture block與
LLM/TTS/Audio events使用同一monotonic clock。measurement前必須固定USB ALSA identity、gain、sample
rate、speaker volume、距離／角度、ambient gate、onset detector
及calibration pulse，並實測總clock/onset uncertainty `<= 50 ms`。在設備inventory與calibration完成前，
acoustic timing狀態為`PENDING`，不能回報latency disposition。

Raw/private logical root為`M4C_SS_PRIVATE_RUNS`，由target private config解析，實體host path不進Git。
Sanitized output預定置於`poc_llm/evidence/m4c_ss/`。Bundle使用relative path、size與per-file SHA-256的
sorted canonical JSON manifest，再對manifest取SHA-256；raw prompt/output/audio不進Git。

## Authorization requested before target work

本ACK請User在需要進Pi時另行裁決下列範圍；目前均未授權：

1. read-only Pi access，核對target、ABI、runtime/model/prompt/schema、TTS/voice/Audio及private roots；
2. USB microphone／speaker inventory、simultaneous I²S playback plus USB capture，以及不產生正式結果的
   acoustic calibration preflight；
3. 後續Pi-native prototype development/test/debug及exact offline execution；
4. 必要的network change、reboot、artifact replacement/download或privileged action；
5. workstation commit/push，以及User審閱後的benchmark/candidate publication。

Workstation implementation與targeted tests已收斂至pre-Pi gate。任何Pi結果、candidate recommendation或
`B_RECOMMENDED` disposition在User審閱前不得發布。

2026-09-19 User另行授權preflight；I2S VoiceHAT speaker＋獨立USB AB13X microphone duplex與frozen
Gemma identity通過engineering check。USB capture實際協商48 kHz mono S16_LE；嚴格monotonic calibration
因system Python無`alsaaudio`而在播放前fail-closed，故`<=50 ms`仍pending。沒有執行任何experiment case。
