# Snowboard 測試規格總論 ( test_spec.md )

本文件是角色間的長期驗收交接契約：將 `arch.md`、`implement/`、適用的 `display_spec.md` / `model_spec.md` 與 `milestone.md` 產品契約轉成可觀察、可重複的驗收條件。本文件維護跨里程碑共用的原則、fixture 定義與回歸策略；各里程碑測項見 `test_spec/` 子目錄下的子檔。測試執行狀態、阻擋與證據索引不寫在本文件，由 Tester 維護於 `reviews/test_progress.md`；Designer 只在 `reviews/milestone_progress.md` 摘要 gate 與階段結果。

---

## 1. 權威來源、範圍與判定

### 1.1 權威順序

`arch.md` → `implement.md / implement/` → `display_spec.md / model_spec.md（適用時）` → `milestone.md` → `test_spec.md`

本文件不得新增、刪除或改寫上游產品行為。若測試需要的可觀察行為未定義、互相矛盾或無法穩定驗證，Tester 交回 Designer；測試阻擋與證據先記於 `reviews/test_progress.md`，跨角色 gate 再由 Designer 摘要到 `reviews/milestone_progress.md`；涉及架構邊界或跨模組契約時再交 Architect。動態 finding、gate 與完成快照不寫入本文件。

### 1.2 子檔案索引

各里程碑測項拆分為獨立子檔，路徑為 `docs/test_spec/test_spec_M{x}.md`：

| 子檔 | 里程碑 | 狀態 |
| :--- | :--- | :--- |
| [test_spec_M1.md](test_spec/test_spec_M1.md) | M1 純軟體核心 | 完成 |
| [test_spec_M2.md](test_spec/test_spec_M2.md) | M2 Mock 對話垂直切片 | 完成 |
| [test_spec_M3.md](test_spec/test_spec_M3.md) | M3 Raspberry Pi HAL 與硬體 bring-up | 完成 |
| [test_spec_M4.md](test_spec/test_spec_M4.md) | M4 本機 AI 語音主線 | 部分完成（017 memory preflight） |
| test_spec_M5.md | M5 外部訊息與工具 | 待補 |
| test_spec_M6.md | M6 語音喚醒、視覺輸入與整體收斂 | 待補 |
| test_spec_M7.md | M7 Display UX 完整化 | 待補 |

### 1.3 Test ID

格式為 `<M階段>-<領域>-<序號>`，例如 `M1-SM-002`。領域代碼：

| 代碼 | 領域 |
| :--- | :--- |
| **EVT** | 事件與識別符 |
| **CON** | 跨層 lifecycle / worker 契約 |
| **BUS** | Event Bus |
| **SM** | State Manager |
| **RM** | Resource Manager |
| **CAN** | Cancel / 收斂 |
| **CFG** | Config |
| **LOG** | Logging / error supervision |
| **BOOT** | Bootstrap / process exit |
| **HAL** | Mock / null HAL |
| **WRK** | Worker / adapter |
| **PAY** | Action payload / ToolRegistry |
| **MSG** | External message buffer |
| **FLOW** | 端到端 session |
| **REG** | Regression / 平台邊界 |

一個自動化 test case 可證明多個 Test ID，但交付證據必須逐一列出 Test ID 到 pytest node ID 的對照；每個 pytest case 也必須能追溯至少一個 Test ID。Test ID 代表一項需要保護的風險或驗收能力，不代表「必須各寫一個 test function」，也不是數量或 coverage 目標。

### 1.4 正式判定

- **Pass**：指定平台、fixture、刺激與全部可觀察結果一致，且所需證據完整。
- **Fail**：已執行但任一可觀察結果不符，或測試本身無法證明其宣稱的風險。
- **Blocked**：因缺少指定平台 / 硬體、上游契約矛盾或外部相依而無法執行或判定。Blocked 不等於 Pass。
- **Developer 自驗成功只代表「待驗收」**；正式判定由 Tester 寫入 `reviews/test_progress.md`，再由 Designer 摘要到 milestone dashboard。

### 1.5 測試價值與範圍門檻

每個 Test ID 至少須直接保護以下一項，否則不列入 milestone gate：

1. milestone 明列的使用者可感知成果或可重複驗收；
2. 跨模組契約不變量，違反時會造成錯誤 action、資料遺失、狀態不一致、資源 / task 洩漏或錯誤 process 終止；
3. 高機率回歸面，例如 config precedence、敏感資料 redaction、race 線性化或 required / optional degradation。

以下內容不單獨建立 gate Test ID：

- `private` 欄位、`private` method、內部容器形狀或不影響契約的呼叫次數；
- 已由同一刺激與證據完整覆蓋的重複斷言；
- 只為提高 test / coverage 數量、沒有對應風險的正反例；
- M3–M7 才會出現的真實硬體、native process、MQTT、wake-daemon 或完整 Display UX；
- 可由 table-driven test 合併的 schema / 錯誤型別組合。

Implement 章節的「最低單元測試」仍是 Developer 的元件測試輸入，但只有符合上述價值門檻者才提升為本文件的 milestone Test ID。

---

## 2. 共用平台、fixture 與證據

### 2.1 平台代碼

| 代碼 | 要求 |
| :--- | :--- |
| **DEV-PY311** | 歷史 Test ID 與 Developer fast loop 的最低版本代碼；Python 3.11，或經團隊指定的單一主要開發版本，執行 Windows / Linux 純 Python、mock / config 測試。不得把此單版本結果當成正式候選 matrix |
| **PORTABLE-PY311** | 正式候選 portable gate：CPython 3.11，執行該 milestone 規定的 non-RPI suite |
| **PORTABLE-PY312** | 正式候選 portable gate：CPython 3.12，執行與 3.11 相同的 suite 與 timeout policy |
| **PORTABLE-PY313** | 正式候選 portable gate：CPython 3.13，執行與 3.11 相同的 suite 與 timeout policy |
| **DEV-PROC** | DEV-PY311，跨平台 subprocess 驗證 exit code (2/3/4/0) 與 pipe/stream readiness |
| **POSIX-PROC** | Linux / Raspberry Pi OS 權威平台，驗證 POSIX `SIGINT` / `SIGTERM` 訊號觸發與原生 process lifecycle；Windows 自動 deselect，不得為此修改 production signal architecture |
| **RPI-NATIVE** | Raspberry Pi 5 / Raspberry Pi OS；驗證 Pi-only dependency、native backend 與指定硬體 fixture。測項使用 `rpi` marker；非 Pi 或未明確選取 `-m rpi` 時由 collection hook **deselect** 並在 collection summary 列出，不得以 skip / xfail 偽裝為已執行 |

M1 / M2 不得以是否恰好在 Raspberry Pi 上執行改變預期；Pi-only test 必須以 `rpi` marker 分流，且不屬本版 M1 / M2 的 Pass 證據。

### 2.1.1 Python minor 支援政策

- Core 正式支援 CPython **3.11、3.12、3.13**；package metadata 必須表達等價的有界範圍 `>=3.11,<3.14`。加入 3.14 或移除既有 minor 都是明示的支援政策變更，須先更新本節、dependency / native ABI matrix 與 candidate gate。
- Developer 日常 fast loop 只需團隊指定的單一主要版本；正式候選則必須在 3.11 / 3.12 / 3.13 執行相同 portable suite。三版本可由 CI、container 或集中驗證環境提供，不要求每台開發機安裝。
- Raspberry Pi 只執行 milestone 已固定的正式部署 runtime；目前目標為 CPython 3.13。Pi 不重跑三個 minor。部署 runtime 或 native ABI 改變時，才撤銷 candidate freeze 並重跑 portable matrix及 Pi gate。
- pure-Python dependency 與 Pi native dependency / ABI 分開鎖定並分開記錄 checksum；portable matrix 不宣稱硬體相容，Pi gate也不取代 Python 語意相容矩陣。

### 2.2 共用 fixture

| Fixture ID | 用途與必要性 |
| :--- | :--- |
| **FX-EVENT** | 可辨識 identity 的 frozen event、nested dict/list sentinel、固定 UUID / counter source |
| **FX-BUS** | 記錄呼叫順序與 event identity 的 handlers、in-memory logger、可控制 raise / cancel 的 handler |
| **FX-BARRIER-WORKER** | 以 `asyncio.Event` 分離 Fact publish、outer task done、abort、force-abort 與 completion notice |
| **FX-RM-GRAPH** | Fake factory / Lifecycle、stable ResourceKey、call log、可控制 READY / failure 的 phase + DAG |
| **FX-M1-PORTS** | M1 專用的 injected `ExternalMessageControl` call recorder 與可設定 accept / reject 的 `ActionPayloadValidator` test double；不得 import Ch 7 / Ch 9 concrete module |
| **FX-CONFIG** | defaults、合法 / 非法 YAML、`.env`、process env、example config 與 secret sentinel |
| **FX-LOG** | in-memory text / JSON handlers、secret / payload / prompt / transcript sentinel、fake supervisor futures |
| **FX-MOCK-HAL** | 固定 PCM / WAV、blank image、mock display call log、MockGPIO event driver |
| **FX-MOCK-WORKER** | deterministic ASR / Vision / LLM / TTS、fake Tool handler、可控制 P5 / exception / cancel 的 adapter |
| **FX-MESSAGE** | in-memory store、fake EventBus、固定 arrival sequence、lock / condition barriers |
| **FX-MOCK-APP** | repository default mock config、三種 mock InputSource、狀態與 Fact recorder |

競態測試只能用 `asyncio.Event`、Condition predicate、queue barrier 或明確 completion notice 控制時序；`sleep()` 只能測產品明定的 timeout / UX 時間本身，不得作同步手段。

### 2.3 所需證據

| 證據代碼 | 內容 |
| :--- | :--- |
| **EV-AUTO** | 完整命令、pytest node ID、Test ID 對照、平台與結果摘要 |
| **EV-RPI** | `EV-PROC` 加 Pi 型號 / OS、完整 40-character implementation SHA、native artifact path + SHA-256、接線表、sanitized config path + SHA-256、fixture SHA、命令、操作步驟、預期 / 實際結果、開始 / 結束時間與 artifact 索引 |
| **EV-MANUAL** | `EV-RPI` 加操作者、固定視覺 / 聽覺 checklist、逐項 pass / fail 與照片 / 影片 metadata；不得取代可自動驗證的 buffer、呼叫順序、格式或 lifecycle 斷言 |
| **EV-RACE** | `EV-AUTO` 加 barrier / call-log 順序，能指出 Fact、task done、notice 或 lock 線性化點 |
| **EV-LOG** | `EV-AUTO` 加 captured log；同時證明必要訊息存在、敏感 sentinel 不存在 |
| **EV-PROC** | subprocess 命令、exit code、stdout/stderr 或 sanitized log、無殘留 task / child 的證據 |
| **EV-REVIEW** | 無法由 runtime 強制的慣例之 code-review 清單與對應自動化 mutation-sentinel 結果 |

任何證據不得包含 credential、完整 payload、transcript、prompt、原始音訊 / 影像或 raw model output。

### 2.4 Candidate、run 與 evidence identity

自 M4 的第一個產品候選起，含 RPI-NATIVE 或人工觀察的驗收必須使用以下共同 identity contract；本節不回溯改判或重跑已完成的 M3：

1. Runner 必須接收外部傳入的 40-character candidate SHA；只讀取當前 `HEAD` 不構成授權。HEAD 不符、SHA 格式錯誤或受保護路徑 dirty 均在測試啟動前 FAIL。
2. 受保護路徑只涵蓋 `src/`、`tests/`、candidate / acceptance runner、candidate CI workflow、dependency / lock、package metadata及 runner 讀取的 config contract。任一變更撤銷 freeze；本機實際 config、evidence與無關文件不在此列。
3. Portable matrix 只在準備或更新 frozen candidate 時執行；三版本使用同一 SHA、run ID與 portable scope，且達0 Fail / Blocked / Skip / XFail。一般development push只跑主要版本與affected tests，portable命令不得收集`rpi` marker。
4. Acceptance使用唯一且不可覆寫的`run_id`；中途失敗保存result與raw log。Debug可按診斷需要執行，不需正式FAIL bundle授權，但debug結果不得標記或合併為正式Pass。
5. Preflight 不產生正式 PASS card；它驗證 target runtime、hardware、artifact / sanitized config checksum、portable matrix index及尚未使用的run output。Branch名稱只作診斷資訊。
6. 有人工觀察時，既有test report / card記錄run ID、Test ID、operator、時間與Pass / Fail；不要求通用READY、nonce、producer PID、獨立record command或額外重錄流程。
7. Tester final reconciliation只核對portable matrix與target result使用同一SHA，且正式target result沒有混用run ID；不要求README、manifest、cards與中間JSON建立逐層checksum chain。

每個自動化 async、process與device readiness等待都必須有由test spec設定的bounded timeout；timeout必須產生非零exit、FAIL result及raw log，不得永久等待或轉為Skip / XFail。現場人工操作依各Test ID的既有步驟執行，不因此建立通用等待framework。

State Manager、EventBus、async cancellation與可模擬的GPIO edge sequence契約，應以fake / simulated fixture納入portable tests。RPI-NATIVE保留無法由portable fixture證明的真實kernel / driver、device ownership、signal、latency、thermal以及人工可聽／可視結果。

---

## 3. Developer 交付 Tester 的必要資料

每個待驗收 revision 至少提供：

1. revision 識別與工作包範圍；
2. implement 契約引用及 Test ID → pytest node ID 對照；
3. 修改檔案、平台、Python 版本、config / fixture 摘要；
4. 聚焦測試、milestone entrypoint、完整 regression 的原始命令與結果摘要；
5. race case 的 barrier / call-log 證據；
6. exit code、log redaction、無殘留 task / child 的相應證據；
7. 未驗證風險與 Pi-only / 後續 milestone 排除項。
8. 若含實體／人工 gate：portable matrix index、外部指定 candidate SHA、target preflight與尚未使用的 acceptance run ID。

缺少必要證據時，Tester 可判定 Blocked 或要求補交；不以測試數量或 coverage 百分比取代逐條 Test ID 驗收。

---

## 4. 回歸策略

- **修改 event schema、Bus 或 logging**：重跑全部 M1 與 M2。
- **修改 SM、RM、Cancel、worker lifecycle 或 timeout**：重跑全部 race、fatal、shutdown、recovery 與兩種 mock session。
- **修改 config**：重跑 config table、example loader、RM graph、default mock startup。
- **修改 action payload、ToolRegistry 或 Reasoner**：重跑 payload 正反例、SM self-check、duplicate/rest、P5 與兩種 session。
- **修改 external-message**：重跑所有 lock / condition race、overflow、flush/discard、Interrupt、shutdown 與 external session。
- **任何新增 subscriber / observer / log field**：重跑 nested mutation sentinel 與完整 redaction suite。

不因單一工作包看似無關而刪除前序 milestone 驗收。若完整 suite 成本過高，Developer 可提出等價的分組、選擇或執行最佳化，由 Tester 確認每個 Test ID 的行為與證據仍完整保留；此類調整不得降低平台、刺激、可觀察結果或 regression 要求。若要移除 / 放寬 Test ID、平台或證據門檻，屬 milestone 驗收變更，須由 Designer 依 `milestone.md` §1.2 提案並取得使用者確認；Tester 或 Designer 都不得單獨以 skip / xfail 或縮減 suite 改變 gate。

---

## 5. 明確延後的覆蓋

以下各階段的特定風險或硬體/模型證據，不在早期里程碑提前要求：

| 階段 | 不提前要求的證據 |
| :--- | :--- |
| **M3** | 真實 audio/display/camera/GPIO 品質、電氣行為、Pi dependency 與 selected Display profile；M2 只驗 mock/null 公開契約 |
| **M4** | LiteRT-LM child READY、terminate/kill/waitpid、固定 baseline 的真實 ASR/TTS/LLM、Display runtime 接線與 native destructive cleanup |
| **M5** | MQTT broker、公開 wire schema、真實 Tool handler 與 reconnect |
| **M6** | 固定 baseline 的 wake/Vision、wake daemon IPC、跨 process mic release proof 與長時間 session soak |
| **M7** | Display 未來 spec revision 的正式資產、動畫、轉場、可讀性與重複 lifecycle 收斂 |
