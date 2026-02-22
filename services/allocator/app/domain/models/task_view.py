from dataclasses import field

from awrfo.types import IDType
from pydantic import NonNegativeFloat
from pydantic.dataclasses import dataclass
from pydantic.types import NonNegativeInt


@dataclass
class TaskView:
    id: IDType
    ts_ms: NonNegativeInt
    pickup: tuple[NonNegativeInt, NonNegativeInt]
    deadline_ms: NonNegativeInt
    blacklist_robot_ids: set[IDType] = field(default_factory=set)
    last_rejected_ts_s: NonNegativeFloat | None = None
    retry_count: NonNegativeInt = 0
