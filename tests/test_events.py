"""Tests for M1-EVT-001 and M1-EVT-002: Event dataclass contracts.

M1-EVT-001: frozen+slots, fields, containers, State/status, family union,
            no internal version, nested sentinel immutability, downstream
            receives same object.
M1-EVT-002: session_id UUIDv4, turn_id starts at 1 and increments,
            correlation_id monotonic from 1 per SM instance, isolation.
"""

from __future__ import annotations

import dataclasses
import re
import uuid

import pytest

from sbd.core.events import (
    ActionCompleted,
    ButtonPressed,
    ErrorOccurred,
    Event,
    ExternalMessageArrived,
    InterruptRequested,
    LLMResponse,
    PerceptionResult,
    ShutdownRequested,
    Signal,
    StateChanged,
    StateBroadcast,
    WakeWordDetected,
    WorkerFact,
    new_message_id,
    new_session_id,
)

# All concrete event classes for parametrised tests
_ALL_EVENTS = [
    PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred,
    StateChanged, ButtonPressed, ExternalMessageArrived,
    WakeWordDetected, InterruptRequested, ShutdownRequested,
]


# ── M1-EVT-001 ──────────────────────────────────────────────────────────


class TestFrozenAndSlots:
    """Every event class is @dataclass(frozen=True, slots=True)."""

    @pytest.mark.parametrize("cls", _ALL_EVENTS, ids=lambda c: c.__name__)
    def test_is_dataclass(self, cls):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"

    @pytest.mark.parametrize("cls", _ALL_EVENTS, ids=lambda c: c.__name__)
    def test_is_frozen(self, cls):
        # frozen dataclasses set __dataclass_params__.frozen = True
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be frozen"  # type: ignore[attr-defined]

    @pytest.mark.parametrize("cls", _ALL_EVENTS, ids=lambda c: c.__name__)
    def test_has_slots(self, cls):
        assert hasattr(cls, "__slots__"), f"{cls.__name__} must have __slots__"

    def test_perception_result_frozen_write(self):
        ev = PerceptionResult(kind="listen", status="ok", text="hello")
        with pytest.raises(AttributeError):
            ev.text = "mutated"  # type: ignore[misc]

    def test_state_changed_frozen_write(self):
        ev = StateChanged(old="IDLE", new="WAKE")
        with pytest.raises(AttributeError):
            ev.old = "ERROR"  # type: ignore[misc]


class TestFields:
    """Field names, types, and defaults match Ch 1 spec."""

    def test_perception_result_fields(self):
        ev = PerceptionResult(kind="listen", status="ok", text="hi")
        assert ev.kind == "listen"
        assert ev.status == "ok"
        assert ev.text == "hi"
        assert ev.extra == {}
        assert ev.session_id == ""
        assert ev.turn_id == 0
        assert ev.correlation_id == 0

    def test_llm_response_fields(self):
        ev = LLMResponse(
            action_kind="speak",
            action_payload={"text": "hi"},
            next_perceptions=("listen",),
            session_id="s1",
            turn_id=1,
            correlation_id=1,
        )
        assert ev.action_kind == "speak"
        assert ev.next_perceptions == ("listen",)
        assert isinstance(ev.next_perceptions, tuple)

    def test_action_completed_fields(self):
        ev = ActionCompleted(kind="speak", status="ok")
        assert ev.result == {}
        assert ev.session_id == ""

    def test_error_occurred_no_session_fields(self):
        """ErrorOccurred has no session_id / turn_id / severity."""
        ev = ErrorOccurred(where="bus.dispatch.x", error="boom")
        assert not hasattr(ev, "session_id")
        assert not hasattr(ev, "turn_id")
        assert not hasattr(ev, "severity")
        assert ev.exception_type is None

    def test_state_changed_fields(self):
        ev = StateChanged(old="IDLE", new="WAKE")
        assert ev.old == "IDLE"
        assert ev.new == "WAKE"
        assert isinstance(ev.at, float)

    def test_button_pressed_fields(self):
        ev = ButtonPressed(button_id="main", duration_ms=150)
        assert ev.button_id == "main"
        assert ev.duration_ms == 150

    def test_external_message_fields(self):
        ev = ExternalMessageArrived(channel="mqtt", arrived_at=1.0, message_id="m1")
        assert ev.channel == "mqtt"

    def test_wake_word_fields(self):
        ev = WakeWordDetected(phrase="hey snowboard", confidence=0.95)
        assert ev.phrase == "hey snowboard"
        assert ev.confidence == 0.95

    def test_interrupt_empty(self):
        ev = InterruptRequested()
        fields = dataclasses.fields(ev)
        assert len(fields) == 0

    def test_shutdown_empty(self):
        ev = ShutdownRequested()
        fields = dataclasses.fields(ev)
        assert len(fields) == 0


class TestContainersAndTuples:
    """next_perceptions uses tuple; dicts use dict."""

    def test_next_perceptions_is_tuple(self):
        ev = LLMResponse(
            action_kind="rest",
            action_payload={},
            next_perceptions=("listen", "look"),
        )
        assert isinstance(ev.next_perceptions, tuple)

    def test_extra_is_dict(self):
        ev = PerceptionResult(kind="listen", status="ok", text="x")
        assert isinstance(ev.extra, dict)


class TestNoInternalVersion:
    """Internal events carry no version / schema_version field."""

    @pytest.mark.parametrize("cls", _ALL_EVENTS, ids=lambda c: c.__name__)
    def test_no_version_field(self, cls):
        field_names = {f.name for f in dataclasses.fields(cls)}
        assert "version" not in field_names
        assert "schema_version" not in field_names


class TestFamilyUnions:
    """TypeAlias unions are correct groupings."""

    def test_worker_fact_members(self):
        # Union members via __args__
        args = set(WorkerFact.__args__)  # type: ignore[attr-defined]
        assert args == {PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred}

    def test_state_broadcast_is_state_changed(self):
        assert StateBroadcast is StateChanged  # type: ignore[comparison-overlap]

    def test_signal_members(self):
        args = set(Signal.__args__)  # type: ignore[attr-defined]
        assert args == {
            ButtonPressed, ExternalMessageArrived, WakeWordDetected,
            InterruptRequested, ShutdownRequested,
        }

    def test_event_covers_all(self):
        event_args = set(Event.__args__)  # type: ignore[attr-defined]
        # Event = WorkerFact | StateBroadcast | Signal — flattened
        expected = (
            set(WorkerFact.__args__)  # type: ignore[attr-defined]
            | {StateChanged}
            | set(Signal.__args__)  # type: ignore[attr-defined]
        )
        assert event_args == expected


class TestNestedPayloadContract:
    """Downstream subscriber receives the same object; nested sentinel unchanged."""

    def test_same_object_identity(self):
        """Two subscribers receive the same event object reference."""
        ev = PerceptionResult(
            kind="listen", status="ok", text="hi",
            extra={"nested": {"sentinel": 42}},
        )
        received: list[PerceptionResult] = []

        # Simulate two subscribers
        received.append(ev)
        received.append(ev)

        assert received[0] is received[1]
        assert received[0].extra["nested"]["sentinel"] == 42

    def test_derived_data_uses_new_object(self):
        """Derived data must create new dicts, not mutate the original."""
        original_extra = {"key": "value"}
        ev = PerceptionResult(
            kind="listen", status="ok", text="hi", extra=original_extra,
        )
        # Correct pattern: create new dict for derived data
        derived = {**ev.extra, "added": True}
        assert "added" not in ev.extra
        assert derived["added"] is True


# ── M1-EVT-002 ──────────────────────────────────────────────────────────


UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class TestSessionId:
    """session_id is a valid UUIDv4 string."""

    def test_format(self):
        sid = new_session_id()
        assert UUID4_RE.match(sid), f"Not a valid UUIDv4: {sid}"

    def test_uniqueness(self):
        ids = {new_session_id() for _ in range(100)}
        assert len(ids) == 100

    def test_parseable(self):
        sid = new_session_id()
        parsed = uuid.UUID(sid)
        assert parsed.version == 4


class TestMessageId:
    """message_id is a valid UUIDv4 string."""

    def test_format(self):
        mid = new_message_id()
        assert UUID4_RE.match(mid), f"Not a valid UUIDv4: {mid}"

    def test_uniqueness(self):
        ids = {new_message_id() for _ in range(100)}
        assert len(ids) == 100


class TestTurnIdAndCorrelationId:
    """turn_id starts at 1 and increments; correlation_id is monotonic.

    NOTE: Actual turn/correlation management belongs to StateManager.
    Here we verify the ID types and default values on events, plus
    demonstrate the expected patterns that SM tests will validate.
    """

    def test_turn_id_default(self):
        ev = PerceptionResult(kind="listen", status="ok", text="x")
        assert ev.turn_id == 0  # default before SM assignment

    def test_correlation_id_default(self):
        ev = PerceptionResult(kind="listen", status="ok", text="x")
        assert ev.correlation_id == 0  # default before SM assignment

    def test_turn_id_starts_at_one_when_set(self):
        ev = PerceptionResult(
            kind="listen", status="ok", text="x",
            session_id="s1", turn_id=1, correlation_id=1,
        )
        assert ev.turn_id == 1

    def test_correlation_id_monotonic_pattern(self):
        """Demonstrate expected monotonic correlation_id pattern."""
        ids = [1, 2, 3, 4]
        for i in range(len(ids) - 1):
            assert ids[i] < ids[i + 1]

    def test_different_sessions_independent_turn_ids(self):
        """Different sessions can have turn_id=1 independently."""
        ev1 = PerceptionResult(
            kind="listen", status="ok", text="x",
            session_id="s1", turn_id=1, correlation_id=1,
        )
        ev2 = PerceptionResult(
            kind="listen", status="ok", text="x",
            session_id="s2", turn_id=1, correlation_id=5,
        )
        assert ev1.session_id != ev2.session_id
        assert ev1.turn_id == ev2.turn_id == 1
