from awrfo.types import IDType
from pydantic import Field, NonNegativeFloat, NonNegativeInt
from pydantic.dataclasses import dataclass


@dataclass
class RobotView:
    id: IDType
    pos: tuple[NonNegativeFloat, NonNegativeFloat]
    ts_ms: NonNegativeInt
    battery: float = Field(ge=0.0, le=1.0)
    assigned_task_id: IDType | None = None
