"""M4B-REC-001 — exact byte thresholds and target resource sampling."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sbd.cognition.litert_lm.adapter import AdapterState
from sbd.cognition.litert_lm.resource import ProcLLMResourceSampler
from tests.test_m4b_gen_001 import _adapter


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="ascii")


def test_m4b_rec_001_sampler_sums_unique_process_group_pss_in_bytes(tmp_path: Path) -> None:
    # stat fields after comm: state, ppid, pgrp.
    for pid, pss in ((101, 100), (102, 200)):
        _write(tmp_path / str(pid) / "stat", f"{pid} (child worker) S 1 77 0 0\n")
        _write(tmp_path / str(pid) / "smaps_rollup", f"Pss: {pss} kB\n")
    _write(tmp_path / "meminfo", "MemAvailable: 768000 kB\n")
    sample = ProcLLMResourceSampler(tmp_path).sample(child_pid=101, child_pgid=77)
    assert sample.owner_pss_bytes == 300 * 1024
    assert sample.mem_available_bytes == 768000 * 1024


def test_m4b_rec_001_sampler_fails_when_owner_or_field_is_missing(tmp_path: Path) -> None:
    _write(tmp_path / "meminfo", "MemAvailable: 1 kB\n")
    with pytest.raises(RuntimeError, match="owner"):
        ProcLLMResourceSampler(tmp_path).sample(child_pid=1, child_pgid=1)


def test_m4b_rec_001_rebuild_cancellation_cleans_blocked_old_child() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        old = children[0]
        stop_entered = asyncio.Event()

        async def blocked_stop() -> None:
            stop_entered.set()
            await asyncio.Event().wait()

        old.stop = blocked_stop  # type: ignore[method-assign]
        recovery = asyncio.create_task(adapter.rebuild())
        await stop_entered.wait()
        recovery.cancel()
        with pytest.raises(asyncio.CancelledError):
            await recovery
        assert old.terminated == 1
        assert len(children) == 1
        assert adapter.state is AdapterState.STOPPED
        assert adapter._child is None

    asyncio.run(scenario())


def test_m4b_rec_001_rebuild_cancellation_cleans_partial_replacement() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        replacement_entered = asyncio.Event()
        original_factory = adapter._child_factory

        def factory(cfg, lock, generation):
            child = original_factory(cfg, lock, generation)
            if generation == 2:
                async def blocked_start():
                    replacement_entered.set()
                    await asyncio.Event().wait()
                child.start = blocked_start  # type: ignore[method-assign]
            return child

        adapter._child_factory = factory
        recovery = asyncio.create_task(adapter.rebuild())
        await replacement_entered.wait()
        recovery.cancel()
        with pytest.raises(asyncio.CancelledError):
            await recovery
        assert children[0].stopped == 1
        assert children[1].terminated == 1
        assert adapter.state is AdapterState.STOPPED
        assert adapter._child is None

    asyncio.run(scenario())
