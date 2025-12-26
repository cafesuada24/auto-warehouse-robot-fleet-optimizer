import dataclasses

from awrfo.types import IDType
from pydantic import NonNegativeInt

from app.domain.types import Position


@dataclasses.dataclass(frozen=True)
class TaskEventBase:
    task_id: IDType
    timestamp_ms: NonNegativeInt


@dataclasses.dataclass(frozen=True)
class TaskCreatedEvent(TaskEventBase):
    pickup: Position
    dropoff: Position

    deadline_ms: NonNegativeInt


@dataclasses.dataclass(frozen=True)
class TaskCompletedEvent(TaskEventBase):
    duration_ms: NonNegativeInt
