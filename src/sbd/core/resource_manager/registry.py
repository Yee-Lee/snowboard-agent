import re
from typing import Iterator, Iterable
from .models import ResourceSpec, ResourceKey
from .errors import ResourceGraphError

class Registry:
    def __init__(self, specs: Iterable[ResourceSpec]):
        self._specs: dict[ResourceKey, ResourceSpec] = {}
        for spec in specs:
            if spec.key in self._specs:
                raise ResourceGraphError(f"Duplicate ResourceKey: {spec.key}")
            self._specs[spec.key] = spec

        self._preflight()

    def _preflight(self) -> None:
        # 1-4 & 7: Check duplicates, phases, existence, null core, capabilities
        capability_owners = set()

        for key, spec in self._specs.items():
            # Check unique dependencies and self dep
            if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*", str(key)):
                raise ResourceGraphError(f"Invalid ResourceKey format: {key}")
            seen_deps = set()
            for dep in spec.dependencies:
                if dep == key:
                    raise ResourceGraphError(f"Resource {key} depends on itself")
                if dep in seen_deps:
                    raise ResourceGraphError(f"Resource {key} has duplicate dependency: {dep}")
                seen_deps.add(dep)

                if dep not in self._specs:
                    raise ResourceGraphError(f"Resource {key} requires unknown dependency: {dep}")

                dep_spec = self._specs[dep]
                if dep_spec.phase > spec.phase:
                    raise ResourceGraphError(f"Resource {key} (phase {spec.phase}) depends on {dep} (phase {dep_spec.phase}) which is later")

            # Check null factory
            if spec.null_factory is not None:
                if str(key) not in {"core.audio", "core.audio.input", "core.audio.output", "core.display", "core.camera"}:
                    raise ResourceGraphError(f"Resource {key} has null_factory outside the core HAL allowlist")

            # Check capability kind
            if spec.capability_kind is not None:
                if spec.capability_kind in capability_owners:
                    raise ResourceGraphError(f"Capability kind {spec.capability_kind} has multiple owners")
                if spec.capability_kind not in {"audio", "display", "camera", "gpio", "listen", "read", "look", "speak", "tool"}:
                    raise ResourceGraphError(f"Invalid capability kind: {spec.capability_kind}")
                capability_owners.add(spec.capability_kind)

            if spec.recoverable and spec.recovery_hook is None:
                raise ResourceGraphError(
                    f"Recoverable resource {key} has no recovery_hook"
                )
            for dependency in spec.capability_dependencies:
                if dependency not in {"audio", "display", "camera", "gpio", "listen", "read", "look", "speak", "tool"}:
                    raise ResourceGraphError(f"Invalid capability dependency: {dependency}")
            if not spec.recoverable and spec.recovery_hook is not None:
                raise ResourceGraphError(
                    f"Resource {key} has recovery_hook but recoverable=False"
                )

        # 5: Kahn topological sort per phase
        # Sort across entire graph first to find cycles
        self._topo_sort()

    def _topo_sort(self) -> list[ResourceKey]:
        in_degree = {k: 0 for k in self._specs}
        adj = {k: [] for k in self._specs}

        for key, spec in self._specs.items():
            for dep in spec.dependencies:
                adj[dep].append(key)
                in_degree[key] += 1

        # Tie break by key for stable sort, but we also respect phase.
        # Actually, phase is already respected since dependencies are in <= phase.
        # Within the same phase, we just tie-break by registration order, but here we just detect cycle.
        queue = [k for k, d in in_degree.items() if d == 0]
        sorted_keys = []

        while queue:
            # Pop next, doesn't matter for cycle detection
            u = queue.pop(0)
            sorted_keys.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(sorted_keys) != len(self._specs):
            raise ResourceGraphError("Cycle detected in resource dependencies")

        return sorted_keys

    def get_spec(self, key: ResourceKey) -> ResourceSpec:
        return self._specs[key]

    def iter_specs(self) -> Iterator[ResourceSpec]:
        return iter(self._specs.values())

    def __contains__(self, key: ResourceKey) -> bool:
        return key in self._specs
