
import dataclasses
from enum import Enum
from uuid import uuid4

from pydantic.dataclasses import dataclass

from app.types import IDType
from app.world.types import Position


class TaskStatus(Enum):
    CREATED = 1
    ASSIGNED = 2
    PICKED = 3
    COMPLETED = 4

@dataclass
class Task:

    pickup: Position
    dropoff: Position

    status: TaskStatus

    id: IDType = dataclasses.field(default_factory=uuid4)


