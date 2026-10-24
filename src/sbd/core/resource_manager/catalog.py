from collections.abc import Iterable
from typing import Any, Optional
from sbd.perception.base import Perception
from sbd.action.base import Action
from sbd.cognition.reasoner import Reasoner

class WorkerCatalog:
    def __init__(self):
        self._perceptions: dict[str, Perception] = {}
        self._actions: dict[str, Action] = {}
        self._reasoner: Optional[Reasoner] = None
        self._sealed: bool = False

    def register(self, kind: str, instance: Any) -> None:
        if self._sealed:
            raise RuntimeError("Cannot register after catalog is sealed")
        if kind == "reasoner":
            if self._reasoner is not None:
                raise ValueError("Reasoner is already registered")
            self._reasoner = instance
        elif kind in ("speak", "tool", "rest"):
            if kind in self._actions:
                raise ValueError(f"Action kind '{kind}' is already registered")
            self._actions[kind] = instance
        else:
            if kind in self._perceptions:
                raise ValueError(f"Perception kind '{kind}' is already registered")
            self._perceptions[kind] = instance

    def register_perception(self, kind: str, worker: Perception) -> None:
        self.register(kind, worker)

    def register_action(self, kind: str, worker: Action) -> None:
        self.register(kind, worker)

    def set_reasoner(self, reasoner: Reasoner) -> None:
        self.register("reasoner", reasoner)


    def seal(self, required_kinds: Iterable[str] = ()) -> None:
        if self._sealed:
            return
        required = {"reasoner", "rest", *required_kinds}
        missing = sorted(required - self._get_candidate_kinds())
        if missing:
            raise RuntimeError(
                "Cannot seal WorkerCatalog; missing required workers: "
                + ", ".join(missing)
            )
        self._sealed = True

    def perception(self, kind: str) -> Perception:
        if not self._sealed:
            raise RuntimeError("Cannot lookup before catalog is sealed")
        if kind not in self._perceptions:
            raise KeyError(f"Perception kind '{kind}' not found")
        return self._perceptions[kind]

    def action(self, kind: str) -> Action:
        if not self._sealed:
            raise RuntimeError("Cannot lookup before catalog is sealed")
        if kind not in self._actions:
            raise KeyError(f"Action kind '{kind}' not found")
        return self._actions[kind]

    def reasoner(self) -> Reasoner:
        if not self._sealed:
            raise RuntimeError("Cannot lookup before catalog is sealed")
        if self._reasoner is None:
            raise RuntimeError("Reasoner not set")
        return self._reasoner

    def _get_candidate_kinds(self) -> set[str]:
        kinds = set(self._perceptions.keys()) | set(self._actions.keys())
        if self._reasoner is not None:
            kinds.add("reasoner")
        return kinds

    @property
    def candidate_kinds(self) -> set[str]:
        return self._get_candidate_kinds()

    @property
    def perception_kinds(self) -> set[str]:
        return set(self._perceptions)

    @property
    def action_kinds(self) -> set[str]:
        return set(self._actions)

    @property
    def is_sealed(self) -> bool:
        return self._sealed
