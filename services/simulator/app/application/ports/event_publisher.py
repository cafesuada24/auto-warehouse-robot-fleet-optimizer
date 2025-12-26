from collections.abc import Iterable
from typing import Protocol

from app.application.events.domain_event import DomainEvent


class EventPublisher(Protocol):
    def enqueue_all(self, items: Iterable[DomainEvent]) -> None: ...
