
import dataclasses
from enum import Enum
from uuid import uuid4

from awrfo.types import IDType
from pydantic import Field, NonNegativeFloat, NonNegativeInt
from pydantic.dataclasses import dataclass

from app.domain.types import Position

from .snapshot import Snapshot
from .task import TaskPhase


class RobotState(Enum):
    IDLE = 1
    MOVING = 2
    WAITING = 3
    PICKING = 4
    DROPPING = 5

class RobotGoalType(Enum):
    MOVE = 1
    WAIT = 2

@dataclass
class RobotGoal:
    type: RobotGoalType
    pos: Position | None = None
    wait_remaining_ms: NonNegativeInt | None = None

@dataclasses.dataclass(frozen=True)
class RobotStateSnapshot(Snapshot):
    robot_id: IDType
    pos: Position
    state: RobotState
    battery: float
    assigned_task_id: IDType | None
    task_phase: TaskPhase | None

@dataclass
class Robot:
    pos: Position
    state: RobotState = RobotState.IDLE
    battery: NonNegativeFloat = Field(le=1.0, default=1.0)
    id: IDType = dataclasses.field(default_factory=uuid4)

    assigned_task_id: IDType | None = None
    task_phase: TaskPhase | None = None
    intent: RobotGoal | None = None

    max_speed_mps: NonNegativeFloat = 1.0
    arrive_eps_m: NonNegativeFloat = 0.05

    def snapshot(self, timestamp_ms: NonNegativeInt) -> RobotStateSnapshot:
        """Produce an immutable snapshot for publishing."""
        return RobotStateSnapshot(
            robot_id=self.id,
            pos=self.pos,
            battery=self.battery,
            state=self.state,
            task_phase=self.task_phase,
            assigned_task_id=self.assigned_task_id,
            timestamp_ms=timestamp_ms,
        )
