from collections.abc import Generator
from typing import Protocol

from app.application.events.domain_event import DomainEvent


class EventStore(Protocol):
    def store(self, event: DomainEvent) -> None: ...

    def iter(self) -> Generator[DomainEvent]: ...
