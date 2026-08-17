# Response: OUT-PROCESS-2026-001 — Portable-first Candidate Gate Reform

- **Response ID**: `OUT-PROCESS-2026-001`
- **Handoff**: `PM-OUT-260817-014-local-hardware-test-gate-reform`
- **Finding**: `OUT-PROCESS-2026-001` — High — 缺少portable-first與candidate freeze gate
- **Status**: `Revised — implementation and dry-run evidence pending`
- **Response owner**: Core Team Designer
- **Date**: 2026-08-17

## 1. Designer disposition

**接受finding。** M3反覆成本不是單一測試寫法造成，而是流程把portable可發現的async / state-machine / event schema問題帶入Pi、在candidate未freeze前產生正式cards，且debug與acceptance共用evidence位置。現行「Tester全面PASS後才commit」也與硬體evidence要求完整SHA形成循環依賴。

修正採用portable-first與provisional candidate snapshot：Developer fast loop完成後，先由Designer核對scope並取得USER同意建立未freeze的candidate commit；Tester對該完整SHA完成三版本portable sign-off，Designer candidate review無Blocking後才freeze同一SHA。Pi只對frozen SHA與部署runtime做preflight及一次正式acceptance。Provisional commit只提供可重現identity，不代表Tester PASS或M4 Accepted。

本response目前不標記`Resolved`：權威流程與runner contract已修訂，但Developer尚未交付可執行runner / CI，Tester也尚未完成六種無硬體failure demonstration。文字規則不能取代fail-closed gate。

## 2. Comparison baseline and candidate identity

| Item | Value |
| :--- | :--- |
| Reviewed branch | `dev_agent_m3` |
| Comparison baseline / intake HEAD | `c559e5cf65d20676696293f06f1e5bc2afd02ae6` |
| Reviewed PM candidate | `c559e5cf65d20676696293f06f1e5bc2afd02ae6`（handoff記載） |
| Reform implementation candidate SHA | `PENDING` — runner、tests、CI與本輪文件完成後，由USER先核准provisional candidate commit，再對該SHA執行dry run |
| Effective scope | 自M4第一個產品候選起；不回溯修改M3 acceptance結論，不重跑M3 20-card |

## 3. Architecture-change declaration

**No architecture change.** 本修正不改production module、public API、event schema、process ownership或runtime lifecycle；只改開發／驗收pipeline、candidate identity、runner與evidence contract，因此不需`AR_impl`。若Developer為runner引入常駐服務、遠端控制process或改production process boundary，須另開架構審查，不能以本response授權。

## 4. Authoritative changes

| Location | Revision |
| :--- | :--- |
| `docs/roles/workflow.md` Git / Pipeline §4 | 允許USER核准的provisional candidate snapshot；定義snapshot → portable sign-off → candidate review / freeze → Pi preflight → acceptance → reconciliation，含owner、entry、exit、rollback與evidence path |
| `docs/test_spec.md` §2.1 / §2.4 / §3 | 正式支援CPython 3.11 / 3.12 / 3.13；Pi固定3.13部署runtime；定義external SHA、protected paths、run isolation、bounded timeout、manual handshake與共同evidence fields |
| `docs/milestone.md` §1.1 / §1.4 | 將portable-first與單一Pi runtime提升為所有後續hardware milestone共同完成條件 |
| `docs/milestones/M4.md` §6.2 / §6.4 | 將reform套用至下一個產品候選；M4 Accepted必須引用同一frozen SHA、portable matrix與單一acceptance run ID |
| `docs/reviews/milestone_progress.md` M4 Forward Gates | 將process gate記為design revised但implementation / dry run pending；不把文件修訂誤報為可執行gate完成 |
| `docs/runbooks/candidate_hardware_gate.md` | 新增共用runbook與runner CLI / schema contract、debug / acceptance隔離、evidence layout及六項無硬體dry run |
| `docs/runbooks/README.md` | 登錄M4起共用candidate gate |

## 5. Required implementation work packages

### WP-PROC-01 — Candidate runner（Developer）

- 實作runbook §3的`portable`、`preflight`、`accept`、`debug`等價命令。
- 外部`--candidate-sha`、40-hex / HEAD equality、protected-path dirty、run ID不可重用均fail closed。
- 以argument list與bounded timeout執行child command；保存stdout、stderr、exit code及FAIL summary。
- Acceptance output不可覆寫；debug manifest不得被acceptance引用。
- Package metadata將Python範圍由無上限`>=3.11`收斂為`>=3.11,<3.14`，並分開portable與Pi native dependency / ABI identity。

最低驗收：六項dry-run injected failure全部在suite / hardware前或指定boundary被拒絕，且沒有acceptance PASS manifest。

### WP-PROC-02 — Gate regression tests（Developer，Tester驗收）

- 以fake git / filesystem / process / manual fixture覆蓋`DRY-SHA`、`DRY-DIRTY`、`DRY-MATRIX`、`DRY-TIMEOUT`、`DRY-MANUAL`、`DRY-RUN-ID`。
- 測試驗證行為與artifact，不以每個finding必須獨立test function作門檻；table-driven可接受。
- Tester必須實際執行、檢查非零exit、reason與raw log，不可只讀code。

### WP-PROC-03 — Portable CI matrix（Developer / CI owner）

- 建立3.11 / 3.12 / 3.13同suite matrix；可平行執行。
- 每個job有job-level及suite-level timeout，輸出version result artifact；aggregation只在三者0 Fail / Blocked / Skip / XFail且同SHA時產生PASS matrix index。
- CI只產portable evidence，不宣稱Pi或人工PASS。缺版本artifact、artifact過期或SHA不符時aggregation Fail。

### WP-PROC-04 — First-use dry run and sign-off（Tester）

- 在無硬體環境實際執行runbook §8六項failure demonstration。
- Evidence放在未來候選的`docs/outsource/evidence/<delivery-id>/portable/<run-id>/`或外部CI artifact index；response補上可定位path、完整candidate SHA及實測時間。
- 六項全PASS後，Tester更新finding為可複審；Designer只核對設計與evidence一致性。

## 6. Gate policy and fallback

1. Contract / Test ID / event schema與靜態檢查先行。
2. Developer日常只跑主要Python版本的受影響tests。
3. USER核准後建立未freeze的provisional candidate commit；runner只接受外部指定完整SHA。
4. 對該SHA跑3.11 / 3.12 / 3.13 portable matrix；任何timeout、Fail、Blocked、Skip、XFail都不得freeze。Designer review無Blocking後，才freeze同一SHA。
5. Pi preflight不寫PASS card，只驗identity、clean boundary、runtime、hardware / artifact / config、matrix與readiness。
6. Debug可單卡反覆執行但只寫debug run；acceptance必須用全新run ID完整跑一次。失敗保存後停止。
7. Protected input變更回portable matrix並建立新SHA；純硬體接線修正不改SHA，但仍使用新run ID與新preflight。
8. Tester核對portable / Pi / SHA / run一致後判定；Designer確認freeze後無變更，才標記milestone Accepted。

## 7. Cost estimate and trade-off

| Cost | Estimate | Notes |
| :--- | :--- | :--- |
| Developer fast loop | 依affected nodes，通常<5分鐘 | 單一主要版本，不要求每台機器三版本 |
| Candidate portable matrix | 每版本5–8分鐘；平行wall time約6–10分鐘，序列15–24分鐘 | 首次實測後校正；目前workspace只有3.12，未宣稱已完成matrix |
| Pi preflight | 約3–5分鐘 | 不產生正式card |
| M4 Pi acceptance | 暫估35–50分鐘人工＋自動 | frozen SHA只正式執行一次；不乘三個Python minor |

接受的取捨是每個candidate增加約6–10分鐘CI wall time與一次provisional commit，換取在上Pi前攔截Python minor、async、schema、state-machine與fake可覆蓋問題。M3已有20-card不重跑；若CI成本日後超標，只能最佳化平行／cache，不能移除3.11 / 3.12 / 3.13任一正式支援版本而不更新支援政策。

## 8. Exit criteria for this finding

`OUT-PROCESS-2026-001`只有在同一候選commit同時滿足以下條件後才能改為`Resolved`：

1. WP-PROC-01至03已提交，package metadata有界且CI matrix可執行；
2. Tester完成六項無硬體dry run，逐項有非零exit、FAIL reason與raw log；
3. Response補上完整40-character candidate SHA、evidence index、實測CI時間與更新後Pi人工估時；
4. Designer確認文件、runner、tests、CI與evidence path一致；
5. 不要求或暗示重跑M3硬體驗證。
