from enum import IntEnum

class StartPhase(IntEnum):
    STATE_MANAGER = 10
    CORE = 20
    BACKEND = 30
    WORKER = 40
    OBSERVER = 50
    INPUT_PRODUCER = 60
