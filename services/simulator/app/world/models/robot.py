
import dataclasses
from enum import Enum
from uuid import uuid4

from pydantic import Field, NonNegativeFloat
from pydantic.dataclasses import dataclass

from app.types import IDType
from app.world.types import Position


class RobotState(Enum):
    IDLE = 1
    MOVING = 2
    WAITING = 3
    PICKING = 4
    DROPPING = 5

@dataclass
class RobotGoal:
    pos: Position | None = None
    wait_remaining: NonNegativeFloat | None = None

@dataclass
class Robot:
    pos: Position
    state: RobotState
    battery: float = Field(ge=0, le=1.0, default=1.0)
    id: IDType = dataclasses.field(default_factory=uuid4)

    intent: RobotGoal | None = None
