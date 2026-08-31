"""M4B-HIST-001 — semantic projection is turn-local and payload-free."""

from __future__ import annotations

from sbd.cognition.llm_child_protocol import encode_reasoning_input
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.core.events import PerceptionResult


def test_m4b_hist_001_second_turn_contains_no_first_turn_or_pending_identity() -> None:
    builder = PromptBuilder()
    first = builder.build(
        perceptions=(PerceptionResult("listen", "ok", "PRIVATE_PRIOR_MARKER"),),
        pending_message_count=2, available_perceptions=("listen",), available_actions=("speak",),
    )
    second = builder.build(
        perceptions=(PerceptionResult("listen", "ok", "CURRENT_MARKER"),),
        pending_message_count=0, available_perceptions=("listen",), available_actions=("speak",),
    )
    assert "PRIVATE_PRIOR_MARKER" in str(encode_reasoning_input(first))
    encoded = encode_reasoning_input(second)
    assert "PRIVATE_PRIOR_MARKER" not in str(encoded)
    assert encoded["pending_message_count"] == 0 and "pending_message_ids" not in encoded
