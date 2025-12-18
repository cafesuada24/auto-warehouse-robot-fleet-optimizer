import dataclasses

from pydantic.dataclasses import dataclass

from app.types import IDType

from .map import Map
from .robot import Robot
from .task import Task


@dataclass
class World:
    map: Map
    robots: dict[IDType, Robot] = dataclasses.field(default_factory=dict)
    tasks: dict[IDType, Task] = dataclasses.field(default_factory=dict)
    time: float = 0.0
