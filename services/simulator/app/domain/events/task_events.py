import dataclasses

from awrfo.types import IDType
from pydantic import NonNegativeInt

from app.domain.types import Position

from .base import EventBase


@dataclasses.dataclass(frozen=True)
class TaskEventBase(EventBase):
    task_id: IDType
    timestamp_ms: NonNegativeInt


@dataclasses.dataclass(frozen=True)
class TaskCreatedEvent(TaskEventBase):
    pickup: Position
    dropoff: Position

    deadline_ms: NonNegativeInt


@dataclasses.dataclass(frozen=True)
class TaskCompletedEvent(TaskEventBase):
    robot_id: IDType
    duration_ms: NonNegativeInt


@dataclasses.dataclass(frozen=True)
class TaskAssignedEvent(TaskEventBase):
    robot_id: IDType


@dataclasses.dataclass(frozen=True)
class TaskCancelledEvent(TaskEventBase):
    robot_id: IDType
    reason: str | None = None


@dataclasses.dataclass(frozen=True)
class TaskFailedEvent(TaskEventBase):
    robot_id: IDType
    reason: str
