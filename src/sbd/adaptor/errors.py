"""Translatable library-adapter errors."""


class AdapterError(RuntimeError):
    pass


class AdapterTimeout(AdapterError):
    pass


class AdapterRejected(AdapterError):
    pass


class AdapterUnavailable(AdapterError):
    pass
