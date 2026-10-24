---
requestor: Tester
owner: Developer
status: Resolved
severity: Blocking
---

# TR_dev_M5_TOOL_I — M5.tool Verification Feedback

- Verified candidate: `6f591db7dcfeb100811bf22153c740ee8d161c99`
- Reference specs: `docs/test_spec/test_spec_M5_tool.md`, `docs/implement/ch_m5_tool.md`, `docs/status/development.md`

## Accepted Scope (No Rework or Pi Rerun Required)

1. **Pi Product & Manual Flows (`M5T-FLOW-001`, `M5T-FLOW-002`, `M5T-FLOW-003`)**:
   - `docs/status/development.md` 與 `docs/implement/ch_m5_tool.md` 已完整記錄 c2 prompt（74 tokens）、首輪 `runtime_prefill_tokens`（93–96 `<= 128`）、Look continuation prefill（45 tokens）、dispatch counts（2 / 1 / 0）、interrupt latency（1.9s）與實測語句／已知限制，且 USER 已驗收 Pi 實機結果並指示關機。**不需重跑 Pi 或補交重複表格**。
2. **已通過之 M5.tool Portable Suites**:
   - `M5T-CFG-001`、`M5T-WRK-001`、`M5T-WRK-002`、`M5T-PAY-001`、`M5T-PAY-002`、`M5T-SM-002`、`M5T-CAN-001`、`M5T-LOG-001` 現有實作與 `tests/test_m5t_*.py`（50 passed）已涵蓋產品失敗風險，**不需補寫模板式負向測試或 log 檢查**。

---

## Blocking Findings (Workstation-Fixable)

### B1. `make_asr_adapter` 簽章變更導致 `tests/test_m4a_cfg_001.py` 3 個既有測試失敗

- **重現命令**：
  ```bash
  PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_m4a_cfg_001.py -o addopts=""
  ```
- **失敗項目與原因**：
  1. `tests/test_m4a_cfg_001.py:131` (`test_m4a_cfg_001_public_factory_signatures_remain_single_cfg_parameter`)：
     - 斷言 `tuple(inspect.signature(make_asr_adapter).parameters) == ("cfg",)`，但 `src/sbd/perception/listen/__init__.py:14` 新增了 `*, initial_prompt: str | None = None`。
  2. `tests/test_m4a_cfg_001.py:165` (`test_m4a_cfg_001_factory_injects_same_verified_lock_by_keyword[asr]`)：
     - 測試將 `WhisperCppASRAdapter` monkeypatch 為 `lambda cfg, *, lock: ...`，但 `make_asr_adapter` 無條件傳入 `initial_prompt=initial_prompt` 觸發 `TypeError: <lambda>() got an unexpected keyword argument 'initial_prompt'`。
  3. `tests/test_m4a_cfg_001.py:201` (`test_m4a_cfg_001_composition_uses_same_real_owner_as_recovery_hook`)：
     - 測試將 `composition_module.make_asr_adapter` monkeypatch 為 `lambda cfg: asr_owner`，但 `src/sbd/core/m2_composition.py:135` 傳入 `initial_prompt=...` 觸發 `TypeError`。
- **明確修正方式**：
  - 在 `src/sbd/perception/listen/__init__.py` 恢復單一參數簽章 `def make_asr_adapter(cfg: ASRConfig) -> ASRAdapter:` 並呼叫 `WhisperCppASRAdapter(cfg, lock=lock)`（保持 M4A public factory 契約不變）。
  - 在 `src/sbd/core/m2_composition.py:135` 呼叫 `asr = make_asr_adapter(config.perception.listen.adapter)`；當 `m5` 為 `True` 時，設定 `asr._initial_prompt = "遠端連線"`（因為 `WhisperCppASRAdapter._default_child` 的 `argv(workdir)` closure 是在 `start()` 時才讀取 `self._initial_prompt`）。
  - 在 `tests/test_m5t_config.py` 新增一個透過 `M2Composition`（M5 config vs M4 config）驗證 `asr._initial_prompt` 為 `"遠端連線"` vs `None` 的測試。

---

### B2. `tests/test_m5t_state_manager.py` 在 Turn 2 進入 `THINK` 前提前結束，未測到 `last_dispatch_status` 單次消費與 `error` 回饋

- **位置**：`tests/test_m5t_state_manager.py:48-53` (`test_tool_feedback_waits_for_primary_and_feedback_joins`)
- **風險說明**：
  - 該測試在 Turn 1 完成 `tool_feedback` 剛切入 Turn 2 (`sm._session.turn_id == 2`) 時就 `break`，最後只斷言 `assert statuses == [None]`。
  - 因此 `src/sbd/core/state_manager/manager.py:770-777`（Turn 2 `THINK` 將 `last_dispatch_status="ok"` 傳給 `reasoner.reason`）與 `manager.py:885-887`（Turn 2 `THINK` 完成後清除 `last_dispatch_status = None`，確保 Turn 3 不會重複拿到 `"ok"`），以及 `manager.py:1244-1255`（`ActionCompleted(tool, "error")` 播報 `"未能確認送出，請稍後再試。"` 並設定 `last_dispatch_status="error"`）在 portable 測試中完全沒有被執行到。
- **明確修正方式**：
  1. 在 `tests/test_m5t_state_manager.py` 的 `test_tool_feedback_waits_for_primary_and_feedback_joins` 中，推進 Turn 2 與 Turn 3 各送出一次 `PerceptionCompleted("listen", "ok", text=...)` 並完成 `speak`，斷言 `statuses == [None, "ok", None]`。
  2. 新增一個簡短測試 `test_tool_error_speaks_failure_feedback_and_passes_error_status_once`，讓 `tool` 回傳 `status="error"`，斷言：
     - `speak` 被呼叫且帶入 `"未能確認送出，請稍後再試。"`；
     - 下一輪 `reasoner.reason` 收到的 `last_dispatch_status` 為 `"error"`，再下一輪回到 `None`。

## Developer Revision — 2026-10-24

- **B1 accepted and repaired:** `make_asr_adapter(cfg)` again exposes only the original `cfg` parameter and constructs Whisper without an extra keyword. `M2Composition` sets `"遠端連線"` on the M5 ASR owner before startup; the M4 profile leaves the prompt unset. The three reported M4A failures now pass, and a new composition regression checks both profiles.
- **B2 accepted and repaired:** the existing join test now drives two subsequent `listen` perceptions and checks reasoner status `[None, "ok", None]`. A separate error test checks the fixed failure speech and `[None, "error", None]`. Both reach the third turn, so the consumption and clearing paths are exercised.
- Workstation command: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_m5t_*.py tests/test_m4a_cfg_001.py tests/test_m4b_cfg_001.py -o addopts=''` — **122 passed**. Targeted compilation and `git diff --check` passed. These are source/test changes after candidate `6f591db`; same-byte Pi verification remains required before a new commit. No Pi result is claimed for this repair. Tester may recheck B1/B2 against the working tree.

## Tester Recheck — 2026-10-24 (`Resolved`)

- **B1 (`M4A-CFG-001` / `M5T-CFG-001`) — Verified & Resolved**:
  - `src/sbd/perception/listen/__init__.py` 恢復 `make_asr_adapter(cfg: ASRConfig) -> ASRAdapter` 單參數簽章；`src/sbd/core/m2_composition.py` 僅在 `m5` profile 下設定 `asr._initial_prompt = "遠端連線"`；`tests/test_m5t_config.py::test_m5_composition_sets_asr_prompt_without_changing_m4` 同時驗證 M4 (`None`) 與 M5 (`"遠端連線"`)。`tests/test_m4a_cfg_001.py` 先前失敗的 3 個測項已全數通過。
- **B2 (`M5T-SM-001`) — Verified & Resolved**:
  - `tests/test_m5t_state_manager.py` 的 `test_tool_feedback_waits_for_primary_and_feedback_joins` 與 `test_tool_error_speaks_failure_feedback_and_passes_error_status_once` 均完整推進至第 3 輪，實測驗證 `statuses == [None, "ok", None]` 與 `[None, "error", None]`，以及固定失敗語音 `"未能確認送出，請稍後再試。"`。
- **Workstation Verification**:
  - `PYTHONPATH=src .venv/bin/python -m pytest -v tests/test_m5t_*.py tests/test_m4a_cfg_001.py tests/test_m4b_cfg_001.py -o addopts=""` → **122 passed in 3.16s**。
  - `PYTHONPATH=src .venv/bin/python -m compileall -q src scripts tests && git diff --check` → **Pass (exit 0)**。
- **Closure & Next Step**:
  - `TR_dev_M5_TOOL_I` 標記為 `Resolved` 並封存至 `docs/reviews/history/TR_dev_M5_TOOL_I.md`。待 Pi 可啟用時，Developer 僅需針對此批修正 bytes 完成 same-byte Pi 驗證即可準備最終 commit。
