---
requestor: "Reviewer"
owner: "Designer"
status: "Resolved"
---

# IR_review_M4B_I — M4b LLM Production Design Review

**審查範圍**：依 `ch_m4b_llm_production.md` §13 列出的 Combined Reviewer delivery 完整輸入。

**審查基準**：`docs/arch.md` 為架構對齊權威；`docs/protocol.md` §4/§6、`docs/model_spec.md` §6
為 selected winner identity 與 wire contract 權威；Ch 2/2b/4/5/6/9/10 為跨章設計一致性基準。

**審查日期**：2026-08-30

---

## 審查結論

**Blocking findings：0**

設計文件已通過全部十項 §13 Reviewer 核對清單。無遺漏、無矛盾、無與架構或跨章契約無法對齊之
核心問題。本審查單直接標記 `Resolved`，M4b 設計可依 §0.2 flow 交 Tester 建立
`TR_spec_M4B_I`。

---

## 核對清單逐項結論

### 1. Protocol/fake 與 real adapter/worker/lock ownership

**結論：通過。**

- `llm_child_protocol.py` 為 pure codec，只含 encode/parse 與 dataclass，不 import native runtime。
- `litert_lm/adapter.py` 是 parent-side owner，持有 process group、IPC、request counter、recovery ticket。
- `litert_lm/worker.py` 是唯一 native runtime import 點。
- `tests/fakes/m4b_llm_child.py` 是 deterministic structured-wire child double，不宣告 product quality PASS。
- Factory seam `make_llm_adapter()` 以三個窄介面 `ScheduleRecovery | None`、`WaitRecovery | None`、
  `LLMResourceSampler | None` 分歧 real/mock，real 要求三者皆非 None 且先讀 tracked lock。
- Production identity 只來自 `DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001` 與
  `model_spec.md` §6，沒有第二來源。

### 2. Structured protocol exact keys / canonical projection / POC-path exclusion / token-metric bounds / state / typed terminal

**結論：通過。**

- §3.1 的 `LLMReadyIdentity`、`LLMWireResult`、`LLMWireError`、`LLMWireCancelled` 與
  `protocol.md` §4.4 exact wire schema 一一對齊，欄位名與型別皆吻合。
- Canonical projection 規則（perception order、pending count 為 int、tools 依 name 排序、rest 必須存在）
  與 Ch 2b §3.1 `PromptBuilder` 及 `protocol.md` §4.4 一致。
- POC absolute path（`/tmp/llm-poc-*`）明確標示為 provenance-only（§7），Core 只取 `LLMConfig` path
  並以 digest 與 artifact lock 驗證。
- Token bounds：prefill 1..128、decode 1..128、kv 1..1024，與 `protocol.md` §4.2 和 §4.4 完全相符。
- Parent state machine（§4）六狀態 + DESTROYED，轉移表與 `protocol.md` §5 state/terminal rules 無矛盾。
- Typed terminal 為 `LLMWireResult | LLMWireError | LLMWireCancelled`，每個 request 恰一個，
  與 `protocol.md` §5「每個 request 恰允許一個 terminal」一致。

### 3. Codec 可重用 common helpers 但不要求改寫 Accepted M4A transport

**結論：通過。**

- §3 明確指出 `framed_child.py` 可重用 bounded line reader 與 process-group termination primitive，
  但 LLM state machine、request/terminal mapping、output validation 只留在 LLM module。
- LLM wire 使用 `protocol_version="snowboard.llm/1"` 而非 Audio 的 `protocol: 1`，二者共存不衝突。
- §10.1 item 10 要求 M4A protocol/lifecycle regressions 保持通過。

### 4. Prompt/output privacy 在 success 與每個 failure cleanup 路徑都封閉

**結論：通過。**

- §2 明確禁止 prompt 與 model output 寫入 log、result、evidence、exception message 或 stderr。
- §3.1 codec 錯誤只含 stage/field/reason，不含 perception text、response、tool arguments、
  credential 或 path。
- §6 item 6 重申所有路徑的隱私邊界，允許欄位只有 public digest、timing、token count、
  child generation、trigger reason 與 resource sample。
- §7 spawn environment 使用 allowlisted 變數，移除 `PYTHONPATH`/`PYTHONHOME`/`LD_PRELOAD`。
- `M4B-PRIV-001` Test ID 覆蓋 success 與 failure 路徑的隱私斷言。

### 5. P5 normalizer 仍由 Reasoner 擁有，fake child 不宣告 product schema/quality PASS

**結論：通過。**

- §3.1 明確指出 RESULT response 仍由 Reasoner 以 Ch 9 validator 再次驗證；child constrained
  schema 不是繞過 product validator 的權威。
- §6 item 1 確認雙層驗證：parent 先驗 exact keys/metrics/bounds，Reasoner 再驗 response
  exact keys 及 Ch 9 capability/tool schema。
- §6 item 3 重申 constrained decoder 或 child 聲稱 schema-valid 不取代 Reasoner validator。
- Fake child (`tests/fakes/m4b_llm_child.py`) 為 deterministic structured-wire child，不宣告
  product schema/quality PASS（§3.1）。

### 6. Hard-coded reason timeout 改成 config-driven 且 15s generation / 2s grace / 0.5s cancel 分層不漂移

**結論：通過。**

- §5.1 明確分層：`AppConfig.cognition.reason_timeout_seconds`（Ch 10 default 30s）為 Reasoner
  外層；child generation 固定 15s；parent terminal-only grace 固定 2s；三者不可混成單一 timeout。
- §7 `LLMConfig` 固定 `generation_timeout_seconds: 15.0`、`terminal_grace_seconds: 2.0`。
- §7 配合 `cancel.abort_timeout_seconds.by_kind["cognition.reasoner"]` 固定 0.5s。
- Ch 10 已確認 `CognitionConfig.reason_timeout_seconds: float = 30.0`。
- 數值在 §7 明確要求「須與本節完全相等；YAML 不得放寬」。

### 7. Unique-owner sampler / raw-byte 8/48/768 trigger / terminal-only schedule/wait / RecoveryTicket / main-owned RM fatal monitor / new READY 形成 single-owner 閉環

**結論：通過。**

- §0.3 完整定義 recycle policy：8 inference attempts / 48 MiB owner PSS delta / 768 MiB
  MemAvailable。
- §0.3 明確要求 raw bytes 比較（`48 * 1024**2` 與 `768 * 1024**2`），不得先四捨五入 MiB。
- §0.3 規定 recycle 不得在 active request 中執行，必須在 operation terminal、Conversation close、
  output/reference discard 與 owner sample 完成後。
- §0.3 窄化 `schedule_recovery(("backend.cognition.reasoner.llm",))`，adapter 保存 ticket 供
  下一個 `generate()` 呼叫 `wait_recovery(ticket)`。
- §0.1 確認 `rm.wait_fatal()` 由 main 常駐監督，即使沒有下一 request 也立即 Level 3。
- §5.2 recovery hook 只在新 child 完成 same-lock authenticate/load/pre-warm/READY 後原子切換
  reference。Capability map 不變、舊 child 永不重新 admit。
- §3 `LLMResourceSampler` Protocol 為 unique-owner PSS 取樣的唯一介面。
- §7 `LLMConfig` 三個 recycle 欄位與 `model_spec.md` §6.4 完全一致。

### 8. Gate 2B narrow harness 與 Core generic renderer 明確列為 product delta / machine FAIL 與 waiver 分欄

**結論：通過。**

- §3.2 開頭明確區分：Gate 2B marker harness 只接受 `listen -> speak -> listen`，Core general
  renderer 為 generic `speak/tool/rest`，二者不可誤稱相同。
- §3.2 表格列出五項 POC schema authority 與其 SHA-256，明確標示 Core disposition。
- §9 POC inheritance 逐項列出 P1~P12 的 Core Gate 3 disposition，每項都標明「重跑」或
  「繼承 + 重驗 delta」。
- §0.1 immutable design inputs 明確記錄 Attempt 006 P9/P10B 維持 FAIL，POC waiver 不得轉成
  Core product PASS。
- `M4B-INH-001` Test ID 覆蓋 machine result/waiver 分欄與 locator/checksum。

### 9. Gemma 4 E2B typo clarification 有記錄 / 非 LiteRT-LM runtime 仍另開 AR_impl

**結論：通過。**

- 文件開頭（L5-8）明確記錄 USER 於 2026-08-29 澄清 `arch.md` 的 `Gemma3:e2b` 是文字 typo，
  E2B 指 Gemma 4 E2B。
- §0.1 Architecture disposition 明確標示 No architecture change / no AR_impl。
- §1.2 明確規定任何 runtime 或 locked identity 偏離仍須另開 change request 或 AR_impl。

### 10. Tester handoff 能直接形成 §10 的 15 個 Test ID / r14 4/64 gates 不被 recycle 重設 / M4A accepted behavior 無矛盾

**結論：通過。**

- §10.2 列出 15 個 Test ID（M4B-CFG-001 至 M4B-INH-001），每個都有 Platform 與 Required risk。
- §10.1 列出 M4B-IPC-001 的 10 項最低覆蓋要求。
- `M4B-RES-001` 明確指出 r14 frozen verifier 公式的 4 MiB/session slope 與 64 MiB late-minus-early
  median delta 不可被 recycle 重設：「48 MiB 是 early recycle trigger，不是放寬 64 MiB gate；
  單次 jump 越界即 FAIL，即使之後 recycle 成功也不洗掉」。
- `M4B-RES-001` 要求至少觀察兩個完成 replacement 及三個 child generation（8-attempt 上限
  在 20 sessions 必然於第 8 與第 16 個 attempt 各排程一次）。
- M4A regression 由 §10.1 item 10 覆蓋，且 §12 明確規定 M4a Accepted 不回退但 final M4
  candidate 必須對 M4a scope 建立 inheritance 並重跑受 M4b composition 影響的 regressions。

---

## Advisory（不影響 Resolved，Owner 可選擇本輪處理或另行記錄）

### ADV-1：§4 step 8 引用的 `prepare_shutdown()` 未列入 Ch 5 新增面

§4 step 8 提到「由 main 先呼叫 RM-owned `prepare_shutdown()` 取消／等待 recovery」，但 §0.1
只列 `rm.wait_fatal()` 為 Ch 5 新增面。建議 Designer 在 Ch 5 更新時一併補上
`prepare_shutdown()` 的語意，或於 §0.1 記錄其為同批 Ch 5 surface。此項語意從 §4 上下文
已足夠推導（取消 in-progress recovery task → 讓 `stop()` 可安全執行），不構成設計遺漏。

---

## 結論

M4b LLM Production Design 通過設計審查。設計與 `arch.md` 架構、`protocol.md` §4 wire contract、
`model_spec.md` §6 winner baseline、Ch 2b worker contract、Ch 5 RM recovery、Ch 9 payload validator、
Ch 10 config schema 及 `M4.md` §6.2.2 planning slices 全面對齊，無架構變更需求。

**下一步**：Tester 可建立 `TR_spec_M4B_I`，於 `docs/test_spec/test_spec_M4.md` 新增完整 M4B 章節，
由 Designer 以 `TR_spec_M4B_I` 確認 15 項 Test ID 100% coverage 後標記 Development Ready。
