"""Action layer contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ActionRequest:
    kind: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    detail: Any = None


class Action(Protocol):
    async def execute(self, request: ActionRequest) -> ActionResult: ...
