"""Tests for M1-CON-001: Cross-layer protocol contracts.

Verifies that minimal conforming fakes satisfy Protocol interfaces and
that lifecycle / in-flight boundaries are correctly defined.
"""
from __future__ import annotations

import asyncio

import pytest

from sbd.core.lifecycle import ForceAbortReport
from sbd.input_events.base import InputSource
from sbd.perception.base import Perception
from sbd.action.base import Action
from sbd.adaptor.base import Adaptor

from tests.fakes import (
    FakeAction,
    FakeAdaptor,
    FakeInputSource,
    FakePerception,
    FakeReasoner,
)


# ── M1-CON-001: Protocol conformance smoke ──────────────────────────────


class TestProtocolConformance:
    """Each fake satisfies its Protocol and exposes the correct interface."""

    def test_input_source_is_protocol_conformant(self):
        fake = FakeInputSource()
        assert isinstance(fake, InputSource)

    def test_perception_is_protocol_conformant(self):
        fake = FakePerception()
        assert isinstance(fake, Perception)

    def test_action_is_protocol_conformant(self):
        fake = FakeAction()
        assert isinstance(fake, Action)

    def test_adaptor_is_protocol_conformant(self):
        fake = FakeAdaptor()
        assert isinstance(fake, Adaptor)


class TestLifecycleBoundaries:
    """Only in-flight workers have abort/force_abort."""

    def test_input_source_has_no_abort(self):
        fake = FakeInputSource()
        assert not hasattr(fake, "abort") or not callable(getattr(fake, "abort", None))
        # InputSource Protocol should NOT declare abort
        assert "abort" not in InputSource.__dict__

    def test_adaptor_has_no_abort(self):
        fake = FakeAdaptor()
        assert not hasattr(fake, "abort") or not callable(getattr(fake, "abort", None))
        assert "abort" not in Adaptor.__dict__

    def test_perception_has_abort_and_force_abort(self):
        fake = FakePerception()
        assert callable(getattr(fake, "abort", None))
        assert callable(getattr(fake, "force_abort", None))

    def test_action_has_abort_and_force_abort(self):
        fake = FakeAction()
        assert callable(getattr(fake, "abort", None))
        assert callable(getattr(fake, "force_abort", None))

    def test_reasoner_has_abort_and_force_abort(self):
        fake = FakeReasoner()
        assert callable(getattr(fake, "abort", None))
        assert callable(getattr(fake, "force_abort", None))


class TestInFlightWorkerMethods:
    """In-flight worker work methods return None; Fact goes through Bus."""

    def test_perception_perceive_returns_none(self):
        fake = FakePerception()
        result = asyncio.run(fake.perceive("sid", 1, 1, 5.0))
        assert result is None

    def test_action_execute_returns_none(self):
        fake = FakeAction()
        result = asyncio.run(fake.execute("sid", 1, 1, {}))
        assert result is None

    def test_reasoner_reason_returns_none(self):
        fake = FakeReasoner()
        result = asyncio.run(fake.reason("sid", 1, 1, (), ()))
        assert result is None


class TestForceAbortReport:
    """ForceAbortReport is a frozen control value, not an Event."""

    def test_frozen(self):
        report = ForceAbortReport()
        with pytest.raises(AttributeError):
            report.destroyed_backends = ("x",)  # type: ignore[misc]

    def test_default_empty(self):
        report = ForceAbortReport()
        assert report.destroyed_backends == ()

    def test_with_backends(self):
        report = ForceAbortReport(destroyed_backends=("backend.cognition.reasoner.llm",))
        assert report.destroyed_backends == ("backend.cognition.reasoner.llm",)

    def test_slots(self):
        report = ForceAbortReport()
        assert hasattr(report, "__slots__")

    def test_force_abort_returns_report(self):
        """force_abort() returns ForceAbortReport, not None."""
        for fake_cls in [FakePerception, FakeAction, FakeReasoner]:
            fake = fake_cls()
            result = asyncio.run(fake.force_abort())
            assert isinstance(result, ForceAbortReport), (
                f"{fake_cls.__name__}.force_abort() must return ForceAbortReport"
            )
