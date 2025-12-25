from threading import Lock
from typing import TypeVar, cast

T = TypeVar('T', bound=object)

class SingletonMeta(type):
    """Singleton meta class."""

    _instances: dict[type[object], object] = {}

    def __call__(cls: type[T], *args: object, **kwds: object) -> T:
        if cls not in SingletonMeta._instances:
            SingletonMeta._instances[cls] = super().__call__(*args, **kwds)
        return cast('T', SingletonMeta._instances[cls])


class ThreadSafeSingletonMeta(type):
    """Thread-safe singleton metaclass."""

    _instances: dict[type[object], object] = {}
    _lock: Lock = Lock()

    def __call__(cls: type[T], *args: object, **kwargs: object) -> T:
        if cls not in ThreadSafeSingletonMeta._instances:
            with ThreadSafeSingletonMeta._lock:
                if cls not in ThreadSafeSingletonMeta._instances:
                    ThreadSafeSingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
        return cast('T', ThreadSafeSingletonMeta._instances[cls])
