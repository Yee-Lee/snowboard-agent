# M4a Accepted Audio production integration

狀態：M4a Gate 3 Accepted；Core candidate `6c3ba95455dc5c2a152aa230b8ae5915887fe6a9` 已完成 Tester exact-SHA 驗收與 Designer final confirmation。

本章將 `audio_m4` Accepted reference 落成 Core Gate 3 可實作的 ASR/TTS adapter、runtime identity、failure convergence 與驗收映射。權威 baseline 見 `docs/model_spec.md`，child wire schema 見 `docs/protocol.md`；既有公開 Protocol、Listen / Speak worker 與 Audio HAL 契約不變。

## 1. Scope / non-scope

本章實作：

- Silero endpoint + persistent whisper.cpp 的 production `ASRAdapter`；
- persistent sherpa/Matcha 的 production `TTSAdapter`；
- checksum-locked Git-external artifacts、隔離 runtime preflight 與 offline install contract；
- config / factory / RM recovery wiring；
- POC inheritance → Core product-delta evidence index；
- portable doubles與 Raspberry Pi exact-SHA acceptance entry points。

本章不修改 `ASRAdapter`、`TTSAdapter`、`Listen`、`Speak`、AudioInput 或 AudioOutput 的公開方法；不把 POC runner、raw audio、model、wheel、`.so` 或 benchmark orchestration 複製進 Core Git；不宣稱 POC PASS 等於 Core product PASS。M4b LLM與M4c display另依其設計落地。

## 2. Process topology

```text
Core controller (no candidate native imports)
  ├─ WhisperCppASRAdapter
  │   └─ ASR supervisor process group (isolated VAD Python)
  │       ├─ Silero ONNX session
  │       └─ persistent whisper.cpp native worker
  └─ MatchaTTSAdapter
      └─ TTS worker process group (isolated sherpa Python)
          └─ persistent Matcha + Vocos engine
```

兩個 adapter 各自擁有 process group、IPC、active request及stderr ring/tail。ASR supervisor是process-group leader；它啟動native whisper worker時不得再建立nested session/process group，確保parent對單一PGID的TERM/KILL涵蓋全部descendant。child不得開 listener、network、Audio HAL或任意檔案路徑；所有工作目錄由 parent 建立為 `0700` 的 per-process temporary directory，normal/error/cancel/force-abort後刪除 bounded WAV/PCM暫存。

VAD與TTS runtime分離是 production contract，不是可選優化：Accepted closure分別使用不同 native stack / NumPy，混入controller或同一venv會撤銷identity sign-off。

Offline launch另有不可由部署或使用者設定放寬的production invariant：parent建立任一Audio child環境時必須強制`ORT_DISABLE_TELEMETRY=1`，覆寫所有繼承值；ASR supervisor與TTS worker的direct module entry也必須在任何直接或間接ONNX Runtime / sherpa native初始化前強制相同值。不得改用runtime API、shell-only export、destination filter或失敗DNS作為zero-attempt替代。這是內部launch invariant，不新增public config、wire schema或dependency identity。

## 3. Files and ownership

```text
src/sbd/perception/listen/whispercpp/
├── __init__.py
├── adapter.py          # parent-side ASRAdapter + recovery owner
└── supervisor.py       # child entry point; imports onnxruntime lazily
src/sbd/action/speak/matcha/
├── __init__.py
├── adapter.py          # parent-side TTSAdapter + recovery owner
└── worker.py           # child entry point; imports sherpa_onnx lazily
src/sbd/adaptor/
└── framed_child.py     # bounded JSON-line control + binary payload helper
requirements/m4a/
├── audio-artifacts.json
├── vad-rpi-cp313.json
├── tts-rpi-cp313.json
├── whispercpp-build.json
└── THIRD_PARTY_NOTICES.md
scripts/
└── m4a_audio_product.py  # build-whisper / install / preflight
```

`framed_child.py`只處理 bounded framing、request identity與child termination proof，不知道ASR/TTS語意。Engine-specific config與validation留在各adapter。

## 4. Common child lifecycle

### 4.1 States

每個 parent adapter維護：

```python
class ChildState(Enum):
    STOPPED = auto()
    STARTING = auto()
    READY = auto()
    BUSY = auto()
    DESTROYED = auto()
```

`start()`只允許`STOPPED→STARTING→READY`，且必須等READY identity全數吻合才return。由於現有RM backend與consumer worker都會呼叫adapter lifecycle，第二次`start()`在同一已驗證child上是idempotent；`stop()`在`STOPPED`為no-op，重複stop不得重啟或raise。

READY至少含protocol version、engine/model/runtime/profile checksum、PID/PGID。任一欄不符時parent先terminate→bounded wait→kill→waitpid，清IPC/workdir後才raise；不得留下半啟動process。

### 4.2 Framing and privacy

Control / payload framing 與 exact schema 以 `docs/protocol.md` Audio Protocol v1 為唯一權威。本章只固定 owner、state 與 cleanup 語意；兩份文件必須同時滿足，不得自行放寬 wire key、bound 或 lifecycle contract。

Parent與child不得log transcript、TTS text、PCM、prompt、raw model output或完整command。允許欄位只有stage、request ID的不可逆hash、duration/size、status/error code、latency、PID/exit與artifact checksum。

### 4.3 Abort and force-abort

- `abort()`：對active request送`CANCEL`並等待bounded `CANCELLED`。若尚在capture/generation可合作結束，adapter回`READY`。若native inference不支援合作取消，`abort()`保持pending，讓Ch 6 Level 1 timeout升Level 2；不得偷偷kill再回報一般timeout。
- `force_abort()`：SIGTERM process group，bounded wait；仍存活才SIGKILL，再waitpid、關閉streams、清temp。完成後state=`DESTROYED`並回`ForceAbortReport((stable_key,))`；未能證明exit/cleanup則raise，Ch 6進Level 3。
- ASR stable key為`backend.perception.listen.asr`；TTS stable key為`backend.action.speak.tts`。
- `rebuild()`只在`DESTROYED`合法；建立全新child、驗READY後原子切換handle並return `None`。失敗時清replacement後raise，RM recovery barrier保持closed。

## 5. ASR adapter

### 5.1 Construction

```python
class WhisperCppASRAdapter(ASRAdapter):
    def __init__(self, config: ASRConfig, *, lock: AudioArtifactLock) -> None: ...
    async def rebuild(self, bus: EventBus, config: AppConfig) -> None: ...
```

Factory只在`driver="whispercpp"`時lazy import本module。Construction讀取已由config loader解析的path，但不import native package、不開audio。`start()`依序驗product locks、venv isolation、artifact checksum、executable ownership/mode與work-root，再spawn supervisor。

### 5.2 Streaming endpoint and transcription

`transcribe(frames)`流程：

1. 建立唯一request ID，送`BEGIN`；每個input frame必須恰640 bytes。任何錯長度在送child前raise `AdapterError`，不得補零或resample。Parent以兩個同一operation內的async task並行執行frame pump與event reader，並遵守Audio Protocol v1每frame credit；reader收到`ENDPOINT`時set event，pump不再取得下一frame，不能等input iterator自然結束。
2. 依序送20 ms PCM。Supervisor保留500 ms bounded pre-speech ring，將S16_LE轉float32，依`model_spec.md`固定512-sample window、64-sample context與endpoint profile執行Silero；end-silence成立後，若從最後speech end累計的audio尚未達600 ms，繼續收至恰滿post-padding才送`ENDPOINT`。每request重設model recurrent/context/endpoint state，不保留上一turn history。
3. Endpoint成立後supervisor以固定pre/post padding形成單一bounded WAV（16 kHz mono S16_LE），停止要求新frame，交persistent whisper worker。
4. whisper worker固定4 threads、`zh`、greedy best-of-1、temperature 0、no timestamps/translate/internal-VAD/context及固定prompt checksum。結果以`RESULT`回parent；parent驗request ID、nonempty UTF-8與bounded metrics後建立`ASRResult(text, language="zh-TW")`。
5. `finally`關閉frame iterator由現有Listen負責；supervisor刪除bounded WAV，回READY。空白結果轉`ASRResult("")`，由Listen發布timeout；child明確可恢復錯誤轉`AdapterError`；protocol/crash/identity錯誤不得偽裝成一般空結果。

如果Listen的overall timeout先發生，依§4.3走abort/force-abort。ASR adapter不另設比worker timeout更長的無界等待；所有READY/IPC/inference/cleanup timeout取自strict config且為有限正值。

### 5.3 ASR failure cleanup

| Injection | Expected convergence |
| :--- | :--- |
| invalid frame / no speech | no artifact leak；contract error或empty result，不破壞child |
| child-declared inference error | `AdapterError`; child回READY；下個request可成功 |
| capture cancel | `CANCELLED`; temp清除；同child可再用 |
| native inference timeout/cancel | Level 1不假成功；Level 2殺完整process group；report ASR key；RM rebuild READY後才解除barrier |
| supervisor/native crash | no normal terminal fact；完整cleanup；需要force-abort/recovery或fatal |

## 6. TTS adapter

### 6.1 Construction

```python
class MatchaTTSAdapter(TTSAdapter):
    def __init__(self, config: TTSConfig, *, lock: AudioArtifactLock) -> None: ...
    async def rebuild(self, bus: EventBus, config: AppConfig) -> None: ...
```

Factory只在`driver="sherpa_matcha"`時lazy import。Child READY前驗isolated interpreter、exact two-wheel inventory、acoustic archive/components、Vocos checksum、provider/profile與voice ID。Archive只能由product preflight安全展開到Git外immutable install root；runtime worker不得每次startup從不受信任archive解壓。

### 6.2 Synthesis

`synthesize(text)`回async generator：

1. 第一個iteration才取得single-flight lock並送`GENERATE`；text必須是既有Speak已驗證的nonempty string，IPC可攜帶但不得log。
2. Child以`sid=0`、speed 1.0、CPU/2 threads、max one sentence生成；native float samples以clamp/round的固定轉換一次轉成little-endian signed 16-bit。
3. Child先送`PCM` header：request ID、16,000 Hz、1 channel、`S16_LE`、sample count、byte count、SHA-256，parent再exact-read payload、驗checksum/長度後以640-byte chunks yield；尾端不足640 bytes時只允許最後一個even-length chunk，不補樣本、不resample。
4. AudioOutput完整consume才由Speak發布`ActionCompleted(ok)`。Generator `aclose()`或Speak abort時送CANCEL並清pending payload；child不得開ALSA device。

TTS output已等於Core AudioOutput stream format；48 kHz stereo S32_LE轉換只存在M3已接受的HAL output adaptation，TTS層不得重做。

### 6.3 TTS failure cleanup

Error/cancel/timeout/force-abort與ASR遵守同一§4.3規則。Actual Matcha child必須覆蓋success/error/timeout/cancel；force-abort可使用可控hang double補足SIGKILL路徑，但至少另有actual child的SIGTERM→waitpid證據。每個case後assert child/thread/fd/iterator/stream/device-owner為零，並以相同baseline完成下一次success。

## 7. Config and composition

### 7.1 Schema additions

```python
@dataclass(frozen=True, slots=True)
class ASRConfig:
    driver: Literal["mock", "null", "whispercpp"] = "mock"
    engine_name: str | None = None
    model_path: Path | None = None
    worker_path: Path | None = None
    runtime_python: Path | None = None       # isolated VAD Python
    vad_model_path: Path | None = None
    artifact_lock_path: Path | None = None
    language: str | None = None
    dsp_profile: str | None = None
    decoder_profile: str | None = None

@dataclass(frozen=True, slots=True)
class TTSConfig:
    driver: Literal["mock", "null", "sherpa_matcha"] = "mock"
    engine_name: str | None = None
    model_path: Path | None = None            # immutable extracted model dir
    vocoder_path: Path | None = None
    runtime_python: Path | None = None
    artifact_lock_path: Path | None = None
    voice_id: str | None = None
    native_sample_rate: int | None = None
    native_channels: int | None = None
    native_sample_format: str | None = None
```

Real-driver exact values：

| Driver | Required equality |
| :--- | :--- |
| `whispercpp` | engine `whisper.cpp-1.9.2`; language `zh-TW`; DSP `silero-6.2.1-endpoint-v1`; decoder `p0-greedy-best-of-1`; all five paths absolute and present at preflight |
| `sherpa_matcha` | engine `sherpa-onnx-1.13.5-matcha`; voice `matcha-zh-en-default-sid-0`; native `16000/1/s16_le`; all four paths absolute and present at preflight |

`mock`/`null`不得要求real path。Unknown/missing/mismatchedreal field由`ConfigValueError`帶完整path在factory/hardware前拒絕。YAML不得提供checksum覆寫；checksum只來自tracked product lock。

### 7.2 Factory / RM

- `make_asr_adapter`與`make_tts_adapter`新增real branch且lazy import。
- 對外factory簽名維持`make_asr_adapter(cfg: ASRConfig) -> ASRAdapter`與`make_tts_adapter(cfg: TTSConfig) -> TTSAdapter`，composition不得額外建立或傳入lock。當driver分別為`whispercpp`或`sherpa_matcha`時，factory從`cfg.artifact_lock_path`讀取tracked product lock，以不import任何native engine的parser完成schema、路徑與Accepted identity驗證，建立`AudioArtifactLock`後再lazy import對應adapter class，並呼叫`WhisperCppASRAdapter(cfg, lock=lock)`或`MatchaTTSAdapter(cfg, lock=lock)`。lock缺失、不可讀、schema錯誤或identity不符時，在建立child、Audio HAL或work artifact前fail closed；`mock`／`null`branch不得讀取lock。
- Composition先建立adapter owner，再將同一owner作為backend `ResourceSpec.instance`與`recovery_hook`；real backend spec設`recoverable=True`，mock/null維持不可recover且force-abort report為空。
- Existing worker dependencies不變。Adapter `start/stop`需idempotent，以容納backend與worker lifecycle既有呼叫順序。
- Recovery hook只交換owner內部child handle；不得回replacement instance，不修改capability map，不publish public event。

## 8. Product lock / preflight

`requirements/m4a/*.json`必須逐列保存distribution/artifact、version、filename、size、SHA-256、source locator、license/notice reference、target OS/arch/Python及baseline source SHA。`m4a_audio_product.py`提供：

- `build-whisper`：只從exact source archive與tracked CPU-only CMake options建置，拒絕network/optional backend，輸出到new path並記product binary identity；
- `install`：先驗所有input，於same-filesystem new staging建立isolated VAD/TTS venv、安全展開artifact與安裝`--no-index --no-deps`exact wheels；完整自驗後才atomic rename，failure刪staging且不覆寫既有install；
- `preflight`：read-only驗既有install與candidate identity，在任何child或Audio HAL啟動前執行下列檢查。

1. 驗schema與Accepted Audio identity；
2. 驗wheel inventory exact match、venv isolated與installed distribution exact match；
3. 驗native worker/model/VAD/acoustic/Vocos及必要unpacked component hash；
4. 驗engine/profile config與tracked lock一致；
5. 驗Core checkout exact SHA（candidate mode）、protected paths clean與network-offline environment；
6. stdout只輸出sanitized JSON result，不輸出local credential、text、PCM或完整私人path。

Canonical command shapes固定於`docs/model_spec.md` §3。現有`scripts/m4_audio_runtime_closure.py`可重用其manifest/venv檢查，但product lock需另補native/artifact/profile與Accepted identity；不得以controller-r2 closure或目前部署M3 SHA替代M4a product candidate preflight。

## 9. Gate 3 tests and evidence

| Test ID | Platform | Required assertion |
| :--- | :--- | :--- |
| `M4A-CFG-001` | portable | real strict fields/equality；mock/null不需artifact；lazy import；invalid config在hardware前拒絕 |
| `M4A-LOCK-001` | portable + Pi preflight | missing/extra/wrong hash/version/interpreter/arch/profile fail closed；不產生child/work artifact |
| `M4A-IPC-001` | portable | Audio Protocol v1 exact keys/bounds、fragment/coalesce、frame credit、request/sequence/hash、BUSY/EOF/late terminal與privacy |
| `M4A-ASR-001` | portable double + Pi | 640-byte sequence→frozen endpoint→nonempty transcript；無resample；request-local state |
| `M4A-ASR-002` | portable + Pi | persistent load、連續turn、empty/error後reopen；無hidden transcript context |
| `M4A-ASR-003` | portable + Pi | timeout/cancel/force-abort/process crash；termination proof、ASR key、RM rebuild barrier、same-baseline recovery |
| `M4A-TTS-001` | portable double + Pi | fixed text→nonempty 16 kHz mono S16_LE→AudioOutput drain/playback complete；voice/profile identity不變 |
| `M4A-TTS-002` | portable + Pi | persistent load、error/timeout/cancel/force-abort；cleanup、TTS key、RM rebuild、same-baseline recovery |
| `M4A-PRIV-001` | portable + Pi | log/result不含transcript/prompt/TTS text/raw output/PCM/credential/private path |
| `M4A-OFF-001` | Pi | network namespace disabled下real ASR/TTS + HAL session PASS；zero network attempt / downloader |
| `M4A-RES-001` | Pi | Core process tree latency/resource/thermal/cleanup；M4b Accepted後再跑real combined envelope |
| `M4A-PKG-001` | portable review + Pi install | clean offline install、exact lock、license/notice inventory；Matcha Accepted Risk明列 |
| `M4A-INH-001` | evidence review | §10每列有POC SHA/locator/checksum、product SHA、inheritance reason、delta Test ID/result |

Portable doubles不得importreal engine；Pi cards指向同一provisional/frozen product SHA。所有formal命令使用bounded timeout與fresh run ID/output。M4a只有Tester对Core product exact SHA PASS且Designer final review無Blocking後才可標子gate完成；`M4A-RES-001`的真實LLM combined row在Accepted M4b input前保持Pending，不得用POC surrogate或early memory preflight冒充。

## 10. Required inheritance / delta index

Developer只負責在`scripts/`提供inheritance generator／template及其`tests/`驗證，不得直接建立或修改Tester-owned的`docs/outsource/evidence/`。Generator接受外部指定的40-character candidate SHA、POC locator與Gate 3 result locator，依下列schema輸出到caller明確指定的新路徑；Developer fast loop只使用temporary output。

Tester在同一產品candidate完成Gate 3執行後，使用該generator產生並核對最終`docs/outsource/evidence/<M4-delivery>/m4a/inheritance.json`。Tester是該正式檔案唯一writer，且至少逐列涵蓋candidate/provenance、P1～P12及Audio internal M4 20-session/failure/offline：

```json
{
  "area": "P1",
  "poc_delivery_id": "POC-audio-DEL-2026-001-R1",
  "accepted_audio_sha": "5694ead4ba6be928fdb4dbdf6da7155b214d72bd",
  "poc_locator": "...",
  "poc_sha256": "...",
  "classification": "reused_rerun",
  "inheritance_reason": "...",
  "product_sha": "<40 hex>",
  "delta_test_id": "M4A-ASR-001",
  "delta_result": "PASS|FAIL|BLOCKED",
  "result_locator": "..."
}
```

`product_sha`由Tester執行的外部candidate runner注入，不從branch HEAD推導。Generator不得自行宣告PASS或把development output寫入正式evidence目錄；缺欄、混SHA、`delta_result=PASS`但locator不存在，或只有「沿用POC」均fail closed。

## 11. Developer work packages

| WP | Scope | Entry / exit |
| :--- | :--- | :--- |
| M4A-WP-09 | tracked model/runtime/artifact/notice locks + product preflight | Accepted identities固定；negative lock regressions全綠 |
| M4A-WP-10 | common framed child owner + ASR supervisor/adapter | portable protocol/lifecycle tests；Pi ASR format/semantic smoke |
| M4A-WP-11 | Matcha worker/adapter + AudioOutput integration | portable framing/lifecycle tests；Pi PCM/playback smoke |
| M4A-WP-12 | config/factory/composition/RM recovery wiring | strict config、lazy import、ASR/TTS recovery barrier regressions |
| M4A-WP-13 | Gate 3 runner + inheritance generator/template + offline/resource/notice support | generator與schema regression全綠，same-SHA inputs ready for Tester；不寫正式evidence |

Developer先更新`docs/reviews/dev_progress_M4.md`估點與狀態，再修改`src/`/`tests/`。Reviewer通過本設計且Designer簽核Tester revised `test_spec_M4.md`之前，不進入production implementation。

## 12. Completion boundary

M4a production implementation complete不等於整體M4 Accepted。M4a子gate結論必須包含Core product SHA、portable result、Pi ASR/TTS/HAL result、inheritance index、offline/cleanup/notice結果；共享real M4a+M4b resource row在LLM input未Accepted前保持Pending。M4c仍依M4a與M4b通過後進場，最終M4另需三子gate在同一產品delivery SHA收斂。
