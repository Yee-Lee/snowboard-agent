# Core Team → PM → LLM POC Team: M4b LLM POC Contract

- **Delivery ID**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Finding ID**: `OUT-M4B-2026-001`、`OUT-M4B-2026-002` ～ `OUT-M4B-2026-006`
- **References**: `PM-OUT-260814-011-m4b-llm-poc-contract-gate`、`PM-OUT-260805-002-m3-m4-poc-planning`、`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`、`docs/milestones/M4.md §6.1–6.2`
- **Revision**: `2026-08-17 / PM-OUT-260817-015`
- **Status**: `GATE 0 R2 COMPLETE — GATE 1 NOT STARTED`
- **Contract owner**: Core Team Designer
- **Relay owner**: PM (轉交 LLM POC Team)
- **Date**: 2026-08-15
- **Architecture change**: `No`

---

## 1. 背景與授權邊界

M4b Local LLM 是以 Core production 架構中的 Resource Manager、Reasoner 與 `docs/protocol.md` 為基礎，整合真實本機 LLM 推論引擎（如 LiteRT-LM / MediaPipe LLM 或其他核准候選）。LLM POC Team 的責任是技術探索、候選評估、persistent child reference wrapper 實作、Pi 5 驗證與 evidence 提交；Core 保留 model baseline 定案、protocol 契約審核、整合驗收與 final ACK 決定權。

**在本 contract 各 gate 取得 Core final ACK 前：**

- LLM POC repository 所有工作只可標示 `Proposed` / `Not authorized`。
- 不得以 POC 自排 roadmap、口頭結果或 branch HEAD 取代 Core 核准的 contract 或 gate evidence。
- Developer 不得引用候選名稱或 POC branch HEAD 解除 Blocked，不得加入 production dependency lock 或開始 real LLM backend。
- 外部 LLM 指引（如 `poc_llm/handoff/20260805-1032-llm-poc-guidance/`）僅供參考，不得視為已授權或已 Accepted 輸入。

---

## 2. 目標

在 Raspberry Pi 5（8GB / 4GB）環境，完成 LLM 推論引擎與 persistent child process 驗證，確認並固定：

1. **Runtime & Model**：確認可離線運行的本機推論引擎（如 LiteRT-LM）、Model 架構、Quantization 格式、版本、授權、checksum 與 Pi 安裝方式。
2. **Persistent Child Protocol**：驗證子行程常駐架構，支援 READY handshake、單 turn generate / result、timeout、cooperative cancel、force abort（SIGTERM/SIGKILL + waitpid proof）、recovery barrier 與 history isolation（單 turn 獨立，無跨 session 狀態殘留）。
3. **Resource & Thermal Budget**：M4b（LLM）與 M4a（ASR + TTS）同時常駐時，符合 target-device Pi 5 資源與散熱限制；4GB 為 mandatory deployment floor，8GB 為 informational portability run。4GB 不通過但 8GB 通過者只能回交 `INCONCLUSIVE / Core threshold decision required`，不得自行宣告 winner；CPU 溫度 < 80°C、無 thermal throttling。

---

## 3. 候選比較基準（Comparison Baseline）

| 域 | 起始候選 | 說明 |
| :--- | :--- | :--- |
| LLM Engine / Runtime | LiteRT-LM (TFLite / MediaPipe LLM)、llama.cpp (可提替代) | 每個候選須提供 exact version、source SHA-256、transitive deps、license |
| Model 候選 | Gemma-2-2B-IT、Qwen2.5-1.5B/3B-Instruct、SmolLM2-1.7B-Instruct | 參數量 ≤ 3B，優先以 1.5B ~ 2B 為主，確保 Pi 5 資源餘裕 |
| Quantization | INT4、INT8、GGUF (Q4_K_M / Q8_0) | 須提供 quantization 工具、參數與 quantized artifact SHA-256 |
| Prompt & Format | zh-TW / en System Prompt + JSON intent output | 評估 intent 抽取準確率與 output formatting 穩定度 |
| Target 平台 | Ubuntu初篩→Raspberry Pi 5 4GB mandatory gate；8GB informational portability run | 不得提交binary、wheel、model weights或`.so`進Core Git；8GB不得補救4GB Fail |

---

## 4. Gate 架構與逐 gate 責任

### Gate 0 ── LLM POC Contract Receipt & Scope Confirmation（合約接收與環境確認）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | PM 將本 contract 正式交付 LLM POC Team |
| Exit | LLM POC Team 提供 receipt 確認已閱讀本 revision，回交 POC repo path、branch、完整 40-character HEAD、initial manifest及 §10 committed planning packet |
| Owner | PM 轉交；LLM POC Team receipt 確認；Core Designer 記錄 |
| Blocking scope | 未完成 Gate 0 前，LLM POC 探索工作不具備正式合約授權 |
| 下一動作 | POC 準備 Gate 1 candidate proposal |

### Gate 1 ── M4b Candidate Proposal & Ubuntu Pre-screening（候選提案與初篩）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 0 完成；POC 已依 §9 crosswalk 凍結 harness / fixture / validator；提出 runtime / model / quantization candidate 清單與 Ubuntu pre-screen packet |
| Exit | Candidate eligibility / provenance / license完整，Ubuntu pre-screen依相同fixture與decision table完成，最多兩個finalist；Core Designer書面確認後才可進入Pi Gate 2 |
| Owner | POC 提交；Core Designer 核准範圍 |
| Blocking scope | 未取得 Core 書面確認前，不得將候選視為已核准，不得在 Core production 引用 |
| 下一動作 | POC 回交 candidate list（manifest + license table）；Core Designer 在 5 個工作日內回覆 |

### Gate 2 ── M4b Pi 5 驗證（POC 執行，分 2A / 2B）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 1 已取得候選授權；POC 依 §5 / §7.1 對核准候選執行。**Gate 2A** 先跑LLM-only P1～P8、P10A、P11、P12；**Gate 2B** 取得Core記錄的Accepted Audio POC final reference package後，跑P9與P10B combined gate |
| Exit | 2A可產生provisional finalist ACK；只有2A與2B都完成、同一POC candidate SHA / fixture revision且全部mandatory gate通過，Core Designer才發final winner ACK |
| Owner | POC 執行；Core Designer 審核；PM 轉達 ACK 通知 |
| Blocking scope | Gate 2A前Core只能準備protocol / fake scaffold；2A provisional ACK後可做不鎖runtime/model的adapter scaffold。未取得2B final winner ACK前，不得加入production dependency / model lock或宣告M4b baseline |
| 下一動作 | 2A evidence可與Audio POC並行；P9 / P10B若缺Accepted Audio package保持`Blocked`，不能以surrogate轉Pass |

### Gate 3 ── M4b Core Production Implementation（Developer 實作，Core 內部 gate）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 2 final winner ACK 已發出；`model_spec.md` 已固定 LiteRT-LM baseline；`docs/protocol.md` 已 review 完成 |
| Exit | Core Tester 對產品 delivery exact SHA 完成 M4b 驗收（`M4B-*` test cases）；Designer 最終 Code Review 無 Blocking finding |
| Owner | Developer 實作；Tester 驗收；Designer 最終審查 |
| Blocking scope | M4b 未 Accepted 前，M4c 不得啟動；M4a + M4b 未同時 Accepted 前，M4 不得宣告 Accepted |
| 下一動作 | Developer取得Gate 2B final winner ACK後建立production integration工作包；2A前後可做的scaffold邊界依本表Blocking scope |

---

## 5. M4b 驗證清單（POC 在 Gate 2 執行）

| ID | 驗證項目 | Required evidence / result |
| :--- | :--- | :--- |
| **M4B-P1** | Persistent Child Lifecycle | Child process 啟動、READY handshake 於 10s 內完成；stdin/stdout JSON-lines framing 正常；clean shutdown 無 process 殘留 |
| **M4B-P2** | Product Result Contract | 固定catalog逐筆輸出exact JSON object：keys恰為`action_kind`、`action_payload`、`next_perceptions`；kind只可`speak/tool/rest`。`speak={"text": non-empty str}`；`tool={"name": registered dotted name, "arguments": object}`且只產tool intent、不執行handler；`rest={}`且`next_perceptions=[]`。speak/tool須有非空、去重後仍可用的`listen/read/look`清單 |
| **M4B-P3** | Output Quality / P5 / Log Hygiene | Core-approved 20-case catalog每case至少3 hot repetitions；涵蓋speak/tool/rest、capability allowlist、unknown kind/tool、空輸出、拒答、壞JSON與unknown action。正常case schema pass率100%；失敗case須由reference normalizer得到P5 apology-speak（若speak+listen可用）或rest，不得raise。log不可含prompt、raw model output、payload、credential或hidden context |
| **M4B-P4** | 推論速度與延遲（Pi 5） | 3 warm-up後，固定input/output token envelope，記錄cold 3次與hot 20次TTFT、total latency及tok/s的raw samples / P50 / P95；TTFT ≤ 2.5s、generation ≥ 4.0 tok/s為Negotiable performance，不自動No-Go |
| **M4B-P5** | Timeout 處理 | 發送超長生成或極端 input 測試；達 timeout 門檻（如 15s）時觸發超時中斷，回傳錯誤代碼，不 hang 住 process |
| **M4B-P6** | Level 1 Cooperative Cancel | 生成中送protocol cancel；500ms內停止operation、釋放短期資源並恢復READY則Pass。Native cancel不可用／timeout可記`Conditional escalation`，candidate仍可進2A，但只在P7 Level 2與rebuild全部Pass時保留winner資格；不得把SIGTERM或SIGKILL稱Level 3 |
| **M4B-P7** | Level 2 Force Abort / Level 3 Fatal | 模擬child unresponsive；單一Level 2 `force_abort()`依序SIGTERM→bounded wait→必要時SIGKILL→waitpid，並完成outer operation及RM rebuild / READY barrier。force-abort、outer completion或rebuild failure / timeout才是Level 3：Core product process exit 4，由部署systemd重啟；POC只證明fatal outcome，不在harness自行冒充產品restart |
| **M4B-P8** | History Isolation | 連續執行 5 次單 turn 對話；驗證 Turn N 不受 Turn N-1 影響；無隱藏 KV cache 累積或 context pollution |
| **M4B-P9** | Gate 2B Combined Residency | prerequisite為Core記錄的Accepted Audio POC final handoff ID / SHA / kit；surrogate只可debug。4GB mandatory：swap=0，記錄Core parent + LLM + ASR/TTS process tree的PSS/RSS、system MemAvailable、threads、CPU、temperature、throttling及latency；總PSS / RSS不得超3.5GB且不OOM。8GB用相同設定跑informational sanity，不另放寬4GB結果 |
| **M4B-P10** | Thermal & Soak | **P10A**：Gate 2A以LLM-only固定20個single-turn session驗process reuse、history isolation、memory slope與cleanup。**P10B**：Gate 2B以同一20-case catalog、Accepted Audio package完成ASR fixture→LLM→TTS generation的20 sessions；session間隔5s，temperature <80°C、throttled=0、無crash / leak / owner殘留 |
| **M4B-P11** | Build & Provenance | 從 clean Pi 5 依 script 可完成環境配置與執行；記錄 OS、Kernel、Python、Runtime、Model SHA-256；所有 dependencies 具開源 license |
| **M4B-P12** | Offline 驗證 | Pi 5 拔除網路線/關閉 Wi-Fi 下完整執行推論；log 證明無任何 external network call 或 API token 傳輸 |

---

## 6. 必要回交結構

POC repository 回交至少包含下列可定位內容；manifest 中的 relative path 必須完整：

```text
poc_llm/
├── deliveries/
│   └── DELIVERY-LLM-POC-M4B-VALIDATION-001.md
├── tools/
│   └── <reproducible M4b runner: child process + inference engine>
├── harness/
│   └── <prompt fixture + benchmark runner + validator>
└── evidence/m4b/
    ├── manifest.json
    ├── environment.txt
    ├── config.sanitized.*
    ├── results.*
    └── raw/
```

`manifest.json` 至少列：POC full SHA、hardware revision (Pi 5 8G/4G)、sanitized config SHA-256、runner 與 fixture SHA-256、candidate source hashes、model weights SHA-256、license、每個 M4B Test ID 狀態、raw artifact path、開始 / 結束時間與完整 reproduction command。未執行為 `Pending`，硬體或環境不足為 `Blocked`；不得標成 `Pass`。

---

## 7. Winner / No-Go 決定表（POC Gate 2 回交時逐項填寫）

| Decision item | Required answer |
| :--- | :--- |
| LLM Engine / Runtime | selected candidate、version、source SHA-256、license、理由與 rejected alternatives |
| Model candidate | model name、quantization method、file SHA-256、source URL / model card、license、Pi install command |
| Persistent child compliance | P1 / P5 / P7 / P8是否Pass；P6是native Pass或有證據的Conditional escalation；Level 2含terminate→kill→waitpid→rebuild / READY barrier |
| 推論效能數據 | TTFT (P50 / P95)、Generation tok/sec、Peak RSS、Thermal peak (°C) |
| Format stability | JSON / intent 結構化輸出成功率（%） |
| Offline confirmation | 是否可在無網路 Pi 5 完整執行；log 是否無 credential / API endpoint |
| Residual risk | 已知限制、未通過項目、是否仍可達成 M4b contract；No-Go 條件說明 |

### 7.1 P1～P12 acceptance matrix

| ID | Classification | Decision rule |
| :--- | :--- | :--- |
| P1 | Mandatory | READY / framing / shutdown任一不符即Fail |
| P2 | Mandatory | Core product schema與validator catalog 100% pass；否則Fail |
| P3 | Mandatory | 事前固定catalog、fallback與log hygiene全Pass；不得以平均值掩蓋單一洩漏 |
| P4 | Negotiable performance | 按固定方法報raw / P50 / P95；未達目標為`Core threshold decision required`，不自行Fail/Pass |
| P5 | Mandatory | timeout bounded、child不hang、terminal result與cleanup完整 |
| P6 | Conditional escalation | native cancel成功則Pass；不支援／timeout只有在P7全Pass時仍eligible，否則Fail |
| P7 | Mandatory | Level 2 termination / waitpid / rebuild proof及Level 3 failure outcome齊全 |
| P8 | Mandatory | 五turn history isolation全Pass |
| P9 | Mandatory for final winner | 缺Accepted Audio package=`Blocked`；surrogate不得Pass；4GB gate必過 |
| P10 | Mandatory | P10A為2A prerequisite；P10B為final winner prerequisite |
| P11 | Mandatory | provenance / license / clean build任一不明即Fail |
| P12 | Mandatory | offline run與network evidence不完整即Fail |

每項結果只可為`PASS`、`FAIL`、`INCONCLUSIVE`、`Blocked`或`Core threshold decision required`。Gate 2A要求P1/P2/P3/P5/P7/P8/P10A/P11/P12全Pass，P6依上表裁決，P4已完整量測；Gate 2B再要求P9/P10B Pass。不得看完候選結果才改fixture、token envelope、warm-up、repetitions或decision rule。

**效能門檻裁量說明**：M4B-P4 的效能目標（TTFT ≤ 2.5s、Generation Speed ≥ 4.0 tok/sec）為起始設計基準，非自動 No-Go 條件。若所有候選在 Pi 5 均未能達到目標值，POC 須記錄實際測量數字（P50 / P95）並回交，由 Core Designer 與 PM / User 協商門檻後再書面確認是否可接受；POC 不得在未取得 Core 書面確認前自行宣告效能可接受或選定 Winner。

---


## 8. External Gate / POC milestone crosswalk

| External gate | POC internal milestone | Delivery area | P IDs | Required evidence / decision |
| :--- | :--- | :--- | :--- | :--- |
| Gate 0 | Internal M0 | Receipt / Initial Manifest | N/A | 本revision receipt、repo path、branch、full SHA、owner / approver、environment inventory |
| Gate 1 | Internal M1 + Ubuntu pre-screen | Frozen harness、candidate proposal、eligibility / license、Ubuntu packet | P1/P2/P3/P4/P5/P6/P8的portable subset；P11 provenance | committed harness / fixture / validator schema、最多2 finalist、Core written ACK |
| Gate 2A | Internal M2 / M3 standalone | Pi lifecycle、result、performance、offline | P1～P8、P10A、P11、P12 | Pi 5 4GB mandatory；provisional finalist ACK，不是winner |
| Gate 2B | Internal M4 combined | Audio+LLM residency / 20-session soak | P9、P10B及2A regression | Accepted Audio POC handoff引用、combined manifest、final winner ACK |
| Gate 3 | Core product milestone M4b | Production adapter / child / product delta | Core `M4B-*` | Core Tester對product exact SHA驗收；POC evidence不等於產品Pass |

POC不得再把External Gate 0與Internal M0當成同一個approval，也不得混用D1～D6 / D1～D8。若保留內部`D*`名稱，milestone index必須逐一映射到上表的唯一delivery area，不得產生第二套gate判定。

## 9. 溝通順序（Contract relay flow）

```
Core Designer (contract owner)
  → [本 delivery] PM 正式轉交 LLM POC Team (relay owner)
    → POC Gate 0 回交 contract receipt + initial manifest + committed planning packet
      → POC Gate 1 回交 frozen harness + candidate list + Ubuntu pre-screen evidence（最多2 finalist）
        → Core Designer 書面確認 Gate 1 (存於 deliveries/)
          → POC Gate 2A 執行 Pi standalone，回交 exact SHA + manifest → provisional finalist ACK
            → Accepted Audio POC final reference package ready
              → POC Gate 2B 執行 P9 / P10B combined gate
                → Core Designer 審核 → final winner ACK (或要求補交)
              → PM 通知 LLM POC Team ACK 結果
                → Developer 取得 Gate 2 final winner ACK → 建立 M4b 工作包
```

每個步驟的 ACK 均由 Core Designer 書面發出，存放於 `docs/outsource/deliveries/`；PM 只負責轉交，不代替 Core 簽發 ACK，也不代替 LLM POC Team 宣告 gate 通過。LLM POC Team 以自己 repo 完整 SHA 與 manifest 回交；不得以 branch HEAD 或部分 evidence 替代。

---

## 10. POC 本輪回覆 packet（由 User / PM 交付後回傳）

LLM POC Team收到本revision後，可整理不依賴候選下載的scaffold，但在Core Gate 1 ACK前不得啟動Pi Gate 2或宣告爭議項目Pass。請在POC repo一次commit以下內容並回覆：

1. authoritative milestone index與External Gate→Internal Milestone→Delivery Area→P1～P12→evidence path唯一crosswalk；
2. Gate 0 receipt與真實Initial Manifest；
3. Gate 1可執行packet：candidate eligibility / provenance / license、Ubuntu pre-screen、frozen harness / fixture catalog / validator、command、timeout、result schema及最多2 finalist decision；
4. Gate 2A / 2B work packages：owner、dependency、platform、entry / exit、estimate、re-estimation trigger、runner、cleanup、failure / no-go及evidence path；
5. P2/P3 catalog與expected result不含敏感prompt / raw output，但須有fixture ID、revision、checksum與validator version；
6. 回覆文件path、branch、完整40-character commit SHA。文件不得預填自己的未來SHA；commit後由回覆訊息提供。

聊天、摘要或branch name不構成Gate 0 exit。Core只對已commit packet作intake；若本地無法解析POC提供的SHA，狀態維持`Blocked — committed input unavailable`。

## 11. 本 contract 阻擋範圍摘要

| 阻擋項目 | 解除條件 |
| :--- | :--- |
| LLM POC 工作視為已正式授權 | Gate 0 POC Receipt + Gate 1 Core 書面確認 |
| Developer 準備protocol / fake adapter scaffold | Gate 0 receipt後可開始；不得鎖runtime/model |
| Developer 準備real adapter scaffold | Gate 2A provisional finalist ACK後可開始；不得標baseline |
| Developer 加入 LLM production dependency / model lock | Gate 2B final winner ACK + `model_spec.md`後 |
| Developer 開始production persistent child integration | Gate 2B final winner ACK且`docs/protocol.md` reviewed |
| M4b 視為 Accepted | Gate 3：Core Tester 對 delivery exact SHA 驗收 PASS |
| M4c 啟動 | M4a + M4b 均取得 Tester 驗收 PASS（同一 delivery SHA） |
| M4 宣告 Accepted | M4a + M4b + M4c 同一 delivery SHA 全數 Tester PASS |
