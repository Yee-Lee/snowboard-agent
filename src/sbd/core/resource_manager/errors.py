from typing import Any

class ResourceManagerError(RuntimeError):
    pass

class ResourceGraphError(ResourceManagerError):
    pass

class ResourceDependencyError(ResourceManagerError):
    pass

class UndeclaredDependencyError(ResourceDependencyError):
    def __init__(self, owner_key: str, dep_key: str):
        super().__init__(f"Resource {owner_key} requires undeclared dependency {dep_key}")
        self.owner_key = owner_key
        self.dep_key = dep_key

class ResourceNotReadyError(ResourceDependencyError):
    def __init__(self, owner_key: str, dep_key: str):
        super().__init__(f"Resource {owner_key} requires dependency {dep_key} which is not ready")
        self.owner_key = owner_key
        self.dep_key = dep_key

class StartupError(ResourceManagerError):
    def __init__(self, root_cause: Any = None, rollback_failures: tuple = ()):
        super().__init__(str(root_cause) if root_cause else "Startup failed")
        self.root_cause = root_cause
        self.rollback_failures = rollback_failures

class RecoveryContractViolation(ResourceManagerError):
    pass

class RecoveryFatalError(ResourceManagerError):
    pass
