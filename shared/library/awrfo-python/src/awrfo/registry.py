from collections.abc import Callable
from functools import wraps
from typing import ParamSpec

from awrfo.singleton import SingletonMeta

P = ParamSpec('P')

# Type aliases for clarity and reuse
type Command = Callable[..., None]
type RegistryStore = dict[str, dict[str, Command]]


class Registry(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.__registry: RegistryStore = {}

    def register_command(
        self,
        group: str,
        name: str,
    ) -> Callable[[Callable[P, None]], Callable[P, None]]:
        """Register a command to a registry group."""
        def decorator(func: Callable[P, None]) -> Callable[P, None]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
                return func(*args, **kwargs)

            self.__registry.setdefault(group, {})[name] = wrapper
            return wrapper

        return decorator

    def get_registry(self) -> RegistryStore:
        """
        Returns a shallow *read-only snapshot* of the registry.
        """
        return {group: commands.copy() for group, commands in self.__registry.items()}
