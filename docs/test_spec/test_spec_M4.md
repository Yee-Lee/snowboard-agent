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
