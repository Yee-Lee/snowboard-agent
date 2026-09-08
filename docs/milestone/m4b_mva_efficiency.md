# M4B-MVA-EFFICIENCY：encoding與Conversation readiness受控實驗

狀態：`IN_PROGRESS / USER SCOPE CONVERGED / REASONER-PROMPT PLAN FREEZE`

External gates：`M4B-MVA-EFFICIENCY OPEN`；`M4B-MVA-POC OPEN`

Baseline：`M4B-MVA-002`

## 2026-09-08 User scope convergence

User stopped further experiment expansion. Existing engineering discovery is retained, but `S3`, `S4`,
additional prewarm variants, broad prompt search and repeated confirmation of already-established
prefill/cache/input-length observations are no longer active work. The remaining pre-formal work is:

1. a minimum executable Reasoner reference that unwraps the product envelope and supports only the
   current `listen` path while preserving a future perception-projector boundary;
2. at most two prompt candidates after `V1`, stopping at the first candidate that passes public
   structure/end/capability checks and has a useful measured latency/token profile;
3. one Core revision request combining the original J/P/S2 and D/H answers with a compact supplemental
   engineering appendix; and
4. only the affected clean-SHA formal measurements after Core freezes the revised surface.

The current voice-input limit is 20 Unicode codepoints. Trusted personality plus other settings have a
separate combined 20-codepoint limit. `128` prefill tokens is telemetry/performance classification, not
admission rejection; `1024` KV capacity remains the hard runtime boundary. The complete bounded plan is
[`PLAN-LLM-POC-M4B-MVA-SCOPE-CONVERGENCE-001`](../response/PLAN-LLM-POC-M4B-MVA-SCOPE-CONVERGENCE-001.md).

## Goal and delivery contribution

以固定Gemma 4 E2B、LiteRT-LM 0.16.0、Pi 5 4GB與既有MVA profile，比較兩種model encoding
（J constrained JSON、P stream-safe prefix）及兩種clean Conversation readiness（D on-demand、
H pre-open後hold 30秒）。結果只供Core Designer採用encoding/readiness/profile；不修改Core產品、
不重做model selection、不重跑MVA-002矩陣、不新增Audio claim。

Exit deliverable是User核准發布的`DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-002`。它必須讓A/B各自得到
`PASS`、`FAIL`、`UNSUPPORTED`或`INCONCLUSIVE`及建議，並提供Core解除兩個gate所需的完整identity。

## Authority and entry review

- Income：`REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002`，SHA-256
  `e13b71756382c067a207caa520c999d4b6ce5ceccbf0a91f7e08d27a07f792c4`。
- Core enclosing source：`f6e0c742f6e32fdc0e16915c6e59f42e5dd6cd69`；source與destination byte comparison PASS。
- POC baseline：DELIVERY-025 commit `23fb481007ebaf9d4c58d66b762a65aacec9196c`。
- Formal historical source/surface：`7bb332670b5fdf45f05f07dd385bec94d914b4e1` /
  `61764d0737fcf374468621bd90d4765739d2f9b2b06e4314b1dbb73229f74e89`。
- User/Core Income授權workstation preparation；Pi access、power、reboot、execution與network switching
  仍需新的operator/User authorization。結果與candidate/profile建議仍需User發布前審核。

2026-09-06 User核准上述完整計畫與B實驗，並建立general rule：所有Pi-specific development、testing、
debugging預設直接在Pi POC workspace修正至完成，不需逐任務取得開發方式例外，再將受控diff帶回
workstation。本輪工作任務、規劃與packet完成後的workstation commit及push亦獲授權。reboot、
network switching、privileged change與結果發布仍未包含。正式hardware evidence須
在push後，以clean exact SHA及frozen packet重跑，development run不得取得正式credit。

User後續明確調整順序：任何implementation前先將本規劃、Income intake、general Pi rule與scope
expansion做成獨立plan-freeze commit並push；Pi development以該SHA為base。開發完成後再回workstation
建立implementation-complete commit/push，正式evidence只使用後者的clean exact SHA。

Entry review結論：scope、delivery contribution、baseline、approver、result semantics及workstation
授權均已辨識。User於2026-09-06確認B必須量實質風險，並要求POC在P不支援時繼續找出可行solution；
因此workstream進入`IN_PROGRESS / SOLUTION DISCOVERY`。新增fallback進入formal Pi comparison前仍須
Core Designer revision。這不是新的產品milestone，也不使external gate關閉。

## Core-requested experiment design

### Shared controls

- 固定name/role/locale/capabilities、兩個public questions、temperature=0、top-p=1、CPU/4、
  32 new-user tokens、128 output tokens、1024 KV；只有J/P的output instruction不同。
- prewarm為none；same boot、fresh child、固定次序；children間隔五秒；不drop cache、不自稱cold。
- 每turn恰一model call；Core envelope與diagnostic JSON一律由software產生。
- prompts、grammar、profile、tokenizer counts、commands、cases、expected sample counts及surface都須在Pi前freeze。
- startup 120秒、generation 30秒、mode 1800秒；保留bounded cancel/TERM/KILL與owner-absence proof。
- `MemAvailable < 512 MiB`、swap增加、OOM/kernel fault、throttling、溫度`>=80°C`、identity/sampler
  loss或cleanup失敗立即停止affected run；不自動retry且保留incomplete/failed evidence。

### Experiment A — encoding

- 固定五組fresh-child paired repetitions：`J1/P1 … J5/P5`，每session兩turn，共10 children／20 generations。
- J為exact constrained JSON `text/end`；P為UTF-8 `S\n<body>`或exact `E`後正常runtime termination。
- first decodable text須與TTFT/TTC分欄；另記first punctuation-or-24-codepoint chunk、token分項、
  session open、owner PSS、cleanup及fixed-public-body frame overhead。
- parser/constraint功能錯誤使P不具資格；natural answer差異列為限制，不以prompt tuning修正結果。

### Experiment B — readiness

- 只用J；固定五組fresh-child paired repetitions：`D1/H1 … D5/H5`，共10 children／20 generations。
- D request到達後才open；H先open clean Conversation、hold exactly 30秒再送request；兩者都不prewarm。
- 本輪預先選擇獨立執行D列，不引用A的J列，避免execution identity與holding證據歧義。
- 分開記startup-to-engine-ready、interaction-ready、request path、holding PSS、close與cleanup；不得把
  preparation time藏入READY名稱。
- 額外固定no-request hold-close、cancel-during-open、end-then-new-session、facts/capability mismatch；
  驗證無history inheritance且任一時間最多一個live Conversation。

## User-directed solution expansion

`UNSUPPORTED`只結束不具能力的單一implementation path，不再結束POC的solution discovery。POC依
[`scope expansion assessment`](../response/ASSESSMENT-LLM-M4B-MVA-EFFICIENCY-SCOPE-EXPANSION-001.md)
執行bounded funnel：

1. `S0`：核對exact 0.16.0 Python/C API constraint能力，不用upstream main推定target。
2. `S1`：優先以public regex/grammar實作exact P；必要時評估同runtime documented lower-level adapter。
3. `S2`：保留constrained J，新增安全incremental JSON semantic extraction以提前取得usable text。
4. `S3`：只在frozen JSON subset可表達時評估一個compact constrained JSON candidate。
5. `S4`：unconstrained P只作最後手段diagnostic，預設不具production adoption資格。

Formal matched comparison維持J baseline，最多加入兩個經User review及Core revision凍結的eligible
solutions。這個上限防止演變成無限prompt/schema search；功能與control gate必須先於performance。

## Work packages and gates

1. `EFF-WP00 — solution discovery`：完成S0～S4 bounded capability matrix、淘汰理由與候選建議；
   具體candidate發布前交User review，需要變更formal comparison時向Core提出baseline revision。
2. `EFF-WP01 — contract/parser`：新增versioned J/P或核准fallback的prompt/grammar與internal semantic projection；完成
   prefix、UTF-8、body representative boundary splits，以及unknown/blank/truncated/E-plus-text/overflow/
   cancel/late-terminal fail-closed tests。不得釋出failure後action或把舊session output送入新session。
3. `EFF-WP02 — controller/evidence`：建立A/B plan、clock/token/PSS/cleanup schema、sanitized writer、
   no-retry ledger及private digest/neutral locator；測試固定order、spacing、expected count與missing value。
4. `EFF-WP03 — freeze`：產生clean full SHA、non-recursive surface digest、exact commands與immutable packet；
   Technical Lead先審identity/environment/cleanup，通過後才向User申請Pi。
5. `EFF-WP04 — selected-runtime proof`：Pi上先做bounded import/load/grammar/one output/same-Conversation
   follow-up/close並立即回報。缺API只停止該implementation path；P constraint缺口回`UNSUPPORTED`
   後轉下一個bounded solution，不使整個discovery提前結束。
6. `EFF-WP05 — measured execution`：依packet執行A、B及額外functional cases；無自動retry、不覆寫。
7. `EFF-WP06 — audit and delivery`：提供per-case sanitized table、median/range、paired deltas、所有regression、
   missing values、cleanup與private bundle digest。User核准後才commit/publish正式Core return。

## Exit and selection boundaries

- A只有parser/constraint/control全數成立才可比較效益；否則該P path為`FAIL`或`UNSUPPORTED`，
  J保持安全baseline且solution funnel繼續。
- H須lifecycle/isolation/cleanup成功，且request path有實測benefit並明列holding cost才具採用資格。
- 五組只報descriptive median/range與paired deltas，不報小樣本P95或significance。
- missing Audio onset固定`null / NO_AUDIO_PROOF`；不得宣稱audible latency改善。
- POC self-PASS不解除gate。Core Designer仍須記錄result full SHA、encoding/readiness/profile採用、
  affected architecture/reviewer clearance，並明確release兩個external gates。

## Current next action

2026-09-07工作階段收尾時，`EFF-WP00`已完成workstation static/import層：exact aarch64 wheel SHA符合
profile，frozen 0.16 source與同版x86 import均確認public regex、LLGuidance、REGEX/JSON constraint type；
同時確認public Python iterator會將cancel/token-limit折成一般iterator結束，因此P的normal-terminal proof
必須使用本輪新增的exact-wheel raw-terminal POC adapter，不能只靠public iterator exhaustion。

`EFF-WP01`已完成獨立efficiency surface的P與incremental J fail-closed decoder、provisional/final邊界、
UTF-8/escape/surrogate/overflow/truncation/cancel/late-invalid tests，以及D/H clean-held Conversation的
single-flight、30秒expiry、identity mismatch、late-open close、no-request close與fresh fallback ownership。
新增backend已連結J/P constraint、raw terminal及D/H adopt；efficiency tests 26項與既有MVA regression
67項均在workstation通過。舊MVA surface lock與歷史結果未修改。

Pi仍不可達，故selected aarch64 runtime import/load/grammar/one-output/follow-up/close、真實chunk形態、
cancel-during-native-open與30秒holding resource皆未驗證，且沒有hardware結果。下次從本commit開始，
先在Pi POC workspace完成上述engineering proof，再補齊`EFF-WP02` controller/evidence、packet與surface
freeze。具體fallback candidate proposal與benchmark發布仍須User review；formal comparison revision仍由
Core Designer凍結，formal evidence只接受後續clean pushed exact SHA。
