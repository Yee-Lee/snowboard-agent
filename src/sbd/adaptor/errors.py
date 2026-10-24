"""Translatable library-adapter errors."""


class AdapterError(RuntimeError):
    pass


class AdapterTimeout(AdapterError):
    pass


class AdapterRejected(AdapterError):
    def __init__(self, message: str = "adapter request rejected", *, code: str | None = None):
        super().__init__(message)
        self.code = code


class AdapterUnavailable(AdapterError):
    pass
