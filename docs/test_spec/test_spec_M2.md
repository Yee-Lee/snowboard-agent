# test_spec_M2.md ── M2 Mock 對話垂直切片

本文件為 `docs/test_spec.md`（總論）的子檔。Test ID 格式、判定規則、平台代碼、共用 fixture 與證據代碼定義於總論；本文件只列 M2 範圍的測項與驗收命令。

---

## 1. M2 範圍說明

- 覆蓋 `milestones/M2.md` 的 M2「Mock 對話垂直切片」。
- 均以 Python 3.11 以上的開發機環境驗收；不得要求 Raspberry Pi 5、網路、credential、模型檔或 Pi-only library。
- **M2 的 Pass 以前序 M1 全部 regression 仍通過為必要條件。**
- milestone entrypoint：`tests/milestones/test_m2_mock_pipeline.py`。M2 驗收同時重跑 M1 entrypoint 與完整 regression。

---

## 2. M2 需求──測試對照

### 2.1 Mock / null HAL 與 worker

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M2-HAL-001** | Ch 2a §2a.1；`milestones/M2.md` §4.1、§4.3–§4.4 | factory top-level import Pi-only 套件，使 mock config 無法啟動 | `FX-MOCK-HAL` 選 mock/null 並監看 imports | factory 只 lazy import 所選 backend；不需要/載入 `sounddevice`、`picamera2`、`gpiod` 或 native display lib | `DEV-PY311` / `EV-AUTO` / M2 startup |
| **M2-HAL-002** | Ch 2a §2a.1–§2a.4；`arch.md` §5.2 | null 回傳非法格式，或 audio iterator 未釋放造成後續 listen 失敗 | 啟停各 null；依多種合法 config 呼叫工作方法；第一個 frames 未關時嘗試第二個，關閉後重開 | lifecycle no-op 且 stop 冪等；audio frame 大小/格式正確、output 完整消費；同 process 第二個 active iterator 被拒、`aclose()` 後可重開且無 task；display no-op 且 size (0,0)；camera RGB/YUV 長度合法、JPEG 可 decode | `DEV-PY311` / `EV-AUTO`、`EV-RACE` / worker P5、Listen cancel |
| **M2-HAL-004** | Ch 2a §2a.3–§2a.5 | mock 行為與 Protocol 偏離，GPIO 多 owner 或 display 破 buffer | display 合法/非法 buffer；camera fixture；GPIO register/debounce/unregister/output | display 僅 show flush 且長度拒絕；camera 固定產指定格式/尺寸；GPIO 一 pin 一 subscriber、debounce、callback 隔離、unregister 冪等、output 需 configure | `DEV-PY311` / `EV-AUTO`、`EV-RACE` / M3 合約前置 |
| **M2-WRK-001** | Ch 2b §1、§5；Ch 1 §1.8；Ch 2 §2.3–§2.4、§2.8 | operation 重入、Fact cardinality 或 cleanup 錯誤 | `FX-MOCK-WORKER` 對每個 worker 觸發 normal、P5、exception、cancel 與純 async force-abort | 同 instance active call 不可重入；normal/P5 恰一 terminal Fact、exception 恰一 Error 且逸出、cancel 無 normal Fact；Fact 只在資源釋放後 publish；force-abort 回空 report 且 outer task done，無 task 殘留 | `DEV-PY311` / `EV-RACE` / 所有 flows |
| **M2-WRK-002** | Ch 2b §2；Ch 7 §6–§7 | perception status/text/extra、timeout cleanup 或 read 順序錯誤 | 固定 ASR/message/image，另觸發空白、timeout、adapter error | Listen/Read/Look 成功回正確 kind/text/IDs；空白/無資料/可翻譯失敗依契約回 timeout/error；timeout 先完成合作式 cleanup；Read 按 arrival order 且最多消費一次 | `DEV-PY311` / `EV-RACE` / flows、message |
| **M2-WRK-003** | Ch 2b §3；Ch 9；`arch.md` §2.7 | prompt 洩漏 payload/隱藏 history，LLM 壞輸出使 session 崩 | perception 完成順序互換、pending IDs、capability 組合、LLM timeout/reject/bad JSON | Prompt 固定 listen/read/look 排序並保留 status；pending 只 count/opaque ID；每次 reason 無隱藏 history；clean failure 產 speak apology 或 rest fallback；只選可用 capability；raw output 不進 event/log | `DEV-PY311` / `EV-AUTO`、`EV-LOG` / flows |
| **M2-WRK-004** | Ch 2b §4；Ch 9 | TTS/tool/rest ownership 錯誤，handler 重複或 Rest 越權收尾 session | 固定 TTS PCM、fake tool、empty rest；成功/可翻譯失敗/cancel | Speak 完整播放後 Fact；Tool 只在 dispatch 執行 handler 一次且派發完成即 Fact；Rest 只回 Fact、不呼叫 SM/flush/釋放他人；可翻譯失敗回 `ActionCompleted(error)`；cancel 不留 task | `DEV-PY311` / `EV-RACE` / flows；native destructive cleanup 留 M4/M5 |

### 2.2 Action payload 與 external message

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M2-PAY-001** | Ch 9 §2–§4、§6–§7、§11 tests 1–7、11–12 | 非 JSON/額外欄位/secret 進 action，Reasoner 與 SM 驗證分岔 | speak/tool/rest 正反例、深層/NaN/bytes/custom 輸入；同 payload 給 Reasoner 與 SM | speak 唯一非空 text；tool exact envelope+dotted name+object args；rest 只 empty dict；非法 JSON 值拒絕且不 mutation；兩端結果一致；錯誤不含 payload/secret | `DEV-PY311` / `EV-AUTO`、`EV-LOG` / SM |
| **M2-PAY-002** | Ch 9 §5；§11 tests 4–5、8–10；Ch 2b §4.2 | registry 在 runtime 漂移、schema 洩漏 handler 或 validate 誤執行 | register duplicate、seal；schemas defensive mutation；validate/dispatch recorder | duplicate/seal 後 register 拒絕；schemas 按 name 排序且無 handler/control，caller 修改不污染；validate 同步且不 dispatch；unknown 在 handler 前拒絕 | `DEV-PY311` / `EV-AUTO` / Reasoner、Tool |
| **M2-MSG-001** | Ch 7 §2–§5；§11 tests 1–5、9–10、15 | payload 進 Bus/log、ID 先發後存、arrival 順序破壞 | 合法/空/非 JSON metadata、多 message ingest，記錄 store 與 publish | 合法訊息先存再 publish；UUIDv4 且 arrival order 跨狀態保持；非法在存前拒絕；rejected/drop-newest 不分 ID/Signal；pending 只曝 metadata；log 無 message text | `DEV-PY311` / `EV-AUTO`、`EV-LOG` / external flow |
| **M2-MSG-002** | Ch 7 §6–§7；§11 tests 4–7、16–20 | read window 非原子、cancel/timeout/notify race 遺失訊息或重複消費 | begin/assign/consume/close；consumer return 同時 ingest；lock 順序兩排列；三個 cancel 時點；notify-before-wait | begin 只移指定 session；consume 同 lock 刪除並 close；item 最多一次；window 先於 consumer ACTIVE；return 後新 message 留 pending；兩種 lock 順序皆不遺失；timeout/cancel 還原殘留且 close 冪等；predicate 不漏 notify | `DEV-PY311` / `EV-RACE` / Read、external flow、Interrupt/Shutdown |
| **M2-MSG-004** | Ch 7 §5；§11 tests 8–9 | overflow 淘汰 turn-owned 資料或誤發 Signal | buffer 滿時套 drop-oldest/drop-newest/reject，含全 turn-owned | drop-oldest 不淘汰 turn-owned，全 turn-owned 退化 drop-newest；drop-newest/reject 不分 ID、不 publish | `DEV-PY311` / `EV-AUTO` / M5 前置 |
| **M2-MSG-005** | Ch 7 §8–§9；§11 tests 11–14 | flush/discard 死鎖、重發新 ID、stop 留下 waiter | flush 期間並行 ingest、discard、stop/repeated stop | flush 重設 ownership 後於 lock 外按 arrival 重發原 ID 且不死鎖；discard 清空並喚醒 waiter 且冪等；stop 後 ingest 拒絕、所有 waiter 收斂、重複 stop no-op | `DEV-PY311` / `EV-RACE` / rest/error/shutdown |

### 2.3 Mock session 與共同完成條件

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M2-FLOW-001** | `arch.md` §4；`milestones/M2.md` §4.1、§4.4 | 本機 wake 主線無法完成多 turn 並正常 rest | `FX-MOCK-APP` 發 Button 或 WakeWord；LLM 先 speak+listen 再 rest | 依序觀察 IDLE→WAKE→PERCEPTION→THINK→ACTION；第二 turn 同旁；rest 完成且 in-flight 空後回 IDLE；IDs/Fact cardinality 正確 | `DEV-PY311` / `EV-RACE` / M2 entrypoint |
| **M2-FLOW-002** | `arch.md` §4.4、§5.1；`milestones/M2.md` §4.1、§4.4 | external 訊息 payload ownership 或 first-turn mapping 錯誤 | ingest 合法 message 後讓 reasoner 選 action 再 rest | first turn 只 read；payload 只由 buffer→Read；狀態主線正確；consume 一次；rest 完成後回 IDLE | `DEV-PY311` / `EV-RACE`、`EV-LOG` / M2 entrypoint |
| **M2-FLOW-003** | Ch 4 §6.4；Ch 9 §8；`milestones/M2.md` §4.2、§4.4 | duplicate 啟動同 kind 兩次或 rest 錯誤驗證無關欄位 | speak/tool 回 duplicate registered kinds；rest 帶 empty/unknown/duplicate | speak/tool 保留首次順序去重且每 kind 只起一 task、不進 ERROR；rest 三種輸入都忽略 next 清單並執行 rest | `DEV-PY311` / `EV-RACE` / M2 entrypoint |
| **M2-FLOW-004** | `arch.md` P5、§4.8、§6.6；Ch 2b §5 | 可翻譯失敗中斷 session，或 action error 仍沿用危險 next 清單 | 各 perception、LLM、action deterministic P5 失敗 | perception timeout/error 送 Reasoner；clean LLM failure 產 fallback；speak/tool error 繞 turn 且改用 default_perceptions；每 operation 只有一 terminal Fact | `DEV-PY311` / `EV-RACE` / M2 entrypoint |
| **M2-FLOW-005** | `arch.md` §3.2、§6.6；Ch 4 §8；Ch 11 §13 | worker exception 與 SM self-check 被混為同一路徑 | worker 不可翻譯 exception；invalid LLM schema/payload | worker 路徑先 `ErrorOccurred` 再 `StateChanged`→ERROR；SM self-check 無前置 Error、直接 `StateChanged`→ERROR；兩者完成 error convergence 回 IDLE 且不 exit 4 | `DEV-PY311` / `EV-RACE`、`EV-LOG` / M2 entrypoint |
| **M2-FLOW-006** | Ch 4 §7、§7.5、§9 test 17a；Ch 7 §8；`milestones/M2.md` §4.4 | completion notice 前提早回 IDLE，或正常 / 異常收斂套錯 buffer 政策 | active operation 與 pending message 下分別觸發 rest/error/interrupt/shutdown；Converger return 後暫停 notice | notice 前維持 pending、拒絕新 wake；in-flight 空後才清 session 且無 task；rest 先回 IDLE 再以原 ID flush-to-wake；error/interrupt/shutdown discard 並關 read window/waiter | `DEV-PY311` / `EV-RACE` / M2 entrypoint |
| **M2-FLOW-008** | `milestones/M2.md` §4.1、§4.4 | 自動化組件可過但 repository default app 無法啟停 | default mock config 執行 `python -m sbd.main`，進 IDLE 後送 Ctrl+C/SIGINT | 不需 Pi 套件、網路、模型或 credential；sanitized log 顯示 IDLE；shutdown 拒新 wake、無 handle/task、exit 0 | `DEV-PROC` / `EV-PROC`、`EV-LOG` / release smoke |
| **M2-REG-001** | `milestones/M2.md` §1.4、§4.4 | M2 修改破壞 M1，或靠 skip/xfail 取得綠燈 | 依序執行 M1 entrypoint、M2 entrypoint、完整 suite | 三者全通過；先前 M1 驗收未刪除/skip/xfail；無 Pi-only import/IO；race 無 sleep 同步；log hygiene 仍成立 | `DEV-PY311` / `EV-AUTO` / test collection diff / M2 共同 gate |

---

## 3. 驗收命令

```bash
python -m pytest -v tests/milestones/test_m1_foundation.py
python -m pytest -v tests/milestones/test_m2_mock_pipeline.py
python -m pytest -v
python -m sbd.main
```

`python -m sbd.main` 是人工 smoke 的補充證據，不取代自動化 session、shutdown 與 exit-code 驗收。四條命令均須通過，且不得刪除、skip 或 xfail 先前 M1 驗收。
