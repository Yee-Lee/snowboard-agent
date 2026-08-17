# Portable-first Candidate / Hardware Acceptance Runbook

本手冊是自 M4 第一個產品候選起的共用 gate。它規範開發除錯、portable candidate、candidate freeze、Pi preflight及正式 acceptance 的順序；里程碑 test spec只補充 suite、timeout、硬體與人工 checklist，不得降低本手冊的 identity / evidence門檻。本流程不回溯改判或重跑已完成的 M3。

## 1. Gate sequence

| Gate | Owner | Entry | Exit | Failure action |
| :--- | :--- | :--- | :--- | :--- |
| G0 Contract / static | Designer + Tester | design、Test ID與schema已簽核 | contract mapping、event schema與專案指定 type check通過 | 回上游 owner；不可進 target debug |
| G1 Developer fast loop | Developer | 工作包 ready | 主要 Python minor的受影響 unit / integration tests通過 | 留在本機修正；log不作 acceptance |
| G2 Provisional snapshot | Designer；commit需 USER | G1完成；candidate scope已核對 | 建立尚未freeze的完整受測SHA；protected paths clean | 不得無USER同意commit；內容變更須建立新candidate |
| G3 Portable candidate | Tester | G2完整SHA | CPython 3.11 / 3.12 / 3.13同一suite全綠；所有等待有timeout | 回Developer；修正後建立新candidate並三版本全重跑 |
| G4 Candidate review / freeze | Designer | G3 matrix完整 | Blocking為零；同一provisional SHA登記為frozen | 受保護輸入改變即撤銷freeze、建立新candidate並回G3 |
| G5 Pi preflight | Tester / operator | frozen SHA、新run ID、Pi ready | identity、runtime、hardware、artifact、config、matrix與handshake全通過 | 不產生PASS card；修正identity或撤銷freeze |
| G6 Pi acceptance | Tester / operator | G5 PASS | 一次完整RPI-NATIVE gate結束 | 保存FAIL後停止；不得續跑或補卡 |
| G7 Reconciliation | Tester；Designer確認 | G6 bundle完整 | portable / Pi / SHA / run ID一致 | Fail / Blocked；不得拼接舊evidence |

## 2. Freeze boundary

Candidate SHA必須由呼叫者以 `--candidate-sha` 傳入。Runner須在任何測試或硬體操作前驗證它恰為40個十六進位字元且等於checked-out `HEAD`；不得以 `git rev-parse HEAD` 的結果自行填入預期值。

Freeze受保護輸入至少包括：

- `src/`、`tests/`；
- `scripts/` 中的candidate / acceptance / observation runner；
- `pyproject.toml`、`pytest.ini`、requirements與lock files；
- CI candidate workflow；
- runner讀取的config schema、example與artifact manifest contract。

上述路徑出現tracked或untracked異動，或其內容在freeze後改變，candidate立即失效。Evidence output不屬產品candidate輸入，但必須寫入獨立run目錄且不可覆寫。

Provisional candidate commit的用途是提供portable matrix可重現的不可變SHA，不是freeze或Accepted宣告。建立前仍須依專案規範展示完整commit title、body及檔案，取得USER明確同意。Portable matrix與Designer review通過後，才把同一SHA寫入freeze manifest；若任一gate要求內容修改，建立新candidate並重跑三版本。

## 3. Runner interface contract

Developer工作包須提供單一入口（建議 `scripts/candidate_gate.py`）；可採其他等價實作，但以下CLI語意與fail-closed行為不可省略：

```text
candidate_gate.py portable \
  --candidate-sha <40-hex> \
  --run-id <unique-portable-run-id> \
  --python 3.11|3.12|3.13 \
  --suite <test-spec-suite> \
  --timeout-seconds <bounded> \
  --output <evidence-root>/portable/<run-id>/python-<minor>

candidate_gate.py preflight \
  --candidate-sha <40-hex> \
  --run-id <new-acceptance-run-id> \
  --portable-index <matrix-index.json> \
  --runtime 3.13 \
  --hardware <sanitized-hardware.json> \
  --config <sanitized-config.yaml> \
  --artifact-manifest <artifacts.json> \
  --output <evidence-root>/acceptance/<run-id>

candidate_gate.py accept \
  --candidate-sha <40-hex> \
  --run-id <same-acceptance-run-id> \
  --preflight <preflight.json> \
  --suite <milestone-rpi-suite> \
  --timeout-seconds <bounded> \
  --output <evidence-root>/acceptance/<run-id>

candidate_gate.py debug \
  --candidate-sha <40-hex> \
  --run-id <debug-run-id> \
  --node <single-card-node> \
  --output <evidence-root>/debug/<run-id>
```

Exit code `0`只表示該命令完整通過。SHA / dirty / matrix / runtime / checksum / run reuse / readiness / manual observation錯誤、timeout、Fail、Blocked、Skip或XFail都必須非零。Runner須以argument list啟動子程序、保存stdout / stderr / exit code，不接受shell字串拼接。

## 4. Portable matrix

三個Python minor執行同一test-spec suite。每個async、subprocess與suite都有bounded timeout；timeout是Fail。Matrix index只有在三個版本皆完成且各為0 Fail / Blocked / Skip / XFail時才能標記`status=Pass`。

State Manager、EventBus、async cancellation、GPIO edge sequence與manual readiness要在本gate使用fake / simulated fixture完成；Pi只驗真實kernel / driver、device ownership、signal、latency、thermal與人工可聽／可視輸出。Portable可驗證的狀態／schema問題不得延至Pi debug。

每個version result及matrix index至少記錄：

- portable run ID、完整candidate SHA、branch、protected-path dirty result；
- exact command argv、platform、Python implementation / minor、dependency lock checksum；
- suite / Test ID mapping、開始／結束、timeout、exit code；
- passed / failed / blocked / skipped / xfailed計數與raw log path。

3.11、3.12、3.13可以在CI平行執行。Developer不需在本機安裝三版本；CI artifact或集中環境輸出matrix index後，由Tester核對。

## 5. Debug, preflight, and acceptance isolation

- `debug/<run-id>/`只用於bring-up與單卡重跑，可保留FAIL / diagnostic evidence，但永遠不能被acceptance manifest引用。
- `acceptance/<run-id>/`在preflight前必須不存在。Preflight以原子方式建立目錄及identity record；已存在或重複run ID即Fail。
- Preflight不執行正式card，也不寫Pass result。它只驗證candidate、clean boundary、Pi 3.13、hardware / config / artifact checksum、portable matrix與runner readiness。
- Acceptance只能在相同run ID的preflight PASS後開始，且須完整執行milestone RPI-NATIVE suite。任一card失敗、中斷或逾時，runner寫入FAIL summary、保留raw log並停止封包。
- 若修正protected input，使用新candidate SHA、重跑G2至G4並建立新acceptance run。若只修正未受保護的實體接線，仍保留失敗run並以新run ID重新preflight / acceptance。

## 6. Readiness and manual observations

涉及child process、device或人工操作時，producer必須發出帶`run_id`、`test_id`、`ready_at_utc`與nonce的明確READY record；consumer在test-spec timeout內等待該record。固定`sleep`不能替代handshake。

人工 observation 必須引用同一run ID、test ID、nonce及晚於READY的timestamp，並包含operator、checklist version、逐項boolean與record command exit code。缺檔、過期、wrong nonce / run、record command失敗或任一false都使card FAIL；不得先填PASS再等待測試。

## 7. Evidence layout and reconciliation

```text
docs/outsource/evidence/<delivery-id>/
├── portable/<portable-run-id>/
│   ├── python-3.11/result.json
│   ├── python-3.12/result.json
│   ├── python-3.13/result.json
│   └── matrix-index.json
├── debug/<debug-run-id>/...
└── acceptance/<acceptance-run-id>/
    ├── identity.json
    ├── preflight.json
    ├── manifest.json
    ├── results/
    ├── cards/
    ├── manual/
    └── logs/
```

`identity.json`、preflight、manifest、每張card / result及manual observation都要包含相同candidate SHA、acceptance run ID與`mode=acceptance`。另須記branch、dirty check、command、platform、Python、config / artifact checksum、開始／結束、exit code與raw log。Tester逐檔核對；README或索引的宣告也必須一致。

## 8. Required no-hardware dry run

在任何M4 Pi acceptance前，Developer與Tester須在fake fixture執行以下failure demonstration。每個case都必須產生非零exit、明確FAIL reason及獨立raw log，且不能建立acceptance PASS manifest：

| Case | Injected condition | Required rejection |
| :--- | :--- | :--- |
| DRY-SHA | 外部SHA與HEAD不符 | 在suite前Fail |
| DRY-DIRTY | `src/`、`tests/`或其他protected input有異動 | 撤銷freeze並Fail |
| DRY-MATRIX | 缺任一Python minor、版本結果非零或matrix混SHA | preflight Fail |
| DRY-TIMEOUT | fake async / process不送completion | bounded timeout，保存FAIL log |
| DRY-MANUAL | READY後沒有有效observation或record command失敗 | card Fail |
| DRY-RUN-ID | acceptance output已存在、混用debug或不同run ID | 拒絕覆寫／拼接 |

Tester須從實際命令輸出與JSON schema判定，不可只閱讀runner原始碼。六項全通過才解除首次M4硬體gate的process blocker。

## 9. Cost envelope and accepted trade-off

以目前M3級別suite作規劃基準：三版本portable matrix預估每版本5–8分鐘；CI平行約6–10分鐘wall time，序列約15–24分鐘。G5 preflight約3–5分鐘；M4 Pi完整自動加人工acceptance暫估35–50分鐘且只對frozen SHA執行一次。實際數字由首次dry run / M4 test spec校正。

Core接受候選前多付約6–10分鐘CI成本，以換取避免在Pi上除錯Python minor、async、state-machine、schema與fake可覆蓋行為。Pi不乘三版本；只有部署runtime、protected input或candidate SHA改變才重啟正式硬體gate。
