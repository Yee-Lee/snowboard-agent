# M4 實測規格：Memory Preflight

本檔包含M4 Core整合的early memory preflight與M4a Gate 3 test contract。下列
`M4-REG-001`只在昂貴integration loop、quality或soak前，以相同target上的最小smoke
command排除明顯的4GB容量風險；它不是新的milestone gate，也不取代M4A-P9、
M4B-P9 / P10B或產品exact-SHA acceptance。M4a正式驗收另依本檔後續13個Test ID。

## M4-REG-001 — Pi 5 4GB memory preflight

| 欄位 | 契約 |
| :--- | :--- |
| Platform | `RPI-NATIVE`；正式預定的Pi 5 4GB測試環境 |
| Owner | Core Tester執行與判讀；Audio / LLM POC不執行combined preflight，也不修改Core runner |
| Timing | Accepted Audio與LLM POC packages均完成Core intake，且Developer已建立Core-owned composition smoke command後、昂貴repetition / quality / soak前；integration debug或artifact / config變更後可重跑 |
| Command | `python3 scripts/m4_memory_preflight.py --max-system-used-mib 3584 --timeout-seconds <N> -- <existing-smoke-command>` |
| Primary metric | 每個sample的`system_used_kib = MemTotal - MemAvailable`；任一sample不得超過3584 MiB |
| Hard risk | swap used非零、swap-in/out增加、full memory-pressure stall增加、cgroup OOM kill增加、smoke nonzero / timeout或process group未cleanup |
| Diagnostic only | process-group sum PSS、sum RSS、最低`MemAvailable`、執行前後system counters；不得以sum RSS作容量判定 |
| Output | stdout JSON；`--output`只供當次debug / analyze選用，不要求run ID、candidate SHA、baseline packet或長期保存 |
| Result | `PREFLIGHT_OK`表示本次smoke未見上述風險；`PREFLIGHT_RISK`表示先停止昂貴測試並調整artifact / config。兩者都不是POC或milestone PASS狀態 |

POC團隊只需依既有contract交付Accepted artifact、固定設定及各自的reproduction command；不為本
測項新增工作。Core Developer完成composition smoke後，Core Tester才以本wrapper執行。單一POC
candidate或尚未intake的package不得用本測項宣稱combined capacity。正式combined residency與
20-session結果仍由M4B-P9 / P10B保存。

### Portable regression

`tests/test_m4_memory_preflight.py`使用injected snapshots固定四條行為：

1. 大量sum RSS不會取代system `MemAvailable`造成false risk；
2. full memory pressure或swap activity產生`PREFLIGHT_RISK`；
3. command結束後的process-group survivor產生`PREFLIGHT_RISK`；
4. 3584 MiB上限明確套用`MemTotal - MemAvailable`，不再使用含糊的「PSS / RSS」。
---

# M4a Gate 3 測試規格

## 概述與範圍

本章節定義 M4a 子 gate 的 Core Gate 3 驗收標準。測試覆蓋來源為
`docs/implement/ch_m4a_audio_production.md`、`docs/protocol.md` Audio Protocol v1、
`docs/implement/ch10_config.md` M4a extension 及 `docs/milestones/M4.md` §6.1 / §6.4。

**M4a Gate 3 通過條件**：Core Tester 對 Core product exact SHA 以既有 runner 執行且 PASS，
Designer final review 無 Blocking，才可標記 M4a 子 gate 完成。POC PASS 不取代產品 PASS。

## 正式命令與 Runner Contract（T1）

所有正式命令使用 `scripts/candidate_gate.py`；不直接傳遞 pytest CLI 參數。
`<python-3.11>`、`<python-3.12>`、`<python-3.13>`分別代表實際回報該minor的
interpreter launcher；不得以同一個未切換環境的`python3`連跑三次。
`<portable-run>` 三版本與 `matrix` 必須共用同一 run ID 與 candidate SHA。
`<acceptance-run>` 供 `preflight` 與 `accept` 共用，且必須不同於 `<portable-run>`。
Portable三個版本目錄、matrix index及preflight的`<acceptance-root>`在各自建立前必須不存在。
`accept`必須重用preflight建立的`<acceptance-root>`；該目錄必須已存在且
`<acceptance-root>/result.json`必須尚不存在。

```text
# Portable matrix — 三版本使用同一 <portable-run> 與 candidate SHA
<python-3.11> scripts/candidate_gate.py portable \
    --candidate-sha <40hex> --run-id <portable-run> \
    --python 3.11 --suite <m4a-portable-suite> \
    --timeout-seconds <N> --output <portable-root>/python-3.11

<python-3.12> scripts/candidate_gate.py portable \
    --candidate-sha <40hex> --run-id <portable-run> \
    --python 3.12 --suite <m4a-portable-suite> \
    --timeout-seconds <N> --output <portable-root>/python-3.12

<python-3.13> scripts/candidate_gate.py portable \
    --candidate-sha <40hex> --run-id <portable-run> \
    --python 3.13 --suite <m4a-portable-suite> \
    --timeout-seconds <N> --output <portable-root>/python-3.13

# Matrix index — 三版本完成後才執行
<python-3.13> scripts/candidate_gate.py matrix \
    --candidate-sha <40hex> --run-id <portable-run> \
    --input-root <portable-root> \
    --output <portable-root>/matrix-index.json

# Target preflight
<python-3.13> scripts/candidate_gate.py preflight \
    --candidate-sha <40hex> --run-id <acceptance-run> \
    --portable-index <portable-root>/matrix-index.json \
    --runtime 3.13 \
    --hardware <hardware.json> \
    --config <sanitized-config.yaml> \
    --artifact-manifest <artifacts.json> \
    --output <acceptance-root>

# Target acceptance
<python-3.13> scripts/candidate_gate.py accept \
    --candidate-sha <40hex> --run-id <acceptance-run> \
    --preflight <acceptance-root>/preflight.json \
    --suite <m4a-rpi-suite> \
    --timeout-seconds <N> \
    --output <acceptance-root>
```

`portable`與`accept`的`--timeout-seconds`必須為有限正數；timeout觸發runner記錄
`Fail`並保存截至timeout的stdout/stderr，不得記為`Pass`。`matrix`與`preflight`
沒有此CLI flag，不得自行傳入；外層執行watchdog仍必須bounded。

## Runner Result Schema（T2）

所有正式 result 的欄位名稱以 `scripts/candidate_gate.py` 為唯一權威；Test-specific card
只能在 runner 標準欄位之外**增加** `test_id` 與測項 metric 欄位，不得刪除、改名或取代下列欄位。

### Base result fields（portable / preflight / acceptance / debug）

| 欄位 | 型別 | 說明 |
| :--- | :--- | :--- |
| `branch` | string | 診斷用；不作 identity |
| `candidate_sha` | string | 40 lowercase hex；外部指定，不從 HEAD 推導 |
| `command` | list[string] | `sys.argv`；不得含 credential / transcript / TTS text / PCM |
| `mode` | string | `portable` / `preflight` / `acceptance` / `debug` |
| `platform` | string | `platform.platform()` |
| `python.implementation` | string | e.g. `CPython` |
| `python.version` | string | e.g. `3.13.2` |
| `run_id` | string | 符合 `^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$`；token only，output directory 另記 |
| `started_at_utc` | ISO 8601 | |
### Pytest-execution fields（portable / acceptance / debug）

| 欄位 | 說明 |
| :--- | :--- |
| `ended_at_utc` | ISO 8601 |
| `exit_code` | subprocess exit code |
| `status` | `Pass`或`Fail`；debug成功時為`Diagnostic` |
| `counts.passed` / `failed` / `skipped` / `xfailed` | JUnit 統計；`failed=skipped=xfailed=0` 才為 Pass |
| `suite_command` | pytest argv list |
| `timeout_seconds` | 正數 |
| `raw_logs` | `list[string]`；run-root-relative stdout/stderr locator |

Portable與acceptance另含`suite`；portable再含`python_minor`（`3.11`、`3.12`
或`3.13`）。Debug另含`node`而不含`suite`／`python_minor`，成功status為
`Diagnostic`；三種mode均保留上列pytest-execution欄位。

### Preflight-mode additional fields

| 欄位 | 說明 |
| :--- | :--- |
| `checksums.artifact_manifest.{path,sha256}` | artifact manifest 路徑與 SHA-256 |
| `checksums.config.{path,sha256}` | sanitized config 路徑與 SHA-256 |
| `checksums.hardware.{path,sha256}` | hardware description 路徑與 SHA-256 |
| `ended_at_utc` | ISO 8601 |
| `exit_code` | 固定為0；失敗另寫failure record，不得產生Pass preflight |
| `portable_index` | matrix-index.json 絕對路徑 |
| `portable_run_id` | 對應 portable run ID |
| `runtime` | `3.13` |
| `status` | 成功為`Pass` |

### Matrix index fields

Matrix index 由 runner 自動產生（`matrix-index.json`）：
`branch`、`candidate_sha`、`command`、`created_at_utc`、`results.{3.11,3.12,3.13}`（relative paths）、`run_id`、`status`。

### Pending 語意（T3）

`Pending` 只用於 test spec tracker 表示尚未執行的項目，不產生任何 runner result 欄位。
尚未執行的 Pi / combined 項目不得出現在任何 runner output 的 `status` 欄位。

## Privacy Domain 分離（T9）

正式 runner metadata 與 M4a product process output 屬於不同 privacy domain，規則互不覆蓋：

**Domain A — Formal runner result（保留）**：`command`（`sys.argv` list）、
`candidate_sha`、`run_id`及該mode實際存在的runner identity欄位必須保留完整；
suite mode另保留`raw_logs` locator，preflight/matrix不得虛構此欄位。
`command` 不得含 credential、transcript、TTS text 或 PCM；允許 suite path 與 runner flag。

**Domain B — M4a product process output（掃描）**：parent/child `stdout`、`stderr`、
structured product result payload 及 product raw log 以 sentinel 掃描下列禁止內容，
任一命中即 Fail：transcript text、TTS input text、prompt、raw model output、
PCM bytes（含 base64 / hex encoding）、credential、private work path。

Result locator 優先使用 run-root-relative path；若 formal card 保留 absolute path，
公開 delivery 前須產生 sanitized locator，不得刪除 runner identity metadata。

---

## M4A-CFG-001 — Config strict equality / real-driver validation

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable |
| **Contract basis** | `ch10_config.md` §6 / §15 條款 20–22；`ch_m4a_audio_production.md` §7.1 / §7.2 |
| **Suite marker** | `not rpi` |
| **Timeout** | `--timeout-seconds 60` |
| **Evidence** | runner `result.json` + JUnit + raw logs；`counts.failed=skipped=xfailed=0` |

**Factory seam cases（T4）**：

| Case | Method | Assertion |
| :--- | :--- | :--- |
| Public factory signature — ASR | `inspect.signature(make_asr_adapter)` | 唯一參數為 `cfg: ASRConfig`；無額外 positional 或 keyword 參數 |
| Public factory signature — TTS | `inspect.signature(make_tts_adapter)` | 唯一參數為 `cfg: TTSConfig` |
| Lock injection keyword-only — ASR | inject sentinel `AudioArtifactLock`；呼叫 `make_asr_adapter(cfg)` | `WhisperCppASRAdapter.__init__` 收到同一 object identity，且只經 `lock=<sentinel>` keyword 傳入 |
| Lock injection keyword-only — TTS | 同上 | `MatchaTTSAdapter.__init__` 收到同一 object identity，且只經 `lock=<sentinel>` keyword 傳入 |
| mock/null no-read lock | driver=`mock` 或 `null` | lock parser call count = 0；`artifact_lock_path` 被忽略 |
| Missing/unreadable lock — no native import | parameterize `whispercpp`與`sherpa_matcha`；lock file不存在或不可讀 | adapter/native module未import；child spawn、Audio HAL、workdir call count全為0 |
| Malformed lock — no native import | parameterize兩個real driver；lock JSON invalid | 同上 |
| Identity mismatch — no native import | parameterize兩個real driver；任一lock identity欄位不符 | 同上 |
| Composition owner identity — real | 建立real backend spec | factory回傳的同一adapter object同時是`ResourceSpec.instance`與`recovery_hook` owner；`recoverable=True` |
| Composition owner identity — mock/null | 建立mock/null backend spec | `recoverable=False`，force-abort report為空，不讀lock |
| Recovery hook boundary | 對real owner執行rebuild | 只原子交換owner內部child handle、return `None`；不替換adapter instance、不改capability map、不publish public event |

**Config validation cases（table-driven）**：

| Case | Input | Expected outcome |
| :--- | :--- | :--- |
| `whispercpp` valid | engine=`whisper.cpp-1.9.2`, language=`zh-TW`, dsp=`silero-6.2.1-endpoint-v1`, decoder=`p0-greedy-best-of-1`, 五個絕對路徑全存在 | `ASRConfig` 建立成功 |
| `sherpa_matcha` valid | engine=`sherpa-onnx-1.13.5-matcha`, voice=`matcha-zh-en-default-sid-0`, native=`16000/1/s16_le`, 四個絕對路徑全存在 | `TTSConfig` 建立成功 |
| Missing required field | `whispercpp` 缺 `model_path` | `ConfigValueError`；訊息含完整 dotted path；factory/HAL/child 建立前拒絕 |
| Mismatched engine version | engine 版本字串不符 | `ConfigValueError` |
| Unknown driver | driver=`whisper`（舊名）或 `piper` | `ConfigValueError`；不 fallback 到 mock |
| YAML checksum override | YAML 提供 `checksum` 欄位 | `UnknownConfigKey` |
| `mock` driver | driver=`mock` | 不要求任何 path，不 import real module |
| `null` driver | driver=`null` | 不要求任何 path，不 import real module |
| Lazy import before factory | driver=`whispercpp`；factory 尚未呼叫 | `sys.modules` 中無 real native module |
| Invalid config pre-hardware | 任何 real-driver invalid case | factory / Audio HAL / child 建立前即拒絕 |

---

## M4A-LOCK-001 — Product lock / artifact identity

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi preflight |
| **Contract basis** | `ch_m4a_audio_production.md` §8；`requirements/m4a/*.json` schema；`ch_m4a_audio_production.md` §7.2 |
| **Suite marker** | Portable: `not rpi`；Pi: `preflight` command（runner preflight mode） |
| **Timeout** | Portable: `--timeout-seconds 60`；Pi candidate `preflight`無timeout flag，外層watchdog 120秒 |
| **Evidence** | Portable: runner `result.json` + JUnit；Pi: product-preflight sanitized JSON + runner `preflight.json`（含 `checksums.*`） |

**Required assertions（table-driven）**：

| Case | Scope | Injection | Expected outcome |
| :--- | :--- | :--- | :--- |
| Missing/unreadable lock file | Portable | 兩個real driver分別注入不存在／permission-denied `artifact_lock_path` | fail closed；adapter/native import = 0；child spawn = 0；Audio HAL = 0；workdir = 0 |
| Extra unknown field in lock | Portable | lock JSON 含額外 key | schema fail closed；同上 counts |
| Wrong SHA-256 | Portable | 任一 artifact SHA-256 不符 | fail closed；同上 counts |
| Wrong version | Portable | version 欄位不符 Accepted identity | fail closed |
| Wrong interpreter | Portable | `interpreter` / `arch` 欄位不符目標 | fail closed |
| Wrong profile | Portable | `profile` 欄位不符 | fail closed |
| Zero artifact on fail | Portable | 上述任一 negative case | 斷言不存在 child process、work directory、臨時 WAV/PCM |
| Product preflight — exact checkout/install | Pi | 以`model_spec.md` §3的`m4a_audio_product.py preflight` command shape傳入frozen 40-hex SHA、tracked lock、immutable install與sanitized config | schema、Accepted identity、wheel inventory、venv isolation、artifact/profile checksum、protected paths與offline環境全數吻合；sanitized success result後才可執行candidate preflight |
| Product preflight failure | Pi | parameterize wrong checkout SHA、dirty protected path、wheel/model/profile drift與network-enabled environment | fail closed；不得spawn ASR/TTS child、不得開Audio HAL；只保存sanitized failure record |
| Valid lock — exact Accepted identity | Portable + Pi | 正確 lock；`accepted_audio_sha=5694ead4ba6be928fdb4dbdf6da7155b214d72bd` | Portable: factory 成功建立 `AudioArtifactLock`；Pi: runner `preflight.json` `status=Pass`，`checksums.artifact_manifest.sha256` 存在且不為空 |

---

## M4A-IPC-001 — Audio Protocol v1 wire contract

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable |
| **Contract basis** | `docs/protocol.md` §1–§5 |
| **Suite marker** | `not rpi` |
| **Timeout** | `--timeout-seconds 60` |
| **Evidence** | runner `result.json` + JUnit + raw logs；`counts.failed=skipped=xfailed=0` |

**Schema / bounds cases（T5）**：

| Category | Case | Expected outcome |
| :--- | :--- | :--- |
| Schema | 任何 message 缺 `protocol:1` | protocol error；parent termination proof；不轉 empty transcript |
| Schema | extra key in control message | protocol error |
| Schema | invalid UTF-8 / JSON | protocol error |
| Bounds — control line | 恰 16 KiB（含 `\n`）— inclusive max | accepted |
| Bounds — control line | 16 KiB + 1 byte（含 `\n`）— exceeded | protocol error |
| Bounds — TTS PCM payload | 恰 64 MiB、even bytes、`sample_count*2` 相符 — inclusive max | accepted |
| Bounds — TTS PCM payload | `payload_bytes=0`或`sample_count=0` | protocol error；payload與sample count必須為正 |
| Bounds — TTS PCM payload | 64 MiB + 2 bytes — exceeded | protocol error |
| Bounds — TTS PCM payload | odd `payload_bytes` | protocol error |
| Bounds — TTS PCM payload | `payload_bytes` ≠ `sample_count * 2` | protocol error |
| Fragment / coalesce | fragmented header read（分批 TCP-like 到達） | 正確 reassemble |
| Fragment / coalesce | header 與 payload 在同一 `read` 到達（coalesced） | 正確分離 |
| Frame credit | parent 在收到 `FRAME_ACCEPTED` 前嘗試送第二個 FRAME | parent 等待；不 bypass credit |
| Request ID — wrong | event 帶錯誤 request_id | protocol error |
| Request ID — duplicate | 重用已用過的 request_id | protocol error |
| Request ID — not strictly increasing | request_id=1 後送 request_id=1 | protocol error |
| Request ID — must be positive int | request_id=0 或負數 | protocol error |
| Sequence | FRAME sequence 不連續（gap 或重複） | protocol error |
| Hash | `pcm_sha256` 或 `bounded_pcm_sha256` 不符 | protocol error |
| BUSY | 第一個 request 未 terminal 前送 BEGIN/GENERATE | child 回 `BUSY`；parent 不排隊 |
| EOF | child pipe 提前 EOF | parent termination proof；不轉 empty transcript 或 normal error |
| Late terminal | terminal 後同 request 再送 event | protocol error |
| ERROR code — ASR whitelist | `INVALID_FRAME`、`NO_SPEECH`、`MULTIPLE_UTTERANCES`、`INFERENCE_REJECTED` | recoverable；child 回 READY |
| ERROR code — ASR unknown | 非上述四個 code | protocol error（非 request ERROR） |
| ERROR code — TTS whitelist | `INVALID_TEXT`、`GENERATION_REJECTED`、`INVALID_PCM` | recoverable；child 回 READY |
| ERROR code — TTS unknown | 非上述三個 code | protocol error |
| SHUTDOWN only in READY | BUSY 狀態收 SHUTDOWN | illegal；parent 視為 protocol error |
| SHUTDOWN_ACK sequence | READY → SHUTDOWN → `SHUTDOWN_ACK` | child state → STOPPED；parent waitpid |
| Privacy — parent stderr | 掃描 Domain B sentinels | 無 transcript / TTS text / PCM / credential |

**READY mismatch / process cleanup cases（T6）**：

| Case | Assertion |
| :--- | :--- |
| ASR READY — exact key set | exact keys為`protocol,event,pid,pgid,runtime_lock_sha256,vad_model_sha256,asr_binary_sha256,asr_model_sha256,profile_sha256`；missing/extra key、`protocol!=1`、`event!=READY`、PID不等於child PID或PGID不等於top-level child PID皆fail |
| ASR READY — each identity mismatch | 對五個identity欄位逐欄parameterize wrong 64-hex value（其他欄正確） | parent：SIGTERM process group → bounded wait → SIGKILL if needed → waitpid；IPC/workdir清除；不進READY |
| TTS READY — exact key set | exact keys為`protocol,event,pid,pgid,runtime_lock_sha256,acoustic_model_sha256,vocoder_sha256,profile_sha256`；structural/PID/PGID規則同ASR |
| TTS READY — each identity mismatch | 對四個identity欄位逐欄parameterize wrong 64-hex value（其他欄正確） | parent：SIGTERM process group → bounded wait → SIGKILL if needed → waitpid；IPC/workdir清除；不進READY |
| ASR nested session — no nested PGID | ASR supervisor 啟動 whisper worker 時，whisper PID 的 PGID 等於 supervisor PGID；不建立第二層 process group |
| Nested descendant cleanup | force-abort 後，PGID 下所有 descendant（含 native whisper）exit proof；process/thread/fd/temp = 0 |
| TTS top-level group | TTS worker PGID 等於 worker PID；force-abort 後 process/thread/fd/temp = 0 |
| Next-success after cleanup | 上述每個READY structural/identity mismatch cleanup完成後，同一owner rebuild全新child並成功完成一次transcription/synthesis |
| Idempotent lifecycle | 對ASR/TTS各自parameterize：第二次`start()`在同一已驗證child上不重spawn；`stop()`於STOPPED為no-op；重複stop不重啟、不raise |

---

## M4A-ASR-001 — ASR 640-byte streaming endpoint / transcription

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable double + Pi |
| **Contract basis** | `ch_m4a_audio_production.md` §5.2；`docs/protocol.md` §2 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Timeout** | Portable: `--timeout-seconds 60`；Pi: `--timeout-seconds 300` |
| **Evidence** | Portable: runner result + JUnit；Pi: runner acceptance result card，額外欄位 `test_id`、`latency_ms`；不含 transcript text 或 PCM |

**Streaming / framing cases**：

| Case | Scope | Assertion |
| :--- | :--- | :--- |
| 正常 640-byte sequence→endpoint→transcript | Portable + Pi | 每frame恰640 bytes；收`FRAME_ACCEPTED`才送下一；收`ENDPOINT`後停送；`RESULT.text` nonempty UTF-8且parent建立`ASRResult(..., language="zh-TW")` |
| 非 640-byte frame（641 或 639） | Portable | parent raise `AdapterError` 在送 child 前；無 resample / 補零 |
| Request-local state | Portable | 兩次連續 request；第二次 Silero state / whisper context 完全重設；不帶前次 history |
| No resample | Portable + Pi | 斷言不呼叫任何 resampler；stream 固定 16 kHz mono S16_LE |

**Fixed endpoint / decoder parameters（T7）**：

| Parameter | Expected value | Assertion method |
| :--- | :--- | :--- |
| Pre-speech ring | 500 ms = 25 個 20 ms frame | inject 25-frame deterministic input；第 26 frame 才觸發 VAD；斷言 ring 長度 |
| Silero window | 512 samples | injected VAD call capture；`window_size_samples=512` |
| Silero context | 64 samples | injected VAD call capture；`context=64` |
| Positive threshold | `0.5` | injected endpoint profile capture；exact float |
| Negative threshold | `0.35` | injected endpoint profile capture；exact float |
| Startup mask | 160 ms = 8個20 ms frame | deterministic startup speech fixture；mask內不觸發 |
| Minimum speech | 250 ms | 249 ms rejected／250 ms accepted boundary |
| End silence | 500 ms | 499 ms不成立／500 ms成立；成立後仍收滿600 ms post-padding |
| Post-padding | speech-end 後恰 600 ms（30 個 20 ms frame）收齊才送 ENDPOINT | inject deterministic speech-then-silence；計 ENDPOINT 前 frame count = 30 |
| ENDPOINT stops pull | ENDPOINT 後 parent 不再 pull input iterator | inject 額外 frames；斷言 iterator.next 未被呼叫 |
| Per-request state reset | 每 request 重設 Silero recurrent / context / endpoint state | inject second request；斷言 VAD state init call count ≥ 2 |
| Whisper threads | 4 | injected whisper invocation capture；`n_threads=4` |
| Whisper language | `zh` | injected capture；`language="zh"` |
| Whisper decode strategy | greedy best-of-1 | injected normalized invocation capture同時驗`strategy="greedy"`與`best_of=1`；不得只驗其中之一 |
| Whisper temperature | 0 | injected capture；`temperature=0` |
| Timestamps off | False | injected capture |
| Translate off | False | injected capture |
| Internal VAD off | False | injected capture |
| Context (prev tokens) off | False | injected capture |
| Prompt checksum | 等於 product lock 中固定值 | injected capture；比對 lock `prompt_sha256` |
| Silero endpoint profile | `silero-6.2.1-endpoint-v1` | Pi READY event `vad_model_sha256` 吻合 lock |

---

## M4A-ASR-002 — ASR persistent load / multi-turn

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4a_audio_production.md` §5.1 / §5.2；`docs/protocol.md` §4 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Timeout** | Portable: `--timeout-seconds 60`；Pi: `--timeout-seconds 300` |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`turn_count`） |

**Required assertions**：

| Case | Scope | Assertion |
| :--- | :--- | :--- |
| Persistent load（不重載） | Portable + Pi | 連續兩 turn；第二次 `start()` idempotent；supervisor / whisper spawn call count = 1 |
| Success → success | Portable + Pi | 兩次 transcription；第一次 `RESULT.text` 不影響第二次 |
| Empty result → reopen | Portable | `RESULT.text=""` → `ASRResult("")`；下一 turn 正常成功 |
| Error → reopen | Portable | `ERROR(NO_SPEECH)` → `AdapterError`；child 回 READY；下一 turn 成功 |
| No hidden context | Portable | 不同 request ID 的 transcript 互不混合；斷言 whisper context 每次清空 |

---

## M4A-ASR-003 — ASR abort / force-abort / recovery

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4a_audio_production.md` §4.3 / §5.3；`docs/protocol.md` §2.2 / §4 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Timeout** | Portable: `--timeout-seconds 60`；Pi: `--timeout-seconds 120` |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`case`、`cleanup_count`） |

**Injected failure table**：

| Injection | Scope | Expected convergence | Artifact assertion | Recovery |
| :--- | :--- | :--- | :--- | :--- |
| Listen timeout — abort | Portable | `CANCEL` 送出；等 `CANCELLED`；child 回 READY | temp WAV/PCM 刪除；orphan fd = 0 | 同 child 下一 turn 成功 |
| Cancel deferred（native inference 不支援合作取消） | Portable | `abort()` pending；Level 1 timeout → `force_abort()` | 不假回成功 | force-abort 後走 Level 2 |
| force_abort | Portable | SIGTERM PGID → bounded wait → SIGKILL → waitpid → close streams → clear temp | state=`DESTROYED`；`ForceAbortReport(stable_key=backend.perception.listen.asr)` | RM `rebuild()` 後 state=READY；barrier 解除前 SM 不接受新 wake；same-baseline 下一 turn 成功 |
| Supervisor crash（PGID exit 非零） | Portable | 無 normal terminal；完整 termination proof | no orphan process/thread/fd | force-abort / recovery 或 fatal |
| ASR stable key 驗證 | Portable | `ForceAbortReport.stable_key` == `backend.perception.listen.asr` | — | — |
| RM rebuild READY barrier | Portable | `rebuild()` 只在 `DESTROYED` 合法；成功後 state=READY | 無 double spawn | barrier 解除；same-baseline next turn 成功 |
| Nested descendant cleanup（T6） | Portable | force-abort 後，supervisor PGID 下含 whisper native 的所有 descendant exit proof | process/thread/fd/temp = 0 | 同上 |
| Actual ASR child termination/recovery | Pi | 對real supervisor送SIGTERM並waitpid；受控timeout/cancel case不得產生normal terminal | descendant/process/thread/fd/temp = 0 | 同一Accepted baseline rebuild READY後完成一次real transcription |

---

## M4A-TTS-001 — TTS text→PCM→AudioOutput

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable double + Pi |
| **Contract basis** | `ch_m4a_audio_production.md` §6.2；`docs/protocol.md` §3 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Timeout** | Portable: `--timeout-seconds 60`；Pi: `--timeout-seconds 300` |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`pcm_sha256`、`sample_rate_hz`、`channels`、`sample_format`、`payload_bytes`）；不含 TTS text 或 raw PCM |

**PCM / framing cases**：

| Case | Scope | Assertion |
| :--- | :--- | :--- |
| Fixed text → 16 kHz mono S16_LE | Portable + Pi | `PCM` header：`sample_rate_hz=16000`、`channels=1`、`sample_format=S16_LE`；`payload_bytes` 正偶數且 ≤ 64 MiB；`pcm_sha256` 吻合 exact payload |
| AudioOutput drain / completion | Portable + Pi | `AudioOutput` 完整 consume；Speak 發布 `ActionCompleted(ok)` |
| 640-byte chunk yield | Portable | generator 每個 chunk 恰 640 bytes；最後一個 even-length 但不足 640；不補樣本 |
| TTS 不 resample | Portable + Pi | output 固定 16 kHz；無 resampler 呼叫 |
| Voice / profile identity | Pi | READY event `acoustic_model_sha256`、`vocoder_sha256`、`profile_sha256` 吻合 lock；`voice_id=matcha-zh-en-default-sid-0` |
| Lazy generator / single-flight | Portable | 建立generator不取得lock且不送`GENERATE`；第一次iteration才取得single-flight lock；第二個concurrent operation收到BUSY且不排隊 |
| Child hardware boundary | Portable + Pi | Matcha child的ALSA/Audio HAL/device-open call count = 0；只有parent的AudioOutput owner可播放 |

**Fixed generation parameters（T8）**：

| Parameter | Expected value | Assertion method |
| :--- | :--- | :--- |
| Speaker ID | `sid=0` | injected Matcha invocation capture |
| Speed | `speed=1.0` | injected capture |
| Provider | CPU | injected capture；無 CUDA / CoreML 等 |
| Threads | 2 | injected capture；`num_threads=2` |
| Max sentence | 1 | injected invocation capture；`max_num_sentences=1`或該binding的等價normalized欄位，且input不自行分句 |
| Conversion oracle | Accepted `audio_m4`的`poc_audio/src/audio_poc/m4a_tts_quality.py::float_samples_to_s16le` | portable test以相同boundary/vector作byte-level oracle；不得另選scale/round規則 |
| Float→S16_LE conversion — clamp low | input ≤ -1.0（e.g. -2.0, -1.0）→ -32768 | oracle table |
| Float→S16_LE conversion — clamp high | input ≥ 1.0（e.g. 1.0, 2.0）→ 32767 | oracle table |
| Float→S16_LE conversion — mid values | `round(value * 32767)`；-0.5→-16384；0→0；0.5→16384 | oracle table |
| Oracle vector | `[-2,-1,-0.5,0,0.5,1,2]` → `[-32768,-32768,-16384,0,16384,32767,32767]` | byte-level comparison；little-endian |
| Conversion — once only | float samples 只轉換一次 | inject 計數 wrapper；conversion call count = 1 |
| Output — little-endian | 輸出為 little-endian S16_LE | struct.unpack_from 驗 byte order |
| Byte count / hash | `payload_bytes == sample_count * 2`；`sha256(payload) == pcm_sha256` | exact match |

---

## M4A-TTS-002 — TTS persistent load / error / abort / recovery

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4a_audio_production.md` §4.3 / §6.3；`docs/protocol.md` §3.2 / §4 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Timeout** | Portable: `--timeout-seconds 60`；Pi: `--timeout-seconds 120` |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`case`、`cleanup_count`） |

**Injected failure table**：

| Injection | Scope | Expected convergence | Cleanup assertion | Recovery |
| :--- | :--- | :--- | :--- | :--- |
| Persistent load | Portable + Pi | 連續兩次synthesis；第二次`start()` idempotent；engine不重載；worker spawn count = 1 | — | 第二次成功 |
| `GENERATION_REJECTED` error | Portable | child 回 ERROR；child 回 READY | orphan fd/thread = 0 | 同 child 下一 synthesis 成功 |
| timeout（Level 1 → Level 2） | Portable | Level 1 不假成功；Level 2 SIGTERM process group | process/thread/fd/iterator/stream/device-owner = 0 | RM rebuild READY；same-baseline 成功 |
| cancel（GENERATE 後送 CANCEL） | Portable | `CANCELLED` 或 `CANCEL_DEFERRED` → force-abort | pending payload 清除 | 同 child 下一 synthesis 成功 |
| force_abort — hang double | Portable | SIGTERM → wait → SIGKILL → waitpid；state=`DESTROYED`；`ForceAbortReport(stable_key=backend.action.speak.tts)` | child/thread/fd/iterator/stream/device-owner = 0 | RM rebuild READY；same-baseline 成功 |
| Actual Matcha child SIGTERM→waitpid（T6） | Pi | real child SIGTERM path；waitpid exit proof | — | — |
| Actual Matcha success/error/timeout/cancel | Pi | 對real child逐項執行bounded success、受控generation rejection、timeout與cancel；timeout/cancel不得假回成功 | 每個case後child/thread/fd/iterator/stream/device-owner = 0或同一healthy child明確回READY | 每個case後以相同Accepted baseline完成下一次real synthesis |
| TTS stable key | Portable | `ForceAbortReport.stable_key` == `backend.action.speak.tts` | — | — |

---

## M4A-PRIV-001 — Privacy / no-log contract

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4a_audio_production.md` §4.2；`docs/protocol.md` §1；本規格 §Privacy Domain 分離 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Timeout** | Portable: `--timeout-seconds 60`；Pi: `--timeout-seconds 60` |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`scanned_paths`、`hits=0`） |

**Domain B product output sentinel scan（table-driven）**：

以下禁止內容針對 M4a product parent/child `stdout`、`stderr`、structured product result payload 及 product raw log 掃描；任一命中即 Fail。
**不適用**於runner自身的`command`、`raw_logs` locator或其他identity欄位（Domain A）；
但locator指向的stdout/stderr若捕獲product process output，其內容仍須納入Domain B sentinel scan。

| Prohibited content | Sentinel type | Expected outcome |
| :--- | :--- | :--- |
| transcript text（ASR 結果） | 固定 test fixture 字串 | 不出現 |
| TTS input text | 固定 test fixture 字串 | 不出現 |
| prompt | 固定 test fixture 字串 | 不出現 |
| raw model output | 固定 test fixture 字串 | 不出現 |
| PCM bytes（raw / base64 / hex） | 固定 byte pattern | 不出現 |
| credential / secret | 固定 test sentinel | 不出現 |
| private work path（full absolute path） | 固定 test workdir prefix | 不出現 |
| request_id → transcript reverse-mapping | log 中只含不可逆 hash | 無法從 log 反推 transcript |

**允許記錄（白名單）**：stage、request ID 的不可逆 hash、duration/size、status/error code、latency_ms、PID/exit、artifact checksum。

**Domain A runner metadata**：`command`及該mode存在的`raw_logs`等identity欄位必須保留；
不掃描locator字串本身，但必須掃描其指向且含product output的內容。

---

## M4A-OFF-001 — Offline isolation / network-zero

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Pi（`rpi` marker） |
| **Contract basis** | `ch_m4a_audio_production.md` §8（preflight step 5）；`docs/milestones/M4.md` §6.4 條款 4 |
| **Timeout** | `--timeout-seconds 600` |
| **Evidence** | runner acceptance result card；額外欄位 `test_id`、`network_attempts=0`、`downloader_calls=0`、`session_result` |
| **Pending** | 正式 Pi 執行前 spec tracker 標 `Pending`；不以 portable mock 或 M4-REG-001 取代；不產生任何 runner `status` 欄位 |

**Required assertions**：

| Case | Assertion |
| :--- | :--- |
| Network namespace disabled | real ASR + TTS + HAL session 在 `ip netns exec <offline-ns>` 或等效隔離下完成 |
| Zero network attempt | 斷言無 DNS query / TCP connect / HTTP request |
| No downloader | `m4a_audio_product.py` 及任何 downloader 未被呼叫；call count = 0 |
| Session PASS | `RESULT.text` nonempty；TTS PCM drain 完成 |

---

## M4A-RES-001 — Core process tree resource / cleanup

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Pi（`rpi` marker）；real LLM combined row 在 Accepted M4b input 前 spec tracker 標 `Pending` |
| **Contract basis** | `docs/milestones/M4.md` §6.4 條款 2 / §6.1；`ch_m4a_audio_production.md` §9 |
| **Timeout** | `--timeout-seconds 600` |
| **Evidence** | runner acceptance result card；額外欄位 `test_id`、`p99_latency_ms`、`peak_system_used_mib`、`orphan_count`；M4a+M4b combined row：spec tracker `Pending` |
| **Pending** | real LLM combined envelope 只在 Accepted M4b 後填入；不得以 POC surrogate 或 M4-REG-001 冒充；`Pending` 不產生任何 runner result |

**Required assertions**：

| Metric | Scope | Assertion |
| :--- | :--- | :--- |
| Latency | Pi（Audio only） | P99 `latency_ms` 記錄於 result card |
| Resource budget | Pi（Audio only） | `system_used_kib = MemTotal - MemAvailable` ≤ 3584 MiB |
| Cleanup | Pi | session 後 `orphan_count=0`；process/thread/fd/temp = 0 |
| Thermal | Pi | CPU throttle 事件記錄（Advisory；不阻擋 Pass） |
| Real LLM combined row | Pi — **Pending** | M4b Accepted 後以同一 runner run 填入 |

---

## M4A-PKG-001 — Offline install / lock / notices

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable review + Pi install |
| **Contract basis** | `ch_m4a_audio_production.md` §8；`requirements/m4a/THIRD_PARTY_NOTICES.md` |
| **Suite marker** | Portable: `not rpi`；Pi: runner `accept` mode |
| **Timeout** | Portable: `--timeout-seconds 60`；Pi: `--timeout-seconds 600` |
| **Evidence** | Portable: runner result + JUnit；Pi: runner acceptance result card（`test_id`、`install_root`、`wheel_count`） |

**Required assertions**：

| Case | Scope | Assertion |
| :--- | :--- | :--- |
| `audio-artifacts.json` schema 完整 | Portable | 每列含 distribution/artifact、version、filename、size、SHA-256、source locator、license/notice reference、target OS/arch/Python、baseline source SHA |
| Reproducible whisper build | Portable review + Pi | `model_spec.md` §3 `build-whisper` command只接受exact source archive與tracked CPU-only CMake options；拒絕network/optional backend、既存output與未列input；記錄product binary SHA-256 |
| Exact product lock | Portable + Pi | `model_spec.md` §3 `install` command使用caller-supplied inputs、`--no-index --no-deps` exact wheels；拒絕system-site resolution與網路下載 |
| Clean offline install — staging→atomic rename | Pi | 先驗全部input，再於same-filesystem new staging安全展開archive／建立隔離venv；完整自驗後才atomic rename；failure刪staging且不覆寫既有install |
| Wheel/artifact inventory exact match | Pi | 實際安裝wheel、native binary、VAD/model/acoustic/Vocos及unpacked components與lock完全一致；無多餘或缺少 |
| THIRD_PARTY_NOTICES.md 完整 | Portable review | runtime、whisper.cpp／Whisper/model repo、Silero、Matcha、Vocos、acoustic archive embedded components及所有dependency均有license/notice entry |
| Matcha Accepted Risk 明列 | Portable review | `THIRD_PARTY_NOTICES.md` 明確標注 Matcha / Vocos 授權風險 |

---

## M4A-INH-001 — POC → Product inheritance / delta index

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Evidence review（Tester 核對 `docs/outsource/evidence/<M4-delivery>/m4a/inheritance.json`）+ Portable（generator schema regression） |
| **Contract basis** | `ch_m4a_audio_production.md` §10；`docs/milestones/M4.md` §6.4 條款 2 |
| **Suite marker** | Generator schema test: `not rpi`；Evidence review: Tester 手動核對 |
| **Timeout** | Portable generator test: `--timeout-seconds 60` |
| **Evidence** | Portable: runner result + JUnit；Evidence review: Tester 簽核紀錄 |
| **Pending** | 正式 `inheritance.json` 只在 Gate 3 完成後由 Tester 產生；開發期間只跑 generator schema regression |

**Locator resolver seam（T10）**：

Portable tests 針對單一 injected locator resolver 驗以下 cases：

| Case | Assertion |
| :--- | :--- |
| Valid local bytes | resolver 取得 content；`sha256(content) == poc_sha256`；accepted |
| Missing file | resolver 失敗；fail closed |
| Unreadable file（permission denied） | resolver 失敗；fail closed |
| Directory instead of file | resolver 失敗；fail closed |
| Wrong content（content OK, wrong hash） | `sha256(content) != poc_sha256`；fail closed |
| Non-empty but missing content | 非空字串 locator 但 resolver 無法取得 content | fail closed；單純非空字串不通過 |

Formal Tester review對核准local file或Git-controlled `<repo>@<40hex>:<path>` locator使用同一
content-hash語意；revision-moving branch、無commit identity或未知scheme一律fail closed。

**Inheritance identity（T11）**：

| Condition | Assertion |
| :--- | :--- |
| P1～P12 及 Audio internal M4 20-session / failure / offline 逐列涵蓋 | inheritance.json 每列含 `area`、`poc_delivery_id`、`accepted_audio_sha`、`poc_locator`、`poc_sha256`、`classification`、`inheritance_reason`、`product_sha`、`delta_test_id`、`delta_result`、`result_locator` |
| `accepted_audio_sha` exact value | 每列 `accepted_audio_sha` == `5694ead4ba6be928fdb4dbdf6da7155b214d72bd` |
| `poc_sha256` 格式與內容 | 64 lowercase hex；`sha256(resolved locator content) == poc_sha256` |
| `delta_test_id` 屬本規格 13 ID | exact member of `{M4A-CFG-001,M4A-LOCK-001,M4A-IPC-001,M4A-ASR-001,M4A-ASR-002,M4A-ASR-003,M4A-TTS-001,M4A-TTS-002,M4A-PRIV-001,M4A-OFF-001,M4A-RES-001,M4A-PKG-001,M4A-INH-001}` |
| `delta_result` 合法值 | 屬 `PASS`、`FAIL`、`BLOCKED` 之一 |
| `delta_result=PASS` 時result locator可解析 | `result_locator` resolver成功取得正式result content，且其中candidate SHA／Test ID／status與本列相符；非空字串不足以通過 |
| All `product_sha` identical | 每個值為40 lowercase hex；所有列相同，且等於外部指定frozen candidate SHA |
| `product_sha` 非 HEAD-derived | 斷言 generator 不讀 `git rev-parse HEAD` 或等效 |
| 無裸「沿用 POC」 | `inheritance_reason` 含具體 delta_test_id 或明確技術理由；純「沿用POC」fail closed |
| Generator 不寫正式 evidence | fast loop 使用 temp output；不寫 `docs/outsource/evidence/` |
| 缺欄 / 混 SHA / locator 不存在 | generator fail closed |
| Wrong `accepted_audio_sha` | fail closed |
| Mixed `product_sha`（不同列不一致） | fail closed |

---

## M4a 里程碑結論欄位

M4a 子 gate 結論文件必須包含（由 Tester 填入，引用 runner 標準欄位）：

| 欄位 | 說明 |
| :--- | :--- |
| `candidate_sha` | 40-character product delivery SHA；M4a / M4b / M4c 共用同一 SHA |
| `portable_run_id` | portable matrix 的 run ID（三版本共用） |
| `portable_matrix_index` | `<portable-root>/matrix-index.json` 路徑（runner 產生） |
| `pi_acceptance_run_id` | M4a target acceptance 的 run ID（不得混用 debug run ID） |
| `pi_result_locators` | M4a ASR / TTS / HAL 各項 Pi acceptance result card run-root-relative locator |
| `inheritance_index_locator` | `docs/outsource/evidence/<M4-delivery>/m4a/inheritance.json` |
| `offline_result_locator` | M4A-OFF-001 acceptance result card locator |
| `m4a_res_audio_only_locator` | M4A-RES-001 Audio-only row acceptance result card locator |
| `m4a_res_combined_locator` | M4A-RES-001 combined row（M4b Accepted 後填入，否則填 `Pending`） |

正式 target result 使用單一 `pi_acceptance_run_id`，不拼接多個 run ID；
debug run ID 不得列入里程碑結論。

---

# M4b Gate 3 測試規格

## 概述與範圍

本章節定義 M4b 子 gate 的 Core Gate 3 驗收標準，共 15 個 Test ID。
測試覆蓋來源為 `docs/implement/ch_m4b_llm_production.md`（簡稱 ch_m4b）、
`docs/protocol.md` §4 / §6、`docs/model_spec.md` §6、
`docs/milestones/M4.md` §6.2 / §6.4。

**M4b Gate 3 通過條件**：Core Tester 對 Core product exact SHA 完成可攜矩陣（CPython 3.11 /
3.12 / 3.13 各 0 Fail / Blocked / Skip / XFail）與 Pi target acceptance（單一 run ID），
Designer final review 無 Blocking，才可標記 M4b 子 gate Accepted。POC waiver 不取代
Core product PASS；機器 P9 / P10B FAIL 與 User waiver 分欄保存，不得混為 Core PASS 欄位。

> **注意**：M4b 與 M4a 共用 `candidate_gate.py` runner contract（命令形狀、result schema、
> Privacy Domain 分離語意）；本章 T1–T3 / T9 定義直接沿用 M4a 規格同名節，不重複抄錄。
> M4b portable suite marker 統一使用 `not rpi`；Pi target suite marker 使用 `rpi`；
> evidence 套件以 `m4b` 子目錄區分。

### M4b formal suite 與 timeout 收斂

M4b 對 T1 的 suite placeholder 固定替換如下，不得沿用 M4a-only suite：

| T1 placeholder | M4b exact value | 必含範圍 |
| :--- | :--- | :--- |
| `<m4a-portable-suite>` | `tests/m4b_portable_suite.txt` | 本章所有 Portable case，加上受 M4b composition 影響的 M4a protocol / lifecycle regression |
| `<m4a-rpi-suite>` | `tests/milestones/test_m4_local_voice.py` | 沿用M4 §6.4 canonical target suite並擴充本章所有Pi-scoped Test ID；每個required M4B card都在同一次pytest execution產生 |

三個 portable command 各使用 runner-level `--timeout-seconds 300`；唯一正式 Pi `accept`
command 使用 runner-level `--timeout-seconds 9000`。下列各 Test ID 的 `Case watchdog` 是該測項
內部的 bounded timeout，不是第二次 `candidate_gate.py accept`，也不得用多個正式 result 拼接 PASS。
`tests/m4b_portable_suite.txt`與`tests/milestones/test_m4_local_voice.py`均為candidate protected input；
前者必須逐行列出tracked test file，後者須收集所有Pi-scoped ID且不得以selection條件漏收。
Portable runner regression另須證明M4b target suite取得caller-supplied candidate SHA、acceptance run ID、
card root及preflight locator，card finalization沿用T2且不從HEAD推導identity；timeout／failure只產一份
formal Fail result與raw logs，不留下可被後續accept重用的Pass card。
正式acceptance成功時，所有`M4B-`prefix card的subset須exact等於
`{M4B-RDY-001,M4B-GEN-001,M4B-OUT-001,M4B-P5-001,M4B-CAN-001,M4B-REC-001,`
`M4B-HIST-001,M4B-PRIV-001,M4B-OFF-001,M4B-RES-001,M4B-PKG-001}`；缺卡、重複卡或
額外unknown M4B card均Fail。canonical M4 suite既有或composition-required的M4A card可共存，但不得
代替任何M4B card。`M4B-LOCK-001`只由同run preflight與portable result證明，CFG／IPC／INH則由
portable matrix／evidence review證明，不虛構Pi card。

---

## M4B-CFG-001 — Config strict equality / factory isolation

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable |
| **Contract basis** | `ch_m4b` §7；`ch10_config.md` LLMConfig shape |
| **Suite marker** | `not rpi` |
| **Case watchdog** | 60 秒；formal portable runner 仍使用本章統一的 300 秒 suite timeout |
| **Evidence** | runner `result.json` + JUnit；`counts.failed=skipped=xfailed=0` |

**Config value cases（table-driven）**：

| Case | Input | Expected outcome |
| :--- | :--- | :--- |
| `litert_lm` valid — exact values | `driver="litert_lm"`；`profile_id="litert-lm-v0.16.0-pi-g2b-r5"`；四個 absolute path 均存在；timeout / recycle 值完全符合 §7 | `LLMConfig` 建立成功 |
| `mock` driver | `driver="mock"`；四個path與`profile_id`皆None | 成功；不讀lock、不import native runtime、不建workdir、不啟用target sampler |
| Unknown driver | `driver="gemma"` 或其他非 `mock`/`litert_lm` | `ConfigValueError`；不 fallback |
| Wrong `profile_id` | `profile_id` 不等於 `"litert-lm-v0.16.0-pi-g2b-r5"` | `ConfigValueError` |
| YAML explicit locked recycle values | YAML明列`recycle_max_inference_attempts=8`、`recycle_owner_pss_delta_mib=48`、`recycle_min_mem_available_mib=768` | `LLMConfig`建立成功；與省略欄位時的locked defaults完全相同 |
| Wrong `recycle_max_inference_attempts` | 以7／9代表低於／高於8的mutation | `ConfigValueError` |
| Wrong `recycle_owner_pss_delta_mib` | 以47／49代表低於／高於48的mutation | `ConfigValueError` |
| Wrong `recycle_min_mem_available_mib` | 以767／769代表低於／高於768的mutation | `ConfigValueError` |
| Wrong `generation_timeout_seconds` | 數值≠15.0 | `ConfigValueError` |
| Wrong `terminal_grace_seconds` | 數值≠2.0 | `ConfigValueError` |
| Wrong `child_ready_timeout_seconds` | 數值≠45.0 | `ConfigValueError` |
| Wrong `rebuild_ready_timeout_seconds` | 數值≠10.0 | `ConfigValueError` |
| Wrong `child_terminate_timeout_seconds` | 數値≠2.0 | `ConfigValueError` |
| Wrong `child_kill_wait_timeout_seconds` | 數值≠1.0 | `ConfigValueError` |
| Wrong Reasoner abort timeout | `cancel.abort_timeout_seconds.by_kind.cognition.reasoner` 缺失或≠0.5 | `ConfigValueError`；不得改用15秒generation timeout |
| Recovery timeout too short | `resource.recovery_timeout_seconds` 無法涵蓋10秒rebuild READY與舊child最長cleanup | `ConfigValueError`；repository product default維持30秒 |
| Outer / child / grace 分層 | injected clocks捕捉`cognition.reason_timeout_seconds`、15秒generation與2秒terminal grace | 三個獨立timer依序作用；Reasoner outer timeout不得取代child deadline或terminal-only grace |
| Invalid real path | 四個real path任一為relative path、directory或missing file | `ConfigValueError`；native import / child spawn / workdir / sampler / RM registration皆為0 |
| YAML recycle value drift | 三個合法欄名任一值偏離8／48／768 | `ConfigValueError`；native import / child spawn / workdir / sampler / RM registration皆為0 |
| Unknown YAML recycle key | 與三個合法欄名不同的未知`recycle_*`欄名 | `UnknownConfigKey`；上述side effect皆為0 |
| Lazy import before factory | `driver="litert_lm"`；factory 尚未呼叫 | `sys.modules` 中無 `litert_lm` / `litert_lm_api` |

**Factory narrow interface cases**：

| Case | Assertion |
| :--- | :--- |
| Public adapter surface | `LLMEngineAdapter` exact async methods為`start/stop/abort/force_abort/generate(value: ReasoningInput)`；`generate`只回`LLMGeneration`，不得回raw text／iterator |
| Public value surface | `LLMGenerationMetrics` exact 7 fields、`LLMGeneration` exact `response/metrics`、`LLMResourceSample` exact `owner_pss_bytes/mem_available_bytes`；皆為immutable value，不帶session/prompt/path |
| Factory signature | `make_llm_adapter(cfg, *, schedule_recovery=None, wait_recovery=None, resource_sampler=None)`；三個port皆keyword-only，不接受額外owner／fallback參數 |
| `schedule_recovery` / `wait_recovery` / `resource_sampler` 三者皆非 None → real branch | factory進入real分支；lazy import`litert_lm.adapter`；shape/path/lock parse先於native import、child spawn、workdir、sampler與RM registration |
| Real driver任一介面為 None | `ConfigValueError`；zero side effect；不得silent fallback成mock |
| `mock` 下三者皆須為 None | 任一非 None 時 `ConfigValueError` |
| `ResourceSpec` ownership — real | composition把factory回傳的同一adapter identity同時登記為`ResourceSpec.instance`與`recovery_hook` owner；`key="backend.cognition.reasoner.llm"`；`recoverable=True` |
| `ResourceSpec` — mock | `recoverable=False`；force-abort report 為空 |

**Config／spawn isolation cases**：

| Case | Assertion |
| :--- | :--- |
| YAML覆寫locked identity | candidate/runtime/model/config checksum、source、license或fallback任一key → `UnknownConfigKey`／`ConfigValueError`；side effect = 0 |
| YAML覆寫frozen runtime profile | 128/128/1024、temperature、top-p、threads、deadline或offline flag任一key → fail closed；不得只靠整檔hash跳過逐欄cross-check |
| Spawn environment | injected spawn capture：`PYTHONNOUSERSITE=1`、bytecode write disabled、移除`PYTHONPATH/PYTHONHOME/LD_PRELOAD`；`LD_LIBRARY_PATH`若存在只含verified closure |

---

## M4B-LOCK-001 — Product lock / artifact identity

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi preflight |
| **Contract basis** | `ch_m4b` §8；`requirements/m4b/llm-artifacts.json` schema；`model_spec.md` §6.2 |
| **Suite marker** | Portable: `not rpi`；Pi: `preflight` command（runner preflight mode） |
| **Case watchdog** | Portable 60秒；Pi preflight外層watchdog 120秒 |
| **Evidence** | Portable: runner result + JUnit；Pi protected raw evidence為runner `preflight.json`（`checksums.m4b_artifact_manifest`、`m4b_python_abi_attestation_sha256`、`m4b_install_inventory_sha256`）與`m4b_llm_product.py preflight` sanitized JSON；兩者的candidate SHA、ABI digest與install-inventory digest須一致。公開欄位只保存digest／status，不公開exact package tuple或absolute private product path |

**Lock schema negative matrix（table-driven）**：

| Case | Injection | Expected outcome |
| :--- | :--- | :--- |
| Missing lock file | `artifact_lock_path` 不存在 | fail closed；child spawn = 0；native import = 0；workdir = 0 |
| Unreadable lock file | `artifact_lock_path` permission denied | fail closed；同上 |
| Extra unknown key | lock JSON 含額外 top-level key | fail closed；side effect = 0 |
| Missing required key | 任一 `lock`/`poc_reference`/`candidate`/`runtime`/`model`/`product_profile`/`runtime_closure`/`licenses` object 缺失 | fail closed |
| Nested extra / missing key | 上述任一object或runtime manifest entry增加unknown key，或刪除required field | fail closed；side effect = 0 |
| Wrong `schema_version` | `schema_version` ≠ 1 | fail closed |
| Wrong `protocol_version` | `protocol_version` ≠ `"snowboard.llm/1"` | fail closed |
| Wrong POC authority | final ACK ID、execution/closure/publication full SHA、R3 manifest ID、formal evidence ID或sanitized digest任一不符 | fail closed |
| Wrong `candidate_id` | 不等於 `CAND-LRT-G4E2B-MOBILE-R1` | fail closed |
| Wrong `pairing_revision` | 不等於 `litert-lm-v0.16.0-pi-g2b-r5` | fail closed |
| Wrong platform | 不等於 `pi-debian13-aarch64` | fail closed |
| Wrong runtime identity | API version、source commit、wheel filename/size、SPDX任一不符 | fail closed |
| Wrong runtime wheel SHA-256 | 不等於 `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` | fail closed |
| Wrong native library SHA-256 | 不等於 `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4` | fail closed |
| Wrong model provenance | source repository/revision、filename、embedded quantization或SPDX任一不符 | fail closed |
| Wrong model SHA-256 | 不等於 `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` | fail closed |
| Wrong model size | 不等於 `2588147712` | fail closed |
| Wrong `config_sha256` | 不等於`c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e`，或內容任一frozen欄不符 | fail closed |
| Wrong Pi protocol schema SHA-256 | 不等於`e1af3bc5f83f1456d393d30acd9bcf9b9a8a7f91cbdcbe7aa0136a17c275301e` | fail closed |
| Wrong prompt/response schema SHA-256 | 不等於`aca834bb448f88dfb403c74c427b5462922ccf23f4f26c1944c47d5731522de6`／`4be45ee60f603d7349ff5fb29b667d6e59970dd0be3ce9176c03e923e0a6fca2` | fail closed |
| Wrong pre-warm prompt SHA-256 | 不等於`4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d` | fail closed |
| Wrong frozen profile value | config-schema digest、128/128/1024、temperature 0.0、top-p 1.0、4 threads、任一deadline或offline/fallback flag不符 | fail closed |
| Wrong runtime closure | manifest locator／computed digest不符，或14-file product-owned LiteRT-LM distribution/native payload任一relative path／size／digest不符、extra／missing／symlink／placeholder | fail closed；tracked manifest不得含target-owned CPython launcher、stdlib、`lib-dynload`、venv launcher或`pyvenv.cfg` |
| Wrong license locator | runtime/model source metadata、Apache-2.0 license或notice locator缺失／不符 | fail closed |
| Absolute path in lock body | lock JSON 含 `/tmp/` 或其他 absolute deployment path | fail closed |
| Valid lock — exact Accepted identity | 完整正確 lock；`driver="litert_lm"` | Portable: factory 成功；Pi: product preflight `status="Pass"`、`runtime_file_count=14`，runner `preflight.json` `status="Pass"`且`checksums.m4b_artifact_manifest.sha256`存在並綁定該product preflight bytes |

**Target CPython ABI boundary（table-driven）**：

| Case | Injection / oracle | Expected outcome |
| :--- | :--- | :--- |
| Exact controlled target ABI | regular、non-symlink、root-owned`/usr/bin/python3.13`；exact `CPython 3.13.5`／`sys.version`；SOABI`cpython-313-aarch64-linux-gnu`；MULTIARCH`aarch64-linux-gnu`；`sys.abiflags=""`；64-bit little-endian；stdlib／platstdlib均為`/usr/lib/python3.13`；glibc identity可取得；五個§8.1 Debian packages皆`install ok installed`、版本皆為同一`3.13.5-*`字串 | install前capture canonical attestation；sorted package tuples、base executable SHA-256及全部ABI欄位形成`python_abi_attestation_sha256` |
| Wrong base interpreter | path非exact `/usr/bin/python3.13`、missing、symlink、non-regular或owner非root | staging／native import／child spawn／network side effect全為0 |
| Wrong Python ABI | patch／exact `sys.version`、SOABI、MULTIARCH、abiflags、word size或endianness任一不符 | fail closed；side effect同上 |
| Wrong stdlib boundary | stdlib或platstdlib不等於`/usr/lib/python3.13`，或dynamic stdlib extension逃出其`lib-dynload` | fail closed；不得把該target bytes寫入tracked manifest |
| Wrong Debian package set | 五個required package任一missing、非installed、duplicate、版本非`3.13.5-*`或五者version字串mixed | fail closed；side effect同上 |
| Target ABI drift | install後base executable digest、package tuple／revision、exact Python identity、stdlib root或glibc任一改變 | preflight及acceptance-start均Fail；child spawn=0；舊PASS preflight/card不得重用 |

**Pi preflight assertions**：

| Case | Assertion |
| :--- | :--- |
| Exact product SHA 與 frozen candidate 吻合 | `candidate_sha` 欄位符合外部指定 40-hex |
| Protected paths clean | 依runbook精確檢查`src/`、`tests/`、candidate/acceptance runner與workflow、dependency/lock/package metadata及runner實際讀取的config contract；一般`docs/`異動不阻擋 |
| Exact target platform | Raspberry Pi 5 4 GB、Debian 13 aarch64、CPU profile與上述exact CPython 3.13.5 ABI attestation全數吻合；錯一項即preflight fail |
| Runtime manifest — exact product payload | `llm-runtime-rpi-cp313.json`只列14個product-owned LiteRT-LM distribution/native file；每個entry以open-no-follow／regular-file方式streaming SHA驗證；symlink／extra／missing或含target-owned interpreter／stdlib／venv files → fail closed |
| ABI reconciliation | product preflight重算的`python_abi_attestation_sha256`須與install inventory及runner `m4b_python_abi_attestation_sha256`完全相同；install inventory digest亦須與runner欄位相同 |
| System-site boundary | `-I`、`PYTHONNOUSERSITE=1`且移除`PYTHONPATH/PYTHONHOME/LD_PRELOAD`；允許`/usr/lib/python3.13` stdlib／`lib-dynload`與platform ABI libraries，但拒絕system/user third-party `site-packages`／`dist-packages`；`litert_lm`與native library只能從verified product site-packages載入 |
| Target sampler capability | child啟動前read-only證明`/proc/meminfo`與owner `smaps_rollup`可讀；缺任一能力即preflight fail，不啟動acceptance |

---

## M4B-IPC-001 — `snowboard.llm/1` wire contract

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable |
| **Contract basis** | `protocol.md` §4.4；`ch_m4b` §3.1 |
| **Suite marker** | `not rpi` |
| **Case watchdog** | 60秒；formal portable runner仍使用本章統一的300秒suite timeout |
| **Evidence** | runner result + JUnit；`counts.failed=skipped=xfailed=0` |

**Frame / schema cases（table-driven）**：

| Category | Case | Expected outcome |
| :--- | :--- | :--- |
| Schema | 任何 frame 缺 `protocol_version` 或值 ≠ `"snowboard.llm/1"` | protocol failure；parent TERM / KILL / waitpid；不轉 P5 |
| Schema | extra key in any frame | protocol failure |
| Schema | READY / GENERATE / CANCEL / RESULT / CANCELLED / ERROR / PING / PONG / SHUTDOWN / SHUTDOWN_ACK任一缺required key，或出現unknown `type` | protocol failure；不得接受partial frame |
| Schema | GENERATE／CANCEL任一required value為wrong type，或含missing／extra key | receiver fail closed；不得呼叫inference／native cancel；parent注入測試須收斂child並視為fatal protocol failure |
| Schema | invalid UTF-8 / JSON | protocol failure |
| Bounds — control line | 恰 16 KiB（含 `\n`）— inclusive max | accepted |
| Bounds — control line | 16 KiB + 1 byte — exceeded | protocol failure |
| Fragment / coalesce | fragmented read（分批到達） | 正確 reassemble |
| Fragment / coalesce | 兩個完整JSON control line在同一 `read` 到達 | 依newline正確分離；不得合併object或遺失第二個frame |
| Control | PING → PONG | exact-key PING在合法狀態得到exact-key PONG；PONG `state="READY"`；兩者皆無request ID |
| Control | SHUTDOWN → SHUTDOWN_ACK | exact-key exchange後bounded child exit / waitpid / stream與workdir cleanup |
| Control | GENERATING時收到SHUTDOWN | 不直接shutdown；parent須先走cancel convergence，child不emit假的SHUTDOWN_ACK |
| Request ID format / length | 不符合`^llm\.\d+\.\d+$`或UTF-8長度超過128 | protocol failure |
| Request ID monotonicity | 同一 child 內 counter 不嚴格遞增 | protocol failure |
| Request ID — duplicate | 重用已使用過的 request_id | protocol failure |
| Request ID embeds private data | request_id 含 session ID / prompt fragment | fail closed（構造測試） |
| Duplicate terminal | 同 request_id 出現第二個 RESULT / CANCELLED / ERROR | protocol failure |
| Late terminal | terminal 後同 request_id 再送任何 frame | protocol failure |
| Wrong request_id in terminal | terminal request_id 與 active request 不符 | protocol failure |
| Direct malformed GENERATE while active | 直接繞過parent admission向child注入第二個GENERATE | child回`BUSY`（`state="GENERATING"`）；parent將此違約frame映射為fatal protocol failure，不得拿本case替代GEN的zero-write assertion |
| EOF | child pipe 提前 EOF | parent termination proof；不轉 P5 |
| Privacy — stdout / stderr / caplog | 掃描 Domain B sentinels | 無 perception text、response、tool args、credential、private path |

**Child authority boundary**：

| Injection | Assertion |
| :--- | :--- |
| Child／runtime嘗試listen socket或network fallback | fail closed；listener/network attempt不成為產品能力；由OFF evidence計數為0 |
| Model回傳valid `tool` intent | child只回mapping；ToolRegistry handler／validator／execution call count = 0，仍由parent Reasoner處理 |
| Child嘗試開Audio／Display HAL | HAL open call count = 0；跨模組side effect視為contract failure |
| Frame／child CLI夾帶任意artifact path | exact-key／allowlist拒絕；實際artifact path只來自已驗lock與`LLMConfig` |
| Process ownership | spawn使用`start_new_session=True`且top-level child PID=PGID；descendant不得逃離owner process group |

**GENERATE canonical input cases**：

| Case | Assertion |
| :--- | :--- |
| Perception cardinality layer恰16 — inclusive max | isolated list-bound validator判定未超過16；full PromptBuilder仍須另套kind enum／duplicate invariant，不得把16筆duplicate資料宣告產品success |
| 三個unique kinds（listen/read/look） | full canonical PromptBuilder accepted；這是目前kind enum下可達的產品success上限 |
| 17 perception — exceeded | `ReasoningInputContractError`；child side effect = 0；不得截斷成16筆 |
| perception text 恰 4096 code points | accepted |
| perception text 4097 code points | `ReasoningInputTooLarge`；child side effect = 0 |
| 渲染後 `> 16 KiB` UTF-8 | `ReasoningInputTooLarge`；child side effect = 0 |
| `None` text → `""` / status 保留 | `None` 映射為空 string；`status` 不改變 |
| `pending_message_count` 為 bool | `ReasoningInputContractError` |
| `pending_message_count` 為float／string／None | `ReasoningInputContractError` |
| `pending_message_count < 0` | `ReasoningInputContractError` |
| `input` / perception 含extra或private key | session、turn、correlation、pending message ID、`extra`或control/handler任一存在即`ReasoningInputContractError`；child side effect = 0 |
| invalid perception `status` | 非`ok/timeout/error`即`ReasoningInputContractError` |
| unknown capability perception／action | `ReasoningInputContractError`；不得保留或fallback成已知kind |
| `rest` 缺席 | `ReasoningInputContractError` |
| duplicate perception kind | `ReasoningInputContractError` |
| perception / action未依canonical order或有duplicate action | sender canonicalize為`listen/read/look`與`speak/tool/rest`；receiver語意不依JSON member order |
| tool 存在但 `tool` action 缺席（或反之） | `ReasoningInputContractError` |
| `speak` / `tool` 存在但 available perceptions 為空 | `ReasoningInputContractError` |
| tool name duplicate / order錯誤 | tool依name排序且name唯一；違約為`ReasoningInputContractError` |
| tool description空白或`input_schema`不是validated closed JSON object | `ReasoningInputContractError` |
| handler / validator附在tool或input | `ReasoningInputContractError`；private callable/control不得encode |
| sort_keys / compact separators / ensure_ascii=False | 以 injected writer capture 驗 encode 參數 |
| Empty private content但static tool projection已超過16 KiB | startup preflight fatal；child spawn／write = 0；不得延後成user-turn P5 |

**RESULT exact keys / metrics bounds cases**：

| Case | Assertion |
| :--- | :--- |
| 缺 `metrics` | parent視為protocol failure；不建立`LLMGeneration`、不轉P5 |
| RESULT缺required key或多extra key | parent protocol failure；不建立`LLMGeneration` |
| 任一 metric 為 NaN / Infinity | protocol failure；不建立`LLMGeneration` |
| 任一 metric 為bool | protocol failure；bool不得當作int/number |
| `init_ms`或`ttft_ms` < 0 | protocol failure |
| 任一token rate ≤ 0 | protocol failure |
| `prefill_tokens` 0 或 129 | protocol failure |
| `decode_tokens` 0 或 129 | protocol failure |
| `kv_tokens` 0 或 1025 | protocol failure |
| `prefill_tokens` 1 和 128（boundary success） | accepted |
| `decode_tokens` 1 和 128（boundary success） | accepted |
| `kv_tokens` 1 和 1024（boundary success） | accepted |
| 15 秒 generation deadline 後收到 RESULT（在 2 秒 grace 內） | 仍是 timeout，不得轉 Pass |
| 2 秒 grace 後任何 terminal | protocol failure |

**ERROR code mapping**：

| Error code | State | Expected parent action |
| :--- | :--- | :--- |
| direct-injected `BUSY` | `GENERATING` | protocol failure（desync）；fatal；只驗child defensive mapping，不代表parent single-flight admission合規 |
| `INVALID_REQUEST` + `READY` | `READY` | Reasoner 可翻譯 P5 |
| direct-injected `INVALID_REQUEST` | `GENERATING` | active request期間直接注入時為protocol failure（desync）；fatal；不得P5且不得改變原active request；只驗child defensive mapping |
| `TIMEOUT` + `READY` | `READY` | cleanup proof 後 Reasoner 可 P5；否則 fatal |
| `GENERATION_FAILED` + `READY` | `READY` | cleanup proof 後 Reasoner 可 P5 |
| `CANCEL_FAILED` + `FATAL` | `FATAL` | fatal；Level 2 |
| `PROTOCOL_ERROR` + `FATAL` | `FATAL` | fatal；Level 2 |
| Unknown / unlisted code | — | protocol failure；fatal |

**M4a protocol / lifecycle regression guard**：

`tests/m4b_portable_suite.txt`須明列M4b實作直接影響的既有M4a framed-child、process-group、
cancel／recovery與candidate-runner tests；三個Python minor的JUnit均須0 Fail / Skip / XFail。
這是`M4B-IPC-001`的required assertion，不得只在inheritance文字聲稱「M4a仍通過」。

---

## M4B-RDY-001 — Startup / pre-warm / READY identity

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable double + Pi |
| **Contract basis** | `protocol.md` §4.1；`ch_m4b` §4；`model_spec.md` §6.3 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Case watchdog** | Portable 60秒；Pi 300秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`engine_load_latency_ms`、`ready_latency_ms`、`prewarm_latency_ms`、`prewarm_prompt_sha256`、sanitized六欄`ready_identity`） |

**Startup state / admission cases**：

| Case | Scope | Assertion |
| :--- | :--- | :--- |
| Startup exact state trace | Portable | `STOPPED→AUTHENTICATING→STARTING→ENGINE_LOADED→PREWARMING→READY`；不得跳過authenticate/pre-warm/baseline或提前admit |
| Non-READY parent admission | Portable | 以`AUTHENTICATING／STARTING／ENGINE_LOADED／PREWARMING`逐態呼叫`generate()`皆local fail closed；child GENERATE wire write與inference call count皆為0；不 emit／admit READY且`start()`不return |
| Pre-warm failure → 不 emit READY | Portable | inject pre-warm Conversation return error；child terminate / parent TERM→KILL→waitpid；`start()` raise；不 READY；無 orphan |
| Pre-warm prompt SHA-256 | Portable | injected prompt capture；`sha256(prompt_bytes) == "4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d"` |
| Pre-warm public input exact value | Portable | capture的structured input exact等於§3.2固定JSON；不得加入history、scored example或private marker |
| Pre-warm 使用同一 renderer / tokenizer / constrained-output path | Portable | injected renderer call capture；與 production GENERATE 使用同一 code path；不 fake |
| Pre-warm Conversation 確實 close / reference discard | Portable | injected Conversation mock；`close()` call count ≥ 1；output / KV reference 設為 None |
| Pre-warm output有效後丟棄 | Portable + Pi | dynamic schema PASS且decode tokens > 0後才算pre-warm成功；result不存入任何field、不進log/evidence |
| READY exact keys | Portable + Pi | exact keys：`type / protocol_version / state / identity`；identity exact keys：`candidate_id / pairing_revision / platform / runtime_sha256 / model_sha256 / config_sha256` |
| READY identity — `candidate_id` mismatch | Portable + Pi controlled | parent TERM → bounded wait → KILL → waitpid；IPC / workdir 清除；`start()` raise |
| READY identity — `pairing_revision` mismatch | Portable + Pi controlled | 同上 |
| READY identity — `platform` mismatch | Portable + Pi controlled | 同上 |
| READY identity — `runtime_sha256` mismatch | Portable + Pi controlled | 同上 |
| READY identity — `model_sha256` mismatch | Portable + Pi controlled | 同上 |
| READY identity — `config_sha256` mismatch | Portable + Pi controlled | 同上 |
| 每個 mismatch 後 next-success | Portable | 同一 owner 重建全新 child 並完成一次 generation |
| Idempotent `start()` — 已在 READY | Portable | 第二次 `start()` no-op；child spawn count = 1 |
| Nonterminal `start()` reentry | Portable | AUTHENTICATING／STARTING／ENGINE_LOADED／PREWARMING任一狀態重入皆拒絕；不得spawn第二個child |
| Startup timeout／invalid first frame | Portable | TERM→bounded KILL→waitpid、IPC/workdir cleanup後`start()` raise；不留下半啟動child |
| Initial resource baseline barrier | Portable + Pi | pre-warm cleanup、READY identity與完整owner sample都成功且baseline只建一次後`start()`才return |
| Initial baseline sample failure | Portable | missing field、unreadable owner、bool、negative逐列注入；parent不得向caller emit／admit READY或讓`start()`return，須TERM→bounded KILL→waitpid並清除IPC／reader／fd／workdir；orphan=0，隨後同owner next-start成功 |
| Rebuild READY（recovery hook） | Portable | hook 只在新 child 完成 `INFERENCE_READY` 後原子切換 reference；舊 child reference 清除 |
| Pi READY identity exact values | Pi | `candidate_id = "CAND-LRT-G4E2B-MOBILE-R1"`；`pairing_revision = "litert-lm-v0.16.0-pi-g2b-r5"`；`platform = "pi-debian13-aarch64"`；`runtime_sha256 = "5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00"`；`model_sha256 = "181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c"`；`config_sha256 = "c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e"`；card保存sanitized六欄READY identity、public pre-warm digest與分離的engine-load/pre-warm timing |
| Model full hash 在 spawn 前完成 | Portable | injected hash capture；不在 READY path 重做 |
| Native library SHA-256 在 child 驗證 | Pi | loaded native library open-no-follow / regular-file / `sha256 == "9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4"` |

---

## M4B-GEN-001 — Single-flight generation / persistent Engine / fresh Conversation

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable double + Pi |
| **Contract basis** | `ch_m4b` §4（步驟 4–5）；`protocol.md` §4.2 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Case watchdog** | Portable 60秒；Pi 300秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`child_pid`、`engine_load_count`、`conversation_count`、`init_ms`、`ttft_ms`、`prefill_tokens`、`decode_tokens`、`kv_tokens`） |

**Required assertions**：

| Case | Scope | Assertion |
| :--- | :--- | :--- |
| Single-flight：第二個 concurrent `generate()` 回 BUSY | Portable | 第一個generate進行中時，第二個`generate()`不排隊、立即raise `AdapterError(BUSY)`；總GENERATE wire write仍為1、active request identity不變、第一個request只收一個terminal且不受影響；完成後next-success |
| Persistent Engine：連續兩 turn 不重載 | Portable + Pi | Engine / process load count = 1；PID 不變（未觸發 recycle） |
| Fresh Conversation：每 turn 建立新 Conversation | Portable + Pi | 每次generate使Conversation count +1；`close()`在finally執行；Pi card的conversation count與turn count一致 |
| Child completion → READY 狀態 | Portable | terminal 後 child 回 `state="READY"`；parent state machine 轉 READY；下一次 generate 可接受 |
| RESULT metrics違約為fatal protocol failure | Portable | 缺metrics、partial metrics、NaN／bool／越界由table代表；不建立`LLMGeneration`、fallback `LLMResponse` count=0且不轉P5；依IPC/CAN收斂TERM／KILL／waitpid，建立same-key `RecoveryTicket`，replacement後next-success |
| 成功 result 含完整 metrics | Portable + Pi | `init_ms / ttft_ms / prefill_tokens_per_second / decode_tokens_per_second` 全為 finite、non-bool number；`init_ms / ttft_ms ≥ 0`；rates `> 0`；三個token count均為non-bool int且在各自boundary內 |
| Rendered input 恰 128 tokens — boundary success | Portable | injected tokenizer mock；accepted |
| Rendered input 129 tokens — exceeded | Portable | `ReasoningInputTooLarge`；child side effect = 0 |
| Runtime prefill_tokens > 128 | Portable | parent 拒絕 RESULT；走 protocol failure |
| Wire 無 CHUNK / partial output | Portable | injected wire capture；零 intermediate output frame |
| Child background thread 不自行寫 wire | Portable | injected thread monitor；wire write 只來自 control loop |

---

## M4B-OUT-001 — Output schema / marker / allowlist

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4b` §3.2 / §6；`protocol.md` §4.4；`ch09_action_payload.md` |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Case watchdog** | Portable 60秒；Pi 300秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`catalog_case_count`、`schema_pass_count`、`current_marker_exactly_once`、`prior_marker_hits=0`、`forbidden_literal_hits=0`、`tool_handler_calls=0`） |

**Constrained-output catalog（table-driven）**：

| Case | Scope | Expected outcome |
| :--- | :--- | :--- |
| `speak` — valid nonblank text + nonempty next_perceptions | Portable + Pi | `LLMGeneration.response.action_kind == "speak"`；Reasoner validator PASS |
| `speak` — blank text (`""` / whitespace) | Portable | Reasoner P5 fallback |
| `speak` — missing `next_perceptions` | Portable | Reasoner P5 fallback |
| `speak` — `next_perceptions` 含 unavailable perception | Portable | Reasoner P5 fallback |
| `tool` — valid name + object arguments + nonempty next_perceptions | Portable + Pi | Reasoner validator PASS（sealed registry）；Pi只驗tool intent，不執行handler |
| `tool` — invalid dotted name | Portable | Reasoner P5 |
| `tool` — `arguments` 非 JSON object | Portable | Reasoner P5 |
| `tool` — name 不在 capability allowlist | Portable | Reasoner P5 |
| `rest` — empty payload + empty next_perceptions | Portable + Pi | Reasoner validator PASS |
| `rest` — 含非空 payload | Portable | Reasoner P5 |
| `rest` — 含非空 next_perceptions | Portable | Reasoner P5 |
| Empty output（`{}`） | Portable | Reasoner P5 |
| Explicit refusal（模型拒答） | Portable | P5 apology-speak；log 不含 raw output |
| Bad JSON | Portable | P5；log 不含 raw output |
| Unknown `action_kind` | Portable | P5 |
| `action_kind` 在 input 無 available branch | Portable | P5 |
| Top-level missing／extra key或duplicate `next_perceptions` | Portable | strict schema／Reasoner拒絕；P5；不得把partial mapping交付SM |
| Dynamic schema沒有合法branch或constraint provider拒絕 | Portable | startup/pre-request fail closed；unconstrained decode call count = 0 |

**Current-marker / forbidden-marker / prior-marker（catalog）**：

| Case | Scope | Assertion |
| :--- | :--- | :--- |
| current-request marker 在 output exactly-once | Portable + Pi | fixed catalog中marker present且不重複 |
| forbidden literal | Portable + Pi | Portable注入違約output驗Reasoner fail closed；Pi fixed catalog驗forbidden literal absence |
| prior-marker（前一 turn marker） | Portable + Pi | 後一turn output不得出現；違約時Reasoner fail closed／P5 |
| marker failure不得bypass Reasoner validator | Portable | 斷言Reasoner validator call count ≥ 1 |

**Child constrained decoder / Reasoner independence**：

| Assertion |
| :--- |
| Production renderer對non-ASCII structured input產生exact bytes：inner JSON使用`ensure_ascii=True`、`sort_keys=True`、compact separators，外層prefix逐字等於§3.2；不得加入history、scored example或retry text |
| `_build_response_schema` branch order固定`speak`、tool name排序、`rest`；top-level exact keys固定`action_kind/action_payload/next_perceptions` |
| child 自稱 schema-valid 不等於 Reasoner PASS；Reasoner 仍獨立 validate |
| sealed tool registry validator 由 Reasoner 呼叫，不傳入 child |
| PromptBuilder只輸出bounded semantic `ReasoningInput`；selected chat template／raw prompt render call count = 0 |

---

## M4B-P5-001 — P5 fallback / fatal boundary

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4b` §6（步驟 2）；`protocol.md` §4.4 code mapping |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Case watchdog** | Portable 60秒；Pi 300秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`case`、`converged_to`） |

**Recoverable P5 cases**：

| Injection | Scope | Expected convergence | Next-success |
| :--- | :--- | :--- | :--- |
| `INVALID_REQUEST / READY`（rendered input > 128 token） | Portable | `ReasoningInputTooLarge` → Reasoner P5 | 同 child 下一 turn 成功 |
| `GENERATION_FAILED / READY`（cleanup 已證明） | Portable | Reasoner P5；log 不含 raw output | 同 child 下一 turn 成功 |
| `TIMEOUT / READY`（cooperative cancel 成功，Conversation discard 已證明） | Portable + Pi | Reasoner P5；不得與Level 2 destructive timeout混判 | 同 child 下一 turn 成功 |
| Local `ReasoningInputTooLarge`（4097 code points／private projection >16 KiB） | Portable | write與child side effect皆為0；Reasoner P5 | 同 child下一turn成功 |
| Empty / refusal / bad JSON（child wire-valid 但 Reasoner 驗失敗） | Portable | Reasoner P5 apology-speak | 同 child 下一 turn 成功 |

**Fatal cases（不得轉 P5）**：

| Injection | Expected outcome |
| :--- | :--- |
| `CANCEL_FAILED / FATAL` | parent TERM→KILL→waitpid；RM recovery；不 P5 |
| `PROTOCOL_ERROR / FATAL` | 同上 |
| Recovery barrier cleanup 未能證明 | 不 P5；adapter raise sanitized non-P5 failure |
| `ReasoningInputContractError` | 發布一個sanitized `ErrorOccurred`並進ERROR；不P5、不啟動child side effect |
| `BUSY` / desync（single-flight 違約） | protocol failure；fatal；不 P5 |
| Recovery / rebuild 失敗 | `RecoveryFatalError`；Level 3；exit 4；不 P5 |

**No-request RM fatal monitor**：

| Case | Assertion |
| :--- | :--- |
| Background recovery failure 發生時無 active request / SM waiter | `rm.wait_fatal()` main supervision 立即進 Level 3；exit 4；不 unobserved |

---

## M4B-CAN-001 — Cancel / TERM / KILL / waitpid / Level 3

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4b` §5；`protocol.md` §4.3 / §4.4 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Case watchdog** | Portable 60秒；Pi 300秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`case`、`native_cancel_calls`、`worker_joined`、`term_sent`、`kill_sent`、`waitpid_exit_code`、`orphan_count=0`、`recovery_ready`） |

**Cooperative cancel path**：

| Injection | Scope | Assertion |
| :--- | :--- | :--- |
| Reasoner timeout → `abort()` | Portable | 只送一次 CANCEL；等 typed `CANCELLED`；worker joined；Conversation / output / reference discard；child 回 READY；下一 turn 成功 |
| LiteRT-LM `Cancelled` 子類先於 `RuntimeError` 父類捕捉 | Portable | 捕捉順序測試；零 `PytestUnhandledThreadExceptionWarning` |
| CANCELLED 後 Reasoner 可 P5 | Portable | P5 apology-speak；log 不含 raw output |
| Session interrupt / shutdown CANCELLED | Portable | 不 publish fallback Fact |
| Shutdown撞上RECOVERING — cleanup success | Portable | injected recovery hook卡在pre-warm；main呼叫RM-owned`prepare_shutdown()`取消／等待recovery，完整清除partial replacement與舊child後再依reverse order `stop()`；adapter不另取control、不建立第二個recovery batch |
| Shutdown撞上RECOVERING — cleanup exception | Portable | cancellation cleanup raise時，`prepare_shutdown()`與`rm.wait_fatal()`觀察同一latched root cause；`RecoveryFatalError`→Level 3、main exit 4一次；partial replacement／舊child皆無orphan、zero unretrieved-task warning且不建立第二batch |
| Shutdown撞上RECOVERING — cleanup timeout | Portable | cancellation cleanup超過bounded timeout時與exception case相同收斂；TERM／KILL／waitpid清除partial replacement與舊child，exit 4一次且zero unretrieved-task warning |

**Level 2 destructive path**：

| Injection | Scope | Assertion |
| :--- | :--- | :--- |
| Native cancel 未在 500 ms 完成 → Level 2 | Portable | `abort()` pending；Level 1 上限到期 → `force_abort()` |
| `force_abort()` — PGID 全滅 | Portable | SIGTERM PGID → 2 秒 → SIGKILL → 1 秒 → waitpid；state = `DESTROYED`；`ForceAbortReport(destroyed_backends=("backend.cognition.reasoner.llm",))` |
| Orphan / descendant = 0 | Portable | process / thread / fd / workdir = 0，且outer operation task在同一Level 2 timeout內done |
| Next-success after recovery | Portable | RM `rebuild()` 後 READY；same-lock pre-warm；下一 turn 成功 |
| Actual child SIGTERM → waitpid | Pi | real child SIGTERM；waitpid exit proof；recovery READY；一次成功 generation |
| Actual TERM-ignoring child → SIGKILL | Pi | controlled child／descendant忽略TERM；2秒後單次KILL PGID、1秒bounded waitpid；zero orphan後recovery READY |

**Level 3**：

| Case | Assertion |
| :--- | :--- |
| Rebuild / replacement failure或timeout | `RecoveryFatalError` → Level 3；`prepare_shutdown()`／`rm.wait_fatal()`保留同一latched root cause，exit 4恰一次；partial replacement與舊child皆無orphan，不建立第二個recovery batch且無unretrieved-task warning |
| Stable key 驗證 | `ForceAbortReport.destroyed_backends == ("backend.cognition.reasoner.llm",)`；Converger聚合後交同一RM key |

---

## M4B-REC-001 — Resource recycle / RecoveryTicket / same-lock rebuild

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4b` §0.3 / §4 / §5.2；`model_spec.md` §6.4 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Case watchdog** | Portable 60秒；Pi 600秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`trigger_reason`、`generation_count`、`ticket_id`、`resource_samples_locator`、`prewarm_timings_locator`） |

**Trigger threshold cases（raw bytes，table-driven）**：

| Case | Injection | Expected outcome |
| :--- | :--- | :--- |
| `inference_attempts >= 8` — exact boundary | 注入 deterministic sampler；第 8 次 terminal 後 | `RECYCLE_PENDING` 設定；RecoveryTicket 建立；本次 result 仍可交 Reasoner |
| `inference_attempts = 7` — below threshold | 同上 | 不觸發 recycle |
| attempt outcome計數 | success、TIMEOUT、CANCELLED、GENERATION_FAILED各建立一次production Conversation並進inference | 四者都使attempt counter +1；cleanup失敗另走destructive path但不得回滾既有counter |
| `owner_pss_bytes - prewarm_owner_pss_bytes >= 48 * 1024**2` — exact raw-byte delta | 注入baseline與48 MiB delta sampler | trigger |
| `owner_pss_bytes - prewarm_owner_pss_bytes = 48 * 1024**2 - 1` — below | 注入baseline與delta sampler | 不觸發 |
| `mem_available_bytes < 768 * 1024**2` — below | 注入 768 MiB - 1 sampler | trigger |
| `mem_available_bytes = 768 * 1024**2` — at threshold | 注入 768 MiB sampler | 不觸發 |
| 四捨五入 MiB 使比較失準 | 未四捨五入 raw bytes 比較 | 不觸發（精確邊界） |
| Unique owner PSS | PGID leader與多層live descendants含重複發現路徑 | 依unique PID只加總一次`smaps_rollup` PSS；不得只看parent或sum RSS |
| Sample failure（PID消失、任一owner unreadable、missing欄、negative、bool或其他non-int） | 注入 broken sampler matrix | destructive recovery；不沿用前值、不交 result；adapter raise sanitized failure |
| Cleanup／sample無法證明 | injection cleanup或sampler failure | destructive path；不交result；Reasoner只發布一個sanitized`ErrorOccurred`；後續`abort()`不得回cooperative success，`force_abort()`回同一destroyed key且不得預開第二個recovery batch |

**Recycle timing / atomicity**：

| Case | Assertion |
| :--- | :--- |
| 不在 active request 中 recycle | generation 中注入觸發樣本；recycle 只在 terminal 後執行 |
| 先設 `RECYCLE_PENDING` 再交 result | Reasoner 收到 result 前 ticket 已存在 |
| 下一個 `generate()` 等 ticket | `wait_recovery(ticket)` 在 `generate()` 內；不直接 fallback |
| Recovery hook 使用同一 RM key | `schedule_recovery(("backend.cognition.reasoner.llm",))` call capture |
| Recovery hook 重走 authenticate / load / pre-warm | injected child factory；pre-warm call count + 1 |
| Planned recovery先收斂舊child | SHUTDOWN → bounded TERM → bounded KILL → waitpid；IPC/workdir/descendant cleanup完成後才建replacement |
| 只有新 `INFERENCE_READY` 後原子切換 reference | barrier 在 READY 前保持 closed；new child 的 attempt counter 從 0 開始 |
| 舊 child 永不重新 admit | 舊 child DESTROYED 後 generate 不送舊 PID |
| Planned path 可與後續 Action 重疊 | injected timeline；舊 LLM child 先 exit |
| schedule／舊child termination失敗 | 立即Level 3／exit 4；不得另開第二個recovery batch或交付本次result |
| stale／wrong RecoveryTicket | `wait_recovery()`不得解除barrier；fatal原樣傳遞，不admit舊child |

**Baseline**：

| Case | Assertion |
| :--- | :--- |
| Baseline 只建立一次（pre-warm cleanup 後） | injected sampler；baseline call count = 1 per child generation |
| Replacement 建立自己的新 baseline | 第二個 child；baseline 再次呼叫 |

**Pi target recycle observation（至少 2 次 replacement）**：

| Assertion |
| :--- |
| 20 accepted sessions 中觀察到 attempt 8 / attempt 16 各觸發一次 planned recycle |
| 每次 replacement 保留同一 exact lock / pre-warm |
| RecoveryTicket 阻擋下一次 admission 直到 READY |
| evidence 保存 child_generation / trigger_reason / pre-post baseline / ticket / pre-warm timing |

---

## M4B-HIST-001 — History isolation / no hidden KV

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4b` §6（步驟 4）；`protocol.md` §4.2 |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Case watchdog** | Portable 60秒；Pi 300秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`turn_count`、`conversation_count`、`child_pid_stable`、`current_marker_pass_count`、`prior_marker_hits=0`） |

**Five-turn isolation catalog（table-driven）**：

每個case使用fixed current/prior marker catalog：前一turn先植入prior sentinel，後一turn要求目前
marker exactly-once、prior sentinel absent且action/schema符合後一turn的預期。單純「模型剛好沒重複」
不算PASS；每列都須同時有current positive oracle與prior negative oracle：

| Contamination injection | Assertion |
| :--- | :--- |
| Turn 1 perception text 含特定 sentinel | Turn 2 current marker exactly-once且不含該sentinel |
| Turn 1 model 回傳 `tool` action | Turn 2依current catalog回指定`speak/rest`，不沿用Turn 1 tool intent／arguments |
| Turn 1 model 回傳 `speak` payload 含特定詞 | Turn 2 current marker／expected action成立且不含該詞 |
| Turn 1 `next_perceptions` 含 `read` | Turn 2 exact `next_perceptions`只取Turn 2 input allowlist，不因Turn 1加入`read` |
| Turn 1 KV state（inject pre-filled Conversation） | Turn 2為fresh instance、current marker PASS、prior marker absent且不繼承KV |

**Persistent Engine / planned generation switch**：

| Case | Assertion |
| :--- | :--- |
| 未觸發 recycle — child PID 不變 | 五 turn 中 PID stable |
| 觸發 planned recycle — generation 切換僅在預期邊界 | child_generation 在 attempt 8 後 +1；不提前 |

---

## M4B-PRIV-001 — Privacy / no-log contract

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable + Pi |
| **Contract basis** | `ch_m4b` §6（步驟 6）；`protocol.md` §4.1；`ch_m4b` §3.1 codec rules |
| **Suite marker** | Portable: `not rpi`；Pi: `rpi` |
| **Case watchdog** | Portable 60秒；Pi 60秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi: result card（`test_id`、`scanned_locators`、`paths_digest`、`hits=0`）；不得保存absolute private path |

**Domain B sentinel scan（table-driven）**：

| Prohibited content | Sentinel type | Expected outcome |
| :--- | :--- | :--- |
| perception text | 固定 test fixture 字串 | 不出現於 stdout / stderr / caplog / exception message |
| model response / raw output | 固定 test fixture 字串 | 不出現 |
| tool arguments | 固定 test fixture 字串 | 不出現 |
| credential / secret | 固定 test sentinel | 不出現 |
| private work path（absolute） | 固定 test workdir prefix | 不出現 |
| request_id → response reverse-mapping | log 只含不可逆 hash | 無法從 log 反推 response |
| prompt text（pre-warm 或 production） | 固定 pre-warm sentinel | 不出現 |
| codec error 含 perception text | error message 掃描 | 不出現 |

上述sentinel matrix必須分別走success、input rejection、generation error、timeout、cancel、protocol
failure、cleanup failure與recovery failure；每條路徑掃描product stdout/stderr、caplog、exception、
structured product result、telemetry、product raw log及公開前evidence。Formal runner Domain A欄位仍依T9保留，
但不得把private work path、prompt、response或payload放進`command`或test-specific card。

**允許記錄（白名單）**：public digest、timing、token count、child_generation、trigger reason、resource sample 數值、PID / exit code、artifact checksum、request_id 本身（不反查）。

---

## M4B-OFF-001 — Offline isolation / network-zero / no system-site

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Pi（`rpi` marker） |
| **Contract basis** | `ch_m4b` §8；`model_spec.md` §6.2；`docs/milestones/M4.md` §6.4 |
| **Case watchdog** | 600秒；受formal Pi suite-level 9000秒timeout外層限制 |
| **Evidence** | runner acceptance result card；額外欄位 `test_id`、`network_attempts=0`、`downloader_calls=0`、`session_status="Pass"`、`session_result_sha256`；不得保存raw response |
| **Pending** | 正式 Pi 執行前 spec tracker 標 `Pending`；不以 portable mock 或其他離線模擬取代 |

**Required assertions**：

| Case | Assertion |
| :--- | :--- |
| Network namespace disabled | real LiteRT-LM Engine session 在 `ip netns exec <offline-ns>` 或等效隔離下完成 |
| Zero network attempt | 斷言無 DNS query / TCP connect / HTTP request |
| No downloader | `m4b_llm_product.py` install / preflight 及任何 downloader 未被呼叫；call count = 0 |
| No system-site import | child 使用 isolated runtime closure；`sys.path` 不含 system-site；無 `PYTHONPATH` / `PYTHONHOME` / `LD_PRELOAD` 逃逸 |
| Allowlisted child environment | `PYTHONNOUSERSITE=1`、bytecode write disabled；`LD_LIBRARY_PATH`若存在只能指向verified closure |
| Loaded-path attestation | runtime module／distribution實際loaded path位於verified closure；native library path與digest吻合，不接受READY自報取代 |
| No runtime fallback | product config的runtime download/network fallback為false、fallback model為null；不得改用alternate model或endpoint |
| Session PASS | 至少一次完整 generation（speak / tool / rest 任一）PASS；log 無 private content |

---

## M4B-RES-001 — 4 GB 20-session combined resource soak

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Pi（`rpi` marker）；同一 Core product SHA 含 M4a（與 M4b 相同 SHA） |
| **Contract basis** | `model_spec.md` §6.4；`ch_m4b` §10.2（`M4B-RES-001`）；`docs/milestones/M4.md` §6.4 條款 3 |
| **Case watchdog** | 3600秒；受formal Pi suite-level 9000秒timeout外層限制 |
| **Evidence** | runner acceptance result card；額外欄位 `test_id`、`session_count`、`generation_count`、`r14_formula_version`、`combined_pss_slope_mib_per_session`、`system_used_slope_mib_per_session`、`combined_pss_late_minus_early_median_delta_mib`、`system_used_late_minus_early_median_delta_mib`、`max_generation_delta_mib`、`swap_used_zero`、`oom_kill_delta=0`、`throttled_zero`、`thermal_max_celsius`、`resource_samples_locator`、`cleanup_locator` |
| **Pending** | 正式 Pi 執行前 spec tracker 標 `Pending`；不以 M4-REG-001 或 portable mock 取代 |

**r14 frozen gate（所有 20 samples 不得刪除 / 分段重算）**：

Portable verifier regression須以tracked sanitized r14 vector重現Attempt 006已接受的四個輸出：combined
PSS slope `5.900893 MiB/session`、combined late-minus-early median `131.578 MiB`、system-used slope
`0.101957 MiB/session`、system-used late-minus-early median `32.750 MiB`（僅容許fixture明定的浮點
tolerance）。無法重現即表示公式漂移，`M4B-RES-001`不得進Pi；target card固定
`r14_formula_version="2026-08-29-r14-user-resource-adjustment"`。

| Metric | Gate | Assertion |
| :--- | :--- | :--- |
| Combined PSS slope | ≤ 4 MiB/session | r14 公式；20 session 完整 samples |
| system_used slope | ≤ 4 MiB/session | r14 公式；20 session 完整 samples |
| late-minus-early combined PSS median delta | ≤ 64 MiB | r14 公式 |
| late-minus-early system_used median delta | ≤ 64 MiB | r14 公式 |
| 每個 child generation 的 post-prewarm owner-PSS baseline-to-clean-terminal delta | ≤ 64 MiB | 任一越界即 FAIL，即使後續 recycle 成功 |

**Additional assertions**：

| Metric | Assertion |
| :--- | :--- |
| `system_used = MemTotal - MemAvailable`；每 sample ≤ 3584 MiB | 任一 sample 超標即 FAIL |
| `swap_used = 0` | 任一 sample 非零即 FAIL |
| Memory PSI excluded | `/proc/pressure/memory` read count = 0；result／sample無PSI欄位且PASS不依賴`psi=1` |
| Zero OOM kill / throttle | run前後kernel OOM-kill counter/log delta = 0；每sample throttled bit = 0 |
| Temperature < 80°C | 每 sample 記錄；超標即 FAIL |
| 20 accepted sessions | session_count = 20；0 rejected |
| Combined functional validity | 每session的schema/current-marker/prior-marker/history及Audio→LLM→TTS terminal均PASS；resource數值不得掩蓋functional failure |
| Accepted M4a composition identity | 同一product SHA保留M4a Accepted lock／inheritance，並通過本章列出的affected M4a protocol/lifecycle/audio regression |
| 至少 2 次 replacement（3 個 child generation） | generation_count ≥ 3；attempt 8 / 16 各排程一次 recycle |
| Per-sample owner accounting | 每筆保存timestamp、session、child generation、Core/controller、VAD、ASR、TTS、LLM各owner的unique-PID PSS/RSS/CPU/thread、MemTotal/MemAvailable/system-used、swap、temperature、throttled與trigger；combined PSS不得重複PID，raw sample count與20 sessions對齊且無missing sample；sum RSS只作diagnostic，不得取代PSS或system-used gate |
| Cleanup residue | 20 session 後 owner process / descendant / thread / fd / workdir / ALSA handle residue = 0 |
| 48 MiB early trigger 不放寬 64 MiB gate | trigger 不得視為已合規；整體斜率仍須達標 |
| Recycle 不刪 pre-trigger sample | 完整 20 samples 保存；不分 generation 重算斜率 |
| Machine P9 / P10B FAIL 與 User waiver 分欄 | evidence 欄位 `poc_p9_p10b_status="FAIL"` / `user_waiver="KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION"` |

---

## M4B-PKG-001 — Offline install / lock / notices

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Portable review + Pi install |
| **Contract basis** | `ch_m4b` §8；`requirements/m4b/THIRD_PARTY_NOTICES.md` |
| **Suite marker** | Portable: `not rpi`；Pi: runner `accept` mode |
| **Case watchdog** | Portable 60秒；Pi 600秒；兩者皆受formal suite-level timeout外層限制 |
| **Evidence** | Portable: runner result + JUnit；Pi protected raw evidence保存exact install inventory與product preflight；公開acceptance card exact額外欄位為`install_inventory_sha256`、`python_abi_attestation_sha256`、`abi_status="Pass"`、`file_count`，只公開digest／status／count，不含package tuple、base／stdlib／product absolute path或raw attestation；card locator沿用run-root-relative T2 contract |

**Required assertions**：

| Case | Scope | Assertion |
| :--- | :--- | :--- |
| `llm-artifacts.json` schema 完整 | Portable | 8個top-level object（`lock/poc_reference/candidate/runtime/model/product_profile/runtime_closure/licenses`）均存在且無extra；所有required fields存在；SHA為64-hex、Git SHA為40-hex |
| `install` — caller-supplied inputs | Portable + Pi | 只接受 checksum-matching offline inputs；`--no-index --no-deps`（或 selected runtime 等價）；拒絕 network / existing output |
| `install` — target ABI before side effect | Portable + Pi | 在建立staging、native import、child spawn或network call前驗證M4B-LOCK-001 exact target ABI；wrong patch／ABI／ownership／package set／stdlib root時上述side effect count皆為0 |
| `install` — target-owned venv boundary | Pi | exact base以`--copies --without-pip`建立venv；`pyvenv.cfg`綁`/usr/bin/python3.13`且`include-system-site-packages=false`；launcher與`pyvenv.cfg`只進run-specific install inventory，不得進14-file tracked payload manifest |
| `install` — same-filesystem staging → atomic rename | Pi | staging 完整自驗後 atomic rename；failure 刪 staging；不覆寫既有 install |
| `install inventory` — exact ABI binding | Portable + Pi | protected inventory exact fields含canonical `python_abi_attestation`、其`python_abi_attestation_sha256`及全部installed files；attestation digest可由canonical bytes重算，missing／extra key、unsafe／duplicate path、digest mismatch均Fail |
| `preflight` — read-only inventory | Pi | 每個 product-owned file open-no-follow／regular-file／streaming SHA；拒絕symlink／extra／missing；target-owned stdlib不冒充14-file payload，但launcher／`pyvenv.cfg`仍受install inventory保護 |
| Install→preflight→acceptance ABI reconciliation | Pi | 三段各自重算target ABI；`python_abi_attestation_sha256`及install inventory digest exact一致後才可啟動child／finalize PKG card |
| Post-install ABI drift | Portable + Pi | package revision／tuple、base executable digest、exact Python identity、stdlib root或glibc任一漂移使preflight與acceptance-start Fail；child spawn=0，舊preflight與PASS card不得重用 |
| Stdlib positive / third-party negative | Portable + Pi | verified venv可import target stdlib與`lib-dynload`；拒絕`/usr/lib/python3/dist-packages`、`/usr/local/.../site-packages`、user site及任一product root外第三方package；`litert_lm`／native loaded path須位於verified product root |
| `preflight` — POC path provenance-only | Pi | checksum-matching product config內的POC `runtime_path/model_path/test_profile`只供provenance；open call count = 0，實際deployment path只取`LLMConfig`並驗digest |
| Wheel / native / model inventory exact match | Pi | 實際安裝 wheel、native library、model 與 lock 完全一致；零多餘或缺少 |
| Controller dependency isolation | Portable | selected runtime/native package不在Core controller`[project.dependencies]`；controller-side import graph無native runtime，只有isolated child可import |
| No target mutation / capture | Portable + Pi | installer不得呼叫`apt`、修改target packages、下載base runtime，或把CPython／stdlib／`lib-dynload` bytes寫回tracked manifest；call／written-entry count皆為0 |
| No moving identity／overwrite | Portable + Pi | install/preflight不讀branch HEAD；拒絕existing install/output且preflight read-only，不覆寫caller artifact/config |
| Sanitized command/card output | Portable + Pi | install/preflight stdout與公開PKG card只含status、public digest／count；exact package/path inventory只留protected raw preflight，不含model/prompt/output、credential或absolute private path |
| `THIRD_PARTY_NOTICES.md` 完整 | Portable review | LiteRT-LM runtime、Gemma 4 E2B、所有 dependency 均有 license / notice entry；Apache-2.0 清楚標注 |

---

## M4B-INH-001 — POC → Product inheritance / delta index

| 欄位 | 契約 |
| :--- | :--- |
| **Scope** | Evidence review（Tester 核對 `docs/outsource/evidence/<M4-delivery>/m4b/inheritance.json`）+ Portable（generator schema regression） |
| **Contract basis** | `ch_m4b` §9；`docs/milestones/M4.md` §6.4 條款 2 |
| **Suite marker** | Generator schema test: `not rpi`；Evidence review: Tester 手動核對 |
| **Case watchdog** | Portable generator test 60秒；formal portable runner仍使用本章統一的300秒suite timeout |
| **Evidence** | Portable: runner result + JUnit；Evidence review: Tester 簽核紀錄 |
| **Pending** | 正式 `inheritance.json` 只在 Gate 3 完成後由 Tester 產生；開發期間只跑 generator schema regression |

**Inheritance identity（required fields per row）**：

| Field | Assertion |
| :--- | :--- |
| `area` | exact member of `{P1,P2,P3,P4,P5,P6.1,P7.1,P8,P9,P10A,P10B,P11,P12}`；覆蓋概念P1～P12且不得自造area |
| `core_ack_id` | `DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001` |
| `poc_delivery_id` | `POC-llm-DEL-2026-001-R3` |
| `poc_execution_sha` | `0c75536e6ee99b502c59438989ca852194648946` |
| `poc_closure_sha` / `poc_publication_sha` | `5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae` / `485bb2a7c07d86a09899f09358c744edd733f875` |
| `poc_evidence_id` | `G2B-PI-COMBINED-006` |
| `poc_manifest_locator` / `poc_manifest_sha256` | resolver取得R3 manifest bytes；digest為64 lowercase hex且內容吻合 |
| `poc_evidence_locator` / `poc_evidence_sha256` | resolver取得formal evidence bytes；digest為64 lowercase hex且內容吻合 |
| `poc_machine_result` | 非空、由上述resolved immutable content解析出的原始machine status；不得由waiver改寫 |
| `user_waiver` | 無waiver時為JSON `null`；有waiver時與User核准字串exact一致，與`poc_machine_result`分欄 |
| `candidate_id` / `pairing_revision` | `CAND-LRT-G4E2B-MOBILE-R1` / `litert-lm-v0.16.0-pi-g2b-r5` |
| `classification` | `inherit` / `delta` / `waiver` 其中之一 |
| `inheritance_reason` | 含具體 delta_test_id 或明確技術理由；裸「沿用 POC」fail closed |
| `product_sha` | 40 lowercase hex；所有列相同；等於外部指定 frozen candidate SHA |
| `delta_test_id` | exact member of `{M4B-CFG-001,M4B-LOCK-001,M4B-IPC-001,M4B-RDY-001,M4B-GEN-001,M4B-OUT-001,M4B-P5-001,M4B-CAN-001,M4B-REC-001,M4B-HIST-001,M4B-PRIV-001,M4B-OFF-001,M4B-RES-001,M4B-PKG-001}`；不得以`M4B-INH-001`建立self-row |
| `delta_result` | final Gate 3只允許`PASS` / `FAIL`；`PASS`只可由下列scope-aware proof的`status="Pass"`正規化，`FAIL`對應`status="Fail"`；Accepted output不得含`BLOCKED` |
| `result_proof_kind` | exact member of`target_card / lock_preflight_reconciliation / portable_reconciliation`，且須與`delta_test_id` scope吻合 |
| `result_locator` | resolver取得下列scope-aware proof；proof內candidate SHA、run ID、Test ID/status binding與本列相符，且所有被引用bytes digest可重算；不得把non-empty locator或suite-level `result.json`冒充Test-ID card |
| `portable_run_id` | portable delta填三版本共用run ID；非portable delta填JSON `null` |
| `acceptance_run_id` | Pi delta填單一正式`pi_acceptance_run_id`；portable/evidence-only delta填JSON `null`；不得使用debug run ID |

**Specific area assertions**：

| Area | Required classification / assertion |
| :--- | :--- |
| P1 / P6.1 / P7.1 lifecycle | Core delta rows至少分別指向`M4B-RDY-001`、`M4B-CAN-001`與`M4B-REC-001` |
| P2 / P3 result quality | 指向`M4B-OUT-001` fixed product catalog；P2舊pairing machine FAIL保持原文，replacement結果另列，不得覆寫歷史 |
| P4 performance | 指向`M4B-GEN-001` target timing/token result；繼承candidate selection數據但不自訂新門檻 |
| P5 timeout | 指向`M4B-P5-001`及直接cancel cleanup的`M4B-CAN-001` |
| P8 history | 指向`M4B-HIST-001`；舊pairing `FAIL / DEPENDENCY_LIMITED_BY_P2`與replacement marker結果分欄 |
| P9 / P10B | `poc_machine_result="FAIL"`；`classification="waiver"`；`user_waiver="KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION"`；Core product `M4B-RES-001`結果仍以獨立delta row填列 |
| P10A | 原始machine PASS可inherit，但Core persistent-child composition差異須有`M4B-GEN-001`／`M4B-REC-001` locator |
| Gate 2B narrow listen→speak harness vs Core generic renderer | 以一或多個`delta_test_id="M4B-OUT-001"`的獨立row記錄具體產品delta reason；不得建立`M4B-INH-001` self-row或把多個ID塞進單一字串欄位 |
| P11 provenance | 至少有`M4B-LOCK-001`與`M4B-PKG-001`的獨立delta row |
| P12 offline | 至少有`M4B-OFF-001`與`M4B-PRIV-001`的獨立delta row |

`M4B-INH-001`是整份index的generator schema＋Tester evidence-review gate；其PASS由本節驗證與
Tester簽核得出，不寫回`inheritance.json`要求自身證明自身。

**Scope-aware result proof（formal Gate 3）**：

| Proof kind | Applicable row | Required oracle |
| :--- | :--- | :--- |
| `target_card` | 有Pi acceptance card的Test ID | 指向同一正式acceptance run已finalize的test-specific card；card直接含`candidate_sha / run_id / test_id / status`且digest可重算 |
| `lock_preflight_reconciliation` | `M4B-LOCK-001` | Tester record同時綁定同一acceptance run的runner `preflight.json`與`m4b_llm_product.py preflight` sanitized identity record；保存兩個locator／digest、candidate SHA、acceptance run ID、`test_id="M4B-LOCK-001"`與reconciled status，並要求兩者`python_abi_attestation_sha256`／install-inventory digest exact相同；exact package/path attestation只由protected raw evidence解析，不寫入公開index |
| `portable_reconciliation` | CFG／IPC或其他無target card而需入列的portable Test ID | Tester record綁三個正式minor共用portable run ID，逐minor保存runner result與JUnit locator／digest、candidate SHA、Python minor、Test ID coverage及reconciled status；suite `result.json`本身不宣稱含Test ID |

任一reconciliation未完成、引用debug／不同run、混合SHA／Test ID、digest mismatch或其底層任一結果
不是相同status時均fail closed。Development期間的blocked狀態只存在review/tracker，不輸出至final
`inheritance.json`。

**Locator resolver seam（Portable）**：

| Case | Assertion |
| :--- | :--- |
| Valid local bytes | resolver取得content；`sha256(content)`等於對應manifest／evidence SHA欄；accepted |
| Missing／unreadable file或directory instead of file | resolver失敗；fail closed |
| Wrong content hash | `sha256(content)`不等於對應`poc_manifest_sha256`／`poc_evidence_sha256`；fail closed |
| Moving revision | branch、tag-only或其他無40-hex immutable revision的locator；fail closed |
| Git-controlled locator | 只接受`<repo>@<40hex>:<path>`或核准的等價immutable scheme，且resolved bytes通過同一hash oracle |

**Generator seam tests（Portable）**：

| Case | Assertion |
| :--- | :--- |
| Valid finalized target card | `target_card`直接解析同一candidate SHA／acceptance run／Test ID／PASS與content digest；accepted |
| Valid LOCK preflight reconciliation | 同一acceptance run的runner preflight與product sanitized preflight locator／digest、identity及`M4B-LOCK-001` binding全吻合；accepted |
| Valid three-minor portable reconciliation | CPython 3.11／3.12／3.13 result＋JUnit locator／digest、共用run ID、candidate SHA、Test ID coverage與PASS全吻合；accepted |
| Generator 不讀 `git rev-parse HEAD` | 斷言 `product_sha` 來自外部注入，非 HEAD-derived |
| Generator 不寫 `docs/outsource/evidence/` | fast loop 使用 temp output |
| Mixed `product_sha` | fail closed |
| Wrong Core ACK／POC delivery／execution-closure-publication SHA | fail closed；不得以branch、short SHA或Core ACK冒充POC delivery identity |
| 缺欄 / locator不存在 / wrong checksum / wrong candidate-pairing identity | fail closed |
| machine result被waiver覆寫或共用同一欄 | fail closed |
| target row缺`acceptance_run_id`、portable row缺`portable_run_id`或任一使用debug run ID | fail closed |
| Non-empty locator 但 resolver 失敗 | fail closed；非空字串不足以通過 |
| Raw suite result冒充Test-ID card | fail closed；須依scope使用target card或Tester reconciliation |
| `M4B-INH-001` self-row | fail closed；index不得自我證明 |
| Unresolved／mixed reconciliation | locator或digest未解析、SHA／run／Test ID混用、三minor不完整任一成立即fail closed |
| Accepted output含`BLOCKED` | fail closed；final Gate 3只允許PASS／FAIL |

**M4a regression coverage（此測試同時驗 M4a contract 未被改寫）**：

M4B-IPC-001的regression guard要求M4b development後重跑受影響M4a測項並保持PASS。
`inheritance.json`另以top-level `m4a_regressions` array保存，每列exact fields為
`m4a_test_id / product_sha / portable_run_id / result_locator / result`；`result`須為`PASS`且locator
解析出的runner `status="Pass"`、candidate SHA、run ID及Test ID吻合。此array不使用M4B row的`delta_test_id`欄，避免把
M4a ID冒充為15個M4B Test ID之一。

---

## M4b 里程碑結論欄位

M4b 子 gate 結論文件必須包含（由 Tester 填入，引用 runner 標準欄位）：

| 欄位 | 說明 |
| :--- | :--- |
| `candidate_sha` | 40-character product delivery SHA；M4a / M4b / M4c 共用同一 SHA |
| `portable_run_id` | M4b portable matrix 的 run ID（三版本共用） |
| `portable_matrix_index` | `<m4b-portable-root>/matrix-index.json` 路徑（runner 產生） |
| `pi_preflight_locator` | 同一candidate SHA／`pi_acceptance_run_id`的`preflight.json` locator |
| `python_abi_attestation_sha256` | install、product preflight、runner preflight與acceptance-start重算後一致的64-hex target ABI digest |
| `install_inventory_sha256` | product preflight、runner preflight與M4B-PKG-001 card一致的64-hex protected install inventory digest |
| `pi_acceptance_run_id` | M4b target acceptance 的 run ID（不得混用 debug run ID） |
| `pi_result_locators` | M4b 各 Pi acceptance result card run-root-relative locator（含 RES / OFF） |
| `inheritance_index_locator` | `docs/outsource/evidence/<M4-delivery>/m4b/inheritance.json` |
| `offline_result_locator` | M4B-OFF-001 acceptance result card locator（`Pending` 直到 Pi 執行） |
| `m4b_res_locator` | M4B-RES-001 acceptance result card locator（`Pending` 直到 Pi 執行） |
| `poc_p9_p10b_status` | `FAIL`（機器 Attempt 006 結果；不得改寫） |
| `user_waiver` | `KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION` |

正式 target result 使用單一 `pi_acceptance_run_id`，不拼接多個 run ID；
debug run ID 不得列入里程碑結論。
M4b Accepted 只關閉 M4b 子 gate；M4c 仍須在 M4a + M4b 均通過後接線，
整體 M4 要求三個子 gate 在同一 exact SHA 收斂。
