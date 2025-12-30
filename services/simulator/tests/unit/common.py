from collections.abc import Iterable

from app.application.events.domain_event import DomainEvent


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def enqueue_all(self, items: Iterable[DomainEvent]) -> None:
        self.events.extend(list(items))
