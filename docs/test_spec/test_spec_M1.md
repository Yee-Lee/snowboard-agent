# test_spec_M1.md ── M1 純軟體核心

本文件為 `docs/test_spec.md`（總論）的子檔。Test ID 格式、判定規則、平台代碼、共用 fixture 與證據代碼定義於總論；本文件只列 M1 範圍的測項與驗收命令。

---

## 1. M1 範圍說明

- 覆蓋 `milestone.md` 的 M1「純軟體核心」。
- 均以 Python 3.11 以上的開發機環境驗收；不得要求 Raspberry Pi 5、網路、credential、模型檔或 Pi-only library。
- M1 驗證 Ch 4 / Ch 11 作為 consumer 的行為時，Ch 7 `ExternalMessageControl` 與 Ch 9 `ActionPayloadValidator` 只使用 injected fake / test double；不得因此提前實作 Ch 7 / Ch 9 concrete module 或 action schema。兩者的 concrete 契約與 schema 驗收屬 M2。
- milestone entrypoint：`tests/milestones/test_m1_foundation.py`。聚焦測試可分散於其他檔案，但該 entrypoint 必須能重現本節所有 M1 行為。

---

## 2. M1 需求──測試對照

### 2.1 事件與跨層契約

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M1-EVT-001** | `arch.md` §3.2–§3.3；Ch 1 §1.2–§1.8；`milestone` §3.4 | schema / 事件族群錯誤使 guard / exact-type dispatch 失真，或 subscriber 污染共享事實 | 以每一 concrete event 正反例建構分類；`FX-EVENT` 經兩個依序 subscriber 派送 | frozen + slots、欄位、容器、State/status、family union 與無內部 version 均符合契約；下游收到同一 object 且 nested sentinel 未變；衍生資料使用新物件 | `DEV-PY311` / `EV-AUTO`、`EV-REVIEW` / 所有 Bus、SM 測試 |
| **M1-EVT-002** | Ch 1 §1.1、§1.8 | session、turn、operation 或訊息互相串線 | 連續建立多個 session/message；同一 SM 建立多 turn/correlation；另建新 SM | session/message 為合法 UUIDv4；turn 首值 1 且 session 內遞增；correlation 於單一 SM instance 從 1 單調遞增，新 instance 隔離 | `DEV-PY311` / `EV-AUTO` / SM、message regression |
| **M1-CON-001** | Ch 2 §2.1–§2.8 | 公開 lifecycle / 控制值不完整，使 RM、SM 與 M2 worker 無法依同一契約裝配 | 以最小 conforming fake 對 `InputSource`、`Perception`、`Action`、`Adaptor`、Reasoner 做公開介面 smoke | 各類公開方法與 in-flight 邊界可由 SM/RM fake 裝配；只有 in-flight worker 有 abort/force-abort；工作方法回 `None`；`ForceAbortReport` 為 frozen 控制值且不進 Bus | `DEV-PY311` / `EV-AUTO` / RM、Cancel、M2 worker |

### 2.2 Event Bus

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M1-BUS-001** | Ch 3 §2–§4、§8 tests 1–7 | 錯誤型別、非決定順序或訂閱生命週期錯誤造成漏送 / 重送 | `FX-BUS` 訂閱同型、不同型與 subclass；token 解除、重複操作；handler 內 subscribe/unsubscribe；無 subscriber publish | exact concrete type 才收到；同型 handlers 依註冊順序各收同一 object 一次；token 精確解除且冪等、重複訂閱拒絕；本次派送用 snapshot、修改自下一次生效；無 subscriber 只 WARNING | `DEV-PY311` / `EV-AUTO`、`EV-LOG` / 所有 event-driven 測試 |
| **M1-BUS-003** | Ch 3 §5.1、§8 tests 8–10 | 一個 observer 失敗阻斷主流程，或 fallback 次序錯誤 | 多個一般 handler 依序成功 / raise | 原事件其餘 handler 繼續；每個失敗按發生順序產一個欄位正確的 `ErrorOccurred`；fallback 不跨來源去重 | `DEV-PY311` / `EV-RACE` / SM ERROR、logging |
| **M1-BUS-004** | Ch 3 §4.4、§5.2–§5.3、§8 tests 11–16 | `ErrorOccurred` handler 再失敗造成遞迴或 runtime 無法收斂 | handler raise `CancelledError`；Error handler raise；fatal 前後等待 `wait_fatal()`；fatal 後再 publish | cancellation 原樣傳出且無 fallback；Error 派送失敗不遞迴且停止剩餘 handlers；publish 與所有 waiter 取得同一 `FatalDispatchError` root/cause；fatal latch 後拒絕派送 | `DEV-PY311` / `EV-RACE`、`EV-PROC` / fatal supervision |

### 2.3 State Manager

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M1-SM-001** | `arch.md` §3.5–§3.6；Ch 4 §3、§5、§9 tests 1–3 | callback 重入或並行 transition 破壞唯一狀態 owner | 啟停 SM；多 producer 同時 publish | 精確訂閱 / 解除九種 public event；callback 只 enqueue；dispatch transition 不交錯 | `DEV-PY311` / `EV-RACE` / 所有 session |
| **M1-SM-002** | `arch.md` §6.3；Ch 4 §4、§6.3、§9 tests 4–7 | Fact 先到即提前啟動下一 phase、資源尚未釋放 | `FX-BARRIER-WORKER` 排列 Fact 與 task done；兩個 perception 交錯完成 | 單一或多 worker 都須每個 terminal Fact + 對應 task done 才前進；Fact fallback Error 排在 completion notice 前時進 ERROR，未啟動下一 action | `DEV-PY311` / `EV-RACE` / M2 flows |
| **M1-SM-003** | `arch.md` §3.6；Ch 4 §5、§8、§9 tests 8–9 | stale/duplicate Fact 或無 Fact return 污染新 turn，bookkeeping 壞掉卻靜默 | 注入錯 session/turn/correlation、duplicate、正常 return 無 Fact | stale / duplicate 只 WARNING/drop 且狀態不變；非 cancel 的無 Fact completion 觸發真正 fatal invariant（`StateManagerInvariantViolation`），不偽裝為 ERROR | `DEV-PY311` / `EV-RACE`、`EV-LOG` / logging fatal |
| **M1-SM-004** | `arch.md` §4.3–§4.5；Ch 4 §6.2、§9 tests 11–13 | wake source 映射錯誤、舊 timer 污染新 session | 三種 wake；timer 到期前 Interrupt/Error/Shutdown；action error 與其他 status | 首 turn 分別為 button/wake→listen、external→read；提前離開會取消 timer 且舊 notice 無效；只有 speak/tool action error 改用 defaults | `DEV-PY311` / `EV-RACE` / M2 flows |
| **M1-SM-005** | `arch.md` §2.7、§3.2、§4.6；Ch 4 §6.4、§8、§9 tests 10–10b；Ch 9 §7–§8 port 契約 | reasoner 壞輸出導致錯誤 action，或資料噪音被錯誤升級 fatal | 注入 `FX-M1-PORTS` validator accept/reject；另給 invalid kind、unknown/duplicate/empty `next_perceptions`、rest 任意清單 | test double 拒絕或 speak/tool 正規化後空→非 fatal SM ERROR 且不發布 `ErrorOccurred`；unknown 移除；duplicate 保留首次順序去重且只起一 worker；rest 忽略該欄位；不驗 Ch 9 concrete schema | `DEV-PY311` / `EV-RACE`、`EV-LOG` / M2 `M2-PAY-001` 補 concrete schema |
| **M1-SM-006** | `arch.md` §4.6–§4.8、§5.1、§6.5；Ch 4 §7、§9 tests 14–19；Ch 7 control port 契約 | 收斂 return 被誤認 in-flight 已空，過早回 IDLE / flush / 接受 wake | 注入 `FX-M1-PORTS` external control call recorder；觸發 rest normal/destructive、Interrupt、Error、Shutdown 並 delay completion/recovery | 所有路徑先等 in-flight empty；rest 回 IDLE 後才呼叫 fake flush；error/interrupt/shutdown 呼叫 fake discard；destructive rest 另等 recovery；shutdown 清空 handles；不驗 Ch 7 store/window concrete 行為 | `DEV-PY311` / `EV-RACE` / M2 `M2-MSG-*` 補 concrete buffer |

### 2.4 Resource Manager 與 Cancel

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M1-RM-001** | Ch 5 §3–§4.1、§9 tests 1–4 | 非法 graph 已碰資源才失敗，造成副作用或依賴未 READY | `FX-RM-GRAPH` 建立 duplicate/self/missing/later-phase/cycle/undeclared graph | 全部在任何 factory 前拒絕；registry preflight 後不可變；resolver 拒 undeclared，consumer 不能取得未 READY dependency | `DEV-PY311` / `EV-AUTO`、`call log` / 所有 bootstrap |
| **M1-RM-002** | Ch 5 §3.5、§4.2、§9 tests 5、23–24 | producer 在 Bus/SM supervision 或 late-fill 前啟動，遺失 fatal/Signal | production-like phase+DAG；以 `FX-M1-PORTS` external control 與 fake wake control 做 late-fill | start order 穩定；fatal supervision 先武裝；SM constructor 只含 A 類依賴；fake B 類 port 在 resource READY 後、receiver arm 前 one-shot setter；無 closure 繞過 resolver，且不建立 Ch 7 concrete module | `DEV-PY311` / `EV-RACE`、`call log` / M2 startup |
| **M1-RM-003** | `arch.md` §6.8；Ch 5 §4.3–§4.6、§9 tests 6–12、25–26 | real/null、required/optional 或固定 wake mapping 錯誤，系統宣稱不存在的能力 | core/worker/input/adaptor start failure 與 read/source/default 組合 | audio/display/camera real failure stop real→start null→capability false；GPIO 無 Null；required fatal、optional 停用；observer/adaptor 不阻主流程；coherence gate 正確停用 optional source 或拒 required 組合 | `DEV-PY311` / `EV-AUTO`、`call log` / M2 mock graph |
| **M1-RM-004** | Ch 5 §3.4、§5；Ch 5 §9 tests 10、13–15、26 | catalog/capability 在 startup 前後可任意改，Reasoner 越權查底層 | seal/freeze 前後 lookup/register/query；null-backed worker；reasoner closure | catalog seal 前不可 runtime lookup、後不可 register；capability freeze 前不可查、unknown KeyError、後不可變；P1/P2 正確；Reasoner 只能查 perception/action kind | `DEV-PY311` / `EV-AUTO` / SM、Reasoner |
| **M1-RM-005** | `arch.md` §6.5、§6.8；Ch 5 §6；§9 tests 16–20 | recovery barrier 過早打開或改動 static capability，接受未 READY session | duplicate destroyed keys、hook READY/fail/timeout、第二批、shutdown during recovery | keys 去重且依 dependency order；所有 hook READY 才 set barrier；capability 不變；fail/timeout/unknown/reentry 為 fatal；shutdown 清理局部 replacement | `DEV-PY311` / `EV-RACE`、`call log` / SM ERROR exit |
| **M1-RM-006** | Ch 5 §4.6、§7；§9 tests 21–22 | rollback/stop 一處失敗阻止其他資源釋放 | 中途 startup failure、stop failure、重複 stop_all | rollback 與 normal stop 都依 reverse started order；單一 failure 不阻後續；stop_all 冪等並回完整 failure report | `DEV-PY311` / `EV-AUTO`、`call log` / shutdown |
| **M1-CAN-001** | `arch.md` §6.4–§6.5；Ch 6 §3–§5；§11 tests 1–7 | 多 worker 被串行中止或不相干 worker 被錯升級 | 空、duplicate、多 target；不同 per-kind timeout；部分 abort return/raise/hang | 空立即成功；duplicate 在呼叫 worker 前拒絕；所有 L1 同時開始；各自 timeout；outer 未 done 不算成功；只有失敗 target 升級 | `DEV-PY311` / `EV-RACE` / SM convergence |
| **M1-CAN-002** | Ch 6 §6、§9；§11 tests 8–10 | outer `task.cancel()` 冒充 native cleanup，留下 orphan | L1 timeout 後讓 force_abort return/raise/hang，或 outer task 繼續 pending | L2 只呼叫 force_abort 且 outer `cancelled()` 為 false；force_abort 或 outer done 任一逾時/raise 使整批 `ConvergenceFatalError`，不回部分成功 | `DEV-PY311` / `EV-RACE`、`EV-PROC` / runtime fatal |
| **M1-CAN-003** | Ch 6 §7–§8；§10–§11 tests 11–15 | report 不穩定、不同 trigger 有不同 L2 policy、重入破壞全域收斂 | 多 report、四 trigger、reentry；orchestration cancel；worker 已發布 Error | destroyed keys 去重且穩定排序；相同 worker 行為得到相同 result；reentry fatal 且 finally 後可重用；`CancelledError` 原樣傳出；Converger 不補第二個 Error | `DEV-PY311` / `EV-RACE`、`EV-LOG` / RM recovery、SM |

### 2.5 Config、logging 與 bootstrap

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M1-CFG-001** | `arch.md` §7.1；Ch 10 §3–§12、§15 tests 1–4、16–17 | precedence 或 global state 造成不可重現設定 | `FX-CONFIG` 無 override、leaf YAML、`.env`、process env；重複 load/mutation | defaults 完整；只覆寫指定 leaf；process env > `.env` > YAML > default；example 不自動讀；結果 immutable 且重複 load 無 global state | `DEV-PY311` / `EV-AUTO` / 所有 startup |
| **M1-CFG-002** | Ch 10 §5–§14、§15 tests 5–12、18 | typo、型別、null、namespace、backend 或 cross-field 錯誤延後到 runtime | table-driven unknown/mismatch/null/required/timeout/kind/stable ResourceKey/real-vs-mock/audio/TTS/GPIO/nested alias | 每個非法設定在 load 時以含 path 的明確 error 拒絕；timeout 拒非有限正值；resource/cancel namespace 不混用；只有完整 stable key 生效；mock 不要求 real 路徑；Audio/TTS 與 GPIO cross-field 一致；nested adapter 只接受正式路徑 | `DEV-PY311` / `EV-AUTO` / bootstrap exit 2、RM graph、M2 mock |
| **M1-CFG-004** | Ch 10 §9、§12、§15 tests 13–15 | secret 透過 repr/log 洩漏，或 `.env` 執行 shell | secret sentinel；malformed `.env`；shell 字樣、unknown/unrelated env | SecretValue 的 str/repr/dataclass repr 不含原值；不做 shell expansion；malformed 與 unknown `SBD_` 拒絕，無關 env 忽略 | `DEV-PY311` / `EV-LOG` / 所有 logging |
| **M1-CFG-005** | Ch 10 §13、§15 tests 19；`milestone` §3.4 | example 與 production loader 漂移，使用者範例無法啟動 | 用 production `load_config(local_path=example)` 載入完整 example | strict merge、decode、field 與 cross-field validation 全通過；adapter 值位於正式 nested paths | `DEV-PY311` / `EV-AUTO` / 每次 config schema 變更 |
| **M1-LOG-001** | Ch 11 §3–§5、§12、§14 tests 1–3、15 | handler 重複、格式不可 parse 或 logging 本身 raise | 重複 configure；text/json；不可 serialize extra；rotation 選項 | sbd 恰一 handler；共同 context 完整；每筆 JSON 單行可 parse；bad extra 不 raise；依 config 選到正確 rotation handler | `DEV-PY311` / `EV-LOG` / 全套；child logger ownership 留 M4 |
| **M1-LOG-002** | Ch 11 §6–§8、§14 tests 4–7 | Error 重複、P5 誤記 ERROR 或 observer 太晚 READY | exact/subclass event；producer 前後；P5 timeout/error；dynamic where | observer 先於 producer READY 且 exact-type；每個 Error 恰一筆 ERROR 無重複 traceback；P5 只 WARNING；where 合法且動態 handler 名已 sanitize | `DEV-PY311` / `EV-LOG` / Bus、workers |
| **M1-LOG-003** | Ch 11 §9、§14 tests 8–9 | credential、payload、prompt 或使用者文字進 log | 各類敏感 sentinel 與含 newline 長字串經所有主要 log path | sentinel 完全不存在；user/library 字串截斷且 newline escape；diagnostic 仍足以定位 kind/where/ID | `DEV-PY311` / `EV-LOG` / M2 全套 |
| **M1-LOG-004** | Ch 11 §10、§13–§14 tests 10–11、17–18 | 多 fatal 重複終止、SM 契約違反被錯當 process fatal 或反之 | Bus/SM fatal 競速；`FX-M1-PORTS` validator 拒絕；人工破壞 bookkeeping | supervisor 只選第一 root 寫一次 CRITICAL traceback；runtime fatal 不再 publish Error / 走 SM recovery；fake validator 拒絕只產一筆無 payload/traceback 的 SM ERROR 且不 exit 4；真正 `StateManagerInvariantViolation` 則 exit 4；不驗 Ch 9 schema | `DEV-PY311` / `EV-RACE`、`EV-PROC`、`EV-LOG` / SM |
| **M1-BOOT-001** | Ch 11 §10–§11、§14 tests 12–16；`milestone` §3.4 | 啟動/執行錯誤回錯 exit code、shutdown 被 cleanup failure 遮蔽 | `DEV-PROC` 分別觸發 config/startup/runtime fatal/normal shutdown；`POSIX-PROC` 驗證 SIGINT/SIGTERM 訊號退出 | exit 依 2/3/4/0；rollback failure 不遮原 StartupError；shutdown 逐項記錄仍完成；Windows deselect POSIX-PROC 節點 | `DEV-PROC` & `POSIX-PROC` / `EV-PROC`、`EV-LOG` / CLI |
| **M1-REG-001** | `milestone` §1.4、§3.1、§3.3–§3.4 | 開發機意外載入 Pi/M2 實作、連網或靠 skip 取得綠燈 | fresh `DEV-PY311` 執行 M1 entrypoint 與 full suite；檢查 markers / imports / network / injected ports | `rpi` marker 已註冊；M1 不 import/call Pi-only dependency、網路/硬體，也不 import/instantiate Ch 7 external-message 或 Ch 9 payload-validator concrete module；無刪除、skip、xfail；兩命令全通過 | `DEV-PY311` / `EV-AUTO` / dependency/import recorder / M1 共同 gate |

---

## 3. 驗收命令

```bash
python -m pytest -v tests/milestones/test_m1_foundation.py
python -m pytest -v
```

兩條命令均須全數通過，且不得刪除、skip 或 xfail 任何 Test ID 對應的測試。
