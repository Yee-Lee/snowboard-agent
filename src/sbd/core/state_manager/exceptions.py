class StateManagerFatalError(RuntimeError):
    pass

class StateManagerWiringError(StateManagerFatalError):
    pass

class WakeMicReleaseUnprovable(StateManagerFatalError):
    pass

class StateManagerInvariantViolation(StateManagerFatalError):
    pass

class WorkerContractViolation(StateManagerFatalError):
    pass

class ReasonerContractViolation(Exception):
    pass

class WakeListenerControlError(RuntimeError):
    pass
