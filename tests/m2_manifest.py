"""M2 test files and Test ID to pytest node traceability manifest."""

from __future__ import annotations


M2_TEST_FILES: tuple[str, ...] = (
    "tests/test_m2_hal_001_002_004.py",
    "tests/test_m2_pay_001_002.py",
    "tests/test_m2_reg_001.py",
    "tests/test_m2_msg_001_002_004_005.py",
    "tests/test_m2_wrk_001_002_004.py",
    "tests/test_m2_wrk_003.py",
    "tests/test_m2_flows.py",
    "tests/test_m2_sm_flows.py",
)

M2_TEST_NODES: dict[str, tuple[str, ...]] = {
    "M2-HAL-001": (
        "tests/test_m2_hal_001_002_004.py::test_m2_hal_001_factories_lazy_load_only_selected_mock_backends",
    ),
    "M2-HAL-002": (
        "tests/test_m2_hal_001_002_004.py::test_m2_hal_002_null_audio_iterator_exclusive_reopen_and_consumption",
        "tests/test_m2_hal_001_002_004.py::test_m2_hal_002_null_display_and_camera_return_format_valid_values",
    ),
    "M2-HAL-004": (
        "tests/test_m2_hal_001_002_004.py::test_m2_hal_004_mock_display_camera_and_gpio_contracts",
    ),
    "M2-WRK-001": (
        "tests/test_m2_wrk_001_002_004.py::test_m2_wrk_001_nonreentry_cancel_force_and_exception_cardinality",
        "tests/test_m2_wrk_001_002_004.py::test_m2_wrk_001_fact_is_published_only_after_audio_cleanup",
    ),
    "M2-WRK-002": (
        "tests/test_m2_wrk_001_002_004.py::test_m2_wrk_002_listen_read_look_success_and_at_most_once",
        "tests/test_m2_wrk_001_002_004.py::test_m2_wrk_002_timeout_and_adapter_errors_translate_to_facts",
    ),
    "M2-WRK-003": (
        "tests/test_m2_wrk_003.py::test_m2_wrk_003_prompt_is_canonical_opaque_and_turn_stateless",
        "tests/test_m2_wrk_003.py::test_m2_wrk_003_clean_failures_fallback_without_raw_output",
        "tests/test_m2_wrk_003.py::test_m2_wrk_003_cancel_and_unexpected_error_are_mutually_exclusive",
    ),
    "M2-WRK-004": (
        "tests/test_m2_wrk_001_002_004.py::test_m2_wrk_004_speak_tool_rest_success_and_p5_error",
        "tests/test_m2_wrk_001_002_004.py::test_m2_wrk_004_cancelled_speak_publishes_no_normal_fact",
    ),
    "M2-PAY-001": (
        "tests/test_m2_pay_001_002.py::test_m2_pay_001_exact_action_schemas_do_not_mutate_inputs",
        "tests/test_m2_pay_001_002.py::test_m2_pay_001_rejects_non_json_depth_and_sanitizes_errors",
    ),
    "M2-PAY-002": (
        "tests/test_m2_pay_001_002.py::test_m2_pay_002_registry_seal_schema_view_and_pure_validation",
        "tests/test_m2_pay_001_002.py::test_m2_pay_002_dispatches_once_and_rejects_unknown_before_handler",
    ),
    "M2-MSG-001": (
        "tests/test_m2_msg_001_002_004_005.py::test_m2_msg_001_store_precedes_signal_and_preserves_arrival_order",
        "tests/test_m2_msg_001_002_004_005.py::test_m2_msg_001_invalid_input_allocates_no_id_or_signal",
    ),
    "M2-MSG-002": (
        "tests/test_m2_msg_001_002_004_005.py::test_m2_msg_002_read_window_is_atomic_and_late_arrival_stays_pending",
        "tests/test_m2_msg_001_002_004_005.py::test_m2_msg_002_cancel_timeout_discard_and_notify_before_wait_restore",
    ),
    "M2-MSG-004": (
        "tests/test_m2_msg_001_002_004_005.py::test_m2_msg_004_rejected_newest_allocates_no_id_or_signal[drop_newest-ExternalMessageDropped]",
        "tests/test_m2_msg_001_002_004_005.py::test_m2_msg_004_rejected_newest_allocates_no_id_or_signal[reject-ExternalMessageBufferFull]",
        "tests/test_m2_msg_001_002_004_005.py::test_m2_msg_004_drop_oldest_never_evicts_turn_owned_item",
    ),
    "M2-MSG-005": (
        "tests/test_m2_msg_001_002_004_005.py::test_m2_msg_005_flush_reuses_ids_and_stop_converges_waiters",
    ),
    "M2-FLOW-001": (
        "tests/test_m2_flows.py::test_m2_flow_001_button_two_turn_speak_then_rest",
    ),
    "M2-FLOW-002": (
        "tests/test_m2_flows.py::test_m2_flow_002_external_message_read_once_action_then_rest",
    ),
    "M2-FLOW-003": (
        "tests/test_m2_sm_flows.py::test_m2_flow_003_speak_tool_dedupe_and_rest_ignores_next",
    ),
    "M2-FLOW-004": (
        "tests/test_m2_sm_flows.py::test_m2_flow_004_action_error_uses_default_perceptions",
        "tests/test_m2_flows.py::test_m2_flow_004_bad_llm_fallback_continues_to_rest",
    ),
    "M2-FLOW-005": (
        "tests/test_m2_sm_flows.py::test_m2_flow_005_worker_error_precedes_error_state_and_self_check_does_not",
    ),
    "M2-FLOW-006": (
        "tests/test_m2_sm_flows.py::test_m2_flow_006_notice_barrier_and_exit_buffer_policies",
    ),
    "M2-FLOW-008": (
        "tests/test_m2_flows.py::test_m2_flow_008_default_process_sigint_exits_zero_from_idle",
    ),
    "M2-REG-001": (
        "tests/test_m2_reg_001.py::test_m2_reg_001_fixture_barrier_and_call_log",
        "tests/test_m2_reg_001.py::test_m2_reg_001_fixture_payloads_are_deterministic",
        "tests/test_m2_reg_001.py::test_m2_reg_001_default_import_avoids_pi_dependencies",
    ),
}

M2_PARTIAL_TEST_IDS: frozenset[str] = frozenset()


def incomplete_test_ids() -> tuple[str, ...]:
    """Return Test IDs that lack complete executable pytest evidence."""
    return tuple(
        test_id
        for test_id, nodes in M2_TEST_NODES.items()
        if not nodes or test_id in M2_PARTIAL_TEST_IDS
    )


def traced_nodes() -> tuple[str, ...]:
    """Flatten node IDs in stable Test ID order for evidence generation."""
    return tuple(node for nodes in M2_TEST_NODES.values() for node in nodes)
