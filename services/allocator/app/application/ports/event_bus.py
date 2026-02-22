from dataclasses import dataclass
from typing import Protocol

from pydantic import NonNegativeFloat


@dataclass(frozen=True)
class EventMessage:
    topic: str
    payload: bytes

class EventBus(Protocol):
    def poll(self, timeout_s: NonNegativeFloat = 0.2) -> EventMessage | None:
        ...

    def publish(self, topic: str, payload: bytes) -> None:
        ...
