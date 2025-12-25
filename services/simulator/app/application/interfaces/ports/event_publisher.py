from collections.abc import Iterable
from typing import Protocol

from app.application.dtos.publish_request import PublishRequest


class EventPublisher(Protocol):
    def enqueue_all(self, items: Iterable[PublishRequest]) -> None: ...
