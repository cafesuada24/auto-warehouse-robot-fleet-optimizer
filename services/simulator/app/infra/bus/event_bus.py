
from collections.abc import Callable
from typing import Any, Protocol


class EventBus[T](Protocol):

    def start(self) -> None:
        """Start the bus."""
        ...

    def subscribe(
        self,
        topic: str,
        callback: Callable[[T], Any] | None = None,
    ) -> None:
        """Register the callback to the specified topic."""

    def publish_event(self, topic: str, message: str | bytes) -> None:
        """Publish an event message to the specified topic."""
        ...

    def cleanup(self) -> None:
        """Clean up bus resources."""
        ...


