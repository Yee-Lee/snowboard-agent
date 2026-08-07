from dataclasses import dataclass
from typing import Any, Callable, Awaitable, Protocol, NewType, Literal

from .phases import StartPhase

ResourceKey = NewType("ResourceKey", str)
CapabilityKind = Literal[
    "audio", "display", "camera", "gpio",
    "listen", "read", "look", "speak", "tool",
]

class Lifecycle(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

Factory = Callable[["ResourceResolver"], Lifecycle]
RecoveryHook = Callable[[], Awaitable[None]]

@dataclass(frozen=True, slots=True)
class ResourceSpec:
    key: ResourceKey
    phase: StartPhase
    factory: Factory
    dependencies: tuple[ResourceKey, ...] = ()
    required: bool = True
    capability_kind: CapabilityKind | None = None
    capability_dependencies: tuple[CapabilityKind, ...] = ()
    null_factory: Factory | None = None
    recoverable: bool = False
    recovery_hook: Any = None

@dataclass(slots=True)
class ManagedRecord:
    spec: ResourceSpec
    instance: Lifecycle | None = None
    started: bool = False
    using_null: bool = False
    own_start_ok: bool = False
    recovery_hook: RecoveryHook | None = None

@dataclass(frozen=True, slots=True)
class StopFailure:
    key: ResourceKey
    error: BaseException

@dataclass(frozen=True, slots=True)
class ShutdownReport:
    failures: tuple[StopFailure, ...]

@dataclass(frozen=True, slots=True)
class RecoveryTicket:
    generation: int
    keys: tuple[ResourceKey, ...]
