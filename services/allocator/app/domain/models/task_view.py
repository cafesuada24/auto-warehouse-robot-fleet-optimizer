from awrfo.types import IDType
from pydantic.dataclasses import dataclass
from pydantic.types import NonNegativeInt

# class TaskStatus(Enum):
#     CREATED = 1
#     ASSIGNED = 2
#     EXECUTING = 3
#     COMPLETED = 4
#     FAILED = 5
#     CANCELLED = 6

@dataclass
class TaskView:
    id: IDType
    ts_ms: NonNegativeInt
    pickup: tuple[NonNegativeInt, NonNegativeInt]
    deadline_ms: NonNegativeInt
    # status: TaskStatus
