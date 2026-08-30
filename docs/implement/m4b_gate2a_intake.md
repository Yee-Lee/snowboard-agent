# M4b Gate 2A result intake and decision contract

狀態：**Historical Gate 2A intake complete；Gate 2B later closed with Gemma POC winner Accepted**。

本文件保存Core Designer對LLM POC Gate 2A完成回交的fail-closed intake與decision record。一般判定
規則仍保留於後續各節；實際結果以§0及
`DELIVERY-LLM-POC-M4B-GATE2A-PROVISIONAL-ACK-001`為準。它在建立當時不授權Gate 2B、不取代POC
immutable manifest / raw evidence，也不把User的model-finalist選擇改寫成current product-config
PASS。後續現況由`DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001`與`model_spec.md` §6控制。

## 0. Actual Gate 2A intake（2026-08-29）

| Identity | Accepted record |
| :--- | :--- |
| POC closure | `llm` / `3c012eb65cc7c8b706fe1c29a3fcafab17696d0f` |
| Gate 2A execution | `e2b59fac609e0d768ff3554754363900cbed70a9` |
| Gate 2A execution-surface SHA-256 | `eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1` |
| User assessment | `ASSESSMENT-LLM-M3-GATE2A-20260829-USER-REVIEW` |
| POC closure delivery | `DELIVERY-021-PM-LLM-POC-GATE2A-CLOSURE-GEMMA-FINALIST` |
| Core decision | `DELIVERY-LLM-POC-M4B-GATE2A-PROVISIONAL-ACK-001` |
| Selected model finalist | `CAND-LRT-G4E2B-MOBILE-R1` / Gemma 4 E2B mobile |
| Rejected formal Gate 2B candidate | `CAND-LRT-Q25-15B-Q8-R1` / Qwen2.5 1.5B Q8 |

| Candidate / run | P2 | P3 | P4 | P5 | P8 | Sanitized SHA-256 | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Qwen / `G2A-PI-QWEN-004` | `FAIL` 0/30 | `PASS` | `Core threshold decision required` | `PASS` | `FAIL / DEPENDENCY_LIMITED_BY_P2` | `e0c000df51c26af5c9cc1f1704f13b8b8816b087d64ba596808b4e3be5b4530f` | excluded from formal Gate 2B |
| Gemma / `G2A-PI-GEMMA-002` | `FAIL` 3/30 | `PASS` | `PASS` | `PASS` | `FAIL / DEPENDENCY_LIMITED_BY_P2` | `41f1d8e4f74bac25fd83a17fd0bdb776e9cb0bae1c4c04fdc345f378592681e7` | sole model finalist；R1 pairing not product-eligible |

User assessment確認兩個final run分別使用fresh boot、相同clean execution surface、read-only authenticated
artifacts、offline namespace、`swap=0`、zero full-model rehash、clean log scan與zero residue。Core接受這份
完成的User evidence review作Gate 2A model-selection authority；raw evidence依packet留在Git外且不可改寫。
Gate 2B consumer receipt須把operator提供的sanitized result檔綁定run ID、checksum及bytes。

## 1. Frozen authorization baseline

| Identity | Required value |
| :--- | :--- |
| Authorization | `DELIVERY-LLM-POC-M4B-GATE2A-PI-AUTH-001` |
| Gate 1 closure | `DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001` |
| POC branch / authorized starting SHA | `llm` / `ed7aaca2e187b2287d442d6841e1ab2610b67570` |
| Gate 2A lock SHA-256 | `2a57754362d30d74c616a58a368bb79208493bc1fdb04b2cf1242c5b68fc683e` |
| Gate 2B lock SHA-256 | `5c89ca0b3499b8983361594ab41869872f189b1b410bf4f3333cac2a780fe775` |
| Platform | Raspberry Pi 5 4 GB / Debian 13 aarch64 / `swap=0` |
| Gate 2A executed items | P2 / P3 / P4 / P5 / P8 only |
| Immutable carried items | P1 / P6.1 / P7.1 / P10A / P11 / P12 |
| Retained candidates | Gemma 4 E2B；Qwen2.5 1.5B Q8 with defect waiver |

授權後的append-only fixes與final execution identity記於§0；每次replacement均須保留ancestor lineage與新
lock。任一未記錄的source、candidate/pairing、runtime/model/config、protocol/fixture或platform drift，
不得以「結果看起來合理」接受。受影響item標`INCONCLUSIVE`並要求append-only replacement candidate /
run；不得回寫或重用原run identity。

## 2. Required result packet

兩名candidate各自必須有一個clean-reboot、fresh-run namespace，並提交：

```text
Gate 2A delivery / response path
POC exact SHA and clean-check result
Gate 2A lock path + reproduced SHA-256
candidate manifest / acquisition manifest / selected Pi config paths + SHA-256
runtime / dependency / adapter-binding / deployed-model identities
boot ID, run ID, start/end timestamps and bounded command
P2 / P3 / P4 / P5 / P8 sanitized result rows
raw evidence locators + content SHA-256
offline / network-disabled proof
swap / temperature / throttling / OOM diagnostics
exit code, timeout status, process/descendant/FD/temp cleanup result
immutable carried Gate 1 result locators and checksums
cumulative scorecard and recommendation rationale
```

Raw prompt、model output、payload、credential、endpoint、host identity、model bytes、wheel或native binary
不得進Core Git。Sanitized result必須足以驗identity、method、status、metric與cleanup，但不可用摘要取代
raw locator/checksum。

## 3. Intake order

Core Designer依下列順序審核；前一步失敗即停止給candidate credit，但仍保存delivery作歷史證據。

### I1 — source and lock identity

- delivery引用完整40-character POC SHA且可解析為授權SHA；
- checkout clean；Gate 2A lock重算完全吻合；
- candidate manifest、acquisition manifest、Pi config、runtime/model/protocol/fixture identity與lock一致；
- evidence manifest不得引用branch HEAD、未固定tag或另一platform config。

### I2 — execution allocation and isolation

- 每candidate使用不同boot ID、run ID與evidence root；
- 只執行P2/P3/P4/P5/P8；不得重跑P7.1改分或把Gate 1 try-run複製成Gate 2A credit；
- Pi 5 4GB、Debian 13 aarch64、swap zero、offline與bounded timeout成立；
- infrastructure/debug attempt不得與formal result合併。

### I3 — result and raw evidence binding

- mandatory P item只有一個formal status：`PASS`、`FAIL`或`INCONCLUSIVE`；P4是既有
  negotiable performance例外，可記`Core threshold decision required`，不得自行改成PASS；
- sanitized row的candidate/run/Test ID/command/timestamp/metric/status與raw locator一致；
- raw artifact checksum可重算，缺件或checksum mismatch為`INCONCLUSIVE`，不是candidate FAIL。

### I4 — cleanup, offline and privacy

- command exit / timeout與status一致；無orphan、descendant、open FD、temp artifact或stale owner；
- network disabled且沒有external attempt、downloader、credential或fallback；
- swap used / in / out均為0，無OOM/kernel pressure，temperature / throttling有記錄；
- committed log/result不含prompt、raw output、payload、credential或private path。

### I5 — cumulative carry-forward

- Gate 1 execution是Gate 2A execution commit ancestor，且carry-forward guard確認execution surface未漂移；
- Gemma P1/P6.1/P7.1/P10A/P11/P12原結果逐項引用；
- Qwen P7.1仍是`FAIL / SLOW_RECOVERY`，ten-second threshold與`18152.025 ms`觀測不改寫；
- cumulative scorecard只加入P2/P3/P4/P5/P8，不平均、刪除或重跑既有FAIL。

## 4. P-item decision checklist

| Item | Required adjudication |
| :--- | :--- |
| P2 | Exact product result keys與speak/tool/rest payload/next-perception contract逐case可驗；任一normal case不合即FAIL |
| P3 | Frozen catalog/repetition、fallback與log hygiene完整；不得以平均掩蓋單一schema/privacy failure |
| P4 | Cold/hot raw samples、P50/P95與tok/s齊全；只依既有threshold分類，不在intake後改method |
| P5 | 同一predeclared continuous request在15秒timeout，terminal、health/rebuild與cleanup完整；不得用早停fixture避開timeout |
| P8 | 五個single-turn無history污染；runtime/model identity不變，不能靠每turn重載engine通過 |

Core直接執行或直接custody的mandatory item須有可定位證據。若POC raw evidence依packet留在Git外且由
USER完成正式review，Core可用該User assessment、exact run ID、sanitized checksum/bytes與closure delivery
作model-selection authority；不得宣稱Core重算raw。未經User review的`PASS`若缺locator/checksum、cleanup
或identity assertion，仍須降為`INCONCLUSIVE`，不得以一般文件敘述補證。

## 5. Provisional selection matrix

| Condition | Designer disposition |
| :--- | :--- |
| Gemma mandatory cumulative items全PASS；P4已完成或取得Core threshold decision | `ELIGIBLE FOR PROVISIONAL ACK` |
| Qwen Gate 2A items全PASS，但P7.1仍FAIL且尚無書面workaround disposition | `NOT RECOMMENDABLE YET — DEFECT DISPOSITION REQUIRED` |
| Qwen Gate 2A items全PASS，且Core/USER接受符合§6的workaround | `ELIGIBLE WITH IMMUTABLE P7.1 FAIL / ACCEPTED WORKAROUND` |
| P2/P8證明current pairing失敗，但User依DELIVERY-019 semantic split選出underlying model | `MODEL FINALIST ONLY`；current pairing不得進Gate 2B，先建立new integration-qualified revision |
| 任一mandatory item FAIL | candidate不進Gate 2B；保留原evidence，不補寫PASS |
| 任一identity/evidence/cleanup不足 | `INCONCLUSIVE`；append-only新run，不拼接 |
| 兩candidate都不eligible | `NO PROVISIONAL FINALIST`；Gate 2B保持Blocked，交USER/Core決定新cycle/no-go |
| 兩candidate都eligible | 依frozen cumulative scorecard與residual risk選最多一名；不得把Gate 2B當第二輪candidate比較 |

Provisional ACK必須同時列出rejected candidate與理由，避免只公布winner而遺失FAIL / waiver lineage。

## 6. Qwen workaround disposition（historical rule；not activated）

實際Gate 2A decision已排除Qwen，不建立workaround、不做threshold decision，也不讓30秒operational
observation進產品config。下表保留作immutable decision lineage，不是open task。

任何Qwen provisional recommendation都必須有Core/USER書面裁決，至少回答：

| Field | Required content |
| :--- | :--- |
| Original defect | P7.1 `FAIL / SLOW_RECOVERY`；10秒SLA；observed rebuild READY `18152.025 ms` |
| Score treatment | FAIL與原receipt保持不變；workaround不回寫POC score |
| Proposed product mechanism | 精確process owner、state transition、startup/recovery順序及memory owner |
| Failure convergence | workaround失敗時如何TERM/KILL/waitpid、barrier或Level 3；不得fallback雲端/另一model |
| 4GB impact | 與Accepted Audio同時常駐的capacity/thermal估算；Gate 2B仍須用real P9/P10B證明 |
| Architecture impact | 是否改變engine residency、RM lifecycle、process owner或public contract；若是，先開`AR_impl` |
| Residual risk | cold boot、recovery、memory、offline、cleanup與shipping限制 |
| Approval | Core Designer recommendation + USER explicit accept/reject identity |

「不常rebuild」、「30秒內最終會好」或把threshold改成20秒都不是workaround。未完成本表前，Qwen即使
Gate 2A新項目全PASS，也不能成為provisional recommendation。

### 6.1 Gemma integration adaptation disposition

Gemma R1 current pairing不能進Gate 2B。New revision依
`ch_m4b_llm_production.md` §1.4固定以下規則：

- 最多兩個new development revisions：先prompt-only；只有documented template/capacity root cause才可
  再做一次config revision；
- development cases、R1 scored catalog與new frozen scored catalog三者分離；scored case literal、private
  output、nonce/trap不得進prompt；
- normalizer repair、retry/best-of/majority vote、P5 fallback或threshold relaxation不能算P2/P8 PASS；
- freeze後valid FAIL停止該revision，不以同identity重調重跑；超過budget回Core/USER re-estimate/no-go；
- changed-surface matrix決定P2/P4/P5/P8哪些必須重驗；未變item才可carry。

## 7. Gate 2A decision output

本輪Core Designer已建立實際delivery：

```text
DELIVERY-LLM-POC-M4B-GATE2A-PROVISIONAL-ACK-001
```

實際ACK包含：

- reviewed POC exact SHA、Gate 2A lock、兩candidate manifest/run/evidence identities；
- I1～I5逐項結果與P2/P3/P4/P5/P8 cumulative table；
- Gemma/Qwen完整disposition，包含Qwen immutable P7.1、formal Gate 2B exclusion與Gemma R1 pairing FAIL；
- 唯一provisional finalist或no-finalist決定；
- Gate 2B authorized / blocked狀態與精確next input；
- 明確聲明不是final winner、Core baseline、production dependency/model lock或M4b PASS。

本ACK保留兩個candidate的machine FAIL與User selection語意；沒有預填PASS，也沒有授權physical
Gate 2B。Gemma R1 current pairing因P2/P8 FAIL只取得model-finalist status，須依ACK建立append-only
integration-qualified revision。

## 8. Gate 2B readiness checklist

只有§7書面選出一名provisional finalist後才檢查：

| Input | Required identity / condition |
| :--- | :--- |
| Model finalist lineage | Gemma model/runtime identity沿用R1；pairing升為new versioned integration revision，before/after checksum與affected evidence逐項記錄；Qwen不得出現 |
| Gate 2B packet | R1 historical lock SHA-256 `03c68362dd5ea6e299f262d773eeda1da611dbe10705bde909bb8445676e1c41`；仍綁定failed R1 product config，不得執行；replacement lock Pending |
| Accepted Audio delivery | `POC-audio-DEL-2026-001-R1` |
| Accepted Audio completion | `audio_m4` / `5694ead4ba6be928fdb4dbdf6da7155b214d72bd` |
| Corrected Audio delivery SHA | `ca51bce9b4e205d9c9faf004d41c27169f108a3f` |
| Audio P9 / combined identity | execution `8be3bc095b504b8eab1dfeb21b94173728b9656f`；controlled checksums由`RESP-AUDIO-M4-GATE2B-001`引用 |
| Gate 2B execution | P9與P10B；new run/evidence；only change-affected regression；Pi 5 4GB mandatory |

Surrogate、Core M4a mock、Audio branch HEAD、8GB informational run或Gate 2A LLM-only resource數據都不能
替代Accepted Audio package。Gate 2B authorization另以Core書面delivery發出，不由本checklist自動成立。

## 9. Phase A completion audit

- [x] Gate 2A frozen authorization、append-only execution與candidate defect lineage已定位。
- [x] Required packet、intake order、P-item與privacy/cleanup判定已固定。
- [x] Provisional selection、no-finalist與inconclusive語意已固定。
- [x] Qwen workaround規則與P7.1 FAIL保留為歷史；actual decision明確排除Qwen。
- [x] DELIVERY-019 prompt/config adaptation budget、anti-overfitting與affected-P規則已固定。
- [x] Gate 2A actual ACK已建立，完整保留P2/P8 FAIL與model-finalist限定語意。
- [x] Gate 2B Accepted Audio identities與surrogate prohibition已固定。

上述checklist保存Gate 2B進場前的歷史條件；後續revision、Pi execution與winner closure已由final
winner ACK收斂。M4b Core product implementation、single design/test review與Gate 3 exact-SHA
acceptance仍未完成。
