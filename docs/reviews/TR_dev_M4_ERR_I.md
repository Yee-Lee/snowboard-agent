---
requestor: "Tester"
owner: "Developer"
status: "Resolved"
severity: "Blocking"
candidate: "f572915d0b0d5c52067e9100c5b022e57aefe506"
target: "tests/test_m4_err_*.py and directly affected retained regressions"
---

# TR_dev_M4_ERR_I — close false-green oracles and reproduce the full portable gate

日期：2026-09-21。Tester 對 candidate
`f572915d0b0d5c52067e9100c5b022e57aefe506` 執行 Verify。Workstation 從 clean detached
worktree 重算的 tracked-content SHA-256 為
`2e3cb7ba5e1cdcb26e8d5dc1d79147b1eb05f41687efdac453700a47dc176f6f`，與 Pi
`M4-ERR-DEV-04` 及 fresh `M4-ERR-TESTER-02` binding 相同；config 與四個 artifact
identity 也相同。Developer 五張 Pi cards、raw logs、JUnit hashes 與 final manifest 可讀且內部一致，
但這不能取代下列 Test Spec acceptance oracle。

## Blocking B1 — taxonomy／publisher／composition tests 可在未驗產品契約時假綠

**依據**：`test_spec_M4_ERR.md` 的 `M4-ERR-PU-003`、`M4-ERR-PU-004`、
`M4-ERR-PI-010`，以及 Tester 規則「assertions 必須觸發產品行為」。

**位置與實際行為**：

- `tests/test_m4_err_faults.py:123` 的 PU-003 只對五個 hard-coded dict 執行
  `sum(path.values()) <= 1`；沒有把五種 taxonomy sequence 注入 State Manager，也沒有驗 timeout
  proof 或 unknown exception wrapping。
- `tests/test_m4_err_faults.py:144` 的 PU-004 只檢查 enum member 與 summary 常數；沒有掃描
  production publisher、broad-catch suppressor 或 cancellation publication。
- `tests/test_m4_err_candidate.py:46` 的 PI-010 只查看六個固定函式，且每個函式只要任一處出現
  `ComponentSystemFault`、`fault.to_event()` 或 `_report_fault()` 字樣就通過；它沒有逐一枚舉
  M4 fault-mapping catch site，也無法拒絕同函式內另一個 lossy／suppressed catch。

**預期／影響**：Test Spec 要求 runtime taxonomy path 與逐 catch-site closed audit。現況即使新增未包裝
的 broad catch、取消路徑 fault publish 或雙 Fact/fault path，仍可能 PASS，屬 blocking false green。

**首選修正與最低驗收**：以 table-driven runtime stimuli 驗五類 taxonomy；AST audit 明確枚舉每個
production `ErrorOccurred` publisher 與每個 M4 mapping catch，逐 site 驗 typed `raise ... from cause`、
cancellation re-raise、無 detached suppression，並保留 spec 列出的 exemptions。加入 negative fixtures，
分別插入 positional／neutral publisher、lossy broad catch、cancel publish 與同函式第二個 bad catch；
每個 fixture 都必須使對應 oracle Fail。

## Blocking B2 — required matrix/privacy/exit assertions 沒有可執行完整映射

**依據**：Test Spec `M4-ERR-PU-007`～`009`、`M4-ERR-PI-004`～`009` 的逐列 steps 與
acceptance criteria。

**可重現缺口**：

- PU-007 只確認 `error_observer.safe_category_for_code` 的 object identity，沒有確認
  `display.status_bar` 也引用同一函式。
- PU-009 沒有把六個 sentinel 各自完整送過 Event、structured log 與 Display；多數 case 只檢查
  summary 常數或 constructor rejection。
- PI-004 的 recovery-hook unit test 沒有驗 recovery failure 的 product exit 4、single public root、
  不產生第二個 `ErrorOccurred`／ERROR cycle。
- PI-005 的 M4-ERR matrix test 只直接覆蓋三種 ASR system fault 與 Audio capture fault，沒有一個
  executable eleven-row catalog 能證明所有 request-outcome、timeout proof、cancel 與 unknown-code rows
  都被收集且執行。
- PI-006 的 matrix test 只參數化四種 system error；沒有可執行七-row catalog 覆蓋 R1/R2 proof、
  illegal SM response 與 unauthorized planned recycle。
- PI-008 只直接驗 callback／edge-read 兩列；未驗 legal／stale event、active Session 進 ERROR、
  startup acquisition exit 3。PI-009 未驗 voice convergence independence、static capability 不變與
  caller hint WARNING/drop。
- PU-008 未以同一完整 matrix 證明 Bus invariant、recovery/proof failure、normal shutdown stop failure
  continuation、fatal no-double-cycle 與 single-root output。

既有 M4A/M4B regression 可以作為某些 row 的直接 oracle，但 Developer 必須提供明確、可機器核對的
row→node mapping，且每個 required row 都實際 collect/execute、zero skip/xfail/xpass；不能用整體
1,715-test count 推定 coverage。

**最低驗收**：建立完整 catalog guard（missing／duplicate／deselected／skip／xfail／xpass 均 Fail），
補足上述 runtime assertions，並以 negative fixtures 證明 Event/log/Display sentinel 任一路徑洩漏、
漏一個 matrix row 或 fatal double-cycle 都會使 suite Fail。

## Blocking B3 — Pi cases 的部分 PASS 沒有觀測到 Test Spec 指定產品行為

**依據**：`M4-ERR-PV-001`、`M4-ERR-PV-002` acceptance criteria。

**位置與實際行為**：

- `tests/test_m4_err_pv_rpi.py:187` 的 ALSA case 確實啟動 live backend 並驗 Event repr，但未 capture
  product structured log；其後把已 sanitized 的 `ErrorOccurred` 注入另一個 `run_app` composition
  只證明 exit 4，不能證明原始 ALSA cause 未進 product log。
- `tests/test_m4_err_pv_rpi.py:220` 的 callback case 收集 `BUTTON_CALLBACK_FAILED` event，但沒有讓
  active Session／State Manager 消費它並斷言進入 ERROR；separate fatal probe 只使用最後一筆
  `GPIO_EVENT_READ_FAILED`。

Live ALSA/GPIO/native-child identity、one-shot injection、ASR/LLM/TTS rebuild 與下一次 native success
的現有 assertions 具實際價值，應保留；本 finding 只要求補上缺失的 product-observable oracle。

**最低驗收**：PV-001 保存 canonical structured log 並斷言 raw sentinel 不存在；PV-002 從 active
Session 經 Event Bus／SM 驗恰一次 ERROR transition。更新 test bytes 後必須使用新 run ID 在 Pi
完整重跑 `M4-ERR-PV-001`～`M4-ERR-PV-005`，不得沿用 `M4-ERR-DEV-04`。

## Blocking B4 — fresh same-bytes portable Verify 有一項 timeout Fail

Pi run `M4-ERR-TESTER-02` 在 CPython 3.13.5、相同 content/config/artifact binding 下執行完整
non-RPi suite，結果為 **1 failed, 1714 passed, 34 deselected**。失敗 node：

`tests/test_m4b_reg_001.py::test_G01_all_constructor_forms_and_affected_test_controls_are_audited`

它被 `pytest-timeout` 在 120 秒終止。正式 raw log SHA-256：
`f3a3cd9f8cda17bc66237dc02c8cedc05f5313e606363ada11d1ee153c0623f6`；JUnit SHA-256：
`91ebf5e78fbb390320174324d7452405884a5975e42098d31432aa76679676f2`。Locator：Pi-local
`~/m4err-dev-20260920-iRHsbo/verification/M4-ERR-TESTER-02/private/`。

在沒有其他 pytest 併發的情況下，以相同 `--timeout=120` 單獨重跑該 node，仍為
**1 failed in 120.40s**；因此不是 full-suite 負載造成的一次性結果。單項 raw log SHA-256：
`0a22bc05e0ac8a78a33557166abc50f7341a85cac381c02aeb22260a86e982b4`；JUnit SHA-256：
`c87b249432f89930108bc00af1d693c6a6e30b0cb882a8a7e3ba83367ae21bdb`。

**最低驗收**：找出與 Developer 宣稱 1,715 Pass 不一致的原因，保留 bounded timeout 並讓 fresh
full portable run 達成 0 Fail／Blocked／Skip／XFail／XPass。任何 test/product/runner byte 修正都產生
新 content digest，回到 Developer convergence，之後再以全新 Tester run 執行完整 portable 與五項 Pi
cases；不得把本次 Fail、focused rerun 或舊 Developer cards 拼接成 PASS。

## Disposition

`f572915` 的 M4-ERR Tester Verify 為 **Fail**。Developer 回覆本單時須逐項列出實際修正、row→node
catalog、negative-control 結果、fresh Pi full-portable 結果與新 same-bytes五-case run locator。Tester
只複驗本單 findings、直接影響與 regression；所有 blocking 清除前不得宣告 M4-ERR Accepted。

## Developer correction response — 2026-09-21

狀態為 **Revised，待 Tester Verify**；Developer 未宣告 Accepted，也未 commit／push。修正後候選的
tracked-content SHA-256 是
`c5edbe68a3d777a2c515a1adfee9a801a3a8b00648b19907e16ecdf81f546634`。工作站與 Pi 隔離
checkout 已各自重算為相同值；config SHA-256 仍為
`101e0d36f90681e1a62740d5b1ffe8842226e2d46874da42b46ed6e57ed0fde8`，四個 artifact identity
也與本單列出的已核對 tuple 相同。

### B1 — closed taxonomy／publisher／catch-site oracles

- `test_m4_err_faults.py` 現在以產品 runtime stimuli 驗證 request outcome、system fault、Display
  degradation、cancellation、fatal 五類 path，包含 timeout proven/unproven 與 unknown exception
  typed wrapping；六個 sentinel 逐一通過 EventBus、canonical structured log 與 StatusBar。
- `test_m4_err_candidate.py` 以 AST 明確盤點所有 production `ErrorOccurred` constructor/publisher 與
  M4 mapping catches，逐 site 驗 cancellation re-raise、typed mapping、cause 與 bounded exemption。
  positional publisher、neutral publisher、lossy broad catch、cancel publication、同函式第二個 bad
  catch 五種 negative fixtures 均被 oracle 拒絕。

### B2 — executable matrix catalog and missing runtime assertions

- 可機器執行的 catalog 為 `tests/m4_err_required_rows.json`，SHA-256
  `73bfacfc72d81bf27f0673ad9e6f9c4a1a2bbb97ad1af4912d91bcae2ea008d0`。它含 **57 個 row、57 個
  唯一 node**：PU-007 8、PU-008 8、PU-009 6、PI-004 2、PI-005 11、PI-006 10、PI-008 5、
  PI-009 7。`test_m4_err_catalog.py` 會在隔離 pytest collection/execution 中核對 exact set 與 JUnit；
  missing、duplicate、deselected、skip、xfail、xpass negative controls 均會 Fail。
- 補足的 runtime assertions 包含兩個 consumer 共用同一 sanitizer、recovery-hook failure exit 4／
  single event／single ERROR／single public root、config 2／startup acquisition 3／normal stop failure 0、
  active Session 消費真實 GPIO callback、Button legal/stale/bounce、Display caller-hint warning/drop、
  atomic disable、voice convergence independence 與 static capability 不變。
- fatal race 實際暴露 RM/SM 同輪完成時未 retrieve 的 task exception；`run_app` 現在收斂已完成的 SM
  waiter，避免第二個 raw traceback。Event/log/Display privacy leak 與 duplicate event／ERROR／public-root
  negative controls均被拒絕。

### B3 — Pi product-observable evidence

- PV-001 從原始 live ALSA injection 所在 EventBus 啟動真正的 `ErrorLoggingObserver`，保存 canonical
  JSON log 並斷言 raw sentinel 不存在。bound observation locator：
  `private/M4-ERR-PV-001/product-observation.json`，SHA-256
  `185116a769fa5d626d7854dd8fe5890e9fa8733a19574904dbc7116bd0a62f4d`。
- PV-002 讓 live gpiod callback fault 經同一 EventBus 進入 active Session／State Manager，等待 serial
  inbox 消費後斷言恰一次 ERROR；另保留 edge-read fault 與 exit 4。bound observation locator：
  `private/M4-ERR-PV-002/product-observation.json`，SHA-256
  `ca8c5ad4dbc08dab2f7745356b9aa27419e7606687d45c0f5a66c6cbfaf10f6d`。
- runner 要求上述 observation 存在、在 card 中綁定 locator/hash，finalize 時再次核對；缺漏或內容變更
  都拒絕完成。

### B4 — bounded G01 and fresh same-bytes Pi convergence

- `m4b_source_violations` 的 assignment-alias resolver 原本會在 alias cycle 反覆改寫，造成 AST-node-count
  次 quadratic passes。現改為 import-rooted、monotonic、每個 target 最多解析一次；新增 cyclic alias
  bounded regression。工作站最終 focused/affected suite：**144 passed in 79.66s**；`git diff --check`
  與 Python compilation 通過。
- 最終 Pi run：`M4-ERR-DEV-06`，target `pi5-4gb-debian13-aarch64-cp3135`、CPython 3.13.5。
  fresh full portable 為 **1750 passed, 34 deselected, 0 failed/skipped/xfail/xpass in 62.05s**；raw log
  SHA-256 `833e49e4169d3d231bd8da60d5d1613bfb9cda92906d5b2f121fb315823e50b8`，JUnit SHA-256
  `84ec508f0584e3cd7a115ae6e497d8889250aacf8c07bc89805098020292b7ac`。
- 同一 binding 的 PV-001～PV-005 各為 `1 passed, 0 failed, 0 skipped`。Pi-local run locator：
  `~/m4err-fix-20260921-1o4NLJ/verification/M4-ERR-DEV-06/`；final manifest：
  `public/final.json`，SHA-256
  `60dabf576c7ff3d998a657681cf55cc24c71d60429e5c92e36f03d4b6322b03a`。
- `M4-ERR-DEV-05` 是未受理的失敗診斷：它在 live PV-002 顯示 Event 已 publish、但 assertion 在 SM
  inbox drain 前讀值。修正等待 consumer 後產生新 digest 並完整重跑 `DEV-06`；沒有拼接舊 cards。

請 Tester 依本單 findings、上述 locator 與直接影響 regression 執行 Verify。

## Tester re-review — 2026-09-21

Disposition：**Rejected/Revised**。修正後工作站與 Pi tracked-content SHA-256 均重算為
`c5edbe68a3d777a2c515a1adfee9a801a3a8b00648b19907e16ecdf81f546634`；config／artifact tuple、
`M4-ERR-DEV-06` portable log／JUnit、五張 PV cards、五組 raw log／JUnit、PV-001／002 product
observations 與 final manifest hashes均核對一致。Tester focused/affected selection實跑
**104 passed in 56.53s**。B3、B4 已清除；B1、B2 仍有下列同 scope blocking false green。

### B1 retained — shared-mapping heuristic仍接受同函式第二個lossy catch

**位置**：`tests/test_m4_err_candidate.py:162`；特別是 `function_has_typed_create`、
`preserved_for_shared_mapping` 與 `tests/test_m4_err_candidate.py:248` 的組合。

**可重現證據**：對 `_catch_violations()` 提供一個函式，其中先有任意
`ComponentSystemFault.create(...)`，另一個 `except Exception as exc` 只執行 `saved = exc`，沒有
typed raise、publish、re-raise 或 bounded exemption。實際結果為空清單：

```text
lossy_second_catch_violations []
```

這是 B1 原最低驗收要求拒絕的「同函式第二個 bad catch」變體。現行 checker 將「函式任何位置存在
typed create」加上「catch 內保存 cause 到任意變數」視為有效 shared mapping，但沒有證明該變數後續
進入 typed `raise ... from cause`；因此真正 suppressed catch 仍可假綠。

**最低修正／複驗**：shared-mapping 例外須綁定明確 mapping sink，並證明保存的同一 cause 會進入
typed raise/publish；任意 assignment 不可滿足。把上述 exact shape 加入 negative fixture，並保留現有
production catch inventory 0 violations。

### B2 retained — catalog只驗prefix數量，必要row可被同prefix假row替換

**位置**：`tests/test_m4_err_catalog.py:24`、`:40`、`:50`、`:106`。

**可重現證據**：讀取現行 catalog，將 key `M4-ERR-PI-005:ASR-11` 改為
`M4-ERR-PI-005:ASR-12`，保留原 node、57 rows、唯一 nodes 與相同 prefix count；`_load_catalog()`
仍成功返回：

```text
catalog_substitution ACCEPTED
```

這表示 required row 缺失時可用未定義 row 補足數量，違反 B2 的 exact row catalog／missing-row
negative control。現有 test 只刪 row，沒有覆蓋 same-prefix substitution。

**最低修正／複驗**：以 Test Spec 固定的 exact required row-ID set 比對 catalog keys（missing 與
unexpected 都 Fail），新增 `ASR-11 → ASR-12` substitution negative fixture；既有 exact collection、
JUnit、duplicate/deselected/skip/xfail/xpass guards 保留。

### Re-review routing

上述任一 test byte 修正都改變 protected content digest；`M4-ERR-DEV-06` 不可作最終 same-bytes
credit。Developer 以新 digest 執行 affected negative controls、fresh full portable 與完整
`M4-ERR-PV-001`～`005`，再把本單更新為 Revised。Tester 下輪只複驗這兩個 retained finding、直接
影響與新 regression。

## Developer retained-finding response — 2026-09-21

狀態已回到 **Revised，待 Tester re-verify**。本輪只修改兩個 retained finding 的 oracle；未沿用
`M4-ERR-DEV-06` 作 same-bytes credit，也未 commit／push。

### B1 retained correction

- shared mapping 不再以「函式內任意 typed create + handler 內任意 assignment」放行。checker 現在
  收集由該 handler bound exception 直接賦值的 target，要求 sink 位於 handler 之後、同一 target
  實際成為 `raise ... from target` cause，而且被 raise 的物件本身必須是 `SystemFault.create` 的結果；
  EventBus 原有 `_HandlerFailure(record, exc)` 保留為具名、封閉的 failure sink。
- Tester 提供的 exact shape 已加入
  `typed-create-with-unconsumed-second-catch` negative fixture。直接重現結果為
  `['5:lossy_or_suppressed_broad_catch']`；另有 cause 流入 untyped raise 的 negative control，避免只靠
  同名 cause 與不相關 typed create 假綠。Production catch inventory 仍為 0 violations。

### B2 retained correction

- `tests/test_m4_err_catalog.py` 現定義 Test Spec 的 exact 57-row `REQUIRED_ROWS`，以完整 key set
  equality 核對；錯誤同時列出 missing 與 unexpected IDs，不再以 prefix count 代替 identity。
- `ASR-11 → ASR-12` exact substitution fixture 已加入。直接重現為
  `M4_ERR_CATALOG_ROW_SET_MISMATCH:missing=['M4-ERR-PI-005:ASR-11']:`
  `unexpected=['M4-ERR-PI-005:ASR-12']`。既有 unique node、exact collection/JUnit、missing、
  duplicate、deselected、skip、xfail、xpass guards 均保留。

### Fresh same-bytes verification

- 工作站：retained targeted **12 passed in 9.67s**；完整 affected selection
  **146 passed in 91.31s**；`git diff --check` 通過。
- 新 tracked-content SHA-256：
  `c4004c40a5f9d3790b9ac54f54c2822cd070cd46637622a5ae0e3a0ab0beb14c`，工作站與 Pi 隔離
  checkout 各自重算一致。
- 新 Pi run `M4-ERR-DEV-08`：fresh full portable **1752 passed, 34 deselected,
  0 failed/skipped/xfail/xpass in 62.71s**。Raw log SHA-256
  `6e1ba1067a0df4134f1974a65d80537eb3a62336ccebb842af0fdad68fe964dd`；JUnit SHA-256
  `adb3c3806e850a037b233f724af1c92be036b4edeaa7c1e7262c6d143b1a5ccc`。
- 同一 `DEV-08` binding 的 PV-001～PV-005 各為 `1 passed, 0 failed, 0 skipped`。Pi-local root：
  `~/m4err-fix-20260921-1o4NLJ/verification/M4-ERR-DEV-08/`。Final manifest
  `public/final.json` SHA-256：
  `a8151c905562fa8a8dbed19d553a58335e3f04324a34c060c0419b67f932c518`。
- PV-001/PV-002 product observation SHA-256 分別為
  `19b79b98cfb3af7a0efe74ffaff503b5509a741033b5e70c8e6ac9b16d650e4b` 與
  `ca8c5ad4dbc08dab2f7745356b9aa27419e7606687d45c0f5a66c6cbfaf10f6d`，均由對應 card 綁定。
- `M4-ERR-DEV-07` 因 completion audit 後再收緊 typed sink 而不作 final credit；所有 protected bytes
  變更都已在全新的 `DEV-08` 完整重跑，未拼接舊 cards。

請 Tester 只依 re-review routing 複驗兩個 retained finding、直接影響與新 regression。

## Tester second re-review — 2026-09-21

Disposition：**Rejected/Revised**。工作站重算的 tracked-content SHA-256 為
`c4004c40a5f9d3790b9ac54f54c2822cd070cd46637622a5ae0e3a0ab0beb14c`，與 Developer 交付相同。
retained targeted selection 實跑 **8 passed in 8.19s**，但獨立 mutation probes 仍證明 B1
acceptance oracle 可假綠。B2 已清除；B1 仍 blocking。

### B2 resolved — exact required row set 已封閉

`tests/test_m4_err_catalog.py:18` 的 `REQUIRED_ROWS` 與 Test Spec 各表的 57 個 required row 一致；
`_load_catalog()` 在 `:68` 以 exact set equality 同時拒絕 missing 與 unexpected IDs。
`ASR-11 → ASR-12` substitution fixture 與獨立查核都得到 row-set mismatch，不再可用
same-prefix 假 row 補數量。

### B1 retained — typed create 或曾經 typed 的變數仍可充當未證明的 sink

**位置**：`tests/test_m4_err_candidate.py:169` 的 function-wide `typed_fault_names`、`:212`
的 `typed_create` 與 `:269` 的 `(typed_create and bound_cause)`。

**可重現證據 1**：broad catch 內建立 typed fault，但既不 raise、publish 也不交給封閉
failure sink：

```python
def map_fault():
    try:
        product()
    except Exception as exc:
        fault = ComponentSystemFault.create(code="BAD", cause=exc)
        saved = exc
```

`_catch_violations(ast.parse(source))` 實際返回：

```text
typed_created_then_suppressed []
```

`typed_create and bound_cause` 只證明 handler 內有 create 與使用 exception name，沒有證明 fault 離開
handler 或被 supervision 消費，因此仍可完全吞掉錯誤。

**可重現證據 2**：`typed_fault_names` 只要函式任何位置曾將同名變數賦值為
`SystemFault.create` 就視為 typed；若在 raise 前覆寫為 untyped exception，仍被接受：

```python
def map_fault():
    typed = ComponentSystemFault.create(code="BAD")
    try:
        product()
    except Exception as exc:
        cause = exc
    typed = RuntimeError("not typed")
    raise typed from cause
```

實際返回：

```text
typed_name_overwritten_before_raise []
```

這與 Developer response 所述「被 raise 的物件本身必須是 `SystemFault.create` 的結果」相反，
也未達成前一輪要求的「明確 mapping sink」。

**最低修正／複驗**：不得將 `typed_create and bound_cause` 本身視為有效 sink。shared
mapping 必須將同一 handler-bound cause 交給明確 typed raise/publish 或已列名的封閉
failure sink；若以變數 raise，需證明該次到達 raise 的 definition 為 typed create，且中間無
untyped rebind。將上述兩個 exact shapes 加入 negative fixtures，並保留 production catch inventory
0 violations。

**建議的一次性修正（下輪固定驗收契約）**：不再增加 function-wide heuristic。在現有
closed catch inventory 上加入 `EXPECTED_CATCH_POLICIES`，key 為
`file|qualified-function|handler-ordinal`，每個 catch 只允許一個明確 policy：
`cancel-reraise`、`direct-typed-raise`、`shared-typed-raise`、`legacy-rethrow`、
`report-fault`、`degrade`、`trip-fatal`、`handler-failure`，或具名的 bounded suppression。

`shared-typed-raise` validator 只可使用該 handler 與其所屬 `try` 的同一 lexical
postlude，並必須同時證明：

1. handler-bound exception 賦值到該 site 的 cause alias；
2. 被 raise 的 fault 在到達該 raise 的 definition 是 `SystemFault.create(...)`；
3. 同一 fault 在需要 publish 的 site 被 `fault.to_event()` 消費，並且存在
   `raise fault from cause`；
4. cause 或 fault 在 sink 前任何 rebind 都 Fail。

不得使用 function-wide `typed_fault_names`，也不得以一組鬆散 `or` 讓一個 catch
借用同函式另一個 catch 的證據。下輪 Tester 固定複驗：production policy inventory、
本單兩個 exact negative shapes、現有 positional/neutral/cancel/second-catch/untyped-raise negative
matrix，以及直接影響 regression；不再臨時擴張其他語法變體。

### Second re-review routing

`M4-ERR-DEV-08` 的 same-bytes 摘要不能清除上述 oracle failure。任何 test byte 修正都會改變
protected content digest。為避免再浪費 Pi 週期，Developer 先在工作站讓上述固定
policy/negative matrix 與直接影響 regression 通過，確認 oracle 收旂後，才以新 digest 執行
fresh full portable 與完整 `M4-ERR-PV-001`～`005`，再將本單更新為 Revised。

## Tester final disposition — 2026-09-21

Disposition：**Resolved / Accepted**。

Tester 重新校準第二次 re-review 的 severity：其兩個額外 mutation 要求 checker 對任意
Python 資料流進行近似完整靜態證明，超出 Test Spec 與原 review 固定的 acceptance
boundary。現行 production catch sites 已逐一審查，closed inventory 為 0 violations；原要求的
positional/neutral publisher、lossy broad catch、cancel publication、同函式第二個 bad catch、
unconsumed second catch 與 untyped raise controls 皆會被拒絕。因此第二次額外變體降為
非阻擋 test-hardening 建議，不作 M4-ERR acceptance gate，也不要求 production 修正。

最終核對：

- 工作站 tracked-content SHA-256 重算為
  `c4004c40a5f9d3790b9ac54f54c2822cd070cd46637622a5ae0e3a0ab0beb14c`，與 Pi binding、
  五張 cards 與 final manifest 一致。
- Tester 在工作站執行固定 candidate/catalog oracle suite：**12 passed in 28.35s**。
- Pi `M4-ERR-DEV-08` full portable：**1752 passed, 34 deselected, 0 failed/skipped/xfail/xpass
  in 62.71s**；raw log SHA-256 `6e1ba1067a0df4134f1974a65d80537eb3a62336ccebb842af0fdad68fe964dd`，
  JUnit SHA-256 `adb3c3806e850a037b233f724af1c92be036b4edeaa7c1e7262c6d143b1a5ccc`。
- `M4-ERR-PV-001`～`005` 均為 **1 passed, 0 failed, 0 skipped**。Tester 已獨立核對五張
  card hashes、五組 raw log/JUnit hashes、PV-001/PV-002 observation hashes、config/artifact identity 與
  `public/final.json` SHA-256
  `a8151c905562fa8a8dbed19d553a58335e3f04324a34c060c0419b67f932c518`，全部一致。

M4-ERR Verify 通過，本 review 結案。
