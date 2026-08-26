---
requestor: "Designer"
owner: "Tester"
status: "Open"
---

# TR_spec_M4_I — M4a Gate 3 test-spec coverage request

- **Milestone**: M4a Accepted Audio production integration
- **Request date**: 2026-08-26
- **Target**: `docs/test_spec/test_spec_M4.md`
- **Entry dependency**: Reviewer approval of `docs/model_spec.md`、`docs/protocol.md` Audio v1、`docs/implement/ch_m4a_audio_production.md`與`docs/implement/ch10_config.md` M4a extension
- **Activation**: Queued；Tester在`IR_review_IV` Resolved前不修改test spec
- **Decision**: `REVISION REQUIRED BEFORE DEVELOPMENT`

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

此輪只有一個Blocking finding且首輪已列出完整直接影響面。Tester提交revision並標記`Revised`後，Designer只核對本finding、直接影響範圍及revision新造成的regression；Advisory不阻擋sign-off。
