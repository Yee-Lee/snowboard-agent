---
requestor: "Designer"
owner: "Tester"
status: "Rejected"
---

# TR_spec_M4B_I — M4b Gate 3 test-spec coverage submission

- **Milestone**: M4b Local LLM production integration
- **Submission date**: 2026-08-30
- **Target**: `docs/test_spec/test_spec_M4.md` — `M4b Gate 3 測試規格`
- **Entry dependency**: Fulfilled — `IR_review_M4B_I` is `Resolved`; Gate 2B final winner ACK is accepted
- **Decision requested**: Designer confirmation of 100% planned coverage and Development Ready
- **Current decision**: `DESIGNER REVIEW REJECTED — TESTER REVISION REQUIRED`

## 1. Submission boundary

Tester submits the complete M4b section required by
`docs/implement/ch_m4b_llm_production.md` §10 / §12 / §14. The submission defines 15 Test IDs,
portable and Pi scopes, one exact-SHA candidate flow, bounded execution, target cards, POC inheritance
and the retained r14 resource gates. It does not claim implementation complete, execute Gate 3,
accept M4b, reopen the POC result, or modify the already Accepted M4a conclusion.

## 2. Requirement closure matrix

| Test ID | Design closure | Planned observable coverage | Result |
| :--- | :--- | :--- | :--- |
| `M4B-CFG-001` | ch_m4b §3.1 / §7；Ch 10 | exact public/factory surfaces, strict real/mock config, three recovery ports, spawn isolation, same-owner ResourceSpec | COVERED |
| `M4B-LOCK-001` | ch_m4b §8；model spec §6.2 | strict nested keys, R3/runtime/native/model/profile/source/license identity, zero side effect, exact Pi preflight | COVERED |
| `M4B-IPC-001` | protocol §1 / §4.4 / §6；ch_m4b §3.1 / §10.1 | framing, exact frames, request/terminal state, canonical input, metrics, control, privacy, child authority and M4a regression guard | COVERED |
| `M4B-RDY-001` | protocol §4.1；ch_m4b §3.2 / §4 | authenticate/load/pre-warm/baseline state trace, fixed prompt, cleanup, READY identity, mismatch/rebuild/startup cleanup | COVERED |
| `M4B-GEN-001` | protocol §4.2；ch_m4b §4 | single-flight, persistent Engine, fresh Conversation, exact metrics/token limits and control-loop-only wire output | COVERED |
| `M4B-OUT-001` | ch_m4b §3.2 / §6；Ch 9 | exact generic renderer bytes, dynamic speak/tool/rest schema, markers, allowlist and independent Reasoner validation | COVERED |
| `M4B-P5-001` | ch_m4b §6；protocol §4.4 | recoverable input/generation/clean-timeout fallback versus protocol/recovery/fatal boundary and RM fatal monitor | COVERED |
| `M4B-CAN-001` | ch_m4b §5；Ch 6 | typed cancel, single native cancel, joined worker, TERM/KILL/waitpid, descendant/outer-task cleanup, recovery and Level 3 | COVERED |
| `M4B-REC-001` | ch_m4b §0.3 / §4 / §5.2 | raw-byte baseline-relative 8/48/768 triggers, unique-owner sampler, terminal-only ticket, same-lock replacement and fatal paths | COVERED |
| `M4B-HIST-001` | ch_m4b §6；protocol §4.2 | five current/prior-marker contamination cases, fresh KV/Conversation and expected generation boundary | COVERED |
| `M4B-PRIV-001` | ch_m4b §3.1 / §6 | Domain B sentinels over success and all cleanup/failure paths, sanitized evidence and Domain A preservation | COVERED |
| `M4B-OFF-001` | ch_m4b §8；model spec §6.2 | disabled-network real inference, zero attempts/downloader, isolated loaded paths/environment and no fallback | COVERED |
| `M4B-RES-001` | ch_m4b §10.2；model spec §6.4；M4 §6.4 | same-SHA M4a+M4b 20-session run, r14 vector/formulas, two replacements, complete owner samples, thermal/OOM/throttle/cleanup | COVERED |
| `M4B-PKG-001` | ch_m4b §8 | offline atomic install, no-follow inventory, controller dependency isolation, read-only preflight and complete Apache-2.0 notices | COVERED |
| `M4B-INH-001` | ch_m4b §9；M4 §6.4 | Core ACK versus POC identity, immutable SHA/locator/checksum, original machine result versus waiver, P1–P12 delta map and M4a regressions | COVERED |

## 3. Cross-cutting gate audit

1. **Formal runner** — M4b substitutes tracked `tests/m4b_portable_suite.txt` and the canonical
   `tests/milestones/test_m4_local_voice.py` into the approved T1 runner shape. Three portable minors
   share one SHA/run ID; one Pi `accept` command creates the exact 11-card M4B subset under one run ID,
   while required M4a composition cards may coexist.
2. **Timeouts** — portable suite timeout is 300 seconds; the single Pi suite timeout is 9000 seconds.
   Every Test ID also has a bounded case watchdog; these do not create additional formal results.
3. **Identity/evidence** — runner T2 fields remain authoritative. Test cards only add Test ID and
   metrics; preflight, matrix, cards, inheritance and conclusion all resolve to the same 40-hex SHA.
4. **Privacy/offline** — formal runner identity is retained while product output/evidence is scanned
   across success, rejection, timeout, cancel, protocol, cleanup and recovery paths. Runtime download,
   system-site, alternate model and endpoint fallback are prohibited.
5. **Resident-retention defect** — Attempt 006 P9/P10B machine FAIL and the User waiver remain separate.
   Core PASS still requires the full unfiltered r14 4/64 gates, complete samples, at least two completed
   replacements and zero cleanup residue on the product SHA.
6. **Inheritance** — rows bind the Core ACK, POC delivery, execution/closure/publication SHAs,
   manifest/evidence bytes, candidate/pairing, machine result, waiver, delta result and formal run.
   M4a regression rows use a separate typed array and cannot violate the 15-ID M4b enum.

## 4. Tester self-check evidence

The following read-only checks pass on the submitted worktree:

```text
git diff --check -- docs/test_spec/test_spec_M4.md
M4B heading count: 15
M4B case-watchdog count: 15
Design §10.2 versus spec heading ID diff: empty
Diff boundary before M4b: none; M4b is appended after the accepted 638-line M4a document
```

The review is specification-only, so no product pytest or Pi acceptance was run. Execution evidence
becomes mandatory after WP-01～06 implementation and a USER-approved provisional candidate SHA.

## 5. Review request and state

Tester self-audit has **Blocking 0**. Designer is requested to verify the matrix and cross-cutting
contracts once, then either:

- set this review to `Resolved` and record `DESIGNER COVERAGE APPROVED — DEVELOPMENT READY`; or
- set it to `Rejected` with all contract-backed Blocking findings in one response.

Until Designer changes the state to `Resolved`, M4b remains **not Development Ready** and Developer
must not start WP-01～06 based on this submission alone. Advisory findings do not block resolution.

## 6. Designer review — Round I（2026-08-30）

**Decision: Rejected — Blocking 6 / Advisory 0.**

Mechanical coverage is sound: the 15 design IDs, 15 M4B headings, 15 scopes and 15 case watchdogs
match exactly; `git diff --check` passes and the M4B section is appended after the unchanged M4a
lineage. The following findings are contract or false-pass defects, not requests for additional
features. Tester should revise only the cited rows and their directly affected evidence rules.

### TR-M4B-I-01 — Blocking：valid explicit recycle config與「任何YAML override失敗」互相矛盾

- **Basis**：`ch_m4b` §7與`ch10_config.md` §6／config example允許YAML明列locked
  `recycle_max_inference_attempts=8`、`recycle_owner_pss_delta_mib=48`、
  `recycle_min_mem_available_mib=768`；禁止的是放寬／漂移，不是合法欄位的存在。
- **Evidence / root cause**：`M4B-CFG-001`先要求「litert_lm valid — exact values」成功，後又規定
  `YAML覆寫recycle_*`任一欄一律`UnknownConfigKey`／`ConfigValueError`。同一份explicit exact YAML
  會同時被要求成功與失敗。
- **Impact**：Developer只能任選一側實作；可能錯誤拒絕repo已設計的production config，或讓相反測項
  假綠燈。
- **Preferred correction**：把該列改為「三欄explicit exact values均accepted；任一值偏離8／48／768
  才`ConfigValueError`」。`UnknownConfigKey`只保留給真正未知欄名。
- **Minimum regression**：同一table先載入explicit exact YAML成功，再各以一個below／above mutation
  失敗；invalid cases的native import、spawn、workdir、sampler與RM registration均為0。

### TR-M4B-I-02 — Blocking：pre-READY與single-flight admission可把違約frame送進child後仍通過

- **Basis**：`ch_m4b` §4 steps 3–4規定adapter只在READY配置request／送GENERATE；
  `protocol.md` §4.4規定BUSY只合法於已有active request的`GENERATING`，且parent→child
  GENERATE／CANCEL同樣受exact-key schema約束。
- **Evidence / root cause**：IPC missing-required-key matrix漏列GENERATE與CANCEL；`M4B-RDY-001`
  允許pre-warm中的child收到GENERATE後回`BUSY(state=GENERATING)`／`INVALID_REQUEST`；
  `M4B-GEN-001`只驗第二個caller得到BUSY，沒有驗第二個GENERATE wire write為0。這會把parent
  admission bug誤當成child防禦成功。
- **Impact**：AUTHENTICATING／STARTING／ENGINE_LOADED／PREWARMING可能提前送private request；
  concurrent call也可能真的送第二frame造成desync，仍被測成single-flight PASS。
- **Preferred correction**：
  1. IPC exact-key negative matrix加入GENERATE與CANCEL的missing／extra／wrong-type cases；
  2. RDY改驗上述四個non-READY parent state呼叫`generate()`皆local fail closed，child
     GENERATE/inference call count為0；
  3. GEN第二個concurrent call須立即BUSY且總GENERATE wire write仍為1，第一個active request不受影響；
  4. 另保留direct malformed-child injection時BUSY／INVALID_REQUEST的fatal mapping，但不得拿它替代
     parent admission assertion。
- **Minimum regression**：state-table × `generate()`；精確斷言write count、active request identity、
  terminal count與next-success。不得新增protocol state/code。

### TR-M4B-I-03 — Blocking：missing metrics的fatal結果被GEN規格放寬成P5

- **Basis**：`protocol.md` §4.4與`ch_m4b` §3.1明定production RESULT缺metrics或metric違約是
  protocol failure；不得建立`LLMGeneration`或轉P5。
- **Evidence / root cause**：`M4B-IPC-001`正確要求missing metrics為protocol failure，但
  `M4B-GEN-001`寫成「partial / missing metrics → P5 / ERROR」，允許等價實作走P5。
- **Impact**：破損／惡意child frame可被包裝成正常apology response，掩蓋process desync並跳過
  destructive cleanup／recovery。
- **Preferred correction**：GEN列改為只允許「protocol failure → no `LLMGeneration`／no P5 →
  terminate/waitpid → same-key recovery」；直接交叉引用IPC/CAN，無需複製整張metric matrix。
- **Minimum regression**：缺metrics、partial metrics、NaN／bool／越界各至少由table代表；斷言
  fallback `LLMResponse` count=0、child收斂、RecoveryTicket identity與replacement next-success。

### TR-M4B-I-04 — Blocking：target READY identity只驗三個digest，且initial baseline失敗無cleanup oracle

- **Basis**：`protocol.md` §4.4 READY identity有六欄；`ch_m4b` §4 step 3要求exact READY加完整
  post-prewarm owner baseline都成功後`start()`才return。
- **Evidence / root cause**：`M4B-RDY-001`的Pi exact-values列只列runtime/model/config digest，未列
  `candidate_id`、`pairing_revision`、`platform`；portable mismatch不能證明real worker wire值。
  同節只有baseline success barrier，沒有initial sampler missing／unreadable／invalid時的startup cleanup。
- **Impact**：Pi child可能自報錯candidate/pairing/platform仍形成target PASS；首次baseline failure亦可能
  留下已prewarm child、IPC或workdir。
- **Preferred correction**：Pi row列齊六個exact值並保存sanitized READY identity；新增initial baseline
  failure matrix，要求不emit/admit READY、`start()` raise、TERM/KILL/waitpid與IPC/workdir cleanup後
  next-start success。這不重開LOCK preflight；它驗的是real child wire與startup ownership。
- **Minimum regression**：六欄逐一real/controlled mismatch；baseline sample的missing field、unreadable、
  bool／negative至少table-driven覆蓋，且orphan/reader/fd/workdir為0。

### TR-M4B-I-05 — Blocking：shutdown撞RECOVERING只覆蓋happy path，漏掉已核准的Level 3 cleanup邊界

- **Basis**：`ch_m4b` §4 step 8及`ch05_resource_manager.md` §6.5規定`prepare_shutdown()`取消RM-owned
  recovery orchestration；未READY replacement cleanup失敗或timeout必須`RecoveryFatalError`→Level 3。
- **Evidence / root cause**：`M4B-CAN-001`只要求成功取消／等待recovery後reverse stop；Level 3表只寫一般
  rebuild/replacement failure，沒有shutdown cancellation cleanup exception／timeout及partial replacement
  residue oracle。
- **Impact**：shutdown race最危險的failure path可能留下replacement child或unretrieved recovery task，
  但所有現有case仍可PASS。
- **Preferred correction**：把該列改成success／cleanup exception／cleanup timeout三列；後兩者保留同一
  latched root cause、main exit 4、不得建立第二batch，並驗partial replacement與舊child皆無orphan。
- **Minimum regression**：injected recovery hook卡在prewarm，分別完成cleanup、raise與超時；斷言
  `prepare_shutdown()`／`rm.wait_fatal()`一致、exit 4一次、zero unretrieved-task warning。

### TR-M4B-I-06 — Blocking：inheritance的result oracle對LOCK／INH不可解析，且INH row形成自我證明

- **Basis**：T2現有`candidate_gate.py` portable/preflight result不含`test_id`，且只有acceptance mode
  建立／finalize test-specific cards；M4B正式card集合又刻意排除LOCK與INH。Inheritance PASS row卻要求
  locator內容同時帶candidate SHA、Test ID、run ID與status。
- **Evidence / root cause**：P11強制M4B-LOCK delta row；narrow-harness規則強制M4B-INH delta row。
  LOCK只有portable＋preflight，兩者皆無Test ID card；INH是用來驗`inheritance.json`本身，再要求該JSON
  內含指向M4B-INH PASS的row，形成未定義的自我證明。另`BLOCKED`被列為合法`delta_result`，但T2沒有
  `Blocked` runner status，也未定義可解析record。
- **Impact**：Developer不是無法產出formal inheritance，就是只能偽造card／只驗非空locator，破壞
  exact-SHA evidence closure。
- **Preferred correction**：
  1. 移除「inheritance內必須有`delta_test_id=M4B-INH-001`」的自指要求；M4B-INH作為整份index的
     generator＋Tester review gate，不拿自身結果證明自身。narrow harness→general renderer產品delta
     由一或多列`M4B-OUT-001`具體reason記錄；
  2. 明定scope-aware oracle：Pi ID指向finalized acceptance card；LOCK指向同run preflight加
     `m4b_llm_product.py preflight`的identity-bound reconciliation record；若其他portable ID要入row，
     使用Tester產生、綁三minor runner/JUnit locators與digest的reconciliation record，不把suite
     `result.json`假稱含Test ID；
  3. final Gate 3 inheritance只允許`PASS/FAIL`。若仍要保留development `BLOCKED`，另定exact blocked
     record schema且禁止它出現在Accepted output。
- **Minimum regression**：target／preflight／portable三種valid proof各一；raw suite result冒充Test-ID
  card、INH self-row、unresolved reconciliation、mixed SHA/run/Test ID及Accepted output含BLOCKED均fail。

## 7. Re-review gate

Tester修訂後將YAML status改回`Revised`，並在本單逐項回覆`TR-M4B-I-01`～`06`的修改位置。
Designer複審只核對這六項、其直接影響面與修正新造成的regression；其餘已通過的15-ID mechanical
coverage、M4a append-only boundary、r14 resource gates、privacy/offline/package內容不重開。
