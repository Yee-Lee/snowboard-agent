# ACK-LLM-POC-M4B-MVA-EFFICIENCY-002 — intake and execution arrangement

- Income：`REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002`
- Work / baseline / gate：`M4B-MVA` / `M4B-MVA-002` / `M4B-MVA-EFFICIENCY`
- Income SHA-256：`e13b71756382c067a207caa520c999d4b6ce5ceccbf0a91f7e08d27a07f792c4`
- Core enclosing source：`f6e0c742f6e32fdc0e16915c6e59f42e5dd6cd69`
- POC delivery baseline：`23fb481007ebaf9d4c58d66b762a65aacec9196c`
- Formal MVA source / surface：`7bb332670b5fdf45f05f07dd385bec94d914b4e1` /
  `61764d0737fcf374468621bd90d4765739d2f9b2b06e4314b1dbb73229f74e89`
- Status：`RECEIVED / USER-EXPANDED PLAN READY / PLAN COMMIT FIRST / DEVELOPMENT NOT STARTED`

## Intake conclusion

2026-09-06已對照Core source與本repo Income；兩份檔案byte-identical且SHA-256一致。依Income，
`M4B-MVA-EFFICIENCY`已Open。這是`M4B-MVA-001`結果之上的prospective bounded experiment，
不回退Step 5、不修改`MVA-002`、long-session或H01–H12結果，也不重跑既有完整矩陣。

本工作直接推進的final checklist item是：提交一份identity完整、可重現、經User發布前審核的
`DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-002`，讓Core Designer可以分別裁決encoding與readiness、
固定profile，並明確解除`M4B-MVA-EFFICIENCY`及`M4B-MVA-POC`。POC結果本身不解除任一gate。

## User-confirmed direction and remaining design freeze

- J維持既有exact `text/end` constrained JSON；P只允許`S\n<nonblank text>`或exact `E`並正常終止。
- J/P decoder都回到相同的internal `SemanticGeneration(text,end)`；Reasoner仍唯一擁有
  speak/listen或rest裁決，model chunk不得成為tool、Fact、action或額外turn。
- P parser錯誤、terminal錯誤、overflow或cancel仍fail closed且不得repair/retry。若selected-runtime
  constraint path不支援，該path回`UNSUPPORTED`，但依User指示POC須繼續bounded solution discovery，
  不能直接把整項工作結束為J retention。
- A固定五組`J1/P1 … J5/P5`；B固定五組獨立`D1/H1 … D5/H5`。本輪預先宣告不重用A的J列作D列，
  使B的identity、holding cost與cleanup證據獨立完整。
- 每個A/B measured session固定兩turn、fresh child、same boot、prewarm none、五秒child間隔；
  public問題、facts、temperature/top-p、CPU/4、32/128/1024與除encoding instruction外的prompt bytes固定。
- Audio不在本任務範圍；audible latency固定回報`null / NO_AUDIO_PROOF`，不得以TTFT或TTC代替。

## Work arrangement

| Order | Work package | Owner | Exit evidence |
| --- | --- | --- | --- |
| 0 | `EFF-WP00` solution discovery | Developer / Technical Lead | exact 0.16.0 API matrix；native P、incremental J、compact constrained JSON及diagnostic fallback的bounded disposition |
| 1 | `EFF-WP01` contract/parser | Developer | 核准candidate的prompt、grammar、incremental parser、dirty-context與Reasoner oracle；boundary/negative/cancel unit tests |
| 2 | `EFF-WP02` controller/evidence | Developer | fixed order、five-second spacing、token/timing/PSS/cleanup fields、sanitized writer與fail-closed verifier |
| 3 | `EFF-WP03` execution freeze | Technical Lead | Core revision、clean full SHA、surface digest、commands、cases、hashes、sample count、timeouts與private locator scheme |
| 4 | `EFF-WP04` selected-runtime proof | POC Test Controller | bounded import/load/constraint/one output/follow-up/close；unsupported path保留且轉下一bounded solution |
| 5 | `EFF-WP05` Pi experiments | POC Test Controller | baseline與最多兩個eligible solution的matched encoding rows；B另有10 children/20 generations及lifecycle cases |
| 6 | `EFF-WP06` audit/review/delivery | Technical Lead → User → Core | encoding/readiness各自disposition、paired deltas、limitations、cleanup、bundle digest與User publication approval |

User已授權擴大solution discovery；目前先做WP00 exact API/source inventory及bounded feasibility設計，
並依general rule在Pi POC workspace直接開發、測試與除錯至完成，再帶回workstation完成規劃、commit與push。
User後續指定implementation前先commit/push本規劃；Pi development以plan-freeze SHA為base，完成後另建
implementation-complete commit/push，再進clean exact-SHA formal execution。
新增fallback若要進入正式comparison，Core須先revision原本「exactly two encodings／no other candidate」
的contract。WP04～WP05仍須新的Pi access／power／execution授權，且只可執行freeze後的exact SHA
與packet。WP06在User審核前不得發布benchmark或採用建議。

## Open controls

- Pi最近記錄為powered off；Pi POC workspace development/test/debug是general rule，但實際
  power/reachability仍須現場成立。reboot、artifact transfer、network switching與privileged change未授權。
- 工作任務、規劃與packet完成後的workstation commit及push已由User明確授權；Pi不得commit/push。
- selected LiteRT-LM對P所需constraint能力尚未target-proven；單一路徑不支援時保留
  `UNSUPPORTED`事實，但POC繼續依scope expansion assessment尋找可行solution。
- 新增fallback尚未獲Core納入formal baseline；POC discovery evidence不得冒充正式matched result。
- Pi dirty-worktree development run一律為`ENGINEERING / NON-FORMAL`；formal result須在workstation
  push後以clean exact SHA、frozen packet與append-only ledger重新執行。

## Plan-freeze round-close audit

| Direct Income | Classification |
| --- | --- |
| `DELIVERY-LLM-POC-M4B-CONTRACT-001.md` | retain：M4b governing contract |
| `core_llm_m4b_tasks.md` | retain：M4b governing scope boundary |
| `DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001.md` | retain：locked provenance仍由後續MVA引用 |
| `REQUEST-LLM-POC-M4B-MVA-MEASURE-001.md` | retain：`M4B-MVA-POC`尚未由Core release |
| `REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002.md` | retain：目前active dependent experiment |

本輪無completed、superseded或incorporated direct Income可移入history；因此不做archival move。
- Core Developer/Tester仍被兩個外部gate阻擋；POC不得修改Core source或代替Architect/Reviewer/Designer裁決。
