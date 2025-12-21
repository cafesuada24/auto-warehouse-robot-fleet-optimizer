
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

@dataclasses.dataclass(frozen=True)
class RobotStateSnapshot:
    robot_id: IDType
    pos: Position
    state: RobotState
    battery: float
    assigned_task_id: IDType | None


@dataclass
class Robot:
    pos: Position
    state: RobotState = RobotState.IDLE
    battery: NonNegativeFloat = Field(le=1.0, default=1.0)
    id: IDType = dataclasses.field(default_factory=uuid4)
    assigned_task_id: IDType | None = None

    intent: RobotGoal | None = None
    max_speed_mps: NonNegativeFloat = 1.0
    arrive_eps_m: NonNegativeFloat = 0.05

    def snapshot(self) -> RobotStateSnapshot:
        """Produce an immutable snapshot for publishing."""
        return RobotStateSnapshot(
            robot_id=self.id,
            pos=self.pos,
            battery=self.battery,
            state=self.state,
            assigned_task_id=self.assigned_task_id,
        )
