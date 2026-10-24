from .models import ResourceKey, Lifecycle, ManagedRecord
from .errors import UndeclaredDependencyError, ResourceNotReadyError

class ResourceResolver:
    def __init__(self, owner_key: ResourceKey, owner_dependencies: tuple[ResourceKey, ...], records: dict[ResourceKey, ManagedRecord]):
        self._owner_key = owner_key
        self._owner_dependencies = owner_dependencies
        self._records = records

    def require(self, key: ResourceKey) -> Lifecycle:
        if key not in self._owner_dependencies:
            raise UndeclaredDependencyError(self._owner_key, key)
        record = self._records[key]
        if not record.started or record.instance is None:
            raise ResourceNotReadyError(self._owner_key, key)
        return record.instance
