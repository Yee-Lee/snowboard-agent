# M4b Authoritative POC Execution Plan

狀態：`GATE 2A POC ROUND COMPLETE / GEMMA MODEL FINALIST / GATE 2B IN_PROGRESS`

Revision：`2026-08-29-gate2b-resource-preflight-r4`

Owner：POC Technical Lead；User已授權累積Gate模型；外部接受者為Core Designer。

## Governing execution model

P1～P12只執行一次，分布於Gate 1、2A、2B；Gate切換本身不造成重跑。相同evidence可沿用
的必要條件是原execution commit為目前clean checkout的ancestor、execution-surface lock digest與
runtime/model/config/protocol/fixture SHA、Pi 5 4GB identity、OS、`swap=0`、offline要求及evidence
manifest一致。Evidence/ACK/docs commit不構成source drift；execution identity drift只使受影響P項失效。

| Stage | Formal P credit | Primary decision | Packet |
| --- | --- | --- | --- |
| Gate 1 | P1, P6, P7, P10A, P11, P12 | LLM是否穩定、Core child整合與recovery是否可行；最多2名finalists | `G1-PI-COMPAT-007` |
| Gate 2A | P2, P3, P4, P5, P8 | 輸出品質、效能、timeout、history；最多1名provisional finalist | `G2A-PI-LLM-002` |
| Gate 2B | P9, P10B | Accepted Audio+LLM 4GB residency與20-session combined stability；final winner | `G2B-PI-COMBINED-001` |

Gate 1完成後，2A不得例行重跑P1/P6/P7/P10A/P11/P12。Gate 2B不得例行重跑1/2A項目；
只有combined integration確實修改的component/boundary才能建立predeclared focused regression。

## Result semantics

- `PASS`：exact identity、有效環境、完整方法與cleanup均通過。
- `FAIL`：有效candidate run證明mandatory rule違反。
- `INCONCLUSIVE`：environment、identity、evidence或方法失效，無法判定candidate。
- `Blocked`：必要artifact、hardware、Accepted Audio kit、權限或review gate未就緒。
- `Conditional escalation`：只限P6，且只有P7完整PASS時仍eligible。
- `Core threshold decision required`：只限完整P4方法未達negotiable target。

未執行為`Pending`。不得把planning/unit test、UTM、workstation或`--plan-only`輸出標成Pi P結果。

## Gate 1 — stability and Core integration

### Historical `006` evidence

`G1-PI-COMPAT-006-20260826T125959Z-001`與manifest
`34cb51b0bdb04a042281722db37514bce1daba234391fa79570482faa53d2208`永久保留。
其10秒READY clock包含完整模型SHA，因此只證明packet implementation defect；不淘汰Gemma/Qwen、
不供P credit、不得覆寫或same-revision重跑。

### Replacement `007`

`G1-PI-COMPAT-007`固定兩名candidate，不補第三名。Model以streaming SHA在任何READY clock前
各驗證一次；artifact必須read-only，之後child只核對strict receipt與metadata。Wheel由v2 installer
只驗證一次。三個purposeful lifecycle如下：

| Work package | P IDs | Single-source evidence | Exit |
| --- | --- | --- | --- |
| `G1-WP01-DEPLOY` | P11 | clean source、license、wheel/model/config SHA、offline install/import、native ELF/linkage | provenance與deploy全PASS |
| `G1-WP02-NORMAL-STABILITY` | P1, P10A | READY<=10s、PING、同一Engine 20 sessions、5s cadence、PSS/system-used slope與median、thermal、clean shutdown | P1/P10A PASS |
| `G1-WP03-CANCEL-RECOVERY` | P6, P7 | generation-active observation、CANCEL<=500ms或conditional、TERM/KILL/waitpid、rebuild/READY、recovery、fatal exit4 | P7 PASS；P6 PASS或valid conditional |
| `G1-WP04-OFFLINE-RECEIPT` | P12 | pre/post offline/swap/throttling、log hygiene、artifact metadata unchanged、manifest | P12 PASS與cumulative receipt ready |

Gate 1 candidate eligibility要求P1/P7/P10A/P11/P12 PASS且P6 PASS或由P7支持的
`Conditional escalation`。User/reviewer/Core接受前結果不得對外成為finalist ACK。

Gate 1已取得Core closure ACK。Gate 2 development surface已通過R4 reviewer驗證，Core與User已授權
Gate 2A Pi execution。Benchmark publication與candidate proposal仍須User evidence review。

## Gate 2A — remaining LLM-only acceptance

Entry為Core接受的Gate 1 cumulative receipt與至少一名finalist。Packet只跑P2/P3/P4/P5/P8：

| Work package | P IDs | Optimized method | Exit |
| --- | --- | --- | --- |
| `G2A-WP01-OUTPUT` | P2, P3 | 10 valid cases ×3 model runs；10 invalid fixtures ×3 reference-normalizer runs；single persistent Engine；log scan | 60/60 exact dispositions、no leakage |
| `G2A-WP02-PERFORMANCE` | P4 | cold 3；warmup 3；hot 20；raw/P50/P95、resource diagnostics | PASS或written Core threshold decision |
| `G2A-WP03-TIMEOUT` | P5 | Pi-only continuous 512-token chunks、單一15–17s outer timeout、same-child health、standard rebuild | PASS；fast chunk固定CONTINUE，不產生early terminal |
| `G2A-WP04-HISTORY` | P8 | 5 fixed nonce/trap single-turn conversations、KV envelope、hash-only evidence | PASS |
| `G2A-WP05-PROVISIONAL` | cumulative | link accepted Gate 1 manifest；review all mandatory items | at most one provisional finalist |

Gate 2A startup/cleanup只作remaining case的operation prerequisite，不重新宣告P1/P7。Read-only Gate 1
model receipt可沿用；Git只需ancestor relation，lock/component digest才控制carry-forward。Metadata或
execution-surface drift使affected identity Blocked，不能暗中rehash/repair。

Qwen首次true-cold child在10秒前未READY；兩次P1.2診斷約19.2秒READY且延遲位於native
`Engine()`，原因未定。User已defer歸因matrix，並允許Gate 2A controller使用30秒操作觀察窗口
抵達remaining cases；P1契約仍為10秒、不得重計或新增credit。Gemma維持10秒。

2026-08-29兩名candidate均完成final-surface Pi observation。User保留machine dispositions、採用
`DELIVERY-019`語意分離，並選定Gemma為唯一model finalist。Gemma current integration仍為P2 FAIL；
P8 FAIL加註`DEPENDENCY_LIMITED_BY_P2`且沒有observed history pollution。M3/Gate 2A POC execution與
selection round完成，但Core external ACK及新的integration-qualified Gemma revision仍是Gate 2B entry。

## Gate 2B — combined final acceptance

Entry為accepted Gate 1 receipt、User-reviewed Gate 2A model-finalist decision、新的integration-qualified
Gemma revision及Core-recorded Accepted Audio handoff ID/full SHA/executable kit。
Surrogate只能debug，不能取得P9/P10B credit。

P9與P10B共用一次4GB `swap=0` offline combined run，避免Audio/LLM重複load：先取idle/residency
sample，再跑20個ASR fixture→LLM→TTS sessions（5s cadence），最後reverse shutdown與owner zero。
Initial attempt `G2B-PI-COMBINED-001`因受控store漏放Accepted TTS verifier所需的兩個sherpa wheel
source而在完整residency前`INCONCLUSIVE`；其evidence固定保留，不提供P credit。Replacement
`G2B-PI-COMBINED-002`已驗證完整Audio closure並使四domain READY，但Pi boot未啟用kernel PSI，
因此第一筆resource sample `INCONCLUSIVE`；零session且cleanup完整。Attempt
`G2B-PI-COMBINED-003`必須在任何domain啟動前驗證完整Audio source與memory/PSI/OOM/thermal probe
closure，使用新exact execution SHA與evidence root；未改變的read-only input root可沿用。

| Work package | P IDs | Exit |
| --- | --- | --- |
| `G2B-WP01-COMBINED` | P9, P10B | P9 system-used每sample<=3584MiB、no OOM/full PSI regression；P10B 20/20、<80°C、throttled=0、no crash/leak/stale/history/owner residue |
| `G2B-WP02-FINAL` | cumulative | link Gate1 P1/P6/P7/P10A/P11/P12 + 2A P2/P3/P4/P5/P8 + 2B P9/P10B；User review後交Core final winner/no-go |

8GB如執行只作identical-config informational sanity，不補救4GB failure。

## Estimates and re-estimation triggers

| Stage | Expected scored cost per candidate | Re-estimate when |
| --- | --- | --- |
| Gate 1 | one model hash、3 Engine lifecycles、20+recovery generations、約100s fixed cadence | artifact/hash >120s、READY >10s、mandatory failure、environment drift |
| Gate 2A | 30 model quality runs、30 cheap normalizer runs、26 performance runs、P5、P8 | execution-surface drift、P4 threshold decision、continuous-timeout implementation defect |
| Gate 2B | one combined residency +20 sessions | Audio SHA/kit/process tree change、headroom<10%、mandatory fault |

Valid mandatory `FAIL`不得retune/rerun。只有reviewed infrastructure/evidence `INCONCLUSIVE`可在新run ID
做一次identical rerun。所有raw evidence在Git外，sanitized manifest不得包含model output、prompt/payload、
binary、weights、credential或endpoint。

## Current execution boundary

Gate 2A final evidence已獲User review，Gemma為唯一model finalist，Qwen不進正式Gate 2B。原始
machine FAIL/PASS不可改寫；Gemma P2/P8不得因選型裁決轉為PASS。Core對`DELIVERY-019`與closure
delivery的ACK依User裁決可在Gate 2B execution期間補入，但final delivery前必須收到。新的Gate 2B
scored execution仍必須使用versioned/frozen integration-qualified Gemma revision、updated consumer
boundary及Accepted Audio staging。Initial attempt 001的staging defect不改寫candidate；attempt 002
lock `c671e2438833c6bc26dec32ca5f49909e325d25d8e134ef3fcb0b996da845d74`將兩個TTS wheel source
納入pre-residency authentication。Attempt 002證明Pi的PSI default-disabled boot不符合P9 measurement
entry；attempt 003 lock `fc59e26d2739c24be39e09c495dcd637bf073ba7370162af0a8b444a9d61975f`
另在residency前fail-close所有resource probes。Pi launch固定private-mount/
read-only-sysfs，避免繼承host `wlan0` view。User已
授權直接commit/push與Pi staging/execution，independent review可後補。禁止把current failed
configuration直接餵入combined scoring。

POC主交付完成後，P1.2 cold-start歸因與未入選candidate的identical Gate 2B envelope可列為
informational/no-credit backlog。它們不得延誤正式Gate 2B，也不得回溯改寫單一finalist的選型結果。
