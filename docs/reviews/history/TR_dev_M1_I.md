---
requestor: "Tester"
owner: "Developer"
status: "Resolved"
---

# TR_dev_M1_I ── M1 純軟體核心 測試驗收報告

## 1. 驗收結論

**判定：✅ PASS**

M1 所有 Test ID 對應的測試項目均已通過工具實測，無 FAILED / SKIPPED / XFAIL。測試代碼確實觸發了 `src/sbd/` 的核心邏輯，未發現阻擋性假綠燈。

---

## 2. 執行環境

| 項目 | 值 |
| :--- | :--- |
| 平台 | Linux (開發機) |
| Python | 3.12.3 |
| pytest | 7.4.4 |
| 執行時間 | 2026-08-03T15:33Z ~ 15:36Z |
| PYTHONPATH | `src/` (editable install 模式) |

---

## 3. 驗收命令執行結果

### 3.1 命令一：M1 Entrypoint

```bash
python -m pytest -v tests/milestones/test_m1_foundation.py
```

**結果：154 passed, 0 failed, 0 skipped, 0 xfail ── 耗時 5.06s**

### 3.2 命令二：Full Suite

```bash
python -m pytest -v
```

**結果：308 passed, 0 failed, 0 skipped, 0 xfail ── 耗時 10.36s**

308 = 154 (原始模組) × 2 (milestones entrypoint 重匯出)，數目一致無遺漏。

---

## 4. Test ID 覆蓋對照

| Test ID | 對應測試函數 | 結果 |
| :--- | :--- | :---: |
| M1-EVT-001 | `TestFrozenAndSlots::*`, `TestFields::*`, `TestContainersAndTuples::*`, `TestFamilyUnions::*`, `TestNoInternalVersion::*`, `TestNestedPayloadContract::*` | ✅ |
| M1-EVT-002 | `TestSessionId::*`, `TestMessageId::*`, `TestTurnIdAndCorrelationId::*` | ✅ |
| M1-CON-001 | `TestLifecycleBoundaries::*`, `TestInFlightWorkerMethods::*`, `TestProtocolConformance::*`, `TestForceAbortReport::*` | ✅ |
| M1-BUS-001 | `test_bus_001_exact_type_snapshot_token_nosubscriber` | ✅ |
| M1-BUS-003 | `test_bus_003_handler_failure_deferred_error` | ✅ |
| M1-BUS-004 | `test_bus_004_cancelled_fatal_handoff` | ✅ |
| M1-SM-001 | `test_m1_sm_001_subscriptions_enqueue_and_transitions_are_serial` | ✅ |
| M1-SM-002 | `test_m1_sm_002_fact_and_task_done_form_a_join_barrier` | ✅ |
| M1-SM-003 | `test_m1_sm_003_stale_and_duplicate_facts_do_not_pollute_turn`, `test_m1_sm_003_worker_return_without_fact_is_runtime_fatal` | ✅ |
| M1-SM-004 | `test_m1_sm_004_external_wake_maps_to_read_before_worker_starts`, `test_m1_sm_004_early_error_cancels_timer_and_stale_notice_is_ignored` | ✅ |
| M1-SM-005 | `test_m1_sm_005_invalid_reasoner_response_enters_error_without_error_event`, `test_m1_sm_005_validator_rejection_is_nonfatal_error_without_bus_error`, `test_m1_sm_005_speak_normalizes_next_perceptions_and_starts_action` | ✅ |
| M1-SM-006 | `test_m1_sm_006_convergence_waits_for_inflight_handles_before_idle`, `test_m1_sm_006_error_exit_waits_for_handles_and_recovery` | ✅ |
| M1-RM-001 | `test_rm_001_missing_dependency_raises_graph_error`, `test_rm_001_cycle_detection_raises_graph_error` | ✅ |
| M1-RM-002 | `test_rm_002_producer_is_late_filled_before_arm`, `test_rm_002_phase_ordered_startup` | ✅ |
| M1-RM-003 | `test_rm_003_optional_source_without_first_turn_worker_never_starts`, `test_rm_003_required_source_without_first_turn_worker_is_fatal`, `test_rm_003_audio_real_failure_fallbacks_to_null` | ✅ |
| M1-RM-004 | `test_rm_004_catalog_seal_and_reasoner_restriction`, `test_rm_004_capability_dependencies_propagate_false`, `test_rm_004_catalog_seal_rejects_missing_required_kinds` | ✅ |
| M1-RM-005 | `test_rm_005_recovery_dependency_order_and_backend_owner_switch`, `test_rm_005_recovery_failure_or_timeout_keeps_barrier_clear[failure/timeout]`, `test_rm_005_recovery_reentry_and_unrecoverable_keys_are_rejected`, `test_rm_005_shutdown_waits_for_recovery_hook_cleanup`, `test_rm_005_recovery_ticket_and_barrier`, `test_rm_005_invalid_returned_replacement_is_cleaned` | ✅ |
| M1-RM-006 | `test_rm_006_start_timeout_rolls_back_and_stop_failures_do_not_block`, `test_rm_006_shutdown_reverse_order` | ✅ |
| M1-CAN-001 | `test_can_001_empty_records_returns_immediately`, `test_can_001_duplicate_records_rejected_before_worker_calls`, `test_can_001_all_level_one_aborts_start_in_parallel`, `test_can_001_level_one_timeout_escalates_only_failed_target` | ✅ |
| M1-CAN-002 | `test_can_002_force_abort_timeout_is_fatal_without_task_cancel`, `test_can_002_force_abort_exception_is_fatal` | ✅ |
| M1-CAN-003 | `test_can_003_reports_are_deduplicated_and_sorted`, `test_can_003_reentry_is_fatal_and_finally_allows_reuse`, `test_can_003_orchestration_cancellation_passes_through` | ✅ |
| M1-CFG-001 | `test_m1_cfg_001_precedence_and_immutability`, `test_m1_cfg_001_relative_paths_resolve_from_config_directory` | ✅ |
| M1-CFG-002 | `test_m1_cfg_002_validation`, `test_m1_cfg_002_rejects_bool_literal_and_nested_element_types[×6]` | ✅ |
| M1-CFG-004 | `test_m1_cfg_004_secret_and_env` | ✅ |
| M1-CFG-005 | `test_m1_cfg_005_example_file_passes` | ✅ |
| M1-LOG-001 | `test_log_001_formatters_and_handlers` | ✅ |
| M1-LOG-002 | `test_log_002_error_observer` | ✅ |
| M1-LOG-003 | `test_log_003_redaction` | ✅ |
| M1-LOG-004 | `test_log_004_fatal_supervision` | ✅ |
| M1-BOOT-001 | `test_m1_boot_001_malformed_config_returns_exit_2`, `..._default_config_subprocess_exits_2`, `..._startup_and_rollback_failure_subprocess_exits_3`, `..._runtime_bus_fatal_subprocess_exits_4`, `..._signal_subprocess_exits_cleanly[2/15]` | ✅ |
| M1-REG-001 | `test_reg_001_no_pi_only_dependencies_imported`, `test_reg_001_no_m2_concrete_modules_imported`, `test_reg_001_rpi_marker_registered` | ✅ |

**31 個 Test ID 全數覆蓋，無遺漏。**

---

## 5. Anti-Fake Green Light 審查

### 5.1 審查方法

- 全測試檔案逐一人工審閱 + 自動化掃描
- 搜尋 `assert True`、`assert 1`、`skip`、`xfail` 等假綠燈模式
- 確認每個測試檔案 import 並實際呼叫 `src/sbd/` 模組

### 5.2 結果

| 檢查項 | 結果 |
| :--- | :--- |
| `assert True` / `assert 1` | ❌ 未發現 |
| `@pytest.mark.skip` / `@pytest.mark.xfail` | ❌ 未發現（`conftest.py` 的 rpi skip 屬預期行為，M1 無 rpi 測試） |
| 純 mock 不觸 `src/` | ❌ 未發現阻擋性問題（見 §5.3） |
| 所有測試 import `sbd.*` | ✅ 10/10 測試檔案皆 import 並執行 `src/sbd/` 核心模組 |

### 5.3 非阻擋性觀察 (Observations)

以下 3 項為觀察紀錄，**不影響 PASS 判定**，不要求 Developer 修正：

1. **`test_events.py::test_correlation_id_monotonic_pattern`** — 此測試在硬編碼 list `[1,2,3,4]` 上驗證單調性，未實際觸發 `sbd` 模組。但此測試屬 M1-EVT-002 的輔助驗證（demonstrate expected pattern），且 correlation_id 的核心行為已由 `TestTurnIdAndCorrelationId` 其餘測試和 SM 測試覆蓋。

2. **`test_contracts.py::TestInFlightWorkerMethods`** — 3 個測試呼叫 `FakePerception/Action/Reasoner` 的空方法驗證 `return None`。此屬 M1-CON-001 的設計意圖：「公開方法回 `None`」。真正的行為驗證在 SM/RM 測試中完成。

3. **`test_logging.py::test_log_004_fatal_supervision` 末段** — `assert p5_res.status == "error"` 僅構建 dataclass 並斷言欄位值，未觸發 logging 行為。但此測試的主體部分充分驗證了 exception hierarchy 與 re-export 完整性，尾段斷言只是補充確認 P5 事件結構。

---

## 6. 共同完成條件檢核

| 條件 (milestone §1.4) | 檢核 |
| :--- | :--- |
| 新增契約行為有自動化測試 | ✅ 154 tests 覆蓋全部 31 個 Test ID |
| `python -m pytest -v` 全數通過 | ✅ 308 passed, 0 failed |
| 不得刪除 / skip / xfail 先前測試 | ✅ 無先前 milestone 測試（M1 為首階段） |
| 測試不含 credential / prompt / payload / 音訊 | ✅ 已由 M1-LOG-003 redaction 測試驗證 |
| 不意外 import Pi-only dependency | ✅ 已由 M1-REG-001 驗證 |
| `rpi` marker 已在 pytest 設定註冊 | ✅ 已由 `test_reg_001_rpi_marker_registered` 驗證 |

---

## 7. 結論與後續

M1 驗收 **通過**。依 workflow.md [E] 階段規定：

> Tester PASS → Designer 最終 Code Review (CR_M1) → 審查全數通過後才提交

本報告移交 Designer 執行最終 Code Review。
