---
requestor: "Designer"
owner: "Designer"
status: "Resolved"
---

# TR_spec_M4_I — M4a Gate 3 test-spec coverage request

- **Milestone**: M4a Accepted Audio production integration
- **Request date**: 2026-08-26
- **Revision date**: 2026-08-26
- **Target**: `docs/test_spec/test_spec_M4.md`
- **Entry dependency**: Fulfilled — `IR_review_M4A_I`已Resolved並明確核准`docs/model_spec.md`、`docs/protocol.md` Audio v1、`docs/implement/ch_m4a_audio_production.md`、`docs/implement/ch10_config.md` M4a extension及跨章節一致性
- **Activation**: Resolved — USER明確指示Designer接手剩餘修訂；T1～T12已完成終局核對
- **Decision**: `DESIGNER COVERAGE APPROVED — DEVELOPMENT READY`

## Final Designer completion（2026-08-26）

USER在Tester第二次submission後明確指示「剩下的你自己補完，不再交由tester」。Designer據此
直接完成test-spec剩餘修訂；下方舊Tester行號摘要保留為歷史，不再作current locator。

| Item | Final evidence in `docs/test_spec/test_spec_M4.md` | Result |
| :--- | :--- | :--- |
| T1 | lines 48–103：matching Python 3.11/3.12/3.13 launchers、六個canonical command、preflight/accept output lifecycle與mode-specific timeout | PASS |
| T2 | lines 105–157：base、pytest-execution、portable/acceptance/debug、preflight與matrix exact schema；`raw_logs`為`list[string]`且只存在適用mode | PASS |
| T3 | lines 121、158–161：safe-token run ID、`Pass|Fail|Diagnostic`及spec-only `Pending` | PASS |
| T4 | lines 192–219、238–249：兩個real factory的signature/lock injection、zero-side-effect、composition/RM owner及product preflight | PASS |
| T5 | lines 262–294：16 KiB／64 MiB inclusive/zero/exceeded boundary、request/sequence/hash、ERROR whitelist及shutdown state | PASS |
| T6 | lines 296–308、402、467–468：完整READY exact keys、ASR五欄/TTS四欄逐欄mismatch、termination proof、PGID、idempotence與real-child recovery | PASS |
| T7 | lines 331–355：完整Silero threshold/window/context/padding及Whisper normalized greedy best-of-1 profile | PASS |
| T8 | lines 418–445：lazy single-flight、child hardware boundary、Accepted oracle、inclusive clamp、vector、endianness、byte/hash與no-resample | PASS |
| T9 | lines 163–178、483–503：runner metadata與product output domain分離，locator保留且captured product log內容仍掃描 | PASS |
| T10 | lines 585–599：單一resolver、local/Git exact-SHA locator及missing/unreadable/directory/hash/scheme negative cases | PASS |
| T11 | lines 601–617：exact Accepted SHA、explicit 13-ID set、POC/result locator內容驗證、same frozen product SHA與fail-closed | PASS |
| T12 | 本節；test spec共638行、13個M4A Test ID，`M4-REG-001`本體與HEAD逐字一致 | PASS |

### Final sign-off

`Resolved — 100% planned M4a Gate 3 coverage approved.`

TR-M4A-001～003均已關閉。Developer現在可先更新`docs/reviews/dev_progress_M4.md`，
建立M4A-WP-09～13估點與工作包，再依test spec實作；不得把尚未執行的Pi／combined
`Pending`誤作M4a acceptance。

## Historical Tester revision summary — 第二次修訂（2026-08-26，superseded locators）

本輪針對 Designer coverage review 所列 3 個 Blocking（TR-M4A-001/002/003）及 T1～T12
checklist 逐項修訂 `docs/test_spec/test_spec_M4.md`。行號以修訂後實際行為準（共 608 行）。

### T1 — Canonical commands（L48–L97）

`test_spec_M4.md` L48「正式命令與 Runner Contract（T1）」節完整替換：刪除原先自訂 pytest
命令形狀，改以 `scripts/candidate_gate.py` 的 `portable`（三版本）→ `matrix` →
`preflight` → `accept` 精確命令，含所有必要 flag（`--candidate-sha`、`--run-id`、
`--python`、`--suite`、`--timeout-seconds`、`--output` 等），與 runner CLI parser 完全對齊。
`<portable-run>` 三版本與 matrix 共用同一 run ID；`<acceptance-run>` 供 preflight 與 accept
共用。Portable各版本目錄、matrix index與preflight acceptance root啟動前不得存在；
`accept`依runner contract重用preflight建立的acceptance root，且`result.json`啟動前不得存在。

### T2 — Exact runner schema（L99–L151）

L99「Runner Result Schema（T2）」節：Common / Portable / Preflight三表及Matrix段落，
欄位名稱以 `candidate_gate.py` `base_result()`、`suite_counts()`、`write_json()` 為唯一
依據：`command`（`sys.argv` list）、`python.{implementation,version}`、`started_at_utc`、
`ended_at_utc`、`counts.{passed,failed,skipped,xfailed}`、`raw_logs`、
`checksums.{artifact_manifest,config,hardware}.{path,sha256}` 等，不另命名或缺漏。
Test-specific card 只增加 `test_id` 與 metric 欄位，不得刪除或改名 runner 既有欄位。

### T3 — Identity / status wording（L115, L148–L151）

L115 明定 `run_id` 符合 `^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$`，token only；output
directory 路徑另記，不塞入 run ID。L148–L151「Pending 語意」：`Pending` 只用於 spec tracker，
不產生任何 runner result `status` 欄位；formal runner 狀態為 `Pass|Fail|Diagnostic`，
不使用全大寫 `PASS/FAIL`。Portable evidence 為 runner `result.json` + JUnit + raw logs +
matrix index；不要求 pytest JSON plugin。

### T4 — CFG / LOCK factory seam（L171–L207, L211–L232）

`M4A-CFG-001`（L171）新增「Factory seam cases（T4）」表（8 cases）：
`inspect.signature` 驗 public factory 唯一參數為 `cfg`；inject sentinel `AudioArtifactLock`
驗 adapter constructor 收到同一 object identity 且只經 keyword-only `lock` 傳入；
mock/null parser call count = 0；missing/malformed/identity-mismatch lock 時
adapter/native import、child spawn、Audio HAL、workdir call count 全為 0。
`M4A-LOCK-001`（L211）`Zero artifact on fail` row 對應同一 4 個 count 斷言。

### T5 — IPC exact bounds / state（L236–L277）

`M4A-IPC-001`（L236）新增以下 cases：
控制行 exact 16 KiB inclusive 接受 / 16 KiB+1 拒絕（含 `\n` 計入）；
TTS PCM exact 64 MiB accepted / 超限 / odd / `sample_count*2` mismatch 拒絕；
request ID 正整數、嚴格遞增、不可重用；allowed ASR ERROR code whitelist（4 個）/ unknown fail；
allowed TTS ERROR code whitelist（3 個）/ unknown fail；SHUTDOWN 只在 READY 合法 /
`SHUTDOWN_ACK` 後 STOPPED。

### T6 — READY / process cleanup（L279–L292, L380, L442）

`M4A-IPC-001`「READY mismatch / process cleanup cases（T6）」表：
ASR READY exact 5-key check，任一 mismatch → SIGTERM PGID → bounded wait → SIGKILL →
waitpid → IPC / workdir 清除 → 不進 READY；TTS READY exact 4-key check，同樣路徑；
ASR nested session：whisper PGID 必須等於 supervisor PGID；
nested descendant cleanup：force-abort 後所有 descendant exit proof，process/thread/fd/temp = 0；
TTS top-level group 等價斷言；next-success after cleanup 驗 rebuild 後可成功。
`M4A-ASR-003`（L380）「Nested descendant cleanup（T6）」row及
`M4A-TTS-002`（L442）real-child row對應PGID、waitpid與cleanup斷言。

### T7 — ASR fixed endpoint / decoder（L315–L334）

`M4A-ASR-001`（L296）新增「Fixed endpoint / decoder parameters（T7）」表（13 items）：
500 ms pre-speech ring（25 frame）、512-sample Silero window、64-sample context、
speech-end 後恰 600 ms post-padding（30 frame）、ENDPOINT 後不 pull input、
每 request state reset；injected whisper invocation capture 驗 4 threads、`language="zh"`、
greedy best-of-1、temperature=0、timestamps/translate/internal-VAD/context 全 off、
prompt checksum 等於 product lock。

### T8 — TTS fixed generation / conversion（L394–L419）

`M4A-TTS-001`（L384）新增「Fixed generation parameters（T8）」表（11 items）：
injected Matcha invocation 驗 `sid=0`、`speed=1.0`、CPU provider、2 threads、
max one sentence；float→S16_LE oracle 固定引用 Accepted `audio_m4`
`float_samples_to_s16le`：≤ -1.0 → -32768、≥ 1.0 → 32767、其餘 `round(value*32767)`；
oracle vector `[-2,-1,-0.5,0,0.5,1,2]` → `[-32768,-32768,-16384,0,16384,32767,32767]`；
byte-level little-endian 驗；conversion call count = 1；`payload_bytes = sample_count * 2`；
`sha256(payload) == pcm_sha256`。

### T9 — Privacy domains（L153–L167, L447–L475）

L153「Privacy Domain 分離（T9）」全域節：明分 Domain A（formal runner metadata，必須保留
`command`/`raw_logs`，但 command 不得含 credential/transcript/TTS text/PCM）與
Domain B（M4a product parent/child stdout/stderr/structured result/raw log，sentinel scan）。
`M4A-PRIV-001`（L447）scope 改為「Domain B product output sentinel scan」，加入
「Domain A runner metadata 不適用」明確說明；result locator 優先 run-root-relative。

### T10 — Locator resolver seam（L556–L569）

`M4A-INH-001`（L545）新增「Locator resolver seam（T10）」表（6 cases）：
valid bytes / missing / unreadable / directory-not-file / wrong content / non-empty-but-missing。
只有 resolver 取得 content 且 `sha256(content) == poc_sha256` 才接受；
單純非空字串不通過。Formal Tester review 使用同一語意。

### T11 — Inheritance identity（L571–L587）

`M4A-INH-001`「Inheritance identity（T11）」表（13 conditions）：
`accepted_audio_sha` exact `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`；
`poc_sha256` 64 lowercase hex 且與 resolved content sha256 相符；
`delta_test_id` 屬本規格 13 ID；`delta_result` ∈ `{PASS,FAIL,BLOCKED}`；
PASS locator 可解析且 hash 吻合；所有 `product_sha` 相同且等於外部 frozen candidate SHA；
`product_sha` 非 HEAD-derived；裸「沿用POC」fail closed；generator 不寫正式 evidence；
缺欄 / 混 SHA / locator 不存在 fail closed；wrong Accepted SHA / mixed product SHA fail closed。

### T12 — Revision summary（本節）

本修訂 summary 逐項列 T1～T11 的 `test_spec_M4.md` 行號與處置（見上）。
13 個 Test ID 完整保留。`M4-REG-001` 原文未變（L7–L33）。
Tester submission曾將YAML status改為`Revised`；本輪Designer複審後已改為`Resolved`。
Tester未修改Designer-owned design/model/milestone文件、runner、`src/`或`tests/`。

### Binding checklist 對照（T1～T12）

| Item | 處置 | 行號 |
| :--- | :--- | :--- |
| T1 Canonical commands | ✓ 替換為 `candidate_gate.py` 精確命令 | L48–L97 |
| T2 Exact runner schema | ✓ Common / Portable / Preflight tables + Matrix段落，欄位名稱與runner一致 | L99–L151 |
| T3 Identity / status wording | ✓ run_id regex、`Pass|Fail`、Pending 語意 | L115, L148–L151 |
| T4 CFG/LOCK factory seam | ✓ 8 factory seam cases + mock/null no-read | L171–L207, L211–L232 |
| T5 IPC exact bounds/state | ✓ 16 KiB / 64 MiB boundary、request ID、ERROR whitelist、SHUTDOWN state | L236–L277 |
| T6 READY/process cleanup | ✓ ASR/TTS READY 5/4-key check + PGID + descendant cleanup | L279–L292, L380, L442 |
| T7 ASR fixed endpoint/decoder | ✓ 500ms/512/64/600ms/reset + whisper參數capture | L315–L334 |
| T8 TTS fixed generation/conversion | ✓ Matcha 5-param + float→S16_LE oracle vector | L394–L419 |
| T9 Privacy domains | ✓ Domain A/B 分離 + M4A-PRIV-001 scope 修正 | L153–L167, L447–L475 |
| T10 Locator resolver seam | ✓ 6 resolver cases + 非空字串不通過 | L556–L569 |
| T11 Inheritance identity | ✓ 13 conditions + exact Accepted SHA + mixed SHA fail closed | L571–L587 |
| T12 Revision summary | ✓ 本節，含行號引用 | — |

## 1. Blocking finding: current M4 spec does not cover M4a

### Contract basis

`docs/milestones/M4.md` §6.1 / §6.4、`DELIVERY-AUDIO-POC-M4A-CONTRACT-001` §7.1、`docs/protocol.md` Audio v1、`docs/implement/ch10_config.md` M4a extension及`docs/implement/ch_m4a_audio_production.md` §9要求Core Gate 3對產品exact SHA重驗adapter/HAL wiring、config/lock/packaging、RM/SM lifecycle、composition、resource、offline及inheritance mapping。

### Evidence

現有`docs/test_spec/test_spec_M4.md`只定義`M4-REG-001` early memory preflight，且文件明確聲明它不是milestone gate、不取代M4A-P9或產品exact-SHA acceptance。它沒有real ASR、real TTS、child protocol、failure/recovery、offline、packaging或inheritance Test ID，因此若直接進Developer會形成POC PASS被誤當Core PASS的false green。

### Expected / actual / impact

- Expected：每個M4a production design requirement都有可觀察Test ID、portable/target scope、candidate identity與evidence欄位。
- Actual：只有diagnostic memory wrapper。
- Impact：無法簽核100% coverage；Developer不得開始M4A-WP-09～13 production implementation。

### Preferred revision

保留`M4-REG-001`原文，新增獨立「M4a Gate 3」章節，至少逐項納入下列Test ID，不重複POC candidate comparison：

| Required Test ID | Minimum coverage |
| :--- | :--- |
| `M4A-CFG-001` | real strict equality / required paths；mock/null exemption；lazy import；invalid config pre-hardware |
| `M4A-LOCK-001` | exact Accepted identity；missing/extra/hash/version/interpreter/arch/profile negative cases；zero artifact on fail |
| `M4A-IPC-001` | Audio Protocol v1 exact schema/bounds；fragment/coalesce；frame credit；wrong/duplicate request/sequence/hash；BUSY/EOF/late terminal/privacy |
| `M4A-ASR-001` | 640-byte frames、fixed Silero endpoint、no resample、nonempty transcript、request-local state |
| `M4A-ASR-002` | persistent load、success/empty/error/reopen、no hidden context |
| `M4A-ASR-003` | timeout/cancel/force-abort/crash、waitpid/cleanup、ASR key、RM recovery barrier、same-baseline recovery |
| `M4A-TTS-001` | fixed text→16 kHz mono S16_LE→AudioOutput completion；voice/profile/checksum identity |
| `M4A-TTS-002` | persistent load、error/timeout/cancel/force-abort、cleanup、TTS key、RM recovery |
| `M4A-PRIV-001` | transcript/prompt/TTS text/raw output/PCM/credential/private path不進log/result |
| `M4A-OFF-001` | disabled network namespace下real ASR/TTS/HAL session；no network/downloader |
| `M4A-RES-001` | Core process tree resource/thermal/cleanup；real LLM combined row在Accepted M4b前保持Pending |
| `M4A-PKG-001` | clean offline install、exact product lock、required notices、Matcha Accepted Risk |
| `M4A-INH-001` | POC→product matrix required fields、same product SHA、locator存在；禁止bare「沿用POC」 |

Tester可用table-driven或現有測試擴充，不要求每個Test ID一個function。Portable tests用deterministic child doubles且不得importreal engines；Pi tests用external provisional/frozen SHA、bounded timeout、fresh output。每張正式result至少含run ID、40-char SHA、完整command、platform/Python、start/end、exit/status/raw log；preflight另含artifact/config checksum。

### Minimum acceptance

1. 上表13項都有test-spec row與contract traceability；
2. portable / Pi / manual / evidence type清楚，未執行Pi項為Pending而非Skip/Pass；
3. injected failure逐列定義expected status、不得產生的artifact、cleanup/identity assertion及next-success recovery；
4. `M4A-RES-001`不以Audio POC surrogate或`M4-REG-001`取代真實combined row；
5. milestone conclusion要求M4a/M4b/M4c同一product SHA，不拼接run ID。

## 2. Revision boundary

應修改：`docs/test_spec/test_spec_M4.md`。若Tester需要補runbook，可新增M4a target section，但不得修改Designer-ownedmodel/design/milestone文件、`src/`或`tests/`。

不需重開：Audio POC Gate 2B、M2A/M2B candidate comparison、M3 HAL acceptance、`M4-REG-001`已核准的diagnostic semantics。

## 3. Review state

此輪共有三組Blocking finding，且已列出完整直接影響面。Tester提交revision並標記`Revised`後，Designer只核對本三組finding、T1～T12及revision新造成的regression；Advisory不阻擋sign-off。

## 4. Designer coverage review（2026-08-26）

### Review result

數量與基本結構檢查通過：`M4-REG-001`原文未修改，13個M4A Test ID均有獨立章節，且`git diff --check`通過。但Test ID存在不等於設計已100%覆蓋；以下3組Blocking會造成正式命令不可執行、已核准行為無驗收或evidence false-pass，因此本輪退回Tester。

### TR-M4A-001 [Blocking] Candidate命令與evidence schema偏離既有runner

- **契約依據**：`docs/runbooks/candidate_hardware_gate.md` §1、§3、§4及`docs/roles/workflow.md` §4要求同一外部candidate SHA依序執行`candidate_gate.py portable`三版本、`matrix`、`preflight`與`accept`，保存既有runner result及raw log。
- **實際證據／根因**：`test_spec_M4.md`「Candidate SHA與Evidence」自行定義`run_id=acceptance/<run-id>/`、uppercase status、flat `python_version`／`start_time`／`end_time`／`raw_log_path`，命令又直接把`--timeout`、`--run-id`及`--candidate-sha`傳給pytest。現有`scripts/candidate_gate.py`要求run ID是3–128字元safe token，使用`--timeout-seconds`，並輸出nested `python`、`started_at_utc`、`ended_at_utc`、`raw_logs`、`Pass|Fail`、JUnit及`result.json`；本環境`pytest --help`亦沒有上述三個test-spec參數。
- **預期／實際／影響**：預期是單一既有runner contract；實際規格要求另一套不存在的CLI與schema。Developer照規格實作會直接遇到argument error，或另造平行runner，portable matrix／Pi preflight因欄位不相容而無法驗證，形成不可執行gate或假綠燈。
- **首選修法**：刪除直接pytest命令與平行result schema，逐字採用runbook的`portable`、`matrix`、`preflight`、`accept` command shapes。`run_id`只保存safe token，`acceptance/<run-id>/`是output directory；正式portable必須對同一SHA/run ID完整跑3.11、3.12、3.13後建立matrix index。各Test ID的result card只能擴充測項欄位，不得改名或取代runner既有identity／time／status／raw-log欄位；`Pending`只表示尚未執行的規格狀態，不可冒充正式runner Pass。
- **應修改**：`test_spec_M4.md` lines 48–75及各Test ID的`Evidence type`／result-card敘述。**不需修改**：`scripts/candidate_gate.py`、runbook、`M4-REG-001`、product code或tests。
- **最低驗收／regression**：spec列出三個portable命令、一個matrix、一個preflight及一個accept命令；所有參數可由現有parser接受；三版本使用同一SHA/run ID；evidence欄位與runner exact一致；不得新增pytest plugin依賴或要求development push執行三版本matrix。

### TR-M4A-002 [Blocking] 已核准factory、protocol與engine runtime細節未被assert

- **契約依據**：`ch_m4a_audio_production.md` §5.2、§6.2、§7.2及`docs/protocol.md` §1／§4／§5固定factory lock injection、wire bounds、READY／shutdown／terminal lifecycle、ASR endpoint/decoder與TTS generation/PCM conversion；`IR_review_M4A_I` Finding 1最低驗收另要求factory signature與lock injection regression。
- **實際證據／根因**：目前CFG／LOCK只驗config與lock可建立，未證明對外factory仍只接收`cfg`、parsed lock確實以keyword-only `lock`交給正確adapter，以及mock/null不讀lock。IPC缺少exact max-boundary、READY mismatch cleanup、strict increasing/non-reused request ID、allowed ERROR code、SHUTDOWN及nested descendant cleanup。ASR未assert 500 ms pre-speech、512-sample window、64-sample context、600 ms post-padding及固定whisper參數；TTS未assert`sid=0`、speed 1.0、2 threads、max-one-sentence與固定clamp/round conversion。
- **預期／實際／影響**：預期是已核准production contract每個normative行為都有可觀察assertion；實際只覆蓋高階成功／失敗名稱。錯誤依賴注入、endpoint drift、decoder profile drift、wire boundary或PCM conversion drift均可能在13個ID全綠時漏過。
- **首選修法**：不新增Test ID；在`M4A-CFG-001`／`LOCK-001`加入factory signature、exact parsed-lock injection及mock/null no-read cases；在`IPC-001`加入16 KiB與64 MiB inclusive/exceeded boundary、READY mismatch termination proof、request/error/shutdown state cases及nested descendant cleanup；在`ASR-001`加入endpoint/padding/decoder table；在`TTS-001`加入generation參數與float→S16_LE boundary conversion table。可用table-driven或既有測試擴充，不要求每項獨立function。
- **應修改**：上述5個Test ID的assertion tables。**不需重開**：已充分覆蓋的ASR/TTS recovery cases、POC quality比較、M3 HAL acceptance。
- **最低驗收／regression**：每個新增case同時列input/injection、expected status/value、不得產生的artifact及必要cleanup；READY/protocol failure必須termination proof且不得轉empty/normal error；factory invalid lock不得import native engine或建立child；ASR/TTS參數必須等於已核准baseline。

### TR-M4A-003 [Blocking] Privacy domain與inheritance locator可形成false-pass

- **契約依據**：workflow要求正式result保留完整command與raw-log locator；`ch_m4a_audio_production.md` §4.2只禁止產品parent/child log保存private payload／完整私人路徑。§10與`M4A-INH-001`則要求locator存在、POC checksum可驗、same product SHA且缺件fail closed。
- **實際證據／根因**：全域schema要求完整command並允許absolute raw-log path，但`M4A-PRIV-001`又對整份result禁止private path，未區分formal runner metadata與product process log。`M4A-INH-001`把「locator存在且可查」實作成只檢查非空字串，且只檢查`poc_sha256`欄位存在，未核對locator實際內容checksum。
- **預期／實際／影響**：預期是必要identity metadata保留、private audio/text/credential不洩漏，且inheritance locator能實際解析並驗hash；實際規格可能刪掉必備command，亦會讓`"missing-but-nonempty"` locator與任意checksum通過。
- **首選修法**：明分兩個domain：candidate runner result保存既有完整command與受控locator，但command不得含credential/private payload；M4A product parent/child stdout/stderr/result payload才執行敏感sentinel掃描。正式公開evidence使用run-root-relative locator或明確sanitized path。`INH-001`對local locator要求存在、可讀且SHA-256等於`poc_sha256`；對核准external locator則要求可解析的durable reference及對應checksum evidence；同時驗`accepted_audio_sha` exact值與所有列`product_sha`一致。
- **應修改**：全域evidence schema、`M4A-PRIV-001`與`M4A-INH-001`。**不需修改**：產品privacy設計、既有runner輸出或Tester-owned正式evidence目錄權責。
- **最低驗收／regression**：合法runner command metadata不被privacy case誤殺；含transcript/TTS text/PCM/credential的product log必Fail；missing/unreadable locator、hash mismatch、wrong Accepted Audio SHA或mixed product SHA均fail closed；單純非空locator不得Pass。

### Historical binding one-round revision checklist（fulfilled）

以下清單是本輪完整且具約束力的修訂範圍。Tester完成全部`T1`～`T12`並在revision summary逐項引用行號後，Designer複審不得再加入本輪原可識別的新Blocking；除非revision自身造成新的安全、資料破壞或candidate identity regression，否則未列事項只能作Advisory且不阻擋`Resolved`。

#### A. 直接替換全域runner／evidence段落

- [x] **T1 — Canonical commands**：將`test_spec_M4.md`目前直接pytest命令替換為下列命令；`<portable-run>`三版本與matrix完全相同，`<acceptance-run>`在preflight與accept完全相同。Portable各版本目錄、matrix index及preflight的`<acceptance-root>`啟動時必須不存在；accept必須重用preflight建立的`<acceptance-root>`，但`result.json`必須不存在：

```text
python3 scripts/candidate_gate.py portable --candidate-sha <40hex> --run-id <portable-run> --python 3.11 --suite <m4a-portable-suite> --timeout-seconds <N> --output <portable-root>/python-3.11
python3 scripts/candidate_gate.py portable --candidate-sha <40hex> --run-id <portable-run> --python 3.12 --suite <m4a-portable-suite> --timeout-seconds <N> --output <portable-root>/python-3.12
python3 scripts/candidate_gate.py portable --candidate-sha <40hex> --run-id <portable-run> --python 3.13 --suite <m4a-portable-suite> --timeout-seconds <N> --output <portable-root>/python-3.13
python3 scripts/candidate_gate.py matrix --candidate-sha <40hex> --run-id <portable-run> --input-root <portable-root> --output <portable-root>/matrix-index.json
python3 scripts/candidate_gate.py preflight --candidate-sha <40hex> --run-id <acceptance-run> --portable-index <portable-root>/matrix-index.json --runtime 3.13 --hardware <hardware.json> --config <sanitized-config.yaml> --artifact-manifest <artifacts.json> --output <acceptance-root>
python3 scripts/candidate_gate.py accept --candidate-sha <40hex> --run-id <acceptance-run> --preflight <acceptance-root>/preflight.json --suite <m4a-rpi-suite> --timeout-seconds <N> --output <acceptance-root>
```

- [x] **T2 — Exact runner schema**：全域欄位不得另命名。Base result引用`candidate_sha`、`command`（argv）、`mode`、`platform`、`python.{implementation,version}`、`run_id`、`started_at_utc`；portable／acceptance suite result另有`ended_at_utc`、`exit_code`、`status`、`raw_logs`、`counts.{passed,failed,skipped,xfailed}`、`suite`、`suite_command`、`timeout_seconds`，portable再含`python_minor`；preflight另有`checksums.{artifact_manifest,config,hardware}.{path,sha256}`、`ended_at_utc`、`exit_code`、`portable_index`、`portable_run_id`、`runtime`、`status`。Matrix依runner保存自己的index schema。Test-specific card可增加`test_id`與metric，但不得刪除、改名或取代該模式既有欄位。
- [x] **T3 — Identity/status wording**：`run_id`明定為符合`^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$`的token；output directory另記，不把路徑塞入run ID。Formal runner狀態依既有schema為`Pass|Fail`，debug成功為`Diagnostic`；尚未執行的Pi／combined項目只在spec tracker記`Pending`，不得產生formal Pass。Portable evidence為runner `result.json`＋JUnit＋raw logs＋matrix index，不要求pytest JSON plugin。

#### B. 補入既有5個Test ID，不新增ID

- [x] **T4 — CFG/LOCK factory seam**：`M4A-CFG-001`／`M4A-LOCK-001`加入ASR與TTS兩組table-driven cases：(a) `inspect.signature`確認public factory只有`cfg`；(b) injected parser回傳sentinel `AudioArtifactLock`，fake adapter constructor收到同一object identity且只經keyword-only `lock`；(c) mock/null parser call count為0；(d) missing/malformed/identity-mismatch lock時adapter/native import、child spawn、Audio HAL及workdir call count全為0。
- [x] **T5 — IPC exact bounds/state**：`M4A-IPC-001`加入16 KiB control line exact-max accepted與max+1 rejected（newline計入frame長度）、TTS PCM exact 64 MiB accepted與超限／odd／`sample_count*2` mismatch rejected；加入request ID為正整數、嚴格遞增、不可重用，ASR/TTS allowed ERROR code whitelist、unknown code failure，以及SHUTDOWN只在READY合法且`SHUTDOWN_ACK`後STOPPED。
- [x] **T6 — READY/process cleanup**：`M4A-IPC-001`加入ASR/TTS READY exact-key與每個identity mismatch case；每個case均要求TERM→bounded wait→KILL-if-needed→waitpid、IPC/workdir清除及不得進READY。`M4A-ASR-003`加入ASR supervisor child與native whisper descendant同一PGID、不得nested session，以及force-abort後descendant/process/thread/fd/temp全為0與next-success；TTS維持單一top-level group等價assertion。
- [x] **T7 — ASR fixed endpoint/decoder**：`M4A-ASR-001`加入deterministic cases驗500 ms pre-speech ring（25個20 ms frame）、512-sample Silero window、64-sample context、speech-end後恰600 ms post-padding（30 frame）、ENDPOINT後不再pull input、每request state reset。另以injected whisper invocation capture驗4 threads、language `zh`、greedy best-of-1、temperature 0、timestamps/translate/internal-VAD/context皆off且prompt checksum等於product lock。
- [x] **T8 — TTS fixed generation/conversion**：`M4A-TTS-001`加入injected Matcha invocation驗`sid=0`、speed `1.0`、provider CPU、2 threads、max one sentence。Float→S16_LE conversion oracle固定引用Accepted `audio_m4`的`poc_audio/src/audio_poc/m4a_tts_quality.py::float_samples_to_s16le`：`<=-1.0→-32768`、`>=1.0→32767`、其餘`round(value*32767)`，只轉換一次並輸出little-endian；vector `[-2,-1,-0.5,0,0.5,1,2]`必須得到`[-32768,-32768,-16384,0,16384,32767,32767]`，並驗byte count/hash、最後even-length chunk及no resample。

#### C. 關閉privacy與inheritance false-pass

- [x] **T9 — Privacy domains**：全域規格明分formal candidate runner metadata與M4a product process output。Runner `command`／`raw_logs`必須保留，但command不得包含credential、transcript、TTS text或PCM；M4A parent/child stdout、stderr、structured product result及raw log以unique sentinels掃描transcript、TTS text、prompt、raw model output、PCM、credential與private work path，任一命中即Fail。Result locator優先使用run-root-relative path；若formal local card保留absolute path，公開delivery前須產生sanitized locator，不能刪除identity metadata假裝通過。
- [x] **T10 — Locator resolver seam**：`M4A-INH-001`定義單一injected locator resolver。Portable table至少含valid bytes、missing、unreadable、directory-not-file與wrong-content cases；只有resolver成功取得content且`sha256(content)==poc_sha256`才可接受。Formal Tester review對核准local／Git-controlled locator使用同一語意，不允許只檢查非空字串。
- [x] **T11 — Inheritance identity**：逐列驗`accepted_audio_sha`恰為`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`、`poc_sha256`為64 lowercase hex且與resolved content相符、`delta_test_id`屬本規格13 ID、`delta_result`屬`PASS|FAIL|BLOCKED`、PASS locator可解析、所有`product_sha`相同且等於外部frozen candidate SHA；wrong Accepted SHA、mixed product SHA、bare「沿用POC」或generator寫入正式evidence均fail closed。
- [x] **T12 — Revision summary**：Tester先提交逐項摘要並將status改回`Revised`；USER其後明確授權Designer接手剩餘test-spec修訂。Final Designer completion表已更新current locators、保留13個Test ID及`M4-REG-001`本體，並將本單標為`Resolved`；runner、src及tests均未修改。

### Historical re-review boundary（fulfilled）

Tester只需修訂`docs/test_spec/test_spec_M4.md`與本單revision summary，再將status改為`Revised`。Designer複審只逐項核對`T1`～`T12`及revision直接造成的regression：所有checkbox對應文字存在且互相一致、canonical commands／schema與現有runner吻合、13個ID仍完整、`M4-REG-001`未變，即將本單標為`Resolved`並交Developer建立WP-09～13。除revision新造成的安全／資料破壞／candidate identity問題外，不追加Blocking；其他新發現只能列Advisory且不阻擋本輪sign-off。
