"""M3 composition extending the M2 dialogue graph with Display ownership."""

from __future__ import annotations

from sbd.core.display import DisplayArbiter, Oled128Renderer
from sbd.core.display.lifecycle import DisplayLifecycle
from sbd.core.display.status_bar import StatusBar
from sbd.core.m2_composition import M2Composition
from sbd.core.resource_manager import ResourceManager, ResourceSpec, StartPhase


class _DisplayOwners:
    def __init__(self, lifecycle: DisplayLifecycle, status: StatusBar) -> None:
        self._lifecycle = lifecycle
        self._status = status

    async def start(self) -> None:
        acquired = self._lifecycle.begin_boot()
        try:
            await self._status.start()
        finally:
            if acquired:
                self._lifecycle.finish_boot()

    async def stop(self) -> None:
        self._lifecycle.begin_shutdown()
        await self._status.stop()


class M3Composition(M2Composition):
    def __call__(self, rm, bus, config) -> None:
        super().__call__(rm, bus, config)
        rm.register(ResourceSpec(
            key="core.display.renderer", phase=StartPhase.CORE,
            dependencies=("core.display",),
            factory=lambda resolver: _NoopLifecycle(Oled128Renderer()),
        ))
        rm.register(ResourceSpec(
            key="core.display.arbiter", phase=StartPhase.CORE,
            dependencies=("core.display", "core.display.renderer"),
            factory=lambda resolver: DisplayArbiter(
                resolver.require("core.display"),
                resolver.require("core.display.renderer").value,
            ),
        ))
        rm.register(ResourceSpec(
            key="observer.status_bar", phase=StartPhase.OBSERVER,
            dependencies=("core.display.arbiter",),
            factory=lambda resolver: _owners(resolver.require("core.display.arbiter"), bus),
            required=False,
        ))


class _NoopLifecycle:
    def __init__(self, value) -> None:
        self.value = value
    async def start(self) -> None: pass
    async def stop(self) -> None: pass


def _owners(arbiter, bus):
    return _DisplayOwners(DisplayLifecycle(arbiter), StatusBar(arbiter, bus))


__all__ = ["M3Composition"]
