# M4-ERR — production error handling closure

狀態：**Accepted；same-bytes Pi Verify complete；commit `f572915d0b0d5c52067e9100c5b022e57aefe506`**

上游：`arch.md` §3.4、§6.4–§6.8；Ch 1、Ch 4–6、Ch 11；Accepted M4A／M4B。

本章是 M4 production component 與通用 Core 的 error-handling delta authority。它不改寫
Accepted M4A／M4B 歷史，也不建立第二套 lifecycle；所有 system fault 仍進既有
`ErrorOccurred → ERROR → convergence → optional RM recovery → IDLE／Level 3` 路徑。

## 1. Scope and fixed boundary

本工作包含：

- 統一 request outcome、system fault、optional degradation、cancellation 與 fatal 的分類；
- native child、adapter、worker、State Manager 間不失真的 cause 與 backend-usability 傳遞；
- Button／GPIO、ASR／Audio input、LLM／Conversation、TTS／Audio output、Display 與共用 Core；
- sanitized diagnostic、ERROR display projection、recovery key、fatal exit 與 startup／shutdown；
- 對所有 M4 production broad catch／lossy mapping 做一次閉合集合 audit。

不包含 M4C scenario composition、streaming speak 選擇、barge-in、重複 session／soak、正式 latency／
memory／thermal threshold、遠端 telemetry 或 end-user 可配置錯誤文案。M4C 只抽樣 whole-product
場景，不重跑本章 cause matrix。

### 1.1 Accepted-history and prospective supersession boundary

Accepted M4A／M4B artifacts、原始test definitions、驗證結果與其SHA維持不可改寫的歷史證據。對含有
M4-ERR的後續candidate，本章只前瞻性取代下列直接衝突的舊oracle：

1. `test_m4a_tts_002_persistent_error_reopen_and_next_success`與
   `test_m4a_tts_002_every_whitelisted_error_reopens_same_child`所要求的TTS system fault後same-child reuse；
2. `test_m4b_p5_001.py::test_product_fatal_boundary_has_no_normal_fact_and_sanitized_traceback`所要求的
   mapped fault `__cause__ is None`；
3. `test_m4b_priv_001.py::test_V01_completion_callback_failure_reaches_worker_supervision`所要求的原始
   `ObservationError`直接逸出 supervision。

這些現行oracle改由本章的typed fault、backend disposition、private cause chain、sanitized public
diagnostic與rebuild契約取代。其餘M4A／M4B identity、lifecycle、cleanup、cancellation、privacy及
anti-weakening assertions全部保留。新的prospective baseline以M4-ERR Test ID、candidate tracked-content
digest及相同bytes Pi evidence綁定；不得修改、重標或假稱取代舊SHA的歷史證據。

## 2. Canonical taxonomy

| Class | Meaning | Product path | Backend decision |
| :--- | :--- | :--- | :--- |
| request outcome | 合法輸入或容量政策產生、可安全翻譯的結果 | 恰一個既有 `PerceptionResult`／`LLMResponse`／`ActionCompleted`；不發 `ErrorOccurred` | 必須已有 terminal／cleanup proof 且 backend 可重用 |
| system fault | native、protocol、HAL、worker 或 Core operation 未完成產品契約 | 發一個 sanitized `ErrorOccurred`，同一 typed exception 逸出 task；SM 進 ERROR | 依 §3 明確判斷；不可由 exception text 猜測 |
| optional degradation | optional surface 失效而核心 voice path 仍有定義 | 一筆 bounded ERROR diagnostic，停用該 optional surface；不製造正常 Fact | 只適用本章明列的 Display runtime disable |
| cancellation | Interrupt／Rest／Error／Shutdown 收斂中的取消 | 不發 Fact、不另發 fault；沿用 Ch 6 proof | 由 Level 1／2 report 決定 |
| fatal | startup、invariant、convergence、recovery 或 required non-recoverable resource 無法證明安全 | 既有 main first-root supervision；exit 2／3／4 | 不回 IDLE、不宣稱 recovery 成功 |

`timeout` 不是固定類別。只有 owner 已取得 request terminal、cleanup 與 reusable proof 時才能翻譯成
request outcome；timeout 後 proof 不完整即為 system fault。`AdapterError`、`RuntimeError` 或未知 native
字串本身不構成分類。

## 3. Typed system-fault contract

### 3.1 Shared types

落點為 `src/sbd/core/faults.py`：

```python
class BackendDisposition(StrEnum):
    REUSABLE = "reusable"
    REBUILD_REQUIRED = "rebuild_required"
    UNPROVEN = "unproven"
    NOT_APPLICABLE = "not_applicable"

class ComponentSystemFault(RuntimeError):
    where: str
    code: str
    safe_summary: str
    backend: BackendDisposition
    recovery_keys: tuple[str, ...]

    def to_event(self) -> ErrorOccurred: ...
```

Construction fail-closed rules：

- `where` 使用 Ch 11 namespace；`code` 為 `^[A-Z][A-Z0-9_]{2,63}$`；summary 只能是 code-declared
  常數，不接受 transcript、prompt、payload、PCM、native message 或 `repr(exc)`。
- `REBUILD_REQUIRED` 必須帶至少一個 stable RM key；key 去重排序。
- `UNPROVEN` 必須帶至少一個 owner 已知的 candidate key；若 fault 不擁有 backend則使用
  `NOT_APPLICABLE`。Level 2 無法回報所宣告的 destroyed key時直接 Level 3。
- `REUSABLE`／`NOT_APPLICABLE` 不得帶 recovery key。
- 原始例外只透過 `raise fault from cause` 保留在 task exception chain，不進 Event／Display。

`ErrorOccurred` 增加 `code`、`backend_disposition`、`recovery_keys`。它仍是 observer／ERROR trigger，
不成為 recovery proof；State Manager 與 Converger 只信 task exception 及 `ForceAbortReport`。所有
production publisher 改用 keyword construction；測試 helper 可使用明確的 legacy-neutral default，但
production 不得留下 `UNCLASSIFIED`。

### 3.2 Backend usability

| Disposition | Required evidence | Convergence result |
| :--- | :--- | :--- |
| `REUSABLE` | request 已 terminal、所有 private input 已清、owner 回 READY、同 owner 可接受下一 operation | ERROR 收斂後可不 rebuild |
| `REBUILD_REQUIRED` | owner 已知目前 backend 不可再 admission，且有 stable resource key | 即使 outer task 已完成也強制 Level 2；成功 report 該 key，再由 RM rebuild |
| `UNPROVEN` | terminal、cleanup 或 owner state 任一無法證明 | fail closed 強制 Level 2；無完整 proof 即 Level 3 |
| `NOT_APPLICABLE` | fault 不擁有可重建 backend | ERROR 收斂，不啟動 RM recovery；若 required resource 已不可用則 publisher 必須改報 fatal |

Backend usability 不得以「child process 尚存活」、「exception 可捕捉」或「下一次可能成功」推論。

### 3.3 Worker and convergence sequence

1. Adapter／HAL 將原始失敗映射為 request outcome 或 `ComponentSystemFault`；未知 exception 一律包成
   component-specific `*_UNEXPECTED` + `UNPROVEN`，保留 `__cause__`。
2. Worker 對 system fault publish `fault.to_event()` 一次，隨後 raise 同一 fault；不得先產生 error Fact。
3. `CancelledError` 原樣 re-raise；cancel path 不轉 system fault。
4. Ch 6 在 Level 1 後收割 completed task exception。`REBUILD_REQUIRED`／`UNPROVEN` 即使 task 已 done
   仍是 Level 2 target；`REUSABLE`／`NOT_APPLICABLE` 不因 system fault 自動破壞 backend。
5. `WorkerRuntime.force_abort()` 必須支援「failed outer call 已完成、fault owner 尚待 destruction proof」；
   只對 Converger 指定的 fault target 呼叫，不得掃蕩其他 idle worker。
6. Level 2 report 必須包含 fault 所宣告且實際被破壞的 keys。缺 key、多報不屬於該 owner 的 key、
   terminate／waitpid／fd／device release proof 不完整，皆為 `ConvergenceFatalError`。
7. Ch 4 只從有效 `ConvergenceResult.destroyed_backends` 呼叫一次 `begin_recovery()`；仍沿用 in-flight
   empty + recovery barrier gate，禁止提早回 IDLE。

這是既有 arch Level 1／2／3 的 fault-information closure，不增加新 state 或 role gate。

## 4. M4 production mapping

### 4.1 Button and GPIO

| Source | Mapping |
| :--- | :--- |
| legal short／long press | 既有 signal；不是 error |
| bounce、release without press、stale event | bounded DEBUG／drop；不是 error |
| button callback exception with GPIO still registered | `BUTTON_CALLBACK_FAILED` + `REUSABLE`；publish once，active Session 走 ERROR |
| GPIO edge read／registration ownership corruption | `GPIO_EVENT_READ_FAILED` + `UNPROVEN`；`core.gpio` 無 recovery hook時走 Level 3 |
| startup chip／line acquisition failure | `StartupError` rollback，exit 3 |

GPIO driver 不得只用 detached task `logger.exception()` 吞掉 callback exception；callback task failure必須進
可監督的 Event Bus／fatal path。錯誤診斷不可包含 pin consumer 或 host path 以外的任意 object repr。

### 4.2 Listen, Audio input and ASR

| Source | Mapping |
| :--- | :--- |
| finite input empty、`NO_SPEECH`、`MULTIPLE_UTTERANCES` | request outcome：`timeout`／`error`；必須 child READY |
| local caller frame contract violation或child `INVALID_FRAME` | `ASR_FRAME_CONTRACT_VIOLATION`；`UNPROVEN`，不可要求 USER 重說 |
| native `INFERENCE_REJECTED` | `ASR_INFERENCE_FAILED` + `REBUILD_REQUIRED` + ASR key |
| protocol mismatch、EOF、child crash | `ASR_PROTOCOL_FAILED` + `REBUILD_REQUIRED` + ASR key |
| ALSA capture/read/adaptation failure | `AUDIO_CAPTURE_FAILED` + `UNPROVEN`；`core.audio.input` 無 recovery hook時 Level 3 |
| operation timeout | abort 後 READY／cleanup proof 完整才是 timeout Fact；否則 `ASR_TIMEOUT_UNPROVEN` |

ASR supervisor 不得把所有 `BaseException` 壓成 `INFERENCE_REJECTED`。至少分出 native inference failure、
supervisor invariant、cancel 與 process termination；parent 收到未知 code 視為 protocol fault。

### 4.3 LLM, Reasoner and Conversation

Accepted M4B outcome matrix維持有效：R1／R2 只有在 request terminal、Conversation cleanup 與
`engine_usable=True` 的 typed proof 完整時才能發布。`ReplaceableGenerationFailure` 保留 typed code與
proof，不再被 broad catch 壓成 `M4B_REASONER_FAILED`。

| Source | Mapping |
| :--- | :--- |
| capacity／input limit／no input | 既有 R1／R2 normal Fact |
| replaceable semantic／generation failure，proof 完整 | 既有 R2；不發 system fault |
| invalid ticket／profile／revision／protocol | `LLM_PROTOCOL_FAILED` + `UNPROVEN` + LLM key |
| child crash、backend unusable | `LLM_BACKEND_FAILED` + `REBUILD_REQUIRED` + LLM key |
| request／close／discard proof 缺失 | `LLM_CLEANUP_UNPROVEN` + `UNPROVEN` + LLM key |
| observer／sampler failure影響 admission truth | `LLM_OBSERVATION_FAILED` + `UNPROVEN` + LLM key |
| SM收到非法 `LLMResponse` | 保留 `ReasonerContractViolation`：ERROR但非 main fatal；不假造 `ErrorOccurred` |

Planned recycle仍是 SM 授權的 private post-close path；system-fault recovery不得偽裝成 planned recycle，
planned-recovery failure仍直接 Level 3。

### 4.4 Speak, TTS and Audio output

有效的 code-declared speak payload 不存在 user-retryable TTS rejection。`INVALID_TEXT` 若從 child 返回，
代表 Core／wire contract fault；`GENERATION_REJECTED` 與 `INVALID_PCM` 都是 system fault。

| Source | Mapping |
| :--- | :--- |
| TTS native generation failure | `TTS_GENERATION_FAILED` + `REBUILD_REQUIRED` + TTS key |
| TTS protocol／PCM identity failure、child crash | `TTS_PROTOCOL_FAILED` + `REBUILD_REQUIRED` + TTS key |
| audio output write／drain／device failure | `AUDIO_PLAYBACK_FAILED` + `UNPROVEN`；non-recoverable output導向 Level 3 |
| cancellation | no `ActionCompleted`；沿用 TTS／Audio cleanup proof |

Speak只在 TTS iterator完整結束且 AudioOutput drain成功後發布 `ActionCompleted(ok)`。任何 system fault
不得降成 `ActionCompleted(error)`；後者只保留給可預期、已證明 backend reusable 的 action outcome。
TTS generation、protocol、PCM identity或child fault發生後，原child必須退出admission並完成destruction
proof；在RM以stable TTS key rebuild前不得接受下一次synthesize。下一次READY／成功證明必須來自
rebuild後的backend，不得以same-child reopen滿足。

### 4.5 Display

Caller hint validation仍是 `DisplayHintError` WARNING／drop。Display native write／show runtime failure採唯一
optional-degradation例外：原子設定 rendering disabled，寫一筆固定 `DISPLAY_RENDER_DISABLED` ERROR，
其後 write意圖為 no-op。不得嘗試在已失效 Display 上顯示自己的錯誤，也不更新靜態 capability map。

主流程 system fault 的 error slot只接收固定安全投影：`audio`、`asr`、`llm`、`tts`、`input`、`internal`；
不顯示 exception text、code細節、路徑、payload或 traceback。若 Display 已 disable，voice error convergence
不受阻。

## 5. Diagnostics, startup, shutdown and fatal exit

- 每個 system fault只有一個 canonical ERROR log；fields 為 `where`、`code`、backend disposition、排序後
  recovery keys與既有 correlation context。`fault.__cause__`必須以object identity保留在受監督task的
  in-memory private exception chain，但不得序列化到Event、Display、structured/public evidence、一般
  canonical log或public fatal output。
- Level 3只輸出一次first-root sanitized traceback；renderer只呈現typed fault class、安全code與固定
  context，不得呼叫generic chained `traceback.format_exception()`把raw cause message寫到公開輸出。
  本slice不持久化raw cause artifact；需要除錯時只可在仍存活process的受控in-memory debugger boundary
  存取exception object。
- Error Display projection與log使用同一 code-to-safe-category純函式；未知 code映射 `internal`。
- Config invalid維持exit 2；resource startup失敗保留root cause、reverse rollback後exit 3。
- Recovery failure、unknown／non-recoverable required backend、Level 2 proof failure、Bus／SM invariant維持
  first-root exit 4；fatal path不再 publish `ErrorOccurred` 或進第二次 ERROR recovery。
- Normal shutdown不rebuild。個別 stop failure照Ch 11記錄並繼續reverse stop；若 termination proof 本身
  不成立，則屬runtime fatal，不得以exit 0掩蓋。
- 所有 diagnostic必須通過既有 privacy redactor；測試 fixture注入 transcript、prompt、PCM sentinel、
  filesystem locator與newline，任何公開 Event／log／Display均不得出現。

## 6. Implementation work packages

| WP | Scope | Exit evidence expected by Test Spec |
| :--- | :--- | :--- |
| `M4-ERR-WP1` | shared fault types、ErrorOccurred schema、safe projection、producer migration | constructor invariants；production code無未分類 publisher |
| `M4-ERR-WP2` | WorkerRuntime、task exception harvest、Converger、SM/RM handoff | 四種 backend disposition；completed-fault Level 2；missing/wrong key fatal |
| `M4-ERR-WP3` | ASR supervisor／adapter、Listen、Audio input | exact code matrix；`INFERENCE_REJECTED` system fault；rebuild／nonrecoverable fatal |
| `M4-ERR-WP4` | LLM adapter／Reasoner／Conversation | R1/R2 proof不退化；broad catch保留cause；unsafe path E1/recovery |
| `M4-ERR-WP5` | TTS／Speak／Audio output | valid-text failures不降成 retry；TTS rebuild；ALSA fatal boundary |
| `M4-ERR-WP6` | Button／GPIO、Display、logging、main supervision | callback不被吞；optional Display disable；single sanitized root diagnostic |
| `M4-ERR-WP7` | composition audit、portable integration、Pi fault injection與same-bytes verify | 全矩陣、cleanup、recovery、exit code、privacy、tracked digest |

WP1→WP2固定共用契約後，WP3–WP6可由Developer安排實作順序；WP7最後收斂。這是單一 Developer
階段，不能拆成多個額外 approval／freeze gate。

## 7. Test Spec handoff requirements

Tester須把下列行為各自映射成可執行 Test ID 與 exact oracle：

1. taxonomy與production publisher closed-set audit；
2. Fact／ErrorOccurred互斥、cause chain保留及 sanitized projection；
3. 四種 backend disposition及 completed-task forced Level 2；
4. recovery key去重、錯 key／缺 key、RM rebuild成功、recovery failure exit 4；
5. ASR四類、LLM R1／R2／E1、TTS／Audio、Button／GPIO、Display disable矩陣；
6. config=2、startup=3、normal shutdown=0、runtime fatal=4及first-root single traceback；
7. transcript／prompt／PCM／payload sentinel不出現在Event、log、Display；
8. Raspberry Pi actual ALSA、GPIO、ASR child、LLM child、TTS child fault injection，以及每個可恢復
   backend的同-baseline READY proof；
9. tracked-only content digest、production config/artifact identity與所有適用自動／整合／硬體結果。

因§1.1的prospective supersession，Tester須做一次聚焦revision：保留既有G05 coverage及G06對所有未受
影響definition的AST anti-weakening；只對§1.1列名的definitions建立明確overlay，以M4-ERR oracle取代
舊衝突assertion。overlay須驗證TTS typed code／disposition／stable key、舊child destroyed、rebuild前無
admission、RM rebuild、rebuild後backend READY；以及mapped fault保留同一original cause object、恰一個
safe `ErrorOccurred`、public fatal renderer無sentinel／raw exception text。舊starting SHA與舊evidence只作
immutable historical baseline，不得改寫。受影響portable suite及相同bytes M4-ERR Pi Verify run仍為commit
前必要條件。

本slice沒有產品需求指定的真人判讀；Pass／Fail一律由上述自動oracle與target facts決定。Portable
environment只涵蓋repo當前支援且Developer實際可執行的平台，不為本slice新增多平台matrix。Broad-catch
audit限M4 production fault-mapping boundaries，並允許本章已定義的cancellation、optional degradation、
startup rollback與bounded cleanup catch；不得要求攔截或改寫整個`src/sbd/`的每個`except`。

Pi fault injection須使用Developer提供、Test Spec固定的deterministic product test seam，同時啟動並核對
actual ALSA／GPIO／native child identity。測試不得以kernel fault injection、實體拔除裝置、改變網路、
reboot或未另行授權的privileged mutation作為必要步驟。

為避免與M4B的`PV-M4B-*`驗證run ID混淆，M4-ERR的Pi test case一律使用完整
`M4-ERR-PV-001`至`M4-ERR-PV-005`，不得在狀態、證據或驗收紀錄中縮寫成`PV-001–005`或單稱
`PV`。五項case合併執行時稱為「M4-ERR Pi Verify run」；其唯一run ID須另外記錄，且不得沿用
`PV-M4B-*`命名空間。

Pi測試使用待提交相同bytes；任何修改皆回Developer並重跑受影響測試。M4-ERR Accepted前不開 M4C
Test Spec／Developer entry。

## 8. Completion boundary

M4-ERR完成時：所有 M4 production failure都有唯一分類、穩定 code、明確 backend decision與可執行
convergence；可恢復 backend在 barrier 前不可接新 session；不可恢復或 proof不完整的 required resource
以exit 4結束；公開診斷不洩漏內容。M4C只需驗證代表性的 PERCEPTION／THINK／ACTION fault 能正確
消費本契約。
